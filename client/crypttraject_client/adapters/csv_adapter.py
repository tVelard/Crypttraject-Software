"""CSV adapter.

Two common shapes are supported:

  (a) "flat records": one row = one record. The user picks an id column.
  (b) "grouped points": many rows per record (lat, lon, ...) grouped by
      an id column, useful for trajectories stored as CSV.

The mapping is declared via constructor arguments so the same adapter
works for very different schemas.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from .base import DataSourceAdapter, Record


@dataclass
class CSVAdapter(DataSourceAdapter):
    path: Path
    id_column: str
    # If point_columns is set, rows are grouped by id_column and accumulated
    # under record.payload["points"] as a list of tuples.
    point_columns: Optional[List[str]] = None  # e.g. ["lat", "lon"]
    # Otherwise, the whole row is exposed as record.payload.
    delimiter: str = ","
    encoding: str = "utf-8"
    limit: Optional[int] = None

    def iter_records(self) -> Iterator[Record]:
        if self.point_columns:
            yield from self._iter_grouped()
        else:
            yield from self._iter_flat()

    # ------------------------------------------------------------------

    def _iter_flat(self) -> Iterator[Record]:
        count = 0
        with open(self.path, encoding=self.encoding, newline="") as fh:
            reader = csv.DictReader(fh, delimiter=self.delimiter)
            for row in reader:
                if self.limit is not None and count >= self.limit:
                    return
                rid = row.get(self.id_column)
                if not rid:
                    continue
                yield Record(record_id=str(rid), payload=dict(row))
                count += 1

    def _iter_grouped(self) -> Iterator[Record]:
        assert self.point_columns is not None
        buckets: Dict[str, List[tuple]] = {}
        with open(self.path, encoding=self.encoding, newline="") as fh:
            reader = csv.DictReader(fh, delimiter=self.delimiter)
            for row in reader:
                rid = row.get(self.id_column)
                if not rid:
                    continue
                try:
                    point = tuple(float(row[c]) for c in self.point_columns)
                except (KeyError, ValueError):
                    continue
                buckets.setdefault(str(rid), []).append(point)
        count = 0
        for rid, points in buckets.items():
            if self.limit is not None and count >= self.limit:
                return
            yield Record(record_id=rid, payload={"points": points})
            count += 1
