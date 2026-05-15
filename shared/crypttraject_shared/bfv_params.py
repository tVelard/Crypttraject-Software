"""BFV scheme parameters shared by client and server.

The plaintext modulus t = 65537 is a Fermat prime (2^16 + 1) that is
NTT-friendly and large enough to hold MinHash values reduced mod t while
preserving strict equality (so Jaccard estimation via diff^2 == 0 stays
exact). n = 4096 yields 2048 batching slots, more than enough for the
default 128 MinHash permutations.
"""

from dataclasses import dataclass

BFV_T = 65537


@dataclass(frozen=True)
class BFVParams:
    n: int = 4096
    t: int = BFV_T
    sec: int = 128

    def validate_num_perm(self, num_perm: int) -> None:
        if num_perm > self.n // 2:
            raise ValueError(
                f"num_perm={num_perm} exceeds available BFV batching slots "
                f"({self.n // 2}). Increase n or reduce num_perm."
            )


DEFAULT_BFV_PARAMS = BFVParams()
