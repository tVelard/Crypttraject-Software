"""Thin HTTP client wrapping the server API.

Uses `requests` to keep dependencies minimal and the client packageable
with PyInstaller without extra complications.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Tuple

import requests

from crypttraject_shared import (
    SimilarityResult,
    decode_blobs,
    encode_blobs,
    pair_key,
    split_pair_key,
)

from .encrypt import encrypt_signatures
from .keys import ClientSession


@dataclass
class ServerClient:
    base_url: str
    # The /cluster step runs an O(n^2) homomorphic pipeline on the server and
    # can take several minutes for a few dozen trajectories. Keep a generous
    # default so the client doesn't give up before the server is done.
    timeout: float = 600.0

    # ------------------------------------------------------------------

    def create_session(self, session: ClientSession) -> str:
        descriptor = session.to_session_descriptor()
        config = {
            "num_perm": session.num_perm,
            "bands": session.bands,
            "rows_per_band": session.rows_per_band,
            "session_id": session.session_id,
        }
        files = {
            "context": ("context.bin", descriptor.context_bytes, "application/octet-stream"),
            "public_key": ("public_key.bin", descriptor.public_key_bytes, "application/octet-stream"),
        }
        data = {"config": json.dumps(config)}
        r = requests.post(
            f"{self.base_url}/session",
            files=files,
            data=data,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["session_id"]

    # ------------------------------------------------------------------

    def upload_signatures(self, session: ClientSession, signatures) -> int:
        payload = encrypt_signatures(session, signatures)
        blob = encode_blobs((sig.record_id, sig.ciphertext) for sig in payload.signatures)
        files = {"blob": ("sigs.bin", blob, "application/octet-stream")}
        r = requests.post(
            f"{self.base_url}/session/{session.session_id}/signatures",
            files=files,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["ingested"]

    # ------------------------------------------------------------------

    def run_cluster(self, session: ClientSession, threshold: float = 0.5) -> SimilarityResult:
        r = requests.post(
            f"{self.base_url}/session/{session.session_id}/cluster",
            json={"threshold": threshold},
            timeout=self.timeout,
        )
        r.raise_for_status()
        info = r.json()
        job_id = info["job_id"]

        r = requests.get(
            f"{self.base_url}/session/{session.session_id}/results/{job_id}",
            timeout=self.timeout,
        )
        r.raise_for_status()
        entries = decode_blobs(r.content)
        pair_cts: Dict[Tuple[str, str], bytes] = {}
        pairs: List[Tuple[str, str]] = []
        for k, ct in entries.items():
            pair = split_pair_key(k)
            pair_cts[pair] = ct
            pairs.append(pair)
        return SimilarityResult(
            session_id=session.session_id,
            candidate_pairs=pairs,
            pair_ciphertexts=pair_cts,
        )

    # ------------------------------------------------------------------

    def drop_session(self, session: ClientSession) -> None:
        requests.delete(
            f"{self.base_url}/session/{session.session_id}",
            timeout=self.timeout,
        )
