"""Server-side session storage.

A session bundles: public BFV context, public key, LSH parameters, and a
dictionary of received ciphertexts keyed by record id.

Storage here is in-memory for the prototype. A future iteration can swap
this for Redis / a database without changing the call sites.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional

from Pyfhel import Pyfhel, PyCtxt

from crypttraject_shared import SessionDescriptor, SignaturePayload


@dataclass
class ServerSession:
    descriptor: SessionDescriptor
    he: Pyfhel
    signatures: Dict[str, PyCtxt] = field(default_factory=dict)

    @classmethod
    def from_descriptor(cls, descriptor: SessionDescriptor) -> "ServerSession":
        he = Pyfhel()
        he.from_bytes_context(descriptor.context_bytes)
        he.from_bytes_public_key(descriptor.public_key_bytes)
        return cls(descriptor=descriptor, he=he)

    def ingest_signatures(self, payload: SignaturePayload) -> int:
        if payload.session_id != self.descriptor.session_id:
            raise ValueError("session_id mismatch")
        for sig in payload.signatures:
            ctxt = PyCtxt(pyfhel=self.he)
            ctxt.from_bytes(sig.ciphertext)
            self.signatures[sig.record_id] = ctxt
        return len(payload.signatures)


class SessionStore:
    """Tiny thread-safe registry of active sessions."""

    def __init__(self) -> None:
        self._sessions: Dict[str, ServerSession] = {}
        self._lock = Lock()

    def register(self, descriptor: SessionDescriptor) -> ServerSession:
        with self._lock:
            session = ServerSession.from_descriptor(descriptor)
            self._sessions[descriptor.session_id] = session
            return session

    def get(self, session_id: str) -> ServerSession:
        with self._lock:
            try:
                return self._sessions[session_id]
            except KeyError as exc:
                raise KeyError(f"unknown session_id: {session_id}") from exc

    def drop(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def find(self, session_id: str) -> Optional[ServerSession]:
        with self._lock:
            return self._sessions.get(session_id)
