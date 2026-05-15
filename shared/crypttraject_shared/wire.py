"""Wire format exchanged between the client and the server.

These dataclasses are deliberately serialization-agnostic: they describe
the logical payload. The HTTP layer (FastAPI) is responsible for the
actual encoding (multipart for raw bytes, JSON for metadata).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class SessionDescriptor:
    """Public material the client uploads once at session creation.

    The secret key is NEVER part of this descriptor.
    """
    session_id: str
    context_bytes: bytes
    public_key_bytes: bytes
    num_perm: int
    bands: int
    rows_per_band: int


@dataclass
class EncryptedSignature:
    record_id: str
    ciphertext: bytes


@dataclass
class SignaturePayload:
    session_id: str
    signatures: List[EncryptedSignature] = field(default_factory=list)


@dataclass
class SimilarityRequest:
    session_id: str
    threshold: float


@dataclass
class SimilarityResult:
    """Server output. Pair similarities are returned as raw ciphertexts of
    the squared-difference vector; the client decrypts and counts zeros to
    recover the Jaccard score. Cluster assignment is then computed
    client-side from those scores.
    """
    session_id: str
    candidate_pairs: List[Tuple[str, str]]
    pair_ciphertexts: Dict[Tuple[str, str], bytes]
