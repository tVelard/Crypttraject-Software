"""End-to-end client CLI.

Wires together: adapter -> feature extractor -> MinHash -> BFV encrypt
-> HTTP upload -> server cluster -> decrypt -> Union-Find clusters.

Example:
    # Geolife .plt directory
    python -m crypttraject_client.cli \\
        --path "dataset/Geolife Trajectories 1.3/Data" \\
        --limit 50 \\
        --server http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict

import numpy as np

from .adapters import GeoHashExtractor, PLTGeolifeAdapter
from .decrypt import build_clusters
from .keys import ClientSession
from .minhash import compute_minhash


log = logging.getLogger("crypttraject.cli")


def _build_adapter(args):
    return PLTGeolifeAdapter(dataset_dir=Path(args.path), limit=args.limit)


def _build_extractor(args):
    return GeoHashExtractor(points_field="points", precision=args.geohash_precision)


def main() -> int:
    parser = argparse.ArgumentParser(description="CryptTraject end-to-end client.")
    parser.add_argument("--path", required=True, help="Geolife .plt directory")
    parser.add_argument("--geohash-precision", type=int, default=6)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--num-perm", type=int, default=128)
    parser.add_argument("--bands", type=int, default=16)
    parser.add_argument("--rows-per-band", type=int, default=8)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--server", required=True, help="Server base URL, e.g. http://localhost:8000")
    parser.add_argument("--timeout", type=float, default=600.0, help="HTTP timeout in seconds (cluster step is O(n^2))")
    parser.add_argument("--key-dir", default=None, help="Persist/reuse a BFV session from this directory")
    parser.add_argument("--output", default="-", help="Write cluster JSON here, or '-' for stdout")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    # 1. Parse + features
    adapter = _build_adapter(args)
    extractor = _build_extractor(args)

    signatures: Dict[str, np.ndarray] = {}
    for rid, tokens in adapter.iter_features(extractor):
        signatures[rid] = compute_minhash(tokens, num_perm=args.num_perm)
    log.info("Computed %d MinHash signatures locally.", len(signatures))
    if len(signatures) < 2:
        log.error("Need at least 2 records to cluster.")
        return 1

    # 2. Key session (new or reuse)
    if args.key_dir and Path(args.key_dir).exists():
        session = ClientSession.load(Path(args.key_dir))
        log.info("Reusing BFV session %s from %s.", session.session_id, args.key_dir)
    else:
        session = ClientSession.new(
            num_perm=args.num_perm,
            bands=args.bands,
            rows_per_band=args.rows_per_band,
        )
        if args.key_dir:
            session.save(Path(args.key_dir))
        log.info("Created BFV session %s.", session.session_id)

    # 3. HTTP: create session, upload sigs, run cluster, fetch results
    from .http_client import ServerClient  # local import to keep `requests` optional

    server = ServerClient(base_url=args.server.rstrip("/"), timeout=args.timeout)
    sid = server.create_session(session)
    log.info("Server session ready: %s", sid)

    ingested = server.upload_signatures(session, signatures)
    log.info("Uploaded %d encrypted signatures.", ingested)

    result = server.run_cluster(session, threshold=args.threshold)
    log.info("Server returned %d pair ciphertexts.", len(result.pair_ciphertexts))

    # 4. Decrypt + cluster locally
    clusters = build_clusters(
        session,
        result,
        all_record_ids=list(signatures.keys()),
        threshold=args.threshold,
    )
    n_clusters = len(set(clusters.values()))
    log.info("Recovered %d clusters across %d records.", n_clusters, len(clusters))

    server.drop_session(session)

    payload = json.dumps({"n_clusters": n_clusters, "clusters": clusters}, indent=2)
    if args.output == "-":
        sys.stdout.write(payload + "\n")
    else:
        Path(args.output).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
