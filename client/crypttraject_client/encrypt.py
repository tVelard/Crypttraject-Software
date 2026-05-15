"""Encrypt MinHash signatures into BFV ciphertexts ready to upload."""

from typing import Dict, List

import numpy as np

from crypttraject_shared import BFV_T, EncryptedSignature, SignaturePayload

from .keys import ClientSession


def encrypt_signature(session: ClientSession, hashvalues: np.ndarray) -> bytes:
    reduced = (hashvalues % BFV_T).astype(np.int64)
    return session.he.encryptInt(reduced).to_bytes()


def encrypt_signatures(
    session: ClientSession, signatures: Dict[str, np.ndarray]
) -> SignaturePayload:
    encrypted: List[EncryptedSignature] = [
        EncryptedSignature(record_id=rid, ciphertext=encrypt_signature(session, sig))
        for rid, sig in signatures.items()
    ]
    return SignaturePayload(session_id=session.session_id, signatures=encrypted)
