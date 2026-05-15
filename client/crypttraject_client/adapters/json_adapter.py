"""JSON / JSONL adapter.

Supports two layouts:
  * JSONL: one JSON object per line, each object = one record.
  * JSON array: a top-level list of objects, each object = one record.

The user declares which key holds the record id, and the rest of the
object is exposed as `record.payload` so any FeatureExtractor can pick
the fields it needs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

from .base import DataSourceAdapter, Record


@dataclass
class JSONAdapter(DataSourceAdapter):
    path: Path
    id_field: str
    jsonl: bool = False
    encoding: str = "utf-8"
    limit: Optional[int] = None
    # Internal cache for JSON-array mode: lets count() and iter_records()
    # share the single file load, avoiding a double parse.
    _array_cache: Optional[list] = field(default=None, repr=False, compare=False)

    def count(self) -> "int | None":
        if self.jsonl:
            # Counting lines would mean a full pass over the file just to
            # parse it again right after. Not worth it — stay indeterminate.
            return None
        data = self._load_array()
        total = len(data)
        if self.limit is not None:
            return min(total, self.limit)
        return total

    def _load_array(self) -> list:
        if self._array_cache is None:
            with open(self.path, encoding=self.encoding) as fh:
                data = json.load(fh)
            if not isinstance(data, list):
                raise ValueError(f"{self.path}: expected a top-level JSON array")
            self._array_cache = data
        return self._array_cache

    def iter_records(self) -> Iterator[Record]:
        if self.jsonl:
            yield from self._iter_jsonl()
        else:
            yield from self._iter_array()

    def _iter_jsonl(self) -> Iterator[Record]:
        count = 0
        with open(self.path, encoding=self.encoding) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                if self.limit is not None and count >= self.limit:
                    return
                obj = json.loads(line)
                rid = obj.get(self.id_field)
                if rid is None:
                    continue
                yield Record(record_id=str(rid), payload=obj)
                count += 1

    def _iter_array(self) -> Iterator[Record]:
        data = self._load_array()
        count = 0
        for obj in data:
            if self.limit is not None and count >= self.limit:
                return
            rid = obj.get(self.id_field)
            if rid is None:
                continue
            yield Record(record_id=str(rid), payload=obj)
            count += 1
