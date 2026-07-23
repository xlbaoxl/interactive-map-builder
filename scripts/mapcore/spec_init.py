"""Create a minimal, editable MapSpec from an inspection result."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from .spec import validate_spec


class SpecInitError(ValueError):
    """Raised when inspection ambiguities must be resolved before initialization."""


_PALETTE = [
    "#2563eb",
    "#0f766e",
    "#d97706",
    "#dc2626",
    "#7c3aed",
    "#0891b2",
    "#4d7c0f",
    "#be185d",
    "#475569",
    "#9333ea",
    "#ea580c",
    "#15803d",
]


def _first(values: Any) -> Optional[str]:
    if isinstance(values, list) and values:
        return str(values[0])
    return None


def _field_details(layer: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    for item in layer.get("fields", []):
        if isinstance(item, Mapping) and str(item.get("name")) == field:
            return item
    return {}


def _relative_source_path(
    inspection: Mapping[str, Any],
    source: Mapping[str, Any],
    spec_dir: Path,
) -> str:
    input_index = int(source.get("input_index", 0))
    inputs = inspection.get("inputs", [])
    if input_index < 0 or input_index >= len(inputs):
        raise SpecInitError("Inspection layer refers to an unknown input index.")
    resolved = Path(str(inputs[input_index]["resolved_path"])).resolve()
    try:
        relative = os.path.relpath(str(resolved), str(spec_dir.resolve()))
    except ValueError:
        raise SpecInitError(
            "Input and specification are on different drives; copy the input beside the project "
            "or write its relative path manually."
        )
    return Path(relative).as_posix()


def _source_spec(
    inspection: Mapping[str, Any],
    layer: Mapping[str, Any],
    spec_dir: Path,
) -> Dict[str, Any]:
    inspected_source = layer.get("source", {})
    source: Dict[str, Any] = {
        "path": _relative_source_path(inspection, inspected_source, spec_dir),
    }
    for key in ("layer", "sheet", "crs", "encoding", "geometry"):
        if inspected_source.get(key) is not None:
            source[key] = inspected_source[key]

    suffix = Path(source["path"]).suffix.casefold()
    if suffix not in {".csv", ".xlsx", ".xls"}:
        if layer.get("crs") is None and source.get("crs") is None:
            raise SpecInitError(
                "Layer {!r} has no CRS; confirm source.crs before initializing the spec.".format(
                    layer.get("name")
                )
            )
        return source

    candidates = layer.get("candidates", {})
    if "geometry" not in source:
        longitudes = candidates.get("longitude", [])
        latitudes = candidates.get("latitude", [])
        wkts = candidates.get("wkt", [])
        lonlat_ready = len(longitudes) == 1 and len(latitudes) == 1
        wkt_ready = len(wkts) == 1
        if lonlat_ready and not wkt_ready:
            source["geometry"] = {
                "type": "lonlat",
                "x_field": str(longitudes[0]),
                "y_field": str(latitudes[0]),
            }
        elif wkt_ready and not lonlat_ready:
            source["geometry"] = {"type": "wkt", "wkt_field": str(wkts[0])}
        else:
            raise SpecInitError(
                "Layer {!r} has ambiguous tabular geometry; confirm longitude/latitude or WKT."
                .format(layer.get("name"))
            )
    if source.get("crs") is None:
        if layer.get("crs") is None:
            raise SpecInitError(
                "Layer {!r} needs an explicit source CRS.".format(layer.get("name"))
            )
        source["crs"] = layer["crs"]
    return source


def _categorical_style(layer: Mapping[str, Any]) -> Dict[str, Any]:
    field = _first(layer.get("candidates", {}).get("category"))
    if not field:
        return {"color": "#2563eb", "fill_opacity": 0.58}
    details = _field_details(layer, field)
    values = details.get("values")
    if not isinstance(values, list) or len(values) != details.get("unique_count"):
        return {"color": "#2563eb", "fill_opacity": 0.58}
    categories = {
        str(value): _PALETTE[index % len(_PALETTE)]
        for index, value in enumerate(values)
    }
    return {
        "mode": "categorical",
        "color_field": field,
        "categories": categories,
        "fill_opacity": 0.58,
    }


def _layer_spec(
    inspection: Mapping[str, Any],
    layer: Mapping[str, Any],
    spec_dir: Path,
) -> Dict[str, Any]:
    candidates = layer.get("candidates", {})
    label = _first(candidates.get("label"))
    identifier = _first(candidates.get("id"))
    search = [str(value) for value in candidates.get("search", [])[:4]]
    filters = [str(value) for value in candidates.get("filter", [])[:3]]
    cards = [str(value) for value in candidates.get("card", [])[:5]]
    numeric = [str(value) for value in candidates.get("numeric", [])[:2]]
    result: Dict[str, Any] = {
        "id": str(layer["layer_id"]),
        "name": str(layer.get("name") or layer["layer_id"]),
        "required": True,
        "visible": True,
        "source": _source_spec(inspection, layer, spec_dir),
        "style": _categorical_style(layer),
    }
    if identifier:
        result["id_field"] = identifier
    if label:
        result["label_field"] = label
        result["tooltip_fields"] = [label] + [
            field for field in filters[:2] if field != label
        ]
        result["popup_fields"] = list(dict.fromkeys(result["tooltip_fields"] + numeric))
    if search:
        result["search_fields"] = search
    if filters:
        result["filter_fields"] = filters
    if cards:
        result["card_fields"] = cards
    sort_fields = list(dict.fromkeys(([label] if label else []) + numeric))
    if sort_fields:
        result["sort_fields"] = sort_fields
    return result


def init_spec_from_inspection(
    inspection: Mapping[str, Any],
    *,
    spec_path: Path,
    template: str = "auto",
    title: Optional[str] = None,
    primary_layer: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert inspection output into the smallest reusable valid MapSpec."""

    layers = inspection.get("layers")
    if not isinstance(layers, list) or not layers:
        raise SpecInitError("Inspection contains no layers.")
    recommendation = inspection.get("template_recommendation", {})
    if template == "auto":
        selected_value = recommendation.get("recommended")
        if recommendation.get("needs_confirmation") or not selected_value:
            raise SpecInitError(
                "Multiple layers require an explicit --template. "
                "Use --primary-layer as well when choosing map-list."
            )
        selected = str(selected_value)
    else:
        selected = str(template)
    if selected not in {"map-list", "multilayer"}:
        raise SpecInitError("template must be auto, map-list, or multilayer")
    layer_ids = [str(layer["layer_id"]) for layer in layers]
    if selected == "multilayer" and primary_layer:
        raise SpecInitError("--primary-layer applies only to the map-list template.")
    if selected == "map-list":
        if primary_layer is None:
            if len(layers) == 1:
                primary_layer = layer_ids[0]
            else:
                raise SpecInitError(
                    "map-list with multiple layers requires --primary-layer; choose one of: {}"
                    .format(", ".join(layer_ids))
                )
        if primary_layer not in layer_ids:
            raise SpecInitError(
                "Unknown primary layer {!r}; choose one of: {}".format(
                    primary_layer, ", ".join(layer_ids)
                )
            )

    spec_dir = spec_path.resolve().parent
    spec_layers = [_layer_spec(inspection, layer, spec_dir) for layer in layers]
    inferred_title = title
    if not inferred_title:
        raw_name = str(layers[0].get("name") or "Interactive map")
        inferred_title = re.sub(r"[_-]+", " ", raw_name).strip() or "Interactive map"
    spec: Dict[str, Any] = {
        "schema_version": "1.0",
        "template": selected,
        "title": inferred_title,
        "subtitle": "Generated from an editable MapSpec",
        "locale": "zh-CN",
        "layers": spec_layers,
        "basemaps": [
            {
                "name": "OpenStreetMap",
                "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                "attribution": "© OpenStreetMap contributors",
                "visible": True,
            }
        ],
        "static": {"enabled": True, "presets": ["slide-16x9", "paper"]},
    }
    if selected == "map-list":
        spec["primary_layer"] = str(primary_layer)
        primary = next(layer for layer in spec_layers if layer["id"] == primary_layer)
        default_sort = _first(primary.get("sort_fields"))
        spec["list"] = {
            "collapsible": True,
            "batch_size": 200,
            "summary_fields": primary.get("card_fields", []),
        }
        if default_sort:
            spec["list"]["default_sort"] = default_sort
    return validate_spec(spec)


__all__ = ["SpecInitError", "init_spec_from_inspection"]
