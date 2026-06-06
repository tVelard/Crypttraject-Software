"""Background workers.

BFV encryption and HTTP I/O are slow enough to freeze the UI for several
seconds. Each long-running operation runs in its own QThread and emits
progress + result signals back to the main thread. The screens never call
these operations synchronously.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from ..adapters import GeoHashExtractor, PLTGeolifeAdapter
from ..decrypt import build_clusters
from ..keys import ClientSession
from ..minhash import compute_minhash
from .state import AppState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_adapter(state: AppState):
    return PLTGeolifeAdapter(dataset_dir=state.source_path, limit=state.limit)


def _make_extractor(state: AppState):
    return GeoHashExtractor(points_field="points", precision=state.geohash_precision)


def _extract_points(record) -> List[Tuple[float, float]]:
    """Pull raw (lat, lon) pairs from a record payload, if any.

    Used purely for the local map view. Returns [] when a record carries no
    usable coordinates, in which case the UI falls back to a table.
    """
    raw = record.payload.get("points")
    if not raw:
        return []
    pts: List[Tuple[float, float]] = []
    for p in raw:
        try:
            lat, lon = float(p[0]), float(p[1])
        except (TypeError, ValueError, IndexError):
            continue
        pts.append((lat, lon))
    return pts


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------

class _BaseWorker(QObject):
    # current, total (0 = unknown / indeterminate), message
    progress = Signal(int, int, str)
    log = Signal(str)
    failed = Signal(str)
    finished = Signal()


# How often to emit a `progress` signal while iterating records.
# Throttling matters: emitting on every record floods the GUI thread on
# large datasets, while emitting too rarely makes the bar look stuck.
_PROGRESS_EVERY = 10


class IngestWorker(_BaseWorker):
    """Parse the data source, compute MinHash signatures, keep raw points.

    Unlike the CLI (which only needs signatures), the GUI also retains the
    raw lat/lon points per record so the map can draw the trajectories
    coloured by cluster. The points stay on this machine.
    """

    # {record_id: signature}, {record_id: [(lat, lon), ...]}
    done = Signal(dict, dict)

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state

    def run(self):
        try:
            adapter = _make_adapter(self.state)
            extractor = _make_extractor(self.state)

            # Ask the adapter for its total upfront. If it can answer cheaply
            # (PLT directory glob, JSON-array len), we get a determinate bar;
            # otherwise total stays 0 and the GUI falls back to indeterminate.
            try:
                total = adapter.count() or 0
            except Exception as exc:   # noqa: BLE001
                self.log.emit(f"[warn] adapter.count() failed: {exc}")
                total = 0
            if total:
                self.log.emit(f"Source contains ~{total} records.")

            sigs: Dict[str, np.ndarray] = {}
            points: Dict[str, List[Tuple[float, float]]] = {}
            self.progress.emit(0, total, "Starting...")

            # Iterate records directly (instead of iter_features) so we can
            # capture both the feature tokens AND the raw points in one pass.
            for record in adapter.iter_records():
                tokens = extractor.extract(record)
                if not tokens:
                    continue
                sigs[record.record_id] = compute_minhash(tokens, num_perm=self.state.num_perm)
                pts = _extract_points(record)
                if pts:
                    points[record.record_id] = pts
                n = len(sigs)
                if n == 1 or n % _PROGRESS_EVERY == 0:
                    self.progress.emit(n, total, f"Hashed {n}" + (f"/{total}" if total else "") + " records")

            self.progress.emit(len(sigs), total, "Hashing complete")
            self.log.emit(
                f"Computed {len(sigs)} MinHash signatures "
                f"({len(points)} with coordinates)."
            )
            self.done.emit(sigs, points)
        except Exception as exc:   # noqa: BLE001
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self.finished.emit()


class EncryptUploadWorker(_BaseWorker):
    """Generate keys (if needed), encrypt locally, upload to the server."""

    done = Signal(str)   # session_id

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state

    def run(self):
        try:
            if self.state.key_dir and Path(self.state.key_dir).exists() \
                    and (Path(self.state.key_dir) / "session.meta.pkl").exists():
                self.log.emit(f"Loading existing BFV keys from {self.state.key_dir}.")
                session = ClientSession.load(Path(self.state.key_dir))
            else:
                self.log.emit("Generating fresh BFV key pair locally...")
                session = ClientSession.new(
                    num_perm=self.state.num_perm,
                    bands=self.state.bands,
                    rows_per_band=self.state.rows_per_band,
                )
                if self.state.key_dir:
                    session.save(Path(self.state.key_dir))
                    self.log.emit(f"Saved session to {self.state.key_dir}.")
            self.state.session = session

            from ..http_client import ServerClient
            server = ServerClient(
                base_url=self.state.server_url.rstrip("/"),
                timeout=self.state.server_timeout,
            )

            self.log.emit("Registering session on the server (public material only)...")
            server.create_session(session)

            self.log.emit(f"Encrypting and uploading {len(self.state.signatures)} signatures...")
            ingested = server.upload_signatures(session, self.state.signatures)
            self.log.emit(f"Server ingested {ingested} ciphertexts.")
            self.done.emit(session.session_id)
        except Exception as exc:   # noqa: BLE001
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self.finished.emit()


class ClusterWorker(_BaseWorker):
    """Trigger the server cluster job, fetch ciphertexts, decrypt locally."""

    done = Signal(dict)   # {record_id: cluster_index}

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state

    def run(self):
        try:
            if self.state.session is None:
                raise RuntimeError("no active client session — re-run the encryption step")

            from ..http_client import ServerClient
            server = ServerClient(
                base_url=self.state.server_url.rstrip("/"),
                timeout=self.state.server_timeout,
            )

            self.log.emit(f"Asking server to compute pair ciphertexts (threshold={self.state.threshold:.2f})...")
            result = server.run_cluster(self.state.session, threshold=self.state.threshold)
            self.log.emit(f"Server returned {len(result.pair_ciphertexts)} pair ciphertexts.")

            self.log.emit("Decrypting and clustering locally...")
            clusters = build_clusters(
                self.state.session,
                result,
                all_record_ids=list(self.state.signatures.keys()),
                threshold=self.state.threshold,
            )
            n_clusters = len(set(clusters.values()))
            self.log.emit(f"Recovered {n_clusters} clusters across {len(clusters)} records.")
            self.done.emit(clusters)

            try:
                server.drop_session(self.state.session)
            except Exception:   # noqa: BLE001
                pass
        except Exception as exc:   # noqa: BLE001
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self.finished.emit()


def run_in_thread(worker: _BaseWorker) -> QThread:
    """Move `worker` to a fresh QThread, hook lifecycle, start it. Returns
    the thread so the caller can keep a reference (preventing GC)."""
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread
