"""GeoJSON trajectory adapter (.geojson / .json files or directories)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional

from .base import DataSourceAdapter, Record
from .points import Point, coerce_geojson_coord, dedupe_consecutive

_GEO_TYPES = frozenset({"linestring", "multipoint", "point"})


def _points_from_geometry(geom: dict) -> List[Point]:
    gtype = (geom.get("type") or "").lower()
    coords = geom.get("coordinates")
    if not coords:
        return []

    points: List[Point] = []
    if gtype == "point":
        pt = coerce_geojson_coord(coords)
        return [pt] if pt else []
    if gtype == "linestring":
        for raw in coords:
            pt = coerce_geojson_coord(raw)
            if pt:
                points.append(pt)
    elif gtype == "multipoint":
        for raw in coords:
            pt = coerce_geojson_coord(raw)
            if pt:
                points.append(pt)
    return dedupe_consecutive(points)


def _feature_id(feature: dict, index: int, file_stem: str) -> str:
    props = feature.get("properties") or {}
    for key in ("id", "name", "trajectory_id", "traj_id", "record_id"):
        val = props.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    fid = feature.get("id")
    if fid is not None and str(fid).strip():
        return str(fid).strip()
    return f"{file_stem}/feature{index}"


def _parse_geojson_file(path: Path) -> List[tuple[str, List[Point]]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    features: List[dict] = []
    if isinstance(data, dict):
        if data.get("type") == "FeatureCollection":
            features = [f for f in (data.get("features") or []) if isinstance(f, dict)]
        elif data.get("type") == "Feature":
            features = [data]
        elif "coordinates" in data:
            features = [{"type": "Feature", "geometry": data, "properties": {}}]
    if not features:
        return []

    records: List[tuple[str, List[Point]]] = []
    for i, feature in enumerate(features, start=1):
        geom = feature.get("geometry")
        if not isinstance(geom, dict):
            continue
        if (geom.get("type") or "").lower() not in _GEO_TYPES:
            continue
        points = _points_from_geometry(geom)
        if points:
            records.append((_feature_id(feature, i, path.stem), points))
    return records


@dataclass
class GeoJsonAdapter(DataSourceAdapter):
    source_path: Path
    limit: Optional[int] = None

    def _geojson_files(self) -> List[Path]:
        if self.source_path.is_file():
            if self.source_path.suffix.lower() in (".geojson", ".json"):
                return [self.source_path]
            return []
        files: List[Path] = []
        for pattern in ("*.geojson", "*.json"):
            files.extend(self.source_path.rglob(pattern))
        return sorted(set(files))

    def count(self) -> int | None:
        if not self.source_path.exists():
            return 0
        total = 0
        for geo_file in self._geojson_files():
            total += len(_parse_geojson_file(geo_file))
            if self.limit is not None and total >= self.limit:
                return self.limit
        return total

    def iter_records(self) -> Iterator[Record]:
        if not self.source_path.exists():
            raise FileNotFoundError(self.source_path)

        count = 0
        for geo_file in self._geojson_files():
            for record_id, points in _parse_geojson_file(geo_file):
                if self.limit is not None and count >= self.limit:
                    return
                yield Record(
                    record_id=f"{geo_file.name}/{record_id}",
                    payload={"points": points},
                )
                count += 1
