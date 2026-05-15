"""Decrypt server results and assemble final clusters.

The server returns, for each candidate pair (A, B), the ciphertext of
(sig_A - sig_B) ** 2. We decrypt locally and count slots equal to 0 to
recover the Jaccard estimate.
"""

from typing import Dict, List, Tuple

import numpy as np
from Pyfhel import PyCtxt

from crypttraject_shared import SimilarityResult

from .keys import ClientSession


def jaccard_from_diff_sq(
    session: ClientSession, diff_sq_ciphertext: bytes
) -> float:
    ctxt = PyCtxt(pyfhel=session.he)
    ctxt.from_bytes(diff_sq_ciphertext)
    values = session.he.decryptInt(ctxt)
    return float(np.sum(values[: session.num_perm] == 0)) / session.num_perm


class _UnionFind:
    def __init__(self, elements: List[str]) -> None:
        self.parent = {e: e for e in elements}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: str, y: str) -> None:
        self.parent[self.find(x)] = self.find(y)


def build_clusters(
    session: ClientSession,
    result: SimilarityResult,
    all_record_ids: List[str],
    threshold: float,
) -> Dict[str, int]:
    """Decrypt every pair ciphertext, threshold, and assign cluster labels."""
    uf = _UnionFind(all_record_ids)
    for pair, ctxt_bytes in result.pair_ciphertexts.items():
        if jaccard_from_diff_sq(session, ctxt_bytes) >= threshold:
            uf.union(*pair)

    root_to_label: Dict[str, int] = {}
    clusters: Dict[str, int] = {}
    for rid in all_record_ids:
        root = uf.find(rid)
        if root not in root_to_label:
            root_to_label[root] = len(root_to_label)
        clusters[rid] = root_to_label[root]
    return clusters
