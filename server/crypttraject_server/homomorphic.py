"""Homomorphic operations run on the server side.

What the server CAN do (no secret key):
  * ciphertext +/- ciphertext   (free, no noise growth worth mentioning)
  * ciphertext * ciphertext     (one multiplication, ~17 bits of noise)
  * ciphertext * plaintext      (free of noise)

What the server CANNOT do:
  * decide whether a ciphertext encrypts 0   (needs the secret key)
  * compare ciphertexts                       (needs the secret key)

The Jaccard pipeline we use is:
    diff    = enc(sig_A) - enc(sig_B)
    diff_sq = diff * diff
    --> return diff_sq to the client; the client decrypts and counts zeros.

LSH note: a band-LSH that operates purely on ciphertexts requires either
zero-testing (impossible without sk) or an interactive protocol with the
client. In this MVP we emit ALL pairs as candidates so the protocol stays
non-interactive end-to-end. A future iteration can add a one-round LSH
exchange where the client returns encrypted equality bits per band.
"""

from itertools import combinations
from typing import Dict, Iterable, List, Tuple

from Pyfhel import PyCtxt

from .session import ServerSession


PairId = Tuple[str, str]


def compute_pair_diff_sq(
    session: ServerSession, id_a: str, id_b: str
) -> bytes:
    ctxt_a = session.signatures[id_a]
    ctxt_b = session.signatures[id_b]
    diff = ctxt_a - ctxt_b
    diff_sq = diff * diff
    return diff_sq.to_bytes()


def _enumerate_pairs(record_ids: Iterable[str]) -> List[PairId]:
    ids = list(record_ids)
    return [(min(a, b), max(a, b)) for a, b in combinations(ids, 2)]


def run_pair_pipeline(session: ServerSession) -> Dict[PairId, bytes]:
    """Produce diff_sq ciphertexts for every pair currently in the session."""
    pairs = _enumerate_pairs(session.signatures.keys())
    return {pair: compute_pair_diff_sq(session, *pair) for pair in pairs}
