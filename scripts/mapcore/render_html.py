"""Render prepared geospatial layers as a self-contained Leaflet HTML page."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from .paths import resource_root


PathLike = Union[str, Path]
_TEMPLATE_FILES = {
    "map-list": "map-list.html.j2",
    "multilayer": "multilayer.html.j2",
}


def _asset_directory() -> Path:
    return resource_root() / "assets" / "templates"


def _read_inline_asset(value: PathLike, label: str) -> str:
    """Accept either inline source text or a path to source text."""

    if isinstance(value, Path):
        if not value.is_file():
            raise FileNotFoundError(f"{label} asset does not exist: {value}")
        return value.read_text(encoding="utf-8")
    if not isinstance(value, str):
        raise TypeError(f"{label} must be source text or a filesystem path")
    if "\n" not in value and "\r" not in value:
        try:
            candidate = Path(value)
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        except OSError:
            # Long inline source can be an invalid Windows path; it is still valid source.
            pass
    return value


def _jsonable(value: Any) -> Any:
    """Convert common geospatial/scientific values to strict JSON values."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        return [_jsonable(item) for item in sorted(value, key=str)]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_jsonable(item) for item in value]

    geo_interface = getattr(value, "__geo_interface__", None)
    if geo_interface is not None:
        return _jsonable(geo_interface)

    item_method = getattr(value, "item", None)
    if callable(item_method):
        try:
            item = item_method()
        except (TypeError, ValueError):
            item = value
        if item is not value:
            return _jsonable(item)

    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        try:
            return isoformat()
        except (TypeError, ValueError):
            pass

    raise TypeError(f"Value of type {type(value).__name__} is not JSON serializable")


def _get_layer_value(layer: Any, key: str, default: Any = None) -> Any:
    if isinstance(layer, Mapping):
        return layer.get(key, default)
    return getattr(layer, key, default)


def _coerce_layers(prepared_layers: Any) -> List[Dict[str, Any]]:
    if isinstance(prepared_layers, Mapping):
        if "feature_collection" in prepared_layers:
            raw_layers: Iterable[Any] = [prepared_layers]
        else:
            raw_layers = prepared_layers.values()
    else:
        raw_layers = prepared_layers

    normalized: List[Dict[str, Any]] = []
    for index, raw_layer in enumerate(raw_layers):
        layer_spec = _get_layer_value(raw_layer, "spec", {})
        feature_collection = _get_layer_value(raw_layer, "feature_collection")
        if feature_collection is None:
            raise ValueError(f"Prepared layer {index + 1} has no feature_collection")
        feature_collection = _jsonable(feature_collection)
        if not isinstance(feature_collection, Mapping):
            raise TypeError(f"Prepared layer {index + 1} feature_collection must be an object")
        features = feature_collection.get("features")
        if not isinstance(features, list):
            raise ValueError(
                f"Prepared layer {index + 1} feature_collection must contain a features array"
            )
        records = _get_layer_value(raw_layer, "records")
        if records is None:
            records = [
                feature.get("properties", {})
                for feature in features
                if isinstance(feature, Mapping)
            ]
        count = _get_layer_value(raw_layer, "count", len(features))
        normalized.append(
            {
                "spec": _jsonable(layer_spec or {}),
                "feature_collection": feature_collection,
                "records": _jsonable(records),
                "count": int(count),
                "bounds": _jsonable(_get_layer_value(raw_layer, "bounds")),
            }
        )
    if not normalized:
        raise ValueError("At least one prepared layer is required")
    return normalized


def _template_name(spec: Mapping[str, Any]) -> str:
    configured: Any = spec.get("template")
    if isinstance(configured, Mapping):
        configured = configured.get("name") or configured.get("type")
    if not configured:
        html_options = spec.get("html")
        if isinstance(html_options, Mapping):
            configured = html_options.get("template")
    name = str(configured or "").strip().lower()
    if name not in _TEMPLATE_FILES:
        supported = ", ".join(sorted(_TEMPLATE_FILES))
        raise ValueError(f"Unsupported HTML template {name!r}; choose one of: {supported}")
    return name


