"""GPX trajectory adapter (.gpx files or directories thereof)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional

from .base import DataSourceAdapter, Record
from .points import Point, dedupe_consecutive


def _local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_gpx_file(path: Path) -> List[tuple[str, List[Point]]]:
    """Return (record_id, points) pairs found in one GPX file."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []

    records: List[tuple[str, List[Point]]] = []
    trk_index = 0
    for elem in root.iter():
        if _local_tag(elem.tag) != "trk":
            continue
        trk_index += 1
        name_elem = next((c for c in elem if _local_tag(c.tag) == "name"), None)
        trk_name = (name_elem.text or "").strip() if name_elem is not None else ""
        record_id = f"{path.stem}/{trk_name}" if trk_name else f"{path.stem}/trk{trk_index}"

        points: List[Point] = []
        for pt_elem in elem.iter():
            tag = _local_tag(pt_elem.tag)
            if tag not in ("trkpt", "rtept", "wpt"):
                continue
            try:
                lat = float(pt_elem.attrib["lat"])
                lon = float(pt_elem.attrib["lon"])
            except (KeyError, ValueError):
                continue
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                points.append((lat, lon))

        points = dedupe_consecutive(points)
        if points:
            records.append((record_id, points))

    # Fallback: file with route points but no <trk> wrapper.
    if not records:
        points = []
        for pt_elem in root.iter():
            if _local_tag(pt_elem.tag) not in ("trkpt", "rtept"):
                continue
            try:
                lat = float(pt_elem.attrib["lat"])
                lon = float(pt_elem.attrib["lon"])
            except (KeyError, ValueError):
                continue
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                points.append((lat, lon))
        points = dedupe_consecutive(points)
        if points:
            records.append((path.stem, points))

    return records


@dataclass
class GpxAdapter(DataSourceAdapter):
    source_path: Path
    limit: Optional[int] = None

    def _gpx_files(self) -> List[Path]:
        if self.source_path.is_file():
            return [self.source_path] if self.source_path.suffix.lower() == ".gpx" else []
        return sorted(self.source_path.rglob("*.gpx"))

    def count(self) -> int | None:
        if not self.source_path.exists():
            return 0
        total = 0
        for gpx in self._gpx_files():
            total += len(_parse_gpx_file(gpx))
            if self.limit is not None and total >= self.limit:
                return self.limit
        return total

    def iter_records(self) -> Iterator[Record]:
        if not self.source_path.exists():
            raise FileNotFoundError(self.source_path)

        count = 0
        for gpx in self._gpx_files():
            for record_id, points in _parse_gpx_file(gpx):
                if self.limit is not None and count >= self.limit:
                    return
                yield Record(
                    record_id=f"{gpx.name}/{record_id}",
                    payload={"points": points},
                )
                count += 1
