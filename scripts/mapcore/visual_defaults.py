"""Lightweight, renderer-neutral visual defaults for Atlas Studio Light.

The resolver deliberately stays small: it distinguishes geometry families,
uses coarse feature/coordinate density, assigns a simple layer role, and fills
only visual values that MapSpec did not explicitly provide. It does not infer
domain meaning or replace user/Agent design choices.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

import geopandas as gpd
import shapely


CATEGORICAL_PALETTE = (
    "#4E8587",  # teal
    "#D39A4A",  # ochre
    "#8C739B",  # muted violet
    "#C56E79",  # rose
    "#718F61",  # moss
    "#607F9D",  # slate blue
    "#A67D62",  # warm brown
    "#7C8588",  # neutral gray
)

SEQUENTIAL_PALETTE = ("#EDF4F2", "#8DB8B3", "#285F62")

_ROLE_COLORS = {
    "primary": {
        "point": "#C45F78",
        "line": "#28786F",
        "polygon": "#5F9294",
    },
    "supporting": {
        "point": "#6E8791",
        "line": "#59747A",
        "polygon": "#8FA8A4",
    },
    "context": {
        "point": "#95A1A3",
        "line": "#879497",
        "polygon": "#B7C2BF",
    },
}

_POINT_RADIUS = {
    "sparse": 5.0,
    "normal": 4.1,
    "dense": 3.2,
    "very_dense": 2.4,
}

_LINE_WEIGHT = {
    "sparse": 1.70,
    "normal": 1.35,
    "dense": 1.02,
    "very_dense": 0.76,
}

_POLYGON_WEIGHT = {
    "sparse": 0.95,
    "normal": 0.75,
    "dense": 0.55,
    "very_dense": 0.38,
}

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

_VISUAL_KEYS = {
    "color",
    "fill_color",
    "weight",
    "opacity",
    "fill_opacity",
    "radius",
}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


def adjust_hex(color: str, amount: float) -> str:
    """Lighten (positive) or darken (negative) a six-digit hex color."""

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
    return "#{:02X}{:02X}{:02X}".format(
        *[max(0, min(255, item)) for item in resolved]
    )


def geometry_metrics(frame: gpd.GeoDataFrame) -> Dict[str, Dict[str, int]]:
    """Return feature and coordinate counts for point, line, and polygon families."""

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
    return {
        family: values["features"]
        for family, values in geometry_metrics(frame).items()
    }


def geometry_family(counts: Mapping[str, int]) -> str:
    populated = [name for name, count in counts.items() if int(count) > 0]
    if len(populated) == 1:
        return populated[0]
    if not populated:
        return "unknown"
    return "mixed"


def density_class(
    family: str,
    feature_count: int,
    coordinate_count: Optional[int] = None,
) -> str:
    """Resolve one coarse density class without substantive spatial analysis."""

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
    for label, (feature_limit, coordinate_limit) in zip(
        ("sparse", "normal", "dense"), thresholds
    ):
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
    """Assign only the minimum hierarchy needed for a coordinated first render."""

    if template == "map-list":
        return "primary" if layer_id == primary_layer else "context"
    if int(layer_count) <= 1:
        return "primary"
    if family == "polygon":
        return "context"
    return "supporting"


def _explicit_value(
    explicit_style: Mapping[str, Any],
    resolved_style: Mapping[str, Any],
    key: str,
    fallback: Any,
) -> Any:
    if key in explicit_style:
        return resolved_style.get(key, explicit_style[key])
    return fallback


def _point_defaults(
    density: str,
    role: str,
    style: Mapping[str, Any],
    explicit: Mapping[str, Any],
) -> Dict[str, Any]:
    default_fill = _ROLE_COLORS[role]["point"]
    fill = str(
        _explicit_value(
            explicit,
            style,
            "fill_color",
            _explicit_value(explicit, style, "color", default_fill),
        )
    )
    if "fill_color" in explicit and "color" in explicit:
        stroke = str(style.get("color"))
        category_stroke = "explicit"
    elif "color" in explicit:
        stroke = str(style.get("color"))
        category_stroke = "same"
    else:
        stroke = "#FFFFFF"
        category_stroke = "white"
    opacity_default = {"primary": 0.96, "supporting": 0.82, "context": 0.48}[role]
    fill_default = {"primary": 0.82, "supporting": 0.70, "context": 0.34}[role]
    fill_default += {
        "sparse": 0.04,
        "normal": 0.0,
        "dense": -0.06,
        "very_dense": -0.13,
    }[density]
    return {
        "fill_color": fill,
        "stroke_color": stroke,
        "weight": float(
            _explicit_value(
                explicit,
                style,
                "weight",
                0.9 if role != "context" else 0.65,
            )
        ),
        "opacity": _clamp(
            float(_explicit_value(explicit, style, "opacity", opacity_default))
        ),
        "fill_opacity": _clamp(
            float(_explicit_value(explicit, style, "fill_opacity", fill_default))
        ),
        "radius": float(
            _explicit_value(explicit, style, "radius", _POINT_RADIUS[density])
        ),
        "category_stroke": category_stroke,
    }


def _line_defaults(
    density: str,
    role: str,
    style: Mapping[str, Any],
    explicit: Mapping[str, Any],
) -> Dict[str, Any]:
    weight = _LINE_WEIGHT[density]
    if role == "primary":
        weight += 0.25
    elif role == "context":
        weight *= 0.70
    opacity_default = {"primary": 0.94, "supporting": 0.74, "context": 0.36}[role]
    return {
        "color": str(
            _explicit_value(explicit, style, "color", _ROLE_COLORS[role]["line"])
        ),
        "weight": float(_explicit_value(explicit, style, "weight", weight)),
        "opacity": _clamp(
            float(_explicit_value(explicit, style, "opacity", opacity_default))
        ),
        "category_stroke": "same",
    }


def _polygon_defaults(
    density: str,
    role: str,
    style: Mapping[str, Any],
    explicit: Mapping[str, Any],
) -> Dict[str, Any]:
    default_fill = _ROLE_COLORS[role]["polygon"]
    fill = str(
        _explicit_value(
            explicit,
            style,
            "fill_color",
            _explicit_value(explicit, style, "color", default_fill),
        )
    )
    if "fill_color" in explicit and "color" in explicit:
        stroke = str(style.get("color"))
        category_stroke = "explicit"
    elif "color" in explicit:
        stroke = str(style.get("color"))
        category_stroke = "same"
    else:
        stroke = adjust_hex(fill, -0.22)
        category_stroke = "darken"
    fill_default = {
        "primary": {
            "sparse": 0.46,
            "normal": 0.43,
            "dense": 0.38,
            "very_dense": 0.33,
        },
        "supporting": {
            "sparse": 0.27,
            "normal": 0.23,
            "dense": 0.19,
            "very_dense": 0.15,
        },
        "context": {
            "sparse": 0.14,
            "normal": 0.11,
            "dense": 0.09,
            "very_dense": 0.07,
        },
    }[role][density]
    opacity_default = {"primary": 0.84, "supporting": 0.58, "context": 0.34}[role]
    weight = _POLYGON_WEIGHT[density]
    if role == "primary":
        weight += 0.15
    elif role == "context":
        weight *= 0.72
    return {
        "fill_color": fill,
        "stroke_color": stroke,
        "weight": float(_explicit_value(explicit, style, "weight", weight)),
        "opacity": _clamp(
            float(_explicit_value(explicit, style, "opacity", opacity_default))
        ),
        "fill_opacity": _clamp(
            float(_explicit_value(explicit, style, "fill_opacity", fill_default))
        ),
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
    """Return one deterministic visual plan shared by HTML and static renderers."""

    metrics = geometry_metrics(frame)
    counts = {family: values["features"] for family, values in metrics.items()}
    family = geometry_family(counts)
    representative = (
        max(counts, key=lambda key: counts[key]) if family == "mixed" else family
    )
    if representative not in {"point", "line", "polygon"}:
        representative = "polygon"
    role = visual_role(
        template=str(template),
        layer_id=str(layer_spec.get("id", "")),
        primary_layer=str(primary_layer) if primary_layer else None,
        family=representative,
        layer_count=int(layer_count),
    )
    style = dict(layer_spec.get("style", {}))
    raw_explicit = dict(explicit_style if explicit_style is not None else style)
    explicit = {
        key: value for key, value in raw_explicit.items() if key in _VISUAL_KEYS
    }

    family_plans: Dict[str, Dict[str, Any]] = {}
    densities: Dict[str, str] = {}
    for name in ("polygon", "line", "point"):
        density = density_class(
            name,
            metrics[name]["features"],
            metrics[name]["coordinates"],
        )
        densities[name] = density
        if name == "point":
            resolved = _point_defaults(density, role, style, explicit)
        elif name == "line":
            resolved = _line_defaults(density, role, style, explicit)
        else:
            resolved = _polygon_defaults(density, role, style, explicit)
        resolved["pane"] = _pane(role, name)
        resolved["draw_order"] = _PANE_ORDER[(role, name)] + min(
            max(int(layer_index), 0), 9
        )
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
    if explicit:
        reasons.append("explicit MapSpec style preserved")

    focus_opacity = {"primary": 1.04, "supporting": 1.14, "context": 1.38}[role]
    focus_fill = {"primary": 1.04, "supporting": 1.14, "context": 1.52}[role]
    dimmed_opacity = {"primary": 0.34, "supporting": 0.46, "context": 0.72}[role]
    dimmed_fill = {"primary": 0.28, "supporting": 0.40, "context": 0.78}[role]
    return {
        "system": "atlas-studio-light",
        "geometry_family": family,
        "geometry_counts": counts,
        "geometry_metrics": metrics,
        "density": primary_density,
        "density_by_family": densities,
        "role": role,
        "draw_order": family_plans[representative]["draw_order"],
        "families": family_plans,
        "states": {
            "focus": {
                "opacity_multiplier": focus_opacity,
                "fill_opacity_multiplier": focus_fill,
                "weight_add": 0.34 if role != "context" else 0.46,
                "radius_multiplier": 1.06,
            },
            "hover": {
                "opacity_multiplier": 1.12,
                "fill_opacity_multiplier": 1.12,
                "weight_add": 0.72,
                "radius_multiplier": 1.14,
            },
            "selected": {
                "opacity_multiplier": 1.18,
                "fill_opacity_multiplier": 1.18,
                "weight_add": 1.55,
                "radius_multiplier": 1.26,
                "stroke_color": "#173F4A",
            },
            "dimmed": {
                "opacity_multiplier": dimmed_opacity,
                "fill_opacity_multiplier": dimmed_fill,
                "weight_multiplier": 0.82,
                "radius_multiplier": 0.94,
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
