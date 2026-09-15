"""Basemap presets, explicit legacy migration, and offline policy diagnostics."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping, Tuple
from urllib.parse import parse_qs, urlsplit

ATTRIBUTION = "OpenFreeMap © OpenMapTiles · Data from © OpenStreetMap contributors"
_DEFAULT_BASEMAPS = [
    {"name": "OpenFreeMap Positron", "kind": "vector", "url": "https://tiles.openfreemap.org/styles/positron",
     "attribution": ATTRIBUTION, "visible": True, "max_zoom": 20},
    {"name": "OpenFreeMap Liberty", "kind": "vector", "url": "https://tiles.openfreemap.org/styles/liberty",
     "attribution": ATTRIBUTION, "visible": False, "max_zoom": 20},
]
_LEGACY_URLS = {
    "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png": 0,
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png": 1,
}


def default_basemaps() -> List[Dict[str, Any]]:
    return deepcopy(_DEFAULT_BASEMAPS)


def migrate_legacy_basemaps(spec: Mapping[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Opt-in migration: replace only the old exact anonymous preset URLs.

    Keep array order/visibility (including all-off), custom URLs and credentials.
    Do not read, repair, or rewrite business data. Caller validates before writing.
    """
    result = deepcopy(dict(spec))
    changes = []
    for i, item in enumerate(result.get("basemaps", [])):
        index = _LEGACY_URLS.get(item.get("url"))
        if index is None or item.get("kind", "raster") != "raster":
            continue
        replacement = deepcopy(_DEFAULT_BASEMAPS[index])
        replacement["visible"] = item.get("visible", False)
        changes.append({"from": str(item.get("name", "")), "to": replacement["name"]})
        result["basemaps"][i] = replacement
    if changes:
        result["schema_version"] = "1.2"
    return result, changes


def basemap_warnings(spec: Mapping[str, Any]) -> List[str]:
    """Configuration checks only: never claim that an online service was tested."""
    warnings = []
    for item in spec.get("basemaps", []):
        url = urlsplit(str(item.get("url", "")))
        host = (url.hostname or "").lower()
        if host == "basemaps.cartocdn.com" or host.endswith(".basemaps.cartocdn.com"):
            key = parse_qs(url.query).get("key", [""])[0].strip()
            if not key or key.lower() in {"your_key", "your_api_key"} or "{" in key:
                warnings.append("CARTO needs an authorized API key; the browser will disable this anonymous source. Use migrate-basemaps or configure an authorized URL.")
        if host == "tile.openstreetmap.org" or host.endswith(".tile.openstreetmap.org"):
            warnings.append("OSM public tiles are disabled in local-file/opaque-origin delivery. Use migrate-basemaps or a policy-compliant hosted deployment.")
    if any(item.get("kind") == "vector" for item in spec.get("basemaps", [])):
        warnings.append("Vector basemaps need WebGL and network access to style, tiles, glyphs and sprites. The renderer is embedded; live provider availability is not verified by build/verify.")
    return warnings


__all__ = ["default_basemaps", "migrate_legacy_basemaps", "basemap_warnings"]
