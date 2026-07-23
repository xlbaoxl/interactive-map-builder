#!/usr/bin/env python
"""Command-line entry point for interactive-map-builder."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import geopandas as gpd
import pandas as pd
from shapely.geometry import mapping

from mapcore.arcgis import ArcGISError, download_feature_service
from mapcore.inspect_data import (
    inspect_frame,
    inspect_inputs,
    inspection_summary,
    recommend_template,
)
from mapcore.loaders import DataLoadError, load_source
from mapcore.normalize import normalize_geodata
from mapcore.paths import resource_root
from mapcore.report import (
    environment_report,
    output_entry,
    sha256_file,
    validate_file_signature,
    write_usage_guide,
    write_json,
)
from mapcore.spec import SpecError, load_spec, write_resolved_spec
from mapcore.spec_init import SpecInitError, init_spec_from_inspection
from mapcore.style import StyleError, resolve_layer_style
from mapcore.validate import ValidationError, ensure_count_consistency, validate_geodata


class BuildError(RuntimeError):
    """Raised when a build cannot meet its declared contract."""


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
            return value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return str(value)


def _selected_fields(
    layer_spec: Mapping[str, Any],
    linked_view: Optional[Mapping[str, Any]],
    list_config: Optional[Mapping[str, Any]] = None,
) -> Set[str]:
    fields: Set[str] = set()
    for key in (
        "tooltip_fields",
        "popup_fields",
        "search_fields",
        "filter_fields",
        "card_fields",
        "sort_fields",
    ):
        fields.update(str(value) for value in layer_spec.get(key, []))
    for key in ("id_field", "label_field"):
        if layer_spec.get(key):
            fields.add(str(layer_spec[key]))
    style = layer_spec.get("style", {})
    if style.get("color_field"):
        fields.add(str(style["color_field"]))
    if linked_view and linked_view.get("layer") == layer_spec["id"]:
        fields.add(str(linked_view["x_field"]))
        fields.add(str(linked_view["y_field"]))
    if list_config:
        for metric in list_config.get("summary_metrics", []):
            if isinstance(metric, Mapping) and metric.get("field"):
                fields.add(str(metric["field"]))
    return fields


def _prepare_layer(
    raw: gpd.GeoDataFrame,
    layer_spec: Mapping[str, Any],
    linked_view: Optional[Mapping[str, Any]],
    list_config: Optional[Mapping[str, Any]],
) -> Tuple[gpd.GeoDataFrame, Dict[str, Any], Dict[str, Any]]:
    source_crs = layer_spec["source"].get("crs")
    if raw.crs is None and source_crs is not None:
        raw = raw.set_crs(source_crs)
    id_field = str(layer_spec.get("id_field") or "__map_id")
    label_field = layer_spec.get("label_field")
    id_attributes = [str(label_field)] if label_field and label_field in raw.columns else []
    normalized, normalization = normalize_geodata(
        raw,
        id_field=id_field,
        id_attributes=id_attributes,
        target_crs="EPSG:4326",
        id_prefix=str(layer_spec["id"]),
    )
    normalized, resolved_layer_spec, style_report = resolve_layer_style(normalized, layer_spec)
    if isinstance(layer_spec, dict):
        layer_spec.clear()
        layer_spec.update(resolved_layer_spec)

    render_data = normalized
    tolerance = layer_spec.get("simplify_tolerance")
    simplify_preset = str(layer_spec.get("simplify", "none"))
    if tolerance is not None and simplify_preset != "none":
        raise BuildError(
            "Layer {} declares both simplify and simplify_tolerance; choose one.".format(
                layer_spec["id"]
            )
        )
    if tolerance is None and simplify_preset in {"light", "medium"}:
        bounds = normalized.total_bounds
        diagonal = math.hypot(float(bounds[2] - bounds[0]), float(bounds[3] - bounds[1]))
        divisor = 5000.0 if simplify_preset == "light" else 2000.0
        tolerance = diagonal / divisor if diagonal > 0 else None
    simplified = False
    if tolerance is not None:
        render_data = normalized.copy()
        render_data.geometry = render_data.geometry.simplify(
            float(tolerance), preserve_topology=True
        )
        simplified = True

    required_fields = sorted(_selected_fields(layer_spec, linked_view, list_config))
    style = layer_spec.get("style", {})
    validation = validate_geodata(
        render_data,
        id_field=id_field,
        required_fields=required_fields,
        category_field=style.get("color_field"),
        allowed_categories=style.get("categories"),
        layer_name=str(layer_spec["id"]),
    )

    fields = [field for field in required_fields if field in render_data.columns]
    if id_field not in fields:
        fields.append(id_field)
    render_frame = render_data[fields + [render_data.geometry.name]].copy()
    properties: List[Dict[str, Any]] = []
    features: List[Dict[str, Any]] = []
    for _, row in render_frame.iterrows():
        values = {field: _json_value(row[field]) for field in fields}
        values["__map_id"] = str(row[id_field])
        values["__label"] = str(row[label_field]) if label_field else str(row[id_field])
        properties.append(values)
        features.append(
            {
                "type": "Feature",
                "id": str(row[id_field]),
                "geometry": mapping(row.geometry),
                "properties": values,
            }
        )
    bounds = render_frame.total_bounds.tolist()
    prepared = {
        "id": layer_spec["id"],
        "spec": dict(layer_spec),
        "feature_collection": {"type": "FeatureCollection", "features": features},
        "records": properties,
        "count": len(features),
        "bounds": bounds,
    }
    layer_report = {
        "id": layer_spec["id"],
        "name": layer_spec["name"],
        "input_count": int(len(raw)),
        "normalized_count": int(len(normalized)),
        "rendered_count": len(features),
        "simplified": simplified,
        "simplify_preset": simplify_preset,
        "simplify_tolerance": tolerance,
        "style": style_report,
        "normalization": normalization.to_dict(),
        "validation": validation.to_dict(),
    }
    return normalized, prepared, layer_report


def build_map(spec_path: Path, out_dir: Path) -> Dict[str, Any]:
    from mapcore.render_figure import render_static_figures
    from mapcore.render_html import render_html

    spec, base_dir = load_spec(spec_path)
    destination = out_dir.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    warnings: List[str] = []
    prepared_layers: List[Dict[str, Any]] = []
    static_layers: Dict[str, gpd.GeoDataFrame] = {}
    layer_reports: List[Dict[str, Any]] = []
    inspection_layers: List[Dict[str, Any]] = []

    for layer_spec in spec["layers"]:
        source_path = Path(layer_spec["source"]["path"])
        resolved_source = source_path if source_path.is_absolute() else base_dir / source_path
        try:
            raw = load_source(layer_spec["source"], base_dir=base_dir)
        except Exception as exc:
            if not layer_spec.get("required", True):
                warnings.append(f"Optional layer {layer_spec['id']} was skipped: {exc}")
                continue
            raise BuildError(f"Required layer {layer_spec['id']} failed to load: {exc}") from exc
        inspection_layers.append(
            inspect_frame(
                raw,
                layer_id=str(layer_spec["id"]),
                name=str(layer_spec["name"]),
                source={
                    key: value
                    for key, value in layer_spec["source"].items()
                    if key != "crs" or value is not None
                },
            )
        )
        normalized, prepared, layer_report = _prepare_layer(
            raw,
            layer_spec,
            spec.get("linked_view"),
            spec.get("list"),
        )
        if resolved_source.is_file():
            layer_report["source"] = {
                "path": str(source_path).replace("\\", "/"),
                "bytes": resolved_source.stat().st_size,
                "sha256": sha256_file(resolved_source),
            }
        prepared_layers.append(prepared)
        static_layers[str(layer_spec["id"])] = normalized
        layer_reports.append(layer_report)

    required_ids = {layer["id"] for layer in spec["layers"] if layer.get("required", True)}
    loaded_ids = {layer["id"] for layer in prepared_layers}
    missing_required = sorted(required_ids - loaded_ids)
    if missing_required:
        raise BuildError("Missing required layers: " + ", ".join(missing_required))
    if not prepared_layers:
        raise BuildError("No layers were available to render.")

    primary_count: Optional[int] = None
    if spec["template"] == "map-list":
        primary = next(
            (layer for layer in prepared_layers if layer["id"] == spec["primary_layer"]), None
        )
        if primary is None:
            raise BuildError("The primary layer was not loaded.")
        primary_count = ensure_count_consistency(
            normalized=int(primary["count"]),
            map_features=len(primary["feature_collection"]["features"]),
            list_records=len(primary["records"]),
        )

    vendor = resource_root() / "assets" / "vendor" / "leaflet-1.9.4"
    outputs_spec = spec.get("outputs", {})
    html_path = destination / outputs_spec.get("html", "map.html")
    html_result = render_html(
        spec,
        prepared_layers,
        html_path,
        (vendor / "leaflet.js").read_text(encoding="utf-8"),
        (vendor / "leaflet.css").read_text(encoding="utf-8"),
    )

    generated_paths: List[Path] = [html_path]
    static_result: Dict[str, Path] = {}
    if spec.get("static", {}).get("enabled", True):
        static_result = render_static_figures(static_layers, spec, destination)
        generated_paths.extend(static_result.values())

    resolved_spec_path = destination / outputs_spec.get("resolved_spec", "map_spec.json")
    write_resolved_spec(spec, resolved_spec_path)
    generated_paths.append(resolved_spec_path)

    inspection_path = destination / outputs_spec.get("inspection", "inspection.json")
    build_inspection = {
        "schema_version": "1.0",
        "inputs": [
            {
                "path": str(layer["source"]["path"]).replace("\\", "/"),
                "sha256": layer.get("source", {}).get("sha256"),
                "bytes": layer.get("source", {}).get("bytes"),
            }
            for layer in layer_reports
        ],
        "layers": inspection_layers,
    }
    build_inspection["template_recommendation"] = recommend_template(inspection_layers)
    write_json(build_inspection, inspection_path)
    generated_paths.append(inspection_path)

    usage_path = destination / outputs_spec.get("usage", "README_使用说明.md")
    write_usage_guide(
        usage_path,
        title=str(spec["title"]),
        html_name=html_path.name,
        figure_names=[path.name for path in static_result.values()],
        basemaps=spec.get("basemaps", []),
    )
    generated_paths.append(usage_path)

    for layer_report, prepared in zip(layer_reports, prepared_layers):
        ensure_count_consistency(
            input=layer_report["input_count"],
            normalized=layer_report["normalized_count"],
            rendered=prepared["count"],
        )

    report_path = destination / outputs_spec.get("report", "build_report.json")
    legend_item_count = sum(
        len(layer.get("style", {}).get("categories", {}))
        if isinstance(layer.get("style", {}).get("categories", {}), Mapping)
        else 0
        for layer in spec["layers"]
    )
    report: Dict[str, Any] = {
        "schema_version": "1.0",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": "0.1.0",
        "status": "pass",
        "template": spec["template"],
        "title": spec["title"],
        "environment": environment_report(),
        "layers": layer_reports,
        "checks": {
            "data_readable_and_nonempty": True,
            "crs_epsg_4326": True,
            "geometry_valid_and_nonempty": True,
            "unique_ids": True,
            "output_counts_consistent": True,
            "primary_count": primary_count,
            "declared_layer_count": len(spec["layers"]),
            "rendered_layer_count": len(prepared_layers),
            "list_record_count": primary_count,
            "legend_item_count": legend_item_count,
            "html_qa": html_result,
        },
        "warnings": warnings,
        "network_dependencies": [
            {"name": item["name"], "url": item["url"], "attribution": item["attribution"]}
            for item in spec.get("basemaps", [])
        ],
        "outputs": [output_entry(path) for path in generated_paths],
    }
    write_json(report, report_path)
    return {"report_path": str(report_path), "report": report}


def verify_dist(out_dir: Path) -> Dict[str, Any]:
    destination = out_dir.resolve()
    report_path = destination / "build_report.json"
    if not report_path.is_file():
        raise BuildError(f"Missing build report: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    errors: List[str] = []
    for entry in report.get("outputs", []):
        path = destination / entry["path"]
        if not path.is_file():
            errors.append(f"Missing output: {entry['path']}")
            continue
        if path.stat().st_size != entry["bytes"]:
            errors.append(f"Size mismatch: {entry['path']}")
        if sha256_file(path) != entry["sha256"]:
            errors.append(f"SHA-256 mismatch: {entry['path']}")
        if not validate_file_signature(path):
            errors.append(f"Invalid file signature: {entry['path']}")
    html_entries = [
        entry for entry in report.get("outputs", []) if str(entry.get("path", "")).lower().endswith(".html")
    ]
    for html_entry in html_entries:
        html_path = destination / html_entry["path"]
        html_text = html_path.read_text(encoding="utf-8")
        if "__interactiveMapBuilderQA" not in html_text:
            errors.append(f"HTML is missing the QA interface: {html_entry['path']}")
        if "https://unpkg.com/leaflet" in html_text or "cdnjs.cloudflare.com" in html_text:
            errors.append(f"HTML UI unexpectedly depends on a CDN: {html_entry['path']}")
    if errors:
        raise BuildError("Verification failed:\n- " + "\n- ".join(errors))
    return {
        "status": "pass",
        "verified_outputs": len(report.get("outputs", [])),
        "report": str(report_path),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="interactive-map-builder",
        description="Build lightweight interactive maps and report-ready figures.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect", help="Inspect one or more supported local inputs."
    )
    inspect_parser.add_argument("inputs", nargs="+")
    inspect_parser.add_argument("--layer")
    inspect_parser.add_argument("--sheet")
    inspect_parser.add_argument("--crs")
    inspect_parser.add_argument("--x")
    inspect_parser.add_argument("--y")
    inspect_parser.add_argument("--wkt")
    inspect_parser.add_argument("--encoding", default="utf-8")
    inspect_parser.add_argument("--output", "--out", dest="output")

    init_parser = subparsers.add_parser(
        "init-spec", help="Create a minimal MapSpec from inspection JSON."
    )
    init_parser.add_argument("inspection", nargs="?")
    init_parser.add_argument("--inspection", dest="inspection_option")
    init_parser.add_argument(
        "--template", choices=("auto", "map-list", "multilayer"), default="auto"
    )
    init_parser.add_argument("--title")
    init_parser.add_argument("--output", "--out", dest="output", default="map_spec.json")

    fetch_parser = subparsers.add_parser(
        "fetch-arcgis", help="Download a FeatureServer layer to local GeoJSON."
    )
    fetch_parser.add_argument("--url", required=True)
    fetch_parser.add_argument("--out", required=True)
    fetch_parser.add_argument("--where", default="1=1")
    fetch_parser.add_argument("--out-fields", default="*")
    fetch_parser.add_argument("--batch-size", type=int, default=200)
    fetch_parser.add_argument("--provenance")

    build_parser = subparsers.add_parser("build", help="Build from a map specification.")
    build_parser.add_argument("spec_path", nargs="?")
    build_parser.add_argument("--spec", dest="spec_option")
    build_parser.add_argument("--output", "--out", dest="output", default="dist")

    verify_parser = subparsers.add_parser("verify", help="Verify a built output directory.")
    verify_parser.add_argument("--dist", default="dist")

    run_parser = subparsers.add_parser(
        "run", help="Inspect, initialize, and build when choices are unambiguous."
    )
    run_parser.add_argument("inputs", nargs="+")
    run_parser.add_argument(
        "--template", choices=("auto", "map-list", "multilayer"), default="auto"
    )
    run_parser.add_argument("--title")
    run_parser.add_argument("--layer")
    run_parser.add_argument("--sheet")
    run_parser.add_argument("--crs")
    run_parser.add_argument("--x")
    run_parser.add_argument("--y")
    run_parser.add_argument("--wkt")
    run_parser.add_argument("--encoding", default="utf-8")
    run_parser.add_argument("--output", "--out", dest="output", default="dist")
    return parser


def _inspection_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    return inspect_inputs(
        args.inputs,
        layer=args.layer,
        sheet=args.sheet,
        crs=args.crs,
        x_field=args.x,
        y_field=args.y,
        wkt_field=args.wkt,
        encoding=args.encoding,
    )


def _required_path(primary: Optional[str], secondary: Optional[str], label: str) -> Path:
    value = primary or secondary
    if not value:
        raise BuildError("{} is required.".format(label))
    return Path(value)


def _copy_run_inputs(inputs: Sequence[str], destination: Path) -> List[str]:
    data_dir = destination / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    copied: List[str] = []
    used = set()
    for index, value in enumerate(inputs):
        source = Path(value).expanduser().resolve()
        if not source.is_file():
            raise BuildError("Input does not exist: {}".format(source))
        name = source.name
        if name.casefold() in used:
            name = "{}-{}{}".format(source.stem, index + 1, source.suffix)
        used.add(name.casefold())
        target = data_dir / name
        if source != target.resolve():
            shutil.copy2(source, target)
        copied.append(str(target))
    return copied


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inspect":
            result = _inspection_from_args(args)
            if args.output:
                write_json(result, Path(args.output))
            print(inspection_summary(result))
            print()
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "init-spec":
            inspection_path = _required_path(
                args.inspection, args.inspection_option, "inspection path"
            )
            inspection = json.loads(inspection_path.read_text(encoding="utf-8"))
            output_path = Path(args.output)
            spec = init_spec_from_inspection(
                inspection,
                spec_path=output_path,
                template=args.template,
                title=args.title,
            )
            write_json(spec, output_path)
            print(
                json.dumps(
                    {
                        "status": "pass",
                        "template": spec["template"],
                        "layers": len(spec["layers"]),
                        "output": str(output_path.resolve()),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "fetch-arcgis":
            fields = args.out_fields if args.out_fields == "*" else args.out_fields.split(",")
            result = download_feature_service(
                args.url,
                args.out,
                where=args.where,
                out_fields=fields,
                batch_size=args.batch_size,
                provenance_path=args.provenance,
            )
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        elif args.command == "build":
            spec_path = _required_path(args.spec_path, args.spec_option, "spec path")
            result = build_map(spec_path, Path(args.output))
            print(
                json.dumps(
                    {
                        "status": "pass",
                        "report": result["report_path"],
                        "outputs": [
                            entry["path"] for entry in result["report"].get("outputs", [])
                        ]
                        + [Path(result["report_path"]).name],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "verify":
            print(json.dumps(verify_dist(Path(args.dist)), ensure_ascii=False, indent=2))
        elif args.command == "run":
            destination = Path(args.output).resolve()
            destination.mkdir(parents=True, exist_ok=True)
            copied_inputs = _copy_run_inputs(args.inputs, destination)
            inspection = inspect_inputs(
                copied_inputs,
                layer=args.layer,
                sheet=args.sheet,
                crs=args.crs,
                x_field=args.x,
                y_field=args.y,
                wkt_field=args.wkt,
                encoding=args.encoding,
            )
            inspection_path = destination / "inspection.json"
            write_json(inspection, inspection_path)
            spec_path = destination / "map_spec.json"
            spec = init_spec_from_inspection(
                inspection,
                spec_path=spec_path,
                template=args.template,
                title=args.title,
            )
            write_json(spec, spec_path)
            result = build_map(spec_path, destination)
            print(
                json.dumps(
                    {
                        "status": "pass",
                        "template": spec["template"],
                        "report": result["report_path"],
                        "outputs": [
                            entry["path"] for entry in result["report"].get("outputs", [])
                        ]
                        + [Path(result["report_path"]).name],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return 0
    except (
        ArcGISError,
        BuildError,
        DataLoadError,
        SpecError,
        SpecInitError,
        StyleError,
        ValidationError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
