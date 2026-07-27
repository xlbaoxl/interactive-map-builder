"""Curated online basemap defaults for generated MapSpec files."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


_DEFAULT_BASEMAPS: List[Dict[str, Any]] = [
    {
        "name": "CARTO Positron",
        "url": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap contributors © CARTO",
        "visible": True,
        "max_zoom": 20,
    },
    {
        "name": "OpenStreetMap Standard",
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap contributors",
        "visible": False,
        "max_zoom": 19,
    },
]


def default_basemaps() -> List[Dict[str, Any]]:
    """Return an independent copy of the curated default basemap list."""

    return deepcopy(_DEFAULT_BASEMAPS)


__all__ = ["default_basemaps"]
