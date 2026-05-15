"""CryptTraject server-side library.

This package only knows about PUBLIC BFV material (context + public key)
and ciphertexts. It must never receive, touch, or persist a secret key.

The homomorphic pipeline implemented here:
  1. Accept a SessionDescriptor (public key + LSH params).
  2. Accept encrypted MinHash signatures.
  3. For every candidate pair found by LSH, compute the encrypted squared
     difference (sig_A - sig_B) ** 2 and return those ciphertexts to the
     client. The client decrypts them locally and assembles clusters.
"""

from .session import SessionStore, ServerSession
from .homomorphic import compute_pair_diff_sq, run_pair_pipeline

__all__ = [
    "SessionStore",
    "ServerSession",
    "compute_pair_diff_sq",
    "run_pair_pipeline",
]


def get_app():
    """Lazy import so the package is usable without FastAPI installed."""
    from .api import app
    return app
