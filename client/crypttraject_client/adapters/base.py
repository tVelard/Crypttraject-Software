"""Adapter and feature-extractor base interfaces.

`DataSourceAdapter` yields `Record`s (one per logical entity to cluster).
`FeatureExtractor` turns a record into a set of feature tokens that
MinHash will hash. Splitting the two means a CSV adapter can be paired
with either a geohash extractor (lat/lon columns) or a token extractor
(text columns) without writing two adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, Set


@dataclass
class Record:
    record_id: str
    payload: Dict[str, Any] = field(default_factory=dict)


class FeatureExtractor(ABC):
    @abstractmethod
    def extract(self, record: Record) -> Set[bytes]:
        """Return the (deduplicated) bytes tokens to feed MinHash."""


class DataSourceAdapter(ABC):
    @abstractmethod
    def iter_records(self) -> Iterator[Record]:
        ...

    def count(self) -> "int | None":
        """Return the total number of records if cheaply computable, else None.

        Used by the GUI to decide between a determinate progress bar and an
        indeterminate one. Subclasses override only when counting is cheap
        (a single directory listing, a `len()` on an already-loaded array...).
        Implementations MUST honor the `limit` if the adapter has one.
        """
        return None

    def iter_features(self, extractor: FeatureExtractor) -> Iterable[tuple]:
        for record in self.iter_records():
            tokens = extractor.extract(record)
            if tokens:
                yield record.record_id, tokens
