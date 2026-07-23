from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from map_builder import build_map, main
from mapcore.inspect_data import inspect_inputs, inspection_summary
from mapcore.spec_init import SpecInitError, init_spec_from_inspection


def _write_csv(path: Path) -> None:
    pd.DataFrame(
        {
            "编号": ["A-1", "A-2", "A-3"],
            "名称": ["甲地", "乙地", "丙地"],
            "状态": ["开放", "评估", "开放"],
            "score": [91, 72, 84],
            "经度": [118.10, 118.20, 118.30],
            "纬度": [39.60, 39.65, 39.70],
        }
    ).to_csv(path, index=False, encoding="utf-8")


def test_inspect_csv_reports_samples_candidates_reasons_and_summary(tmp_path: Path) -> None:
    source = tmp_path / "点位.csv"
    _write_csv(source)

    inspection = inspect_inputs([str(source)], crs="EPSG:4326")
    assert inspection["template_recommendation"]["recommended"] == "map-list"
    assert inspection["template_recommendation"]["needs_confirmation"] is False
    assert inspection["template_recommendation"]["reasons"]
    layer = inspection["layers"][0]
    assert layer["candidates"]["longitude"] == ["经度"]
    assert layer["candidates"]["latitude"] == ["纬度"]
    assert layer["candidates"]["id"][0] == "编号"
    assert layer["candidates"]["label"][0] == "名称"
    assert layer["candidates"]["category"][0] == "状态"
    status = next(field for field in layer["fields"] if field["name"] == "状态")
    assert status["sample_values"] == ["开放", "评估"]
    assert status["values"] == ["开放", "评估"]
    summary = inspection_summary(inspection)
    assert "Recommended template: map-list" in summary
    assert "Suggested label: 名称" in summary


def test_init_spec_consumes_inspection_and_builds_csv_end_to_end(tmp_path: Path) -> None:
    source = tmp_path / "places.csv"
    _write_csv(source)
    inspection = inspect_inputs([str(source)], crs="EPSG:4326")
    project = tmp_path / "project"
    spec_path = project / "map_spec.json"
    spec = init_spec_from_inspection(
        inspection,
        spec_path=spec_path,
        template="auto",
        title="点位检查示例",
    )
    project.mkdir()
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    assert spec["layers"][0]["source"]["geometry"] == {
        "type": "lonlat",
        "x_field": "经度",
        "y_field": "纬度",
    }
    result = build_map(spec_path, tmp_path / "dist")
    assert result["report"]["checks"]["primary_count"] == 3
    assert (tmp_path / "dist" / "inspection.json").is_file()
    assert (tmp_path / "dist" / "README_使用说明.md").is_file()


def test_init_spec_stops_for_ambiguous_tabular_geometry(tmp_path: Path) -> None:
    source = tmp_path / "ambiguous.csv"
    pd.DataFrame(
        {
            "name": ["A", "B"],
            "lon": [1, 2],
            "longitude": [1, 2],
            "lat": [3, 4],
        }
    ).to_csv(source, index=False)
    inspection = inspect_inputs([str(source)], crs="EPSG:4326")
    with pytest.raises(SpecInitError, match="ambiguous tabular geometry"):
        init_spec_from_inspection(inspection, spec_path=tmp_path / "map_spec.json")


def test_multiple_inputs_require_template_confirmation(tmp_path: Path) -> None:
    paths = []
    for index in range(2):
        path = tmp_path / "layer-{}.geojson".format(index)
        gpd.GeoDataFrame(
            {"id": ["P{}".format(index)], "name": ["Layer {}".format(index)]},
            geometry=[Point(118 + index * 0.1, 39.6)],
            crs="EPSG:4326",
        ).to_file(path, driver="GeoJSON")
        paths.append(str(path))
    inspection = inspect_inputs(paths)
    assert len(inspection["layers"]) == 2
    recommendation = inspection["template_recommendation"]
    assert recommendation["recommended"] is None
    assert recommendation["template_candidates"] == ["map-list", "multilayer"]
    assert recommendation["needs_confirmation"] is True
    with pytest.raises(SpecInitError, match="explicit --template"):
        init_spec_from_inspection(
            inspection,
            spec_path=tmp_path / "map_spec.json",
            template="auto",
        )
    with pytest.raises(SpecInitError, match="requires --primary-layer"):
        init_spec_from_inspection(
            inspection,
            spec_path=tmp_path / "map_spec.json",
            template="map-list",
        )
    spec = init_spec_from_inspection(
        inspection,
        spec_path=tmp_path / "map_spec.json",
        template="map-list",
        primary_layer="layer-1",
    )
    assert spec["primary_layer"] == "layer-1"


def test_cli_three_step_workflow_and_output_listing(tmp_path: Path, capsys) -> None:
    source = tmp_path / "places.csv"
    _write_csv(source)
    inspection_path = tmp_path / "inspection.json"
    spec_path = tmp_path / "map_spec.json"
    dist = tmp_path / "dist"

    assert main(
        [
            "inspect",
            str(source),
            "--crs",
            "EPSG:4326",
            "--output",
            str(inspection_path),
        ]
    ) == 0
    assert main(
        [
            "init-spec",
            str(inspection_path),
            "--output",
            str(spec_path),
        ]
    ) == 0
    assert main(["build", str(spec_path), "--output", str(dist)]) == 0
    output = capsys.readouterr().out
    assert '"outputs"' in output
    assert "map.html" in output
    assert "README_使用说明.md" in output


def test_run_quick_path_bundles_a_portable_input_copy(tmp_path: Path) -> None:
    source = tmp_path / "source" / "places.csv"
    source.parent.mkdir()
    _write_csv(source)
    dist = tmp_path / "dist"

    assert main(
        [
            "run",
            str(source),
            "--crs",
            "EPSG:4326",
            "--output",
            str(dist),
        ]
    ) == 0
    resolved = json.loads((dist / "map_spec.json").read_text(encoding="utf-8"))
    assert resolved["layers"][0]["source"]["path"] == "data/places.csv"
    assert (dist / "data" / "places.csv").is_file()
