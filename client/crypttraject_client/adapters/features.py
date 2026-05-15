"""Concrete feature extractors.

GeoHashExtractor   — for records carrying a list of (lat, lon) points.
FieldTokenExtractor — for records carrying free-form text fields.
"""

from dataclasses import dataclass, field
from typing import List, Set

import pygeohash as pgh

from .base import FeatureExtractor, Record


@dataclass
class GeoHashExtractor(FeatureExtractor):
    points_field: str = "points"
    precision: int = 6

    def extract(self, record: Record) -> Set[bytes]:
        points = record.payload.get(self.points_field) or []
        cells: Set[bytes] = set()
        for lat, lon in points:
            try:
                cells.add(pgh.encode(float(lat), float(lon), precision=self.precision).encode("utf-8"))
            except Exception:
                continue
        return cells


@dataclass
class FieldTokenExtractor(FeatureExtractor):
    """Tokenize selected text fields on whitespace, lowercased.

    Good default for CSV/JSON records where you cluster on a few text
    columns (e.g. an item description, a tag list).
    """

    fields: List[str] = field(default_factory=list)

    def extract(self, record: Record) -> Set[bytes]:
        tokens: Set[bytes] = set()
        for f in self.fields:
            value = record.payload.get(f)
            if value is None:
                continue
            for tok in str(value).lower().split():
                if tok:
                    tokens.add(tok.encode("utf-8"))
        return tokens
