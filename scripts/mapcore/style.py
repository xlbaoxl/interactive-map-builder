"""Resolve shared single, categorical, and graduated map styles."""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, MutableMapping, Sequence, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, to_hex


class StyleError(ValueError):
    """Raised when a declared style cannot be applied deterministically."""


_DEFAULT_GRADUATED_COLORS = ("#eff3ff", "#6baed6", "#08519c")


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        return str(value)
    if abs(value) >= 1000:
        return "{:,.0f}".format(value)
    if abs(value) >= 10:
        return "{:.1f}".format(value).rstrip("0").rstrip(".")
    return "{:.3f}".format(value).rstrip("0").rstrip(".")


def _strict_breaks(values: Sequence[float]) -> np.ndarray:
    result = np.asarray([float(value) for value in values], dtype=float)
    if result.ndim != 1 or len(result) < 3:
        raise StyleError("Graduated breaks must contain at least three numeric boundaries.")
    if not np.isfinite(result).all() or np.any(np.diff(result) <= 0):
        raise StyleError("Graduated breaks must be finite and strictly increasing.")
    return result


def _computed_breaks(values: pd.Series, method: str, classes: int) -> np.ndarray:
    raw = values.to_numpy(dtype=float)
    if method == "quantile":
        result = np.quantile(raw, np.linspace(0, 1, classes + 1))
    elif method == "equal_interval":
        minimum = float(np.min(raw))
        maximum = float(np.max(raw))
        result = np.linspace(minimum, maximum, classes + 1)
    else:
        raise StyleError("Unknown graduated method: {}".format(method))
    result = np.unique(result)
    if len(result) < 2:
        value = float(result[0])
        delta = max(abs(value) * 0.01, 0.5)
        result = np.asarray([value - delta, value + delta])
    return result


def _colors(values: Sequence[str], count: int) -> Sequence[str]:
    configured = [str(value) for value in values] if values else list(_DEFAULT_GRADUATED_COLORS)
    if len(configured) == count:
        return configured
    cmap = LinearSegmentedColormap.from_list("interactive-map-builder", configured)
    if count == 1:
        return [to_hex(cmap(0.5), keep_alpha=False)]
    return [to_hex(cmap(index / (count - 1)), keep_alpha=False) for index in range(count)]


def resolve_layer_style(
    frame: gpd.GeoDataFrame,
    layer_spec: Mapping[str, Any],
) -> Tuple[gpd.GeoDataFrame, Dict[str, Any], Dict[str, Any]]:
    """Resolve a layer style into the categorical contract shared by both renderers."""

    resolved_layer = dict(layer_spec)
    style = dict(resolved_layer.get("style", {}))
    mode = str(style.get("mode") or ("categorical" if style.get("color_field") else "single"))
    if mode != "graduated":
        style["mode"] = mode
        resolved_layer["style"] = style
        return frame, resolved_layer, {"mode": mode}

    field = str(style.get("field") or style.get("color_field") or "")
    if not field or field not in frame.columns:
        raise StyleError("Graduated style field is missing: {!r}".format(field))
    numeric = pd.to_numeric(frame[field], errors="coerce")
    invalid = frame.index[frame[field].notna() & numeric.isna()].tolist()
    if invalid:
        raise StyleError(
            "Graduated field {!r} contains non-numeric values at index(es): {}".format(
                field, ", ".join(str(value) for value in invalid[:10])
            )
        )
    valid = numeric.dropna()
    if valid.empty:
        raise StyleError("Graduated field {!r} contains no numeric values.".format(field))

    method = str(style.get("method", "quantile"))
    requested_classes = int(style.get("classes", 5))
    if method == "custom_breaks":
        breaks = _strict_breaks(style.get("breaks", []))
        if float(valid.min()) < breaks[0] or float(valid.max()) > breaks[-1]:
            raise StyleError("Custom breaks must include the full observed value range.")
    else:
        breaks = _computed_breaks(valid, method, requested_classes)

    class_count = len(breaks) - 1
    labels = [
        "{} – {}".format(_format_number(breaks[index]), _format_number(breaks[index + 1]))
        for index in range(class_count)
    ]
    palette = list(_colors(style.get("colors", []), class_count))
    missing_label = "Missing"
    derived_field = "__imb_class"
    while derived_field in frame.columns:
        derived_field += "_"
    classified = pd.cut(
        numeric,
        bins=breaks,
        labels=labels,
        include_lowest=True,
        duplicates="drop",
    ).astype("object")
    classified = classified.where(numeric.notna(), missing_label)

    resolved_frame = frame.copy()
    resolved_frame[derived_field] = classified
    categories = {label: palette[index] for index, label in enumerate(labels)}
    if numeric.isna().any():
        categories[missing_label] = str(style.get("missing_color", "#9ca3af"))

    style.update(
        {
            "mode": "graduated",
            "field": field,
            "method": method,
            "classes": class_count,
            "breaks": [float(value) for value in breaks],
            "colors": palette,
            "color_field": derived_field,
            "categories": categories,
        }
    )
    resolved_layer["style"] = style
    report = {
        "mode": "graduated",
        "field": field,
        "method": method,
        "requested_classes": requested_classes,
        "resolved_classes": class_count,
        "breaks": [float(value) for value in breaks],
        "categories": categories,
        "missing_count": int(numeric.isna().sum()),
    }
    return resolved_frame, resolved_layer, report


__all__ = ["StyleError", "resolve_layer_style"]
