"""Concrete feature extractors.

GeoHashExtractor — for records carrying a list of (lat, lon) points.
"""

from dataclasses import dataclass
from typing import Set

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
