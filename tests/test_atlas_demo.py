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
            "category_code": category,
            "category_en": category,
            "category_zh": category,
            "land_use_code": "unclassified",
            "land_use_en": "Unclassified",
            "land_use_zh": "未分类",
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
    categories = ("residential", "mixed_commercial", "civic_other")
    for index, (name, category) in enumerate(zip(LAND_USE_FILES, categories), start=1):
        _write_collection(project / name, [_feature(str(index), category, -74.01 + index * 0.002)])

    merged = merge_land_use_snapshots(project)
    payload = json.loads(merged.read_text(encoding="utf-8"))
    assert len(payload["features"]) == 3
    assert [item["properties"]["id"] for item in payload["features"]] == ["1", "2", "3"]

    spec = atlas_map_list_spec(3, "en-US")
    assert spec["template"] == "map-list"
    assert spec["title"] == "Lower Manhattan Parcels and Land Use"
    assert spec["locale"] == "en-US"
    assert spec["subtitle"].startswith("Financial District—Civic Center")
    assert spec["primary_layer"] == "parcels"
    assert spec["layers"][0]["source"]["path"] == "parcels.geojson"
    assert spec["layers"][0]["filter_fields"] == [
        "category_code",
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
    chinese = atlas_map_list_spec(3, "zh-CN")
    assert chinese["title"] == "Lower Manhattan 地块与用地"
    assert chinese["layers"][0]["popup_fields"][1:3] == [
        "category_zh",
        "land_use_zh",
    ]


def test_prepare_demo_project_does_not_modify_source_snapshots(tmp_path: Path) -> None:
    examples = tmp_path / "examples"
    source = examples / "map-list"
    source.mkdir(parents=True)
    categories = ("residential", "mixed_commercial", "civic_other")
    for index, (name, category) in enumerate(zip(LAND_USE_FILES, categories), start=1):
        _write_collection(source / name, [_feature(str(index), category, -74.01 + index * 0.002)])
    original = {path: path.read_bytes() for path in source.iterdir()}

    destination = tmp_path / "prepared"
    spec_path = prepare_demo_project(
        "map-list",
        examples_root=examples,
        destination=destination,
        locale="zh-CN",
    )
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    assert spec["template"] == "map-list"
    assert spec["locale"] == "zh-CN"
    assert (destination / "parcels.geojson").is_file()
    assert original == {path: path.read_bytes() for path in source.iterdir()}
