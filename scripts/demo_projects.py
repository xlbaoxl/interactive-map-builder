"""Prepare repository demo projects without duplicating large source snapshots.

The checked-in Lower Manhattan data is split into three GeoJSON files to make its
provenance and category counts explicit.  The public Atlas demo should nevertheless
exercise the real ``map-list`` workflow: one primary layer with a category field.
This module creates that merged project in a temporary directory for Pages, browser
checks, and deterministic screenshots.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

LAND_USE_FILES: Sequence[str] = (
    "residential.geojson",
    "mixed-commercial.geojson",
    "civic-other.geojson",
)

LAND_USE_COLORS: Mapping[str, str] = {
    "居住用地": "#2f7f83",
    "混合与商业用地": "#e39a3b",
    "公共与其他用地": "#8b68a6",
}

FIELD_LABELS: Mapping[str, str] = {
    "name": "地块地址",
    "address": "地址",
    "category": "用地大类",
    "land_use": "详细用途",
    "zoning": "主要分区",
    "lot_area_sqft": "地块面积（平方英尺）",
    "building_area_sqft": "建筑面积（平方英尺）",
    "built_far": "已建容积率",
    "floors": "楼层数",
    "year_built": "建成年份",
    "bbl": "地块编号 BBL",
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
        category = str(properties.get("category") or "").strip()
        if category not in LAND_USE_COLORS:
            raise ValueError(f"Unknown land-use category in demo data: {category!r}")

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


def atlas_map_list_spec(feature_count: int) -> Dict[str, Any]:
    """Return the v1 MapSpec used by the public Atlas parcel demo."""

    categories = {
        value: {"label": value, "color": color}
        for value, color in LAND_USE_COLORS.items()
    }
    return {
        "schema_version": "1.0",
        "template": "map-list",
        "title": "下曼哈顿地块与用地",
        "subtitle": f"金融区—市政中心 · {feature_count:,} 个真实税务地块 · NYC Open Data",
        "locale": "zh-CN",
        "primary_layer": "parcels",
        "layers": [
            {
                "id": "parcels",
                "name": "税务地块",
                "source": {"path": "parcels.geojson"},
                "required": True,
                "visible": True,
                "id_field": "id",
                "label_field": "name",
                "search_fields": ["name", "address", "zoning", "bbl"],
                "tooltip_fields": ["name", "category", "zoning"],
                "popup_fields": [
                    "address",
                    "category",
                    "land_use",
                    "zoning",
                    "lot_area_sqft",
                    "building_area_sqft",
                    "built_far",
                    "floors",
                    "year_built",
                    "bbl",
                ],
                "filter_fields": ["category", "year_built", "floors", "built_far"],
                "card_fields": ["category", "zoning", "floors", "year_built"],
                "sort_fields": [
                    "name",
                    "year_built",
                    "floors",
                    "built_far",
                    "building_area_sqft",
                ],
                "field_labels": dict(FIELD_LABELS),
                "source_note": (
                    "NYC Open Data TAX_LOT_POLYGON (i38t-6if2) joined to "
                    "PLUTO (64uk-42ks), snapshot 2026-07-24"
                ),
                "style": {
                    "mode": "categorical",
                    "color_field": "category",
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
                {"type": "count", "label": "匹配地块"},
                {
                    "type": "sum",
                    "field": "building_area_sqft",
                    "label": "总建筑面积",
                },
                {
                    "type": "median",
                    "field": "year_built",
                    "label": "中位建成年份",
                },
                {
                    "type": "mean",
                    "field": "built_far",
                    "label": "平均容积率",
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


def prepare_demo_project(
    example_name: str,
    *,
    examples_root: Path,
    destination: Path,
) -> Path:
    """Copy one checked-in example and prepare its public-demo MapSpec."""

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
        spec = atlas_map_list_spec(feature_count)
        spec_path.write_text(
            json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    elif not spec_path.is_file():
        raise FileNotFoundError(f"Example is missing map_spec.json: {destination}")
    return spec_path


__all__ = [
    "FIELD_LABELS",
    "LAND_USE_COLORS",
    "LAND_USE_FILES",
    "atlas_map_list_spec",
    "merge_land_use_snapshots",
    "prepare_demo_project",
]
