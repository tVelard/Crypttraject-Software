"""Shared helpers for GPS point extraction across adapters."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

Point = Tuple[float, float]


def coerce_point(raw: Sequence) -> Point | None:
    """Parse a (lat, lon) or [lat, lon] pair, skipping invalid values."""
    try:
        lat, lon = float(raw[0]), float(raw[1])
    except (TypeError, ValueError, IndexError):
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    return lat, lon


def coerce_geojson_coord(raw: Sequence) -> Point | None:
    """GeoJSON stores coordinates as [longitude, latitude]."""
    try:
        lon, lat = float(raw[0]), float(raw[1])
    except (TypeError, ValueError, IndexError):
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    return lat, lon


def dedupe_consecutive(points: Iterable[Point]) -> List[Point]:
    """Drop identical consecutive points while preserving order."""
    out: List[Point] = []
    prev: Point | None = None
    for pt in points:
        if pt != prev:
            out.append(pt)
            prev = pt
    return out
