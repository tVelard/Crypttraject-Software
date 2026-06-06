"""Data-source adapters.

The client ingests Geolife `.plt` trajectory directories and turns each
trajectory into a set of geohash feature tokens (bytes) ready to feed
MinHash.

Adding a new source = subclassing `DataSourceAdapter` and implementing
`iter_records()`. The encryption pipeline never has to know what kind of
source it came from.
"""

from .base import DataSourceAdapter, Record, FeatureExtractor
from .plt_adapter import PLTGeolifeAdapter
from .features import GeoHashExtractor

__all__ = [
    "DataSourceAdapter",
    "Record",
    "FeatureExtractor",
    "PLTGeolifeAdapter",
    "GeoHashExtractor",
]
