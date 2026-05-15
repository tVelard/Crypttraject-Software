"""Shared primitives between CryptTraject client and server.

This package MUST NOT depend on any client-side secret material
(no secret key handling) nor on any server-side state (no DB, no API).
It only exposes BFV parameters, serialization helpers and the wire
format used between client and server.
"""

from .bfv_params import BFVParams, DEFAULT_BFV_PARAMS, BFV_T
from .wire import (
    SessionDescriptor,
    EncryptedSignature,
    SignaturePayload,
    SimilarityRequest,
    SimilarityResult,
)
from .codec import encode_blobs, decode_blobs, pair_key, split_pair_key

__all__ = [
    "BFVParams",
    "DEFAULT_BFV_PARAMS",
    "BFV_T",
    "SessionDescriptor",
    "EncryptedSignature",
    "SignaturePayload",
    "SimilarityRequest",
    "SimilarityResult",
    "encode_blobs",
    "decode_blobs",
    "pair_key",
    "split_pair_key",
]
