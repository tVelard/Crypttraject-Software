"""MinHash signature computation. Pure local operation, no FHE involved."""

from typing import Iterable

import numpy as np
from datasketch import MinHash


def compute_minhash(features: Iterable[bytes], num_perm: int = 128) -> np.ndarray:
    """Hash an iterable of feature tokens into a MinHash signature.

    Caller is responsible for turning a record into a deduplicated set of
    `bytes` tokens (geohash cells, n-grams, normalized terms, ...). The
    adapter layer handles that domain-specific work.
    """
    m = MinHash(num_perm=num_perm)
    for tok in features:
        m.update(tok)
    return m.hashvalues.copy()
