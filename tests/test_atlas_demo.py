from __future__ import annotations

import json
from pathlib import Path

from demo_projects import (
    LAND_USE_FILES,
    atlas_map_list_spec,
    merge_land_use_snapshots,
    prepare_demo_project,
)


def _feature(identifier: str, category: str, x: float) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "id": identifier,
            "name": f"{identifier} BROADWAY",
            "address": f"{identifier} BROADWAY",
            "category": category,
            "land_use": category,
            "zoning": "C5-5",
            "lot_area_sqft": 1000,
            "building_area_sqft": 5000,
            "built_far": 5.0,
            "floors": 5,
            "year_built": 1930,
            "bbl": identifier,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[x, 40.70], [x + 0.001, 40.70], [x + 0.001, 40.701], [x, 40.70]]
            ],
        },
    }


def _write_collection(path: Path, features: list[dict]) -> None:
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_merge_land_use_snapshots_and_generate_true_map_list(tmp_path: Path) -> None:
    project = tmp_path / "map-list"
    project.mkdir()
    categories = ("居住用地", "混合与商业用地", "公共与其他用地")
    for index, (name, category) in enumerate(zip(LAND_USE_FILES, categories), start=1):
        _write_collection(project / name, [_feature(str(index), category, -74.01 + index * 0.002)])

    merged = merge_land_use_snapshots(project)
    payload = json.loads(merged.read_text(encoding="utf-8"))
    assert len(payload["features"]) == 3
    assert [item["properties"]["id"] for item in payload["features"]] == ["1", "2", "3"]

    spec = atlas_map_list_spec(3)
    assert spec["template"] == "map-list"
    assert spec["primary_layer"] == "parcels"
    assert spec["layers"][0]["source"]["path"] == "parcels.geojson"
    assert spec["layers"][0]["filter_fields"] == [
        "category",
        "year_built",
        "floors",
        "built_far",
    ]
    assert [metric["type"] for metric in spec["list"]["summary_metrics"]] == [
        "count",
        "sum",
        "median",
        "mean",
    ]


def test_prepare_demo_project_does_not_modify_source_snapshots(tmp_path: Path) -> None:
    examples = tmp_path / "examples"
    source = examples / "map-list"
    source.mkdir(parents=True)
    categories = ("居住用地", "混合与商业用地", "公共与其他用地")
    for index, (name, category) in enumerate(zip(LAND_USE_FILES, categories), start=1):
        _write_collection(source / name, [_feature(str(index), category, -74.01 + index * 0.002)])
    original = {path: path.read_bytes() for path in source.iterdir()}

    destination = tmp_path / "prepared"
    spec_path = prepare_demo_project(
        "map-list",
        examples_root=examples,
        destination=destination,
    )
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    assert spec["template"] == "map-list"
    assert (destination / "parcels.geojson").is_file()
    assert original == {path: path.read_bytes() for path in source.iterdir()}
