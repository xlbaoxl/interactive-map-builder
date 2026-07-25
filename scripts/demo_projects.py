"""Prepare localized public demo projects from checked-in source snapshots."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from mapcore.locales import (
    DEFAULT_LOCALE,
    catalog_value,
    load_catalog,
    require_locale,
)


LAND_USE_FILES: Sequence[str] = (
    "residential.geojson",
    "mixed-commercial.geojson",
    "civic-other.geojson",
)

LAND_USE_COLORS: Mapping[str, str] = {
    "residential": "#2f7f83",
    "mixed_commercial": "#e39a3b",
    "civic_other": "#8b68a6",
}


def _read_collection(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection" or not isinstance(
        payload.get("features"), list
    ):
        raise ValueError(f"Expected a GeoJSON FeatureCollection: {path}")
    return payload


def merge_land_use_snapshots(project: Path) -> Path:
    """Merge the three checked-in land-use snapshots into one stable collection."""

    features = []
    for name in LAND_USE_FILES:
        source = project / name
        if not source.is_file():
            raise FileNotFoundError(f"Missing demo source: {source}")
        features.extend(_read_collection(source)["features"])

    identifiers = []
    for feature in features:
        properties = feature.get("properties") or {}
        identifier = str(properties.get("id") or feature.get("id") or "").strip()
        if not identifier:
            raise ValueError("Every demo parcel must have a stable id.")
        identifiers.append(identifier)
        category = str(properties.get("category_code") or "").strip()
        if category not in LAND_USE_COLORS:
            raise ValueError(f"Unknown land-use category code in demo data: {category!r}")

    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Merged demo parcel ids are not unique.")

    features.sort(
        key=lambda feature: str((feature.get("properties") or {}).get("id") or "")
    )
    destination = project / "parcels.geojson"
    destination.write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": features},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    return destination


def atlas_map_list_spec(
    feature_count: int,
    locale: str = DEFAULT_LOCALE,
) -> Dict[str, Any]:
    """Return the MapSpec 1.1 configuration used by one public parcel demo."""

    selected_locale = require_locale(locale)
    catalog = load_catalog(selected_locale)
    messages = catalog_value(catalog, "demo", "map_list")
    suffix = str(catalog_value(catalog, "demo", "display_suffix"))
    category_field = f"category_{suffix}"
    land_use_field = f"land_use_{suffix}"
    field_labels = dict(messages["field_labels"])
    field_labels[category_field] = field_labels.pop("category")
    field_labels[land_use_field] = field_labels.pop("land_use")
    categories = {
        code: {
            "label": str(messages["category_labels"][code]),
            "color": color,
        }
        for code, color in LAND_USE_COLORS.items()
    }
    summary_labels = messages["summary_labels"]
    return {
        "schema_version": "1.1",
        "template": "map-list",
        "title": str(messages["title"]),
        "subtitle": str(messages["subtitle"]).format(
            feature_count=f"{feature_count:,}"
        ),
        "locale": selected_locale,
        "primary_layer": "parcels",
        "layers": [
            {
                "id": "parcels",
                "name": str(messages["layer_name"]),
                "source": {"path": "parcels.geojson"},
                "required": True,
                "visible": True,
                "id_field": "id",
                "label_field": "name",
                "search_fields": ["name", "address", "zoning", "bbl"],
                "tooltip_fields": ["name", category_field, "zoning"],
                "popup_fields": [
                    "address",
                    category_field,
                    land_use_field,
                    "zoning",
                    "lot_area_sqft",
                    "building_area_sqft",
                    "built_far",
                    "floors",
                    "year_built",
                    "bbl",
                ],
                "filter_fields": [
                    "category_code",
                    "year_built",
                    "floors",
                    "built_far",
                ],
                "card_fields": [
                    "zoning",
                    "floors",
                    "year_built",
                    "built_far",
                    "lot_area_sqft",
                    "building_area_sqft",
                ],
                "sort_fields": [
                    "name",
                    "year_built",
                    "floors",
                    "built_far",
                    "building_area_sqft",
                ],
                "field_labels": field_labels,
                "source_note": (
                    "NYC Open Data TAX_LOT_POLYGON (i38t-6if2) joined to "
                    "PLUTO (64uk-42ks), snapshot 2026-07-24"
                ),
                "style": {
                    "mode": "categorical",
                    "color_field": "category_code",
                    "weight": 0.75,
                    "opacity": 0.92,
                    "fill_opacity": 0.72,
                    "categories": categories,
                },
            }
        ],
        "basemaps": [
            {
                "name": "Carto Positron",
                "url": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
                "attribution": "© OpenStreetMap contributors © CARTO",
                "visible": True,
            },
            {
                "name": "OpenStreetMap",
                "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                "attribution": "© OpenStreetMap contributors",
                "visible": False,
            },
        ],
        "map": {
            "search_behavior": "highlight",
            "controls": {
                "fullscreen": True,
                "scale": True,
                "basemap_switcher": True,
                "layer_control": False,
                "legend": True,
            },
        },
        "list": {
            "batch_size": 100,
            "default_sort": "name",
            "collapsible": True,
            "summary_update_with_filter": True,
            "summary_metrics": [
                {"type": "count", "label": str(summary_labels["count"])},
                {
                    "type": "sum",
                    "field": "building_area_sqft",
                    "label": str(summary_labels["building_area"]),
                },
                {
                    "type": "median",
                    "field": "year_built",
                    "label": str(summary_labels["year_built"]),
                },
                {
                    "type": "mean",
                    "field": "built_far",
                    "label": str(summary_labels["built_far"]),
                },
            ],
        },
        "static": {
            "enabled": True,
            "presets": ["slide-16x9", "paper"],
            "source_note": (
                "NYC Open Data: TAX_LOT_POLYGON (i38t-6if2) joined to "
                "PLUTO (64uk-42ks), snapshot 2026-07-24"
            ),
        },
    }


def _localized_multilayer_spec(
    base_spec: Mapping[str, Any],
    locale: str,
) -> Dict[str, Any]:
    selected_locale = require_locale(locale)
    messages = catalog_value(load_catalog(selected_locale), "demo", "multilayer")
    spec = deepcopy(dict(base_spec))
    spec["schema_version"] = "1.1"
    spec["locale"] = selected_locale
    spec["title"] = str(messages["title"])
    spec["subtitle"] = str(messages["subtitle"])
    layer_messages = messages["layers"]
    for layer in spec["layers"]:
        localized = layer_messages[str(layer["id"])]
        layer["name"] = str(localized["name"])
        layer["field_labels"] = dict(localized["field_labels"])
    return spec


def prepare_demo_project(
    example_name: str,
    *,
    examples_root: Path,
    destination: Path,
    locale: str = DEFAULT_LOCALE,
) -> Path:
    """Copy one checked-in example and prepare its localized public MapSpec."""

    selected_locale = require_locale(locale)
    source = examples_root / example_name
    if not source.is_dir():
        raise FileNotFoundError(f"Unknown example: {source}")
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)

    spec_path = destination / "map_spec.json"
    if example_name == "map-list":
        merged = merge_land_use_snapshots(destination)
        feature_count = len(_read_collection(merged)["features"])
        spec = atlas_map_list_spec(feature_count, selected_locale)
    elif example_name == "multilayer":
        if not spec_path.is_file():
            raise FileNotFoundError(f"Example is missing map_spec.json: {destination}")
        spec = _localized_multilayer_spec(
            json.loads(spec_path.read_text(encoding="utf-8")),
            selected_locale,
        )
    else:
        if not spec_path.is_file():
            raise FileNotFoundError(f"Example is missing map_spec.json: {destination}")
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        spec["schema_version"] = "1.1"
        spec["locale"] = selected_locale
    spec_path.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return spec_path


__all__ = [
    "LAND_USE_COLORS",
    "LAND_USE_FILES",
    "atlas_map_list_spec",
    "merge_land_use_snapshots",
    "prepare_demo_project",
]
