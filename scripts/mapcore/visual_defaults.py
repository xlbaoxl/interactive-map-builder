"""Renderer-neutral visual defaults for Atlas Studio Light.

The resolver combines geometry, coarse density, layer hierarchy, and a small
set of urban-map semantic roles. Explicit MapSpec values always win.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

import geopandas as gpd
import shapely

from .semantic_styles import (
    CATEGORICAL_PALETTE,
    infer_semantic_role,
    semantic_color,
)

SEQUENTIAL_PALETTE = ("#EDF4F2", "#8DB8B3", "#285F62")

_ROLE_COLORS = {
    "primary": {"point": "#C45F78", "line": "#28786F", "polygon": "#5F9294"},
    "supporting": {"point": "#6E8791", "line": "#59747A", "polygon": "#8FA8A4"},
    "context": {"point": "#849397", "line": "#748589", "polygon": "#AEBBBC"},
}

_POINT_RADIUS = {"sparse": 5.0, "normal": 4.1, "dense": 3.2, "very_dense": 2.4}
_LINE_WEIGHT = {"sparse": 1.85, "normal": 1.48, "dense": 1.10, "very_dense": 0.84}
_POLYGON_WEIGHT = {"sparse": 1.05, "normal": 0.84, "dense": 0.64, "very_dense": 0.46}

_PANE_ORDER = {
    ("context", "polygon"): 330,
    ("supporting", "polygon"): 340,
    ("primary", "polygon"): 350,
    ("context", "line"): 410,
    ("supporting", "line"): 420,
    ("primary", "line"): 430,
    ("context", "point"): 490,
    ("supporting", "point"): 500,
    ("primary", "point"): 510,
}

_VISUAL_KEYS = {"color", "fill_color", "weight", "opacity", "fill_opacity", "radius"}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


def adjust_hex(color: str, amount: float) -> str:
    source = str(color or "").strip()
    value = source.lstrip("#")
    if len(value) != 6:
        return source
    try:
        channels = [int(value[index : index + 2], 16) for index in (0, 2, 4)]
    except ValueError:
        return source
    if amount >= 0:
        resolved = [round(channel + (255 - channel) * amount) for channel in channels]
    else:
        resolved = [round(channel * (1 + amount)) for channel in channels]
    return "#{:02X}{:02X}{:02X}".format(*[max(0, min(255, item)) for item in resolved])


def geometry_metrics(frame: gpd.GeoDataFrame) -> Dict[str, Dict[str, int]]:
    metrics = {
        "point": {"features": 0, "coordinates": 0},
        "line": {"features": 0, "coordinates": 0},
        "polygon": {"features": 0, "coordinates": 0},
    }
    for geometry in frame.geometry:
        if geometry is None or geometry.is_empty:
            continue
        name = str(geometry.geom_type).lower()
        if "point" in name:
            family = "point"
        elif "line" in name:
            family = "line"
        elif "polygon" in name:
            family = "polygon"
        else:
            continue
        metrics[family]["features"] += 1
        metrics[family]["coordinates"] += int(shapely.get_num_coordinates(geometry))
    return metrics


def geometry_counts(frame: gpd.GeoDataFrame) -> Dict[str, int]:
    return {family: values["features"] for family, values in geometry_metrics(frame).items()}


def geometry_family(counts: Mapping[str, int]) -> str:
    populated = [name for name, count in counts.items() if int(count) > 0]
    if len(populated) == 1:
        return populated[0]
    if not populated:
        return "unknown"
    return "mixed"


def density_class(family: str, feature_count: int, coordinate_count: Optional[int] = None) -> str:
    features = max(0, int(feature_count))
    coordinates = max(0, int(coordinate_count or 0))
    if family == "point":
        thresholds = ((80, 120), (350, 500), (1200, 1800))
    elif family == "line":
        thresholds = ((25, 1200), (120, 6000), (600, 24000))
    elif family == "polygon":
        thresholds = ((20, 2000), (120, 10000), (600, 50000))
    else:
        thresholds = ((80, 2000), (500, 10000), (2000, 50000))
    for label, (feature_limit, coordinate_limit) in zip(("sparse", "normal", "dense"), thresholds):
        if features <= feature_limit and coordinates <= coordinate_limit:
            return label
    return "very_dense"


def visual_role(
    *,
    template: str,
    layer_id: str,
    primary_layer: Optional[str],
    family: str,
    layer_count: int,
) -> str:
    if template == "map-list":
        return "primary" if layer_id == primary_layer else "context"
    if int(layer_count) <= 1:
        return "primary"
    if family == "polygon":
        return "context"
    return "supporting"


def _explicit_value(explicit: Mapping[str, Any], style: Mapping[str, Any], key: str, fallback: Any) -> Any:
    if key in explicit:
        return style.get(key, explicit[key])
    return fallback


def _default_color(role: str, semantic_role: Optional[str], family: str) -> str:
    return semantic_color(semantic_role, family, _ROLE_COLORS[role][family])


def _point_opacity(role: str, semantic_role: Optional[str], density: str) -> Dict[str, float]:
    opacity = {"primary": 0.98, "supporting": 0.90, "context": 0.62}[role]
    fill = {"primary": 0.86, "supporting": 0.76, "context": 0.48}[role]
    fill += {"sparse": 0.04, "normal": 0.0, "dense": -0.04, "very_dense": -0.09}[density]
    if semantic_role in {"parking", "commercial"}:
        opacity = max(opacity, 0.92)
        fill = max(fill, 0.72 if density == "very_dense" else 0.78)
    if semantic_role == "water":
        fill = max(fill, 0.72)
    return {"opacity": _clamp(opacity), "fill": _clamp(fill)}


def _point_defaults(
    density: str,
    role: str,
    semantic_role: Optional[str],
    style: Mapping[str, Any],
    explicit: Mapping[str, Any],
) -> Dict[str, Any]:
    default_fill = _default_color(role, semantic_role, "point")
    fill = str(_explicit_value(explicit, style, "fill_color", _explicit_value(explicit, style, "color", default_fill)))
    if "fill_color" in explicit and "color" in explicit:
        stroke = str(style.get("color"))
        category_stroke = "explicit"
    elif "color" in explicit:
        stroke = str(style.get("color"))
        category_stroke = "same"
    else:
        stroke = "#FFFFFF"
        category_stroke = "white"
    alpha = _point_opacity(role, semantic_role, density)
    return {
        "fill_color": fill,
        "stroke_color": stroke,
        "weight": float(_explicit_value(explicit, style, "weight", 0.9 if role != "context" else 0.75)),
        "opacity": _clamp(float(_explicit_value(explicit, style, "opacity", alpha["opacity"]))),
        "fill_opacity": _clamp(float(_explicit_value(explicit, style, "fill_opacity", alpha["fill"]))),
        "radius": float(_explicit_value(explicit, style, "radius", _POINT_RADIUS[density])),
        "category_stroke": category_stroke,
    }


def _line_defaults(
    density: str,
    role: str,
    semantic_role: Optional[str],
    style: Mapping[str, Any],
    explicit: Mapping[str, Any],
) -> Dict[str, Any]:
    weight = _LINE_WEIGHT[density]
    if role == "primary":
        weight += 0.30
    elif role == "context":
        weight *= 0.78
    if semantic_role == "study_boundary":
        weight = max(weight, 1.65)
    elif semantic_role in {"water", "pedestrian"}:
        weight = max(weight, 1.15)
    opacity_default = {"primary": 0.96, "supporting": 0.84, "context": 0.55}[role]
    if semantic_role in {"water", "pedestrian", "study_boundary"}:
        opacity_default = max(opacity_default, 0.86)
    return {
        "color": str(_explicit_value(explicit, style, "color", _default_color(role, semantic_role, "line"))),
        "weight": float(_explicit_value(explicit, style, "weight", weight)),
        "opacity": _clamp(float(_explicit_value(explicit, style, "opacity", opacity_default))),
        "category_stroke": "same",
    }


def _polygon_alpha(role: str, semantic_role: Optional[str], density: str) -> Dict[str, float]:
    generic_fill = {
        "primary": {"sparse": 0.50, "normal": 0.46, "dense": 0.41, "very_dense": 0.36},
        "supporting": {"sparse": 0.34, "normal": 0.30, "dense": 0.26, "very_dense": 0.22},
        "context": {"sparse": 0.19, "normal": 0.16, "dense": 0.13, "very_dense": 0.10},
    }[role][density]
    opacity = {"primary": 0.90, "supporting": 0.72, "context": 0.54}[role]
    if semantic_role == "water":
        generic_fill = {"sparse": 0.44, "normal": 0.40, "dense": 0.35, "very_dense": 0.31}[density]
        opacity = 0.88
    elif semantic_role == "green_space":
        generic_fill = {"sparse": 0.38, "normal": 0.34, "dense": 0.30, "very_dense": 0.26}[density]
        opacity = 0.82
    elif semantic_role == "parking":
        generic_fill = {"sparse": 0.44, "normal": 0.40, "dense": 0.36, "very_dense": 0.32}[density]
        opacity = 0.88
    elif semantic_role == "commercial":
        generic_fill = {"sparse": 0.42, "normal": 0.38, "dense": 0.34, "very_dense": 0.30}[density]
        opacity = 0.86
    elif semantic_role == "study_boundary":
        generic_fill = 0.07
        opacity = 0.92
    elif semantic_role == "area_boundary":
        generic_fill = 0.05
        opacity = 0.62
    return {"fill": generic_fill, "opacity": opacity}


def _polygon_defaults(
    density: str,
    role: str,
    semantic_role: Optional[str],
    style: Mapping[str, Any],
    explicit: Mapping[str, Any],
) -> Dict[str, Any]:
    default_fill = _default_color(role, semantic_role, "polygon")
    fill = str(_explicit_value(explicit, style, "fill_color", _explicit_value(explicit, style, "color", default_fill)))
    if "fill_color" in explicit and "color" in explicit:
        stroke = str(style.get("color"))
        category_stroke = "explicit"
    elif "color" in explicit:
        stroke = str(style.get("color"))
        category_stroke = "same"
    else:
        stroke_base = _default_color(role, semantic_role, "line")
        stroke = stroke_base if semantic_role else adjust_hex(fill, -0.22)
        category_stroke = "darken"
    alpha = _polygon_alpha(role, semantic_role, density)
    weight = _POLYGON_WEIGHT[density]
    if role == "primary":
        weight += 0.18
    elif role == "context":
        weight *= 0.86
    if semantic_role == "study_boundary":
        weight = max(weight, 1.75)
    elif semantic_role == "area_boundary":
        weight = max(weight, 0.85)
    elif semantic_role in {"water", "green_space", "parking", "commercial"}:
        weight = max(weight, 0.78)
    return {
        "fill_color": fill,
        "stroke_color": stroke,
        "weight": float(_explicit_value(explicit, style, "weight", weight)),
        "opacity": _clamp(float(_explicit_value(explicit, style, "opacity", alpha["opacity"]))),
        "fill_opacity": _clamp(float(_explicit_value(explicit, style, "fill_opacity", alpha["fill"]))),
        "category_stroke": category_stroke,
    }


def _pane(role: str, family: str) -> str:
    return f"imb-{role}-{family}"


def resolve_visual_plan(
    frame: gpd.GeoDataFrame,
    layer_spec: Mapping[str, Any],
    *,
    template: str,
    primary_layer: Optional[str],
    layer_count: int,
    layer_index: int,
    explicit_style: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    metrics = geometry_metrics(frame)
    counts = {family: values["features"] for family, values in metrics.items()}
    family = geometry_family(counts)
    representative = max(counts, key=lambda key: counts[key]) if family == "mixed" else family
    if representative not in {"point", "line", "polygon"}:
        representative = "polygon"
    role = visual_role(
        template=str(template),
        layer_id=str(layer_spec.get("id", "")),
        primary_layer=str(primary_layer) if primary_layer else None,
        family=representative,
        layer_count=int(layer_count),
    )
    semantic_role = infer_semantic_role(layer_spec)
    style = dict(layer_spec.get("style", {}))
    raw_explicit = dict(explicit_style if explicit_style is not None else style)
    explicit = {key: value for key, value in raw_explicit.items() if key in _VISUAL_KEYS}

    family_plans: Dict[str, Dict[str, Any]] = {}
    densities: Dict[str, str] = {}
    for name in ("polygon", "line", "point"):
        density = density_class(name, metrics[name]["features"], metrics[name]["coordinates"])
        densities[name] = density
        if name == "point":
            resolved = _point_defaults(density, role, semantic_role, style, explicit)
        elif name == "line":
            resolved = _line_defaults(density, role, semantic_role, style, explicit)
        else:
            resolved = _polygon_defaults(density, role, semantic_role, style, explicit)
        resolved["pane"] = _pane(role, name)
        resolved["draw_order"] = _PANE_ORDER[(role, name)] + min(max(int(layer_index), 0), 9)
        family_plans[name] = resolved

    categories = style.get("categories")
    category_count = len(categories) if isinstance(categories, Mapping) else 0
    primary_density = densities[representative]
    reasons = [
        f"{family} geometry",
        f"{len(frame)} feature(s)",
        f"{primary_density} density",
        f"{role} visual role",
    ]
    if semantic_role:
        reasons.append(f"{semantic_role} semantic role")
    if explicit:
        reasons.append("explicit MapSpec style preserved")

    # Focus should be immediately visible, particularly for polygon context layers.
    focus_opacity = {"primary": 1.08, "supporting": 1.22, "context": 1.70}[role]
    focus_fill = {"primary": 1.08, "supporting": 1.24, "context": 1.95}[role]
    if semantic_role in {"study_boundary", "area_boundary"}:
        focus_fill = 2.45
    dimmed_opacity = {"primary": 0.30, "supporting": 0.38, "context": 0.46}[role]
    dimmed_fill = {"primary": 0.24, "supporting": 0.32, "context": 0.40}[role]
    return {
        "system": "atlas-studio-light",
        "geometry_family": family,
        "representative_family": representative,
        "geometry_counts": counts,
        "geometry_metrics": metrics,
        "density": primary_density,
        "density_by_family": densities,
        "role": role,
        "semantic_role": semantic_role,
        "draw_order": family_plans[representative]["draw_order"],
        "families": family_plans,
        "states": {
            "focus": {
                "opacity_multiplier": focus_opacity,
                "fill_opacity_multiplier": focus_fill,
                "weight_add": 0.52 if role != "context" else 0.86,
                "radius_multiplier": 1.08,
            },
            "hover": {
                "opacity_multiplier": 1.12,
                "fill_opacity_multiplier": 1.14,
                "weight_add": 0.76,
                "radius_multiplier": 1.14,
            },
            "selected": {
                "opacity_multiplier": 1.18,
                "fill_opacity_multiplier": 1.20,
                "weight_add": 1.65,
                "radius_multiplier": 1.26,
                "stroke_color": "#173F4A",
            },
            "dimmed": {
                "opacity_multiplier": dimmed_opacity,
                "fill_opacity_multiplier": dimmed_fill,
                "weight_multiplier": 0.76,
                "radius_multiplier": 0.90,
            },
        },
        "category_count": category_count,
        "explicit_style_keys": sorted(str(key) for key in explicit),
        "reasons": reasons,
    }


__all__ = [
    "CATEGORICAL_PALETTE",
    "SEQUENTIAL_PALETTE",
    "adjust_hex",
    "density_class",
    "geometry_counts",
    "geometry_family",
    "geometry_metrics",
    "resolve_visual_plan",
    "visual_role",
]
