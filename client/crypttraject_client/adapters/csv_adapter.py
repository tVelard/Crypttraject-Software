"""CSV trajectory adapter.

Supports:
  - One trajectory per file (lat/lon columns, optional header).
  - Many trajectories per file when an id column is present
    (id, trajectory_id, traj_id, record_id, …).
  - A directory of .csv files (one trajectory per file).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from .base import DataSourceAdapter, Record
from .points import Point, dedupe_consecutive

_LAT_NAMES = frozenset({"lat", "latitude", "y"})
_LON_NAMES = frozenset({"lon", "lng", "long", "longitude", "x"})
_ID_NAMES = frozenset({"id", "trajectory_id", "traj_id", "record_id", "track_id", "name"})


def _norm(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _detect_columns(fieldnames: List[str]) -> tuple[str | None, str, str]:
    norm = {_norm(h): h for h in fieldnames}
    lat_col = next((norm[k] for k in _LAT_NAMES if k in norm), None)
    lon_col = next((norm[k] for k in _LON_NAMES if k in norm), None)
    id_col = next((norm[k] for k in _ID_NAMES if k in norm), None)
    if lat_col is None or lon_col is None:
        raise ValueError(
            f"CSV must include latitude/longitude columns; got {fieldnames!r}"
        )
    return id_col, lat_col, lon_col


def _parse_csv_file(path: Path) -> List[tuple[str, List[Point]]]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            return []
        id_col, lat_col, lon_col = _detect_columns(list(reader.fieldnames))

        grouped: Dict[str, List[Point]] = {}
        for row in reader:
            try:
                lat = float(row[lat_col])
                lon = float(row[lon_col])
            except (KeyError, TypeError, ValueError):
                continue
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                continue
            rid = row[id_col].strip() if id_col and row.get(id_col) else path.stem
            grouped.setdefault(rid, []).append((lat, lon))

    return [(rid, dedupe_consecutive(pts)) for rid, pts in grouped.items() if pts]


@dataclass
class CsvAdapter(DataSourceAdapter):
    source_path: Path
    limit: Optional[int] = None

    def _csv_files(self) -> List[Path]:
        if self.source_path.is_file():
            return [self.source_path] if self.source_path.suffix.lower() == ".csv" else []
        return sorted(self.source_path.rglob("*.csv"))

    def count(self) -> int | None:
        if not self.source_path.exists():
            return 0
        total = 0
        for csv_file in self._csv_files():
            total += len(_parse_csv_file(csv_file))
            if self.limit is not None and total >= self.limit:
                return self.limit
        return total

    def iter_records(self) -> Iterator[Record]:
        if not self.source_path.exists():
            raise FileNotFoundError(self.source_path)

        count = 0
        for csv_file in self._csv_files():
            for record_id, points in _parse_csv_file(csv_file):
                if self.limit is not None and count >= self.limit:
                    return
                yield Record(
                    record_id=f"{csv_file.name}/{record_id}",
                    payload={"points": points},
                )
                count += 1
