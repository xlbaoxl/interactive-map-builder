"""Render report-ready static maps from the same layer styles as the HTML map.

The public entry point is :func:`render_static_figures`.  It deliberately
accepts already-loaded GeoDataFrames so that reading, repair and validation
remain the responsibility of the common data pipeline.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


OUTPUT_NAMES = {
    "slide_png": "map_slide_16x9.png",
    "paper_png": "map_paper.png",
    "paper_svg": "map_paper.svg",
    "paper_pdf": "map_paper.pdf",
}


class StaticFigureOutputs(dict):
    """Path mapping with non-file renderer metadata attached."""

    def __init__(self, paths: Mapping[str, Path], font_report: Mapping[str, Any]) -> None:
        super().__init__(paths)
        self.font_report = dict(font_report)


_CJK_FONTS = (
    "Noto Sans CJK SC",
    "Noto Sans SC",
    "Microsoft YaHei",
    "SimHei",
    "Arial Unicode MS",
)


def _contains_cjk(value: Any) -> bool:
    return bool(re.search(r"[\u3400-\u9fff\uf900-\ufaff]", str(value)))


def _configure_fonts(spec: Mapping[str, Any]) -> Dict[str, Any]:
    """Select an installed CJK font and report portable fallback state."""

    installed = {item.name for item in font_manager.fontManager.ttflist}
    selected = next((name for name in _CJK_FONTS if name in installed), None)
    rcParams["font.family"] = "sans-serif"
    rcParams["font.sans-serif"] = ([selected] if selected else []) + ["DejaVu Sans"]
    rcParams["axes.unicode_minus"] = False
    cjk_requested = _contains_cjk(spec)
    warning = None
    if cjk_requested and selected is None:
        warning = (
            "Static figure text contains CJK characters, but no supported CJK font was found."
        )
    return {
        "font": selected or "DejaVu Sans",
        "cjk_text_detected": cjk_requested,
        "cjk_font_found": selected is not None,
        "warning": warning,
    }

_DEFAULT_STYLES = {
    "point": {
        "color": "#d1495b",
        "stroke_color": "#ffffff",
        "size": 42,
        "weight": 0.8,
        "opacity": 0.95,
        "marker": "o",
        "zorder": 30,
    },
    "line": {
        "color": "#40566e",
        "weight": 2.2,
        "opacity": 0.9,
        "zorder": 20,
    },
    "polygon": {
        "fill_color": "#7ca6d8",
        "stroke_color": "#ffffff",
        "weight": 1.0,
        "fill_opacity": 0.78,
        "opacity": 1.0,
        "zorder": 10,
    },
}


def _normalise_layers(layers: Any) -> Dict[str, gpd.GeoDataFrame]:
    """Return an insertion-ordered mapping of names to GeoDataFrames."""
    normalised: Dict[str, gpd.GeoDataFrame] = {}
    if isinstance(layers, Mapping):
        iterator: Iterable[Tuple[str, Any]] = layers.items()
    elif isinstance(layers, Sequence) and not isinstance(layers, (str, bytes)):
        pairs: List[Tuple[str, Any]] = []
        for index, item in enumerate(layers):
            if isinstance(item, tuple) and len(item) == 2:
                pairs.append((str(item[0]), item[1]))
            elif isinstance(item, Mapping) and "gdf" in item:
                pairs.append((str(item.get("name", "layer_%d" % index)), item["gdf"]))
            else:
                pairs.append(("layer_%d" % index, item))
        iterator = pairs
    else:
        raise TypeError("layers must be a mapping or a sequence of GeoDataFrames")

    for name, frame in iterator:
        if not isinstance(frame, gpd.GeoDataFrame):
            raise TypeError("layer %r is not a GeoDataFrame" % name)
        if frame.crs is None:
            raise ValueError("layer %r has no CRS; assign it before rendering" % name)
        normalised[str(name)] = frame
    if not normalised:
        raise ValueError("at least one layer is required")
    if not any(not frame.empty for frame in normalised.values()):
        raise ValueError("all layers are empty")
    return normalised


def _layer_name(layer_spec: Mapping[str, Any], index: int) -> str:
    return str(layer_spec.get("id") or layer_spec.get("name") or "layer_%d" % index)


def _ordered_layers(
    layers: Mapping[str, gpd.GeoDataFrame], spec: Mapping[str, Any]
) -> List[Tuple[str, gpd.GeoDataFrame, Mapping[str, Any]]]:
    specs = spec.get("layers", [])
    if not isinstance(specs, list):
        raise ValueError("spec.layers must be an array")

    result: List[Tuple[str, gpd.GeoDataFrame, Mapping[str, Any]]] = []
    used = set()
    for index, raw in enumerate(specs):
        if not isinstance(raw, Mapping):
            raise ValueError("every spec.layers item must be an object")
        name = _layer_name(raw, index)
        if name not in layers:
            if raw.get("required", True):
                raise ValueError("required layer %r is missing" % name)
            continue
        result.append((name, layers[name], raw))
        used.add(name)
    for name, frame in layers.items():
        if name not in used:
            result.append((name, frame, {"name": name, "label": name, "style": {}}))
    return result


def _plot_crs(frames: Iterable[gpd.GeoDataFrame]) -> Any:
    """Prefer a local metric CRS, with Web Mercator as a safe fallback."""
    for frame in frames:
        if frame.empty:
            continue
        try:
            wgs84 = frame.to_crs("EPSG:4326")
            estimated = wgs84.estimate_utm_crs()
            if estimated is not None:
                return estimated
        except (ValueError, RuntimeError):
            pass
    return "EPSG:3857"


def _style_mapping(layer_spec: Mapping[str, Any]) -> Dict[str, Any]:
    raw = layer_spec.get("style", {})
    return dict(raw) if isinstance(raw, Mapping) else {}


def _category_config(
    layer_spec: Mapping[str, Any], spec: Mapping[str, Any]
) -> Tuple[Any, Mapping[str, Any]]:
    style = _style_mapping(layer_spec)
    field = style.get("color_field")
    categories = style.get("categories") or {}
    if not isinstance(categories, Mapping):
        categories = {}
    return field, categories


def _geometry_family(geometry_types: Iterable[str]) -> str:
    values = {str(value).lower() for value in geometry_types}
    if any("polygon" in value for value in values):
        return "polygon"
    if any("line" in value for value in values):
        return "line"
    return "point"


def _canonical_style(family: str, raw: Mapping[str, Any]) -> Dict[str, Any]:
    style = dict(_DEFAULT_STYLES[family])
    style.update(raw)
    if family == "polygon" and "color" in raw and "fill_color" not in raw:
        style["fill_color"] = raw["color"]
    if family == "point" and "radius" in style and "size" not in raw:
        radius = float(style["radius"])
        style["size"] = max(8.0, radius * radius * 1.5)
    return style


def _rule_style(rule: Any) -> Dict[str, Any]:
    if isinstance(rule, str):
        return {"color": rule, "fill_color": rule}
    if isinstance(rule, Mapping):
        result = dict(rule)
        if "label" in result:
            result.pop("label")
        return result
    return {}


def _rule_label(value: Any, rule: Any) -> str:
    if isinstance(rule, Mapping) and rule.get("label"):
        return str(rule["label"])
    return str(value)


def _plot_subset(
    axis: Any, frame: gpd.GeoDataFrame, family: str, raw_style: Mapping[str, Any]
) -> None:
    style = _canonical_style(family, raw_style)
    common = {
        "ax": axis,
        "alpha": float(style.get("opacity", 1.0)),
        "zorder": float(style.get("zorder", _DEFAULT_STYLES[family]["zorder"])),
    }
    if family == "polygon":
        frame.plot(
            facecolor=style.get("fill_color", style.get("color")),
            edgecolor=style.get("stroke_color", style.get("color", "#ffffff")),
            linewidth=float(style.get("weight", 1.0)),
            alpha=float(style.get("fill_opacity", style.get("opacity", 1.0))),
            **{key: value for key, value in common.items() if key != "alpha"}
        )
    elif family == "line":
        frame.plot(
            color=style.get("color", "#40566e"),
            linewidth=float(style.get("weight", 2.0)),
            **common
        )
    else:
        frame.plot(
            color=style.get("color", style.get("fill_color", "#d1495b")),
            edgecolor=style.get("stroke_color", "#ffffff"),
            linewidth=float(style.get("weight", 0.8)),
            markersize=float(style.get("size", 42)),
            marker=str(style.get("marker", "o")),
            **common
        )


def _legend_handle(family: str, style_raw: Mapping[str, Any], label: str) -> Any:
    style = _canonical_style(family, style_raw)
    if family == "polygon":
        return Patch(
            facecolor=style.get("fill_color"),
            edgecolor=style.get("stroke_color"),
            linewidth=float(style.get("weight", 1.0)),
            alpha=float(style.get("fill_opacity", 1.0)),
            label=label,
        )
    if family == "line":
        return Line2D(
            [0],
            [0],
            color=style.get("color"),
            linewidth=float(style.get("weight", 2.0)),
            alpha=float(style.get("opacity", 1.0)),
            label=label,
        )
    return Line2D(
        [0],
        [0],
        linestyle="",
        marker=str(style.get("marker", "o")),
        markerfacecolor=style.get("color", style.get("fill_color")),
        markeredgecolor=style.get("stroke_color"),
        markersize=max(5.0, math.sqrt(float(style.get("size", 42)))),
        alpha=float(style.get("opacity", 1.0)),
        label=label,
    )


def _plot_layers(
    axis: Any,
    layers: Sequence[Tuple[str, gpd.GeoDataFrame, Mapping[str, Any]]],
    spec: Mapping[str, Any],
    destination_crs: Any,
) -> List[Any]:
    handles: List[Any] = []
    legend_keys = set()
    for name, original, layer_spec in layers:
        if original.empty or layer_spec.get("visible", True) is False:
            continue
        frame = original.to_crs(destination_crs)
        frame = frame.loc[~frame.geometry.is_empty & frame.geometry.notna()].copy()
        if frame.empty:
            continue
        base_style = _style_mapping(layer_spec)
        field, categories = _category_config(layer_spec, spec)
        groups: List[Tuple[Any, gpd.GeoDataFrame, Any]]
        if field and field in frame.columns and categories:
            groups = []
            for value, subset in frame.groupby(field, dropna=False, sort=False):
                rule = categories.get(str(value), categories.get(value, {}))
                groups.append((value, subset, rule))
        else:
            groups = [(None, frame, {})]

        for value, group, rule in groups:
            combined = dict(base_style)
            combined.update(_rule_style(rule))
            families = group.geom_type.map(lambda item: _geometry_family([item]))
            for family in ("polygon", "line", "point"):
                subset = group.loc[families == family]
                if subset.empty:
                    continue
                _plot_subset(axis, subset, family, combined)
                label = (
                    _rule_label(value, rule)
                    if value is not None
                    else str(layer_spec.get("label") or name)
                )
                legend_key = (family, label)
                if legend_key not in legend_keys:
                    handles.append(_legend_handle(family, combined, label))
                    legend_keys.add(legend_key)
    return handles


def _nice_distance(target: float) -> float:
    if not math.isfinite(target) or target <= 0:
        return 1.0
    power = 10.0 ** math.floor(math.log10(target))
    scaled = target / power
    factor = 1.0 if scaled < 2 else 2.0 if scaled < 5 else 5.0
    return factor * power


def _add_scale_bar(axis: Any) -> None:
    x_min, x_max = axis.get_xlim()
    y_min, y_max = axis.get_ylim()
    width = x_max - x_min
    height = y_max - y_min
    distance = _nice_distance(width * 0.18)
    start_x = x_min + width * 0.055
    y = y_min + height * 0.065
    axis.plot(
        [start_x, start_x + distance],
        [y, y],
        color="#17202a",
        linewidth=3,
        solid_capstyle="butt",
        zorder=100,
    )
    axis.plot(
        [start_x, start_x],
        [y - height * 0.008, y + height * 0.008],
        color="#17202a",
        linewidth=1.2,
        zorder=100,
    )
    axis.plot(
        [start_x + distance, start_x + distance],
        [y - height * 0.008, y + height * 0.008],
        color="#17202a",
        linewidth=1.2,
        zorder=100,
    )
    label = "≈ %.1f km" % (distance / 1000.0) if distance < 10000 else "≈ %d km" % round(distance / 1000.0)
    if distance < 1000:
        label = "≈ %d m" % round(distance)
    axis.text(
        start_x + distance / 2.0,
        y + height * 0.018,
        label,
        ha="center",
        va="bottom",
        fontsize=8,
        color="#17202a",
        zorder=100,
    )


def _add_north_arrow(axis: Any) -> None:
    axis.annotate(
        "N",
        xy=(0.94, 0.91),
        xytext=(0.94, 0.80),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        color="#17202a",
        arrowprops={"arrowstyle": "-|>", "color": "#17202a", "lw": 1.4},
        zorder=100,
    )


def _render_canvas(
    layers: Sequence[Tuple[str, gpd.GeoDataFrame, Mapping[str, Any]]],
    spec: Mapping[str, Any],
    destination_crs: Any,
    figsize: Tuple[float, float],
) -> Any:
    static = spec.get("static", {})
    if not isinstance(static, Mapping):
        static = {}
    figure, axis = plt.subplots(figsize=figsize, facecolor="#ffffff")
    figure.subplots_adjust(left=0.025, right=0.975, top=0.91, bottom=0.085)
    axis.set_facecolor(str(static.get("background", "#f5f7f9")))
    handles = _plot_layers(axis, layers, spec, destination_crs)
    axis.margins(x=0.05, y=0.07)
    axis.set_aspect("equal", adjustable="datalim")
    axis.set_axis_off()

    if static.get("legend", True) and handles:
        axis.legend(
            handles=handles,
            loc="lower right",
            frameon=True,
            framealpha=0.94,
            facecolor="#ffffff",
            edgecolor="#d9dee5",
            fontsize=8,
            title=static.get("legend_title"),
            title_fontsize=9,
        )
    if static.get("north_arrow", True):
        _add_north_arrow(axis)
    if static.get("scale_bar", True):
        _add_scale_bar(axis)

    title = static.get("title") or spec.get("title") or "Interactive map"
    axis.set_title(str(title), loc="left", fontsize=15, fontweight="bold", pad=12)
    source = (
        static.get("source_note")
        or "Source: not specified"
    )
    source_text = str(source)
    if not source_text.lower().startswith("source"):
        source_text = "Source: " + source_text
    figure.text(0.025, 0.025, source_text, ha="left", va="bottom", fontsize=7, color="#566573")
    figure.text(
        0.975,
        0.025,
        "Scale is approximate",
        ha="right",
        va="bottom",
        fontsize=7,
        color="#7b8794",
    )
    return figure


def render_static_figures(
    layers: Any, spec: Mapping[str, Any], out_dir: Any
) -> StaticFigureOutputs:
    """Render the fixed slide and publication figure bundle.

    Parameters
    ----------
    layers:
        Mapping of layer names to validated GeoDataFrames, or a sequence of
        ``(name, GeoDataFrame)`` pairs.
    spec:
        Parsed map spec.  ``layers[*].style`` drives both category colors and
        base geometry styling; ``color_field`` selects categorical styling.
    out_dir:
        Destination directory. It is created when needed.

    Returns
    -------
    dict
        Keys are ``slide_png``, ``paper_png``, ``paper_svg`` and
        ``paper_pdf``; values are paths to the created files.
    """
    if not isinstance(spec, Mapping):
        raise TypeError("spec must be a mapping")
    font_report = _configure_fonts(spec)
    normalised = _normalise_layers(layers)
    ordered = _ordered_layers(normalised, spec)
    destination_crs = _plot_crs(frame for _, frame, _ in ordered)
    destination = Path(out_dir)
    destination.mkdir(parents=True, exist_ok=True)
    presets = set(spec.get("static", {}).get("presets", ["slide-16x9", "paper"]))
    paths: Dict[str, Path] = {}

    if "slide-16x9" in presets:
        paths["slide_png"] = destination / OUTPUT_NAMES["slide_png"]
        slide = _render_canvas(ordered, spec, destination_crs, (12.8, 7.2))
        slide.savefig(
            str(paths["slide_png"]),
            format="png",
            dpi=150,
            metadata={"Software": "interactive-map-builder"},
        )
        plt.close(slide)

    if "paper" in presets:
        for key in ("paper_png", "paper_svg", "paper_pdf"):
            paths[key] = destination / OUTPUT_NAMES[key]
        paper = _render_canvas(ordered, spec, destination_crs, (7.2, 5.4))
        paper.savefig(
            str(paths["paper_png"]),
            format="png",
            dpi=300,
            metadata={"Software": "interactive-map-builder"},
        )
        paper.savefig(
            str(paths["paper_svg"]),
            format="svg",
            metadata={"Creator": "interactive-map-builder", "Date": None},
        )
        paper.savefig(
            str(paths["paper_pdf"]),
            format="pdf",
            metadata={
                "Creator": "interactive-map-builder",
                "CreationDate": None,
                "ModDate": None,
            },
        )
        plt.close(paper)
    return StaticFigureOutputs(paths, font_report)


__all__ = ["OUTPUT_NAMES", "render_static_figures"]
