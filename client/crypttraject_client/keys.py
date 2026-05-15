"""Client-side BFV session: parameters, key generation and local persistence.

Security invariant: the secret key produced here MUST stay on this machine.
The `to_session_descriptor()` method returns only public material safe to
upload to the server.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import uuid4

from Pyfhel import Pyfhel

from crypttraject_shared import BFVParams, DEFAULT_BFV_PARAMS, SessionDescriptor


@dataclass
class ClientSession:
    """Holds the BFV context + key pair + LSH parameters for one session."""

    he: Pyfhel
    params: BFVParams
    num_perm: int
    bands: int
    rows_per_band: int
    session_id: str

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def new(
        cls,
        num_perm: int = 128,
        bands: int = 16,
        rows_per_band: int = 8,
        params: BFVParams = DEFAULT_BFV_PARAMS,
        session_id: Optional[str] = None,
    ) -> "ClientSession":
        if bands * rows_per_band != num_perm:
            raise ValueError(
                f"bands ({bands}) * rows_per_band ({rows_per_band}) must equal num_perm ({num_perm})"
            )
        params.validate_num_perm(num_perm)

        he = Pyfhel()
        he.contextGen(scheme="bfv", n=params.n, t=params.t, sec=params.sec)
        he.keyGen()
        return cls(
            he=he,
            params=params,
            num_perm=num_perm,
            bands=bands,
            rows_per_band=rows_per_band,
            session_id=session_id or uuid4().hex,
        )

    @classmethod
    def load(cls, key_dir: Path) -> "ClientSession":
        meta = pickle.loads((key_dir / "session.meta.pkl").read_bytes())
        he = Pyfhel()
        he.from_bytes_context((key_dir / "context.pkl").read_bytes())
        he.from_bytes_public_key((key_dir / "public_key.pkl").read_bytes())
        he.from_bytes_secret_key((key_dir / "secret_key.pkl").read_bytes())
        return cls(
            he=he,
            params=BFVParams(**meta["params"]),
            num_perm=meta["num_perm"],
            bands=meta["bands"],
            rows_per_band=meta["rows_per_band"],
            session_id=meta["session_id"],
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, key_dir: Path) -> None:
        key_dir.mkdir(parents=True, exist_ok=True)
        (key_dir / "context.pkl").write_bytes(self.he.to_bytes_context())
        (key_dir / "public_key.pkl").write_bytes(self.he.to_bytes_public_key())
        (key_dir / "secret_key.pkl").write_bytes(self.he.to_bytes_secret_key())
        meta = {
            "session_id": self.session_id,
            "num_perm": self.num_perm,
            "bands": self.bands,
            "rows_per_band": self.rows_per_band,
            "params": {"n": self.params.n, "t": self.params.t, "sec": self.params.sec},
        }
        (key_dir / "session.meta.pkl").write_bytes(pickle.dumps(meta))

    # ------------------------------------------------------------------
    # Server-facing material
    # ------------------------------------------------------------------

    def to_session_descriptor(self) -> SessionDescriptor:
        """Return only what is safe to share with the server. Never the secret key."""
        return SessionDescriptor(
            session_id=self.session_id,
            context_bytes=self.he.to_bytes_context(),
            public_key_bytes=self.he.to_bytes_public_key(),
            num_perm=self.num_perm,
            bands=self.bands,
            rows_per_band=self.rows_per_band,
        )