def _layer_keys(layer_spec: Mapping[str, Any]) -> set:
    return {
        str(layer_spec[key])
        for key in ("id", "layer_id", "name")
        if layer_spec.get(key) not in (None, "")
    }


def _validate_required_layers(
    template_name: str,
    spec: Mapping[str, Any],
    layers: List[Dict[str, Any]],
) -> None:
    if template_name != "multilayer":
        return
    declared = spec.get("layers")
    if not isinstance(declared, list):
        return
    prepared_keys = set()
    for layer in layers:
        layer_spec = layer.get("spec")
        if isinstance(layer_spec, Mapping):
            prepared_keys.update(_layer_keys(layer_spec))
    for index, declared_layer in enumerate(declared):
        if not isinstance(declared_layer, Mapping) or not declared_layer.get("required"):
            continue
        required_keys = _layer_keys(declared_layer)
        if required_keys and prepared_keys.isdisjoint(required_keys):
            expected = sorted(required_keys)[0]
            raise ValueError(f"Required multilayer input is missing: {expected}")
        if not required_keys and index >= len(layers):
            raise ValueError(f"Required multilayer input at position {index + 1} is missing")


def _safe_json_script(value: Any) -> str:
    """Serialize JSON without allowing data to close its script element."""

    serialized = json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return (
        serialized.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _safe_script_source(source: str) -> str:
    return re.sub(r"</script", r"<\\/script", source, flags=re.IGNORECASE)


def _safe_style_source(source: str) -> str:
    return re.sub(r"</style", r"<\\/style", source, flags=re.IGNORECASE)


def _language(spec: Mapping[str, Any]) -> str:
    configured = str(spec.get("language") or spec.get("locale") or "zh-CN")
    if re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", configured):
        return configured
    return "zh-CN"


def render_html(
    spec: Mapping[str, Any],
    prepared_layers: Any,
    out_path: PathLike,
    leaflet_js: PathLike,
    leaflet_css: PathLike,
) -> Dict[str, Any]:
    """Render one of the bundled Leaflet templates to a single UTF-8 HTML file.

    ``prepared_layers`` may be a sequence or a name-to-layer mapping. Each layer
    must expose ``spec``, ``feature_collection``, ``records``, ``count``, and
    ``bounds`` either as mapping keys or attributes.
    """

    if not isinstance(spec, Mapping):
        raise TypeError("spec must be a mapping")
    selected_template = _template_name(spec)
    layers = _coerce_layers(prepared_layers)
    _validate_required_layers(selected_template, spec, layers)

    assets = _asset_directory()
    environment = Environment(
        loader=FileSystemLoader(str(assets)),
        autoescape=select_autoescape(("html", "j2")),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    template = environment.get_template(_TEMPLATE_FILES[selected_template])
    payload = {
        "version": "1.0",
        "template": selected_template,
        "spec": _jsonable(spec),
        "layers": layers,
    }
    rendered = template.render(
        language=_language(spec),
        page_title=str(spec.get("title") or "Interactive map"),
        payload_json=_safe_json_script(payload),
        leaflet_js=_safe_script_source(_read_inline_asset(leaflet_js, "Leaflet JavaScript")),
        leaflet_css=_safe_style_source(_read_inline_asset(leaflet_css, "Leaflet CSS")),
        shared_js=_safe_script_source(
            (assets / "shared.js").read_text(encoding="utf-8")
        ),
        shared_css=_safe_style_source(
            (assets / "shared.css").read_text(encoding="utf-8")
        ),
    )

    destination = Path(out_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as output:
        output.write(rendered)
    layer_counts = {}
    for index, layer in enumerate(layers):
        layer_spec = layer.get("spec", {})
        identifier = (
            layer_spec.get("id")
            or layer_spec.get("layer_id")
            or layer_spec.get("name")
            or f"layer-{index + 1}"
        )
        layer_counts[str(identifier)] = int(layer["count"])
    return {
        "path": destination.name,
        "template": selected_template,
        "single_file": True,
        "leaflet_embedded": True,
        "qa_interface": "__interactiveMapBuilderQA",
        "feature_count": sum(layer_counts.values()),
        "layer_counts": layer_counts,
    }


__all__ = ["render_html"]
