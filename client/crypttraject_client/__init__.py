"""CryptTraject client-side library.

Responsibilities (and ONLY these):
  * Parse a local Geolife .plt trajectory directory via an adapter.
  * Compute MinHash signatures locally.
  * Generate / persist a BFV key pair locally.
  * Encrypt signatures and prepare the SessionDescriptor + SignaturePayload
    to upload to the server.
  * Decrypt the squared-difference ciphertexts returned by the server and
    recover Jaccard scores + clusters.

The server-side code MUST NOT import anything from this package, and this
package MUST NOT import anything from `crypttraject_server`. The secret
key lives exclusively here.
"""

from .keys import ClientSession
from .minhash import compute_minhash
from .encrypt import encrypt_signature, encrypt_signatures
from .decrypt import jaccard_from_diff_sq, build_clusters

__all__ = [
    "ClientSession",
    "compute_minhash",
    "encrypt_signature",
    "encrypt_signatures",
    "jaccard_from_diff_sq",
    "build_clusters",
]


def get_http_client():
    """Lazy import so the lib is usable without `requests` installed."""
    from .http_client import ServerClient
    return ServerClient
