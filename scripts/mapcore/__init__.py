"""Core data utilities for Interactive Map Builder.

Public helpers are imported on first access. Version queries, updater checks,
and CLI help can therefore run before the GIS runtime is loaded or repaired.
"""

from importlib import import_module

from .version import __version__


_EXPORTS = {
    "ArcGISDownloadResult": ".arcgis",
    "ArcGISError": ".arcgis",
    "DataLoadError": ".loaders",
    "DELIVERY_MANIFEST_NAME": ".delivery",
    "NormalizationReport": ".normalize",
    "ValidationError": ".validate",
    "ValidationReport": ".validate",
    "current_schema_version": ".spec",
    "download_feature_service": ".arcgis",
    "ensure_count_consistency": ".validate",
    "fetch_arcgis": ".arcgis",
    "load_geodata": ".loaders",
    "load_input": ".loaders",
    "load_source": ".loaders",
    "normalize_geodata": ".normalize",
    "stable_feature_id": ".normalize",
    "validate_geodata": ".validate",
}

__all__ = [*_EXPORTS, "__version__"]


def __getattr__(name: str):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name, __name__), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
