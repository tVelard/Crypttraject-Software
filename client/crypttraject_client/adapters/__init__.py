"""Generic data-source adapters.

The whole point of this layer is the genericity requirement of the
project: the client must ingest CSV, JSON, SQL, .plt, ... and turn each
record into a SET of feature tokens (bytes) ready to feed MinHash.

Adding a new source = subclassing `DataSourceAdapter` and implementing
`iter_records()`. The encryption pipeline never has to know what kind of
database it came from.
"""

from .base import DataSourceAdapter, Record, FeatureExtractor
from .csv_adapter import CSVAdapter
from .json_adapter import JSONAdapter
from .plt_adapter import PLTGeolifeAdapter
from .features import GeoHashExtractor, FieldTokenExtractor

__all__ = [
    "DataSourceAdapter",
    "Record",
    "FeatureExtractor",
    "CSVAdapter",
    "JSONAdapter",
    "PLTGeolifeAdapter",
    "GeoHashExtractor",
    "FieldTokenExtractor",
]
