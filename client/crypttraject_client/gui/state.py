"""Shared state passed between the GUI screens.

A single mutable container is simpler than threading parameters through
constructors and signals when every screen only touches a couple of fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..keys import ClientSession


@dataclass
class AppState:
    # ---- source: a Geolife .plt trajectory directory ----
    source_path: Optional[Path] = None
    geohash_precision: int = 6
    limit: Optional[int] = 50

    # ---- BFV / LSH ----
    num_perm: int = 128
    bands: int = 16
    rows_per_band: int = 8
    threshold: float = 0.5

    # ---- server ----
    server_url: str = "https://crypttraject.rezel.net/api"
    # HTTP timeout (seconds). The /cluster step is O(n^2) and CPU-heavy on the
    # server, so this is generous; raise it further for very large runs.
    server_timeout: float = 600.0
    key_dir: Optional[Path] = None

    # ---- runtime artifacts ----
    signatures: Dict[str, np.ndarray] = field(default_factory=dict)
    # Raw geographic points per record, kept ONLY for local visualization.
    # These never leave the machine (the server only ever sees ciphertexts).
    record_points: Dict[str, List[Tuple[float, float]]] = field(default_factory=dict)
    session: Optional[ClientSession] = None
    clusters: Dict[str, int] = field(default_factory=dict)

    def reset_run(self) -> None:
        """Clear artifacts from a previous run, keep the configuration."""
        self.signatures = {}
        self.record_points = {}
        self.session = None
        self.clusters = {}

    def has_geo(self) -> bool:
        """True when at least one record carries plottable coordinates."""
        return any(self.record_points.values())
