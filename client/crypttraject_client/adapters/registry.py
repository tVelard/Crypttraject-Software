"""Source/extractor registry, auto-detection, and factory helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .base import DataSourceAdapter, FeatureExtractor
from .csv_adapter import CsvAdapter
from .features import GeoHashExtractor
from .geojson_adapter import GeoJsonAdapter
from .gpx_adapter import GpxAdapter
from .plt_adapter import PLTGeolifeAdapter

AdapterFactory = Callable[[Path, Optional[int]], DataSourceAdapter]
ExtractorFactory = Callable[[int], FeatureExtractor]


@dataclass(frozen=True)
class SourceSpec:
    id: str
    label: str
    description: str
    default_extractor: str
    accepts_file: bool
    accepts_dir: bool
    factory: AdapterFactory


@dataclass(frozen=True)
class ExtractorSpec:
    id: str
    label: str
    description: str
    factory: ExtractorFactory


def _adapter_geolife(path: Path, limit: Optional[int]) -> DataSourceAdapter:
    return PLTGeolifeAdapter(dataset_dir=path, limit=limit)


def _adapter_gpx(path: Path, limit: Optional[int]) -> DataSourceAdapter:
    return GpxAdapter(source_path=path, limit=limit)


def _adapter_csv(path: Path, limit: Optional[int]) -> DataSourceAdapter:
    return CsvAdapter(source_path=path, limit=limit)


def _adapter_geojson(path: Path, limit: Optional[int]) -> DataSourceAdapter:
    return GeoJsonAdapter(source_path=path, limit=limit)


def _extractor_geohash(precision: int) -> FeatureExtractor:
    return GeoHashExtractor(points_field="points", precision=precision)


SOURCE_SPECS: Dict[str, SourceSpec] = {
    "geolife-plt": SourceSpec(
        id="geolife-plt",
        label="Geolife (.plt directory)",
        description="Microsoft Geolife GPS trajectories (.plt files in a folder tree).",
        default_extractor="geohash",
        accepts_file=False,
        accepts_dir=True,
        factory=_adapter_geolife,
    ),
    "gpx": SourceSpec(
        id="gpx",
        label="GPX",
        description="GPS Exchange Format (.gpx file or folder of .gpx files).",
        default_extractor="geohash",
        accepts_file=True,
        accepts_dir=True,
        factory=_adapter_gpx,
    ),
    "csv": SourceSpec(
        id="csv",
        label="CSV",
        description="Comma-separated points with lat/lon columns (file or folder).",
        default_extractor="geohash",
        accepts_file=True,
        accepts_dir=True,
        factory=_adapter_csv,
    ),
    "geojson": SourceSpec(
        id="geojson",
        label="GeoJSON",
        description="GeoJSON FeatureCollection with LineString / MultiPoint geometries.",
        default_extractor="geohash",
        accepts_file=True,
        accepts_dir=True,
        factory=_adapter_geojson,
    ),
}

EXTRACTOR_SPECS: Dict[str, ExtractorSpec] = {
    "geohash": ExtractorSpec(
        id="geohash",
        label="Geohash cells",
        description="Encode GPS points as geohash grid cells (set-based MinHash input).",
        factory=_extractor_geohash,
    ),
}

SOURCE_IDS: List[str] = list(SOURCE_SPECS.keys())
EXTRACTOR_IDS: List[str] = list(EXTRACTOR_SPECS.keys())


def _dir_has_glob(root: Path, pattern: str) -> bool:
    return next(root.rglob(pattern), None) is not None


def _looks_like_geojson(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    gtype = data.get("type")
    if gtype == "FeatureCollection":
        return bool(data.get("features"))
    if gtype == "Feature":
        return isinstance(data.get("geometry"), dict)
    return "coordinates" in data


def detect_source(path: Path) -> str:
    """Guess the best source adapter id for *path* (file or directory)."""
    if not path.exists():
        return "geolife-plt"

    if path.is_file():
        ext = path.suffix.lower()
        if ext == ".gpx":
            return "gpx"
        if ext == ".csv":
            return "csv"
        if ext == ".geojson":
            return "geojson"
        if ext == ".json" and _looks_like_geojson(path):
            return "geojson"
        if ext == ".plt":
            return "geolife-plt"
        return "gpx"

    # Directory — pick the format with the most matching files.
    counts = {
        "geolife-plt": sum(1 for _ in path.rglob("*.plt")),
        "gpx": sum(1 for _ in path.rglob("*.gpx")),
        "csv": sum(1 for _ in path.rglob("*.csv")),
        "geojson": sum(1 for _ in path.rglob("*.geojson")),
    }
    json_geo = 0
    for jf in path.rglob("*.json"):
        if _looks_like_geojson(jf):
            json_geo += 1
    counts["geojson"] += json_geo

    best = max(counts, key=counts.get)
    if counts[best] > 0:
        return best
    return "geolife-plt"


def default_extractor_for(source_id: str) -> str:
    spec = SOURCE_SPECS.get(source_id)
    if spec is None:
        raise KeyError(f"Unknown source id: {source_id!r}")
    return spec.default_extractor


def create_adapter(
    source_id: str,
    path: Path,
    limit: Optional[int] = None,
) -> DataSourceAdapter:
    spec = SOURCE_SPECS.get(source_id)
    if spec is None:
        raise KeyError(f"Unknown source id: {source_id!r}")
    if path.is_file() and not spec.accepts_file:
        raise ValueError(f"{spec.label} requires a directory, not a file.")
    if path.is_dir() and not spec.accepts_dir:
        raise ValueError(f"{spec.label} requires a file, not a directory.")
    return spec.factory(path, limit)


def create_extractor(extractor_id: str, *, geohash_precision: int = 6) -> FeatureExtractor:
    spec = EXTRACTOR_SPECS.get(extractor_id)
    if spec is None:
        raise KeyError(f"Unknown extractor id: {extractor_id!r}")
    return spec.factory(geohash_precision)


def validate_source_path(source_id: str, path: Path) -> None:
    """Raise ValueError when *path* is incompatible with *source_id*."""
    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")

    spec = SOURCE_SPECS[source_id]
    if path.is_file():
        if not spec.accepts_file:
            raise ValueError(f"{spec.label} requires a directory.")
        ext = path.suffix.lower()
        if source_id == "gpx" and ext != ".gpx":
            raise ValueError("GPX source expects a .gpx file.")
        if source_id == "csv" and ext != ".csv":
            raise ValueError("CSV source expects a .csv file.")
        if source_id == "geojson" and ext not in (".geojson", ".json"):
            raise ValueError("GeoJSON source expects a .geojson or .json file.")
        if source_id == "geolife-plt":
            raise ValueError("Geolife source expects a directory of .plt files.")
        if source_id == "geojson" and ext == ".json" and not _looks_like_geojson(path):
            raise ValueError("JSON file is not a valid GeoJSON document.")
        return

    if not spec.accepts_dir:
        raise ValueError(f"{spec.label} requires a file, not a directory.")

    if source_id == "geolife-plt" and not _dir_has_glob(path, "*.plt"):
        raise ValueError("Directory contains no .plt files (Geolife format).")
    if source_id == "gpx" and not _dir_has_glob(path, "*.gpx"):
        raise ValueError("Directory contains no .gpx files.")
    if source_id == "csv" and not _dir_has_glob(path, "*.csv"):
        raise ValueError("Directory contains no .csv files.")
    if source_id == "geojson" and not (
        _dir_has_glob(path, "*.geojson")
        or any(_looks_like_geojson(p) for p in path.rglob("*.json"))
    ):
        raise ValueError("Directory contains no GeoJSON files.")
