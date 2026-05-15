"""Binary codec for ciphertext-heavy payloads.

We avoid base64+JSON for ciphertext bundles because BFV ciphertexts are
large (tens to hundreds of kB each) and base64 inflates them by 33%. The
format below is a tiny length-prefixed packing scheme — much cheaper
than pickle and language-agnostic if we ever need a non-Python client.

Layout (all integers little-endian):
    magic        : 4 bytes  (b"CTJ1")
    n_entries    : uint32
    repeated n_entries times:
        key_len  : uint32
        key      : utf-8 bytes
        val_len  : uint32
        val      : raw bytes

For pair payloads the key is "id_a\\x00id_b" (NUL-separated).
"""

from __future__ import annotations

import struct
from typing import Dict, Iterable, Tuple

_MAGIC = b"CTJ1"
_HEADER = struct.Struct("<4sI")
_LEN = struct.Struct("<I")


def encode_blobs(entries: Iterable[Tuple[str, bytes]]) -> bytes:
    items = list(entries)
    parts = [_HEADER.pack(_MAGIC, len(items))]
    for key, val in items:
        kb = key.encode("utf-8")
        parts.append(_LEN.pack(len(kb)))
        parts.append(kb)
        parts.append(_LEN.pack(len(val)))
        parts.append(val)
    return b"".join(parts)


def decode_blobs(data: bytes) -> Dict[str, bytes]:
    magic, n = _HEADER.unpack_from(data, 0)
    if magic != _MAGIC:
        raise ValueError(f"bad magic: {magic!r}")
    offset = _HEADER.size
    out: Dict[str, bytes] = {}
    for _ in range(n):
        (kl,) = _LEN.unpack_from(data, offset); offset += _LEN.size
        key = data[offset:offset + kl].decode("utf-8"); offset += kl
        (vl,) = _LEN.unpack_from(data, offset); offset += _LEN.size
        val = bytes(data[offset:offset + vl]); offset += vl
        out[key] = val
    return out


_PAIR_SEP = "\x00"


def pair_key(a: str, b: str) -> str:
    return f"{a}{_PAIR_SEP}{b}"


def split_pair_key(key: str) -> Tuple[str, str]:
    a, b = key.split(_PAIR_SEP, 1)
    return a, b
