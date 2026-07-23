"""Inspect supported inputs and infer useful MapSpec field candidates."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import geopandas as gpd
import pandas as pd

from .loaders import DataLoadError, load_geodata
from .report import sha256_file


LONGITUDE_NAMES = (
    "longitude",
    "longitude_wgs84",
    "lon",
    "lng",
    "x",
    "经度",
)
LATITUDE_NAMES = (
    "latitude",
    "latitude_wgs84",
    "lat",
    "y",
    "纬度",
)
WKT_NAMES = ("wkt", "geometry", "geom", "几何")


def _json_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        missing = pd.isna(value)
        if isinstance(missing, bool) and missing:
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _deduplicate(values: Iterable[str], limit: int = 12) -> List[str]:
    output: List[str] = []
    seen = set()
    for value in values:
        if value and value not in seen:
            output.append(value)
            seen.add(value)
        if len(output) >= limit:
            break
    return output


def _name_matches(name: str, tokens: Sequence[str]) -> bool:
    folded = name.casefold()
    return any(token in folded for token in tokens)


def _exact_aliases(columns: Sequence[str], aliases: Sequence[str]) -> List[str]:
    alias_order = {alias.casefold(): index for index, alias in enumerate(aliases)}
    matches = [name for name in columns if name.casefold() in alias_order]
    return sorted(matches, key=lambda name: (alias_order[name.casefold()], name.casefold()))


def _field_summaries(table: pd.DataFrame, geometry_name: Optional[str] = None) -> List[Dict[str, Any]]:
    summaries: List[Dict[str, Any]] = []
    for column in table.columns:
        name = str(column)
        if geometry_name is not None and name == geometry_name:
            continue
        series = table[column]
        non_null = series.dropna()
        comparable = non_null.map(_json_value)
        unique_count = int(comparable.nunique(dropna=True))
        distinct = comparable.drop_duplicates()
        item = {
            "name": name,
            "dtype": str(series.dtype),
            "non_null_count": int(non_null.size),
            "unique_count": unique_count,
            "unique_ratio": round(unique_count / max(int(non_null.size), 1), 6),
            "sample_values": [_json_value(value) for value in distinct.head(3).tolist()],
        }
        if unique_count <= 20:
            item["values"] = [_json_value(value) for value in distinct.tolist()]
        summaries.append(item)
    return summaries


def infer_field_candidates(
    table: pd.DataFrame,
    *,
    geometry_name: Optional[str] = None,
) -> Dict[str, List[str]]:
    """Rank fields for common map roles without silently choosing among ties."""

    summaries = _field_summaries(table, geometry_name)
    columns = [item["name"] for item in summaries]
    by_name = {item["name"]: item for item in summaries}
    row_count = max(len(table), 1)

    id_tokens = ("id", "code", "编号", "编码", "代码")
    label_tokens = ("name", "title", "名称", "项目", "社区", "地点")
    category_tokens = (
        "status",
        "type",
        "class",
        "kind",
        "category",
        "district",
        "borough",
        "region",
        "状态",
        "类型",
        "类别",
        "行政区",
        "街道",
    )
    search_tokens = ("name", "title", "address", "code", "id", "名称", "地址", "编号", "编码")

    def id_score(name: str) -> Tuple[int, float, str]:
        item = by_name[name]
        name_score = 2 if _name_matches(name, id_tokens) else 0
        unique_score = 1 if item["unique_ratio"] >= 0.98 else 0
        return (name_score + unique_score, item["unique_ratio"], name.casefold())

    id_fields = [
        name
        for name in columns
        if (
            _name_matches(name, id_tokens)
            or (
                by_name[name]["unique_ratio"] >= 0.98
                and by_name[name]["non_null_count"] >= int(row_count * 0.95)
            )
        )
    ]
    id_fields.sort(key=id_score, reverse=True)

    text_fields = [
        name
        for name in columns
        if (
            pd.api.types.is_string_dtype(table[name])
            or pd.api.types.is_object_dtype(table[name])
        )
    ]
    label_fields = [
        name
        for name in text_fields
        if _name_matches(name, label_tokens) or by_name[name]["unique_ratio"] >= 0.2
    ]
    label_fields.sort(
        key=lambda name: (
            1 if _name_matches(name, label_tokens) else 0,
            by_name[name]["unique_ratio"],
            name.casefold(),
        ),
        reverse=True,
    )

    category_fields = [
        name
        for name in columns
        if (
            1 < by_name[name]["unique_count"] <= min(50, max(8, int(row_count * 0.2)))
            and (
                _name_matches(name, category_tokens)
                or (
                    by_name[name]["unique_ratio"] <= 0.5
                    and (
                        name in text_fields
                        or pd.api.types.is_integer_dtype(table[name])
                    )
                )
            )
        )
    ]
    category_fields.sort(
        key=lambda name: (
            1 if _name_matches(name, category_tokens) else 0,
            -by_name[name]["unique_count"],
            name.casefold(),
        ),
        reverse=True,
    )

    numeric_fields = [
        name
        for name in columns
        if pd.api.types.is_numeric_dtype(table[name])
        and name.casefold()
        not in {alias.casefold() for alias in LONGITUDE_NAMES + LATITUDE_NAMES}
    ]
    search_fields = _deduplicate(
        list(label_fields)
        + [name for name in columns if _name_matches(name, search_tokens)]
        + list(id_fields)
    )
    filter_fields = _deduplicate(category_fields, limit=8)
    card_fields = _deduplicate(
        list(label_fields[:1]) + list(category_fields[:2]) + list(numeric_fields[:2]),
        limit=6,
    )

    return {
        "id": _deduplicate(id_fields),
        "label": _deduplicate(label_fields),
        "category": _deduplicate(category_fields),
        "numeric": _deduplicate(numeric_fields),
        "search": search_fields,
        "filter": filter_fields,
        "card": card_fields,
        "longitude": _exact_aliases(columns, LONGITUDE_NAMES),
        "latitude": _exact_aliases(columns, LATITUDE_NAMES),
        "wkt": _exact_aliases(columns, WKT_NAMES),
    }


def inspect_frame(
    frame: gpd.GeoDataFrame,
    *,
    layer_id: str,
    name: str,
    source: Mapping[str, Any],
) -> Dict[str, Any]:
    geometry_name = frame.geometry.name
    candidates = infer_field_candidates(frame, geometry_name=geometry_name)
    geometry_types = (
        sorted(str(value) for value in frame.geometry.geom_type.dropna().unique().tolist())
        if len(frame)
        else []
    )
    bounds = None
    if len(frame) and frame.geometry.notna().any() and not frame.geometry.is_empty.all():
        bounds = [_json_value(value) for value in frame.total_bounds.tolist()]
    return {
        "layer_id": layer_id,
        "name": name,
        "source": dict(source),
        "feature_count": int(len(frame)),
        "non_empty_geometry_count": int(
            sum(geometry is not None and not geometry.is_empty for geometry in frame.geometry)
        ),
        "geometry_types": geometry_types,
        "crs": frame.crs.to_string() if frame.crs is not None else None,
        "bounds": bounds,
        "fields": _field_summaries(frame, geometry_name),
        "candidates": candidates,
    }


def inspect_table(
    table: pd.DataFrame,
    *,
    layer_id: str,
    name: str,
    source: Mapping[str, Any],
    crs: Optional[str],
) -> Dict[str, Any]:
    candidates = infer_field_candidates(table)
    issues = []
    if not crs:
        issues.append("Tabular geometry requires an explicit source CRS.")
    lonlat_ready = len(candidates["longitude"]) == 1 and len(candidates["latitude"]) == 1
    wkt_ready = len(candidates["wkt"]) == 1
    if not lonlat_ready and not wkt_ready:
        issues.append("Confirm one longitude/latitude pair or one WKT field.")
    elif lonlat_ready and wkt_ready:
        issues.append("Both coordinate and WKT mappings are plausible; choose one.")
    return {
        "layer_id": layer_id,
        "name": name,
        "source": dict(source),
        "feature_count": int(len(table)),
        "non_empty_geometry_count": None,
        "geometry_types": [],
        "crs": crs,
        "bounds": None,
        "fields": _field_summaries(table),
        "candidates": candidates,
        "blocking_issues": issues,
    }


def _safe_layer_id(name: str, index: int, used: set) -> str:
    candidate = re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-_")
    if not candidate or not candidate[0].isalpha():
        candidate = "layer-{}".format(index + 1)
    base = candidate
    counter = 2
    while candidate in used:
        candidate = "{}-{}".format(base, counter)
        counter += 1
    used.add(candidate)
    return candidate


def _list_gpkg_layers(path: Path) -> List[str]:
    try:
        import pyogrio

        return [str(row[0]) for row in pyogrio.list_layers(path)]
    except Exception as exc:
        raise DataLoadError("Could not list GeoPackage layers: {}".format(exc)) from exc


def _input_record(path: Path, supplied: str) -> Dict[str, Any]:
    return {
        "input": supplied.replace("\\", "/"),
        "resolved_path": str(path).replace("\\", "/"),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def recommend_template(layers: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    reasons: List[str] = []
    geometry_families = set()
    for layer in layers:
        for geometry_type in layer.get("geometry_types", []):
            folded = str(geometry_type).casefold()
            if "point" in folded:
                geometry_families.add("point")
            elif "line" in folded:
                geometry_families.add("line")
            elif "polygon" in folded:
                geometry_families.add("polygon")
    if len(layers) > 1:
        reasons.append("Multiple input layers benefit from independent visibility controls.")
    if len(geometry_families) > 1:
        reasons.append("Mixed geometry families are best compared in a multilayer explorer.")
    if len(layers) > 1 or len(geometry_families) > 1:
        return {"template": "multilayer", "reasons": reasons}

    reasons.append("One primary layer can be browsed record by record.")
    if layers:
        candidates = layers[0].get("candidates", {})
        if candidates.get("label") or candidates.get("id"):
            reasons.append("A likely label or ID field supports searchable list cards.")
        if candidates.get("filter"):
            reasons.append("Low-cardinality fields can drive list filters.")
    return {"template": "map-list", "reasons": reasons}


def inspect_inputs(
    inputs: Sequence[str],
    *,
    layer: Optional[str] = None,
    sheet: Optional[str] = None,
    crs: Optional[str] = None,
    x_field: Optional[str] = None,
    y_field: Optional[str] = None,
    wkt_field: Optional[str] = None,
    encoding: str = "utf-8",
) -> Dict[str, Any]:
    """Inspect one or more supported inputs without guessing CRS or ambiguous geometry."""

    if not inputs:
        raise DataLoadError("At least one input is required.")
    if len(inputs) > 1 and (layer is not None or sheet is not None):
        raise DataLoadError("--layer and --sheet can only be used when inspecting one input.")

    result: Dict[str, Any] = {
        "schema_version": "1.0",
        "inputs": [],
        "layers": [],
    }
    used_layer_ids: set = set()

    for input_index, supplied in enumerate(inputs):
        source_path = Path(supplied).expanduser().resolve()
        if not source_path.is_file():
            raise DataLoadError("Input does not exist: {}".format(source_path))
        result["inputs"].append(_input_record(source_path, supplied))
        suffix = source_path.suffix.lower()

        if suffix == ".gpkg":
            names = [layer] if layer is not None else _list_gpkg_layers(source_path)
            for name in names:
                frame = load_geodata(source_path, layer=name)
                layer_id = _safe_layer_id(str(name), len(result["layers"]), used_layer_ids)
                result["layers"].append(
                    inspect_frame(
                        frame,
                        layer_id=layer_id,
                        name=str(name),
                        source={
                            "input_index": input_index,
                            "path": supplied.replace("\\", "/"),
                            "layer": str(name),
                        },
                    )
                )
            continue

        if suffix in {".csv", ".xlsx", ".xls"}:
            if suffix == ".csv":
                tables = [(source_path.stem, pd.read_csv(source_path, encoding=encoding))]
            else:
                workbook = pd.ExcelFile(source_path)
                names = [sheet] if sheet is not None else list(workbook.sheet_names)
                tables = [
                    (str(name), pd.read_excel(source_path, sheet_name=name))
                    for name in names
                ]
            for table_name, table in tables:
                source: Dict[str, Any] = {
                    "input_index": input_index,
                    "path": supplied.replace("\\", "/"),
                }
                if suffix in {".xlsx", ".xls"}:
                    source["sheet"] = table_name
                layer_id = _safe_layer_id(table_name, len(result["layers"]), used_layer_ids)
                if (x_field and y_field) or wkt_field:
                    frame = load_geodata(
                        source_path,
                        lon_field=x_field,
                        lat_field=y_field,
                        wkt_field=wkt_field,
                        crs=crs,
                        encoding=encoding,
                        sheet_name=table_name if suffix in {".xlsx", ".xls"} else 0,
                    )
                    if x_field and y_field:
                        source["geometry"] = {
                            "type": "lonlat",
                            "x_field": x_field,
                            "y_field": y_field,
                        }
                    else:
                        source["geometry"] = {"type": "wkt", "wkt_field": wkt_field}
                    source["crs"] = crs
                    result["layers"].append(
                        inspect_frame(
                            frame,
                            layer_id=layer_id,
                            name=table_name,
                            source=source,
                        )
                    )
                else:
                    result["layers"].append(
                        inspect_table(
                            table,
                            layer_id=layer_id,
                            name=table_name,
                            source=source,
                            crs=crs,
                        )
                    )
            continue

        frame = load_geodata(source_path, encoding=encoding)
        if frame.crs is None and crs:
            frame = frame.set_crs(crs)
        layer_id = _safe_layer_id(source_path.stem, len(result["layers"]), used_layer_ids)
        result["layers"].append(
            inspect_frame(
                frame,
                layer_id=layer_id,
                name=source_path.stem,
                source={
                    "input_index": input_index,
                    "path": supplied.replace("\\", "/"),
                },
            )
        )

    result["template_recommendation"] = recommend_template(result["layers"])
    return result


def inspection_summary(inspection: Mapping[str, Any]) -> str:
    """Return a compact, readable summary suitable for the Skill's first round."""

    layers = inspection.get("layers", [])
    lines = ["Found {} candidate layer(s):".format(len(layers))]
    for index, layer in enumerate(layers, start=1):
        candidates = layer.get("candidates", {})
        lines.extend(
            [
                "",
                "{}. {} ({})".format(index, layer.get("name"), layer.get("layer_id")),
                "   - Features: {}".format(layer.get("feature_count")),
                "   - Geometry: {}".format(
                    ", ".join(layer.get("geometry_types", [])) or "not mapped yet"
                ),
                "   - CRS: {}".format(layer.get("crs") or "needs confirmation"),
                "   - Suggested ID: {}".format(", ".join(candidates.get("id", [])[:3]) or "generated"),
                "   - Suggested label: {}".format(", ".join(candidates.get("label", [])[:3]) or "none"),
                "   - Suggested category: {}".format(
                    ", ".join(candidates.get("category", [])[:3]) or "none"
                ),
            ]
        )
        for issue in layer.get("blocking_issues", []):
            lines.append("   - Needs confirmation: {}".format(issue))
    recommendation = inspection.get("template_recommendation", {})
    lines.extend(
        [
            "",
            "Recommended template: {}".format(recommendation.get("template", "map-list")),
        ]
    )
    lines.extend("- {}".format(reason) for reason in recommendation.get("reasons", []))
    return "\n".join(lines)


__all__ = [
    "infer_field_candidates",
    "inspect_frame",
    "inspect_inputs",
    "inspect_table",
    "inspection_summary",
    "recommend_template",
]
