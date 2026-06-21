"""Data-source adapters and feature extractors.

Ingest GPS trajectories from several file formats, turn each trajectory
into geohash feature tokens, then feed MinHash.  See ``registry.py`` for
auto-detection and factory helpers.
"""

from .base import DataSourceAdapter, FeatureExtractor, Record
from .csv_adapter import CsvAdapter
from .features import GeoHashExtractor
from .geojson_adapter import GeoJsonAdapter
from .gpx_adapter import GpxAdapter
from .plt_adapter import PLTGeolifeAdapter
from .registry import (
    EXTRACTOR_IDS,
    EXTRACTOR_SPECS,
    SOURCE_IDS,
    SOURCE_SPECS,
    create_adapter,
    create_extractor,
    default_extractor_for,
    detect_source,
    validate_source_path,
)

__all__ = [
    "CsvAdapter",
    "DataSourceAdapter",
    "EXTRACTOR_IDS",
    "EXTRACTOR_SPECS",
    "FeatureExtractor",
    "GeoHashExtractor",
    "GeoJsonAdapter",
    "GpxAdapter",
    "PLTGeolifeAdapter",
    "Record",
    "SOURCE_IDS",
    "SOURCE_SPECS",
    "create_adapter",
    "create_extractor",
    "default_extractor_for",
    "detect_source",
    "validate_source_path",
]
