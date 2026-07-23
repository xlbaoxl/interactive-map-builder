"""Core data utilities for Interactive Map Builder.

The package deliberately keeps loading, normalization, validation, and remote
acquisition separate so callers can inspect data before deciding how to build
a map.
"""

from .arcgis import ArcGISDownloadResult, ArcGISError, download_feature_service, fetch_arcgis
from .loaders import DataLoadError, load_geodata, load_input, load_source
from .normalize import NormalizationReport, normalize_geodata, stable_feature_id
from .validate import (
    ValidationError,
    ValidationReport,
    ensure_count_consistency,
    validate_geodata,
)

__all__ = [
    "ArcGISDownloadResult",
    "ArcGISError",
    "DataLoadError",
    "NormalizationReport",
    "ValidationError",
    "ValidationReport",
    "download_feature_service",
    "ensure_count_consistency",
    "fetch_arcgis",
    "load_geodata",
    "load_input",
    "load_source",
    "normalize_geodata",
    "stable_feature_id",
    "validate_geodata",
]
