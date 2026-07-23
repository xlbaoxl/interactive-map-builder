from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

from map_builder import build_map, verify_dist
from mapcore.spec import SpecError, validate_spec


def _minimal_spec() -> dict:
    return {
        "schema_version": "1.0",
        "template": "map-list",
        "title": "Contract",
        "primary_layer": "places",
        "layers": [
            {
                "id": "places",
                "name": "Places",
                "source": {"path": "places.geojson"},
                "id_field": "id",
                "label_field": "name",
                "source_note": "Synthetic",
            }
        ],
    }


@pytest.mark.parametrize(
    ("scope", "key", "value"),
    [
        ("root", "language", "zh-CN"),
        ("root", "theme", "clean-light"),
        ("root", "outputs", {"html": "custom.html"}),
        ("source", "format", "geojson"),
        ("layer", "simplify_tolerance", 0.001),
    ],
)
def test_mapspec_rejects_removed_fields(scope: str, key: str, value) -> None:
    spec = _minimal_spec()
    if scope == "root":
        spec[key] = value
    elif scope == "source":
        spec["layers"][0]["source"][key] = value
    else:
        spec["layers"][0][key] = value
    with pytest.raises(SpecError, match=key):
        validate_spec(spec)


def test_mapspec_accepts_canonical_display_static_and_link_fields() -> None:
    spec = _minimal_spec()
    layer = spec["layers"][0]
    layer["field_labels"] = {"status": "Review status"}
    layer["link_key"] = "project_id"
    layer["style"] = {
        "mode": "categorical",
        "color_field": "status",
        "missing_label": "Not classified",
        "categories": {
            "ready": {"label": "Ready label", "color": "#0f766e"},
            "review": "#d97706",
        },
    }
    spec["static"] = {
        "enabled": True,
        "presets": ["slide-16x9"],
        "title": "Static title",
        "background": "#ffffff",
        "legend": True,
        "legend_title": "Status",
        "north_arrow": False,
        "scale_bar": False,
        "source_note": "Synthetic",
    }
    resolved = validate_spec(spec)
    assert resolved["layers"][0]["style"]["missing_color"] == "#9ca3af"
    assert resolved["layers"][0]["style"]["categories"]["ready"]["label"] == "Ready label"


def test_canonical_fields_affect_build_and_nulls_are_soft(tmp_path: Path) -> None:
    source = tmp_path / "places.geojson"
    gpd.GeoDataFrame(
        {
            "id": ["a", "b"],
            "name": [None, "Beta"],
            "status": [None, "ready"],
            "note": [None, "Complete"],
            "score": [None, 10.0],
            "x": [None, 2.0],
            "y": [3.0, None],
            "project_id": [None, "shared"],
        },
        geometry=[Point(118.1, 39.6), Point(118.2, 39.7)],
        crs="EPSG:4326",
    ).to_file(source, driver="GeoJSON")
    spec = _minimal_spec()
    layer = spec["layers"][0]
    layer.update(
        {
            "field_labels": {"status": "Review status", "note": "Notes"},
            "link_key": "project_id",
            "tooltip_fields": ["name", "note"],
            "popup_fields": ["name", "note"],
            "search_fields": ["name"],
            "card_fields": ["status", "note"],
            "sort_fields": ["name", "score"],
            "style": {
                "mode": "categorical",
                "color_field": "status",
                "categories": {
                    "ready": {"label": "Ready label", "color": "#0f766e"}
                },
            },
        }
    )
    spec["linked_view"] = {
        "layer": "places",
        "x_field": "x",
        "y_field": "y",
    }
    spec["list"] = {
        "summary_metrics": [
            {"type": "mean", "field": "score", "label": "Mean score"}
        ]
    }
    spec["static"] = {
        "enabled": True,
        "presets": ["slide-16x9"],
        "source_note": "Synthetic",
    }
    spec_path = tmp_path / "map_spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    dist = tmp_path / "dist"
    result = build_map(spec_path, dist)
    resolved = json.loads((dist / "map_spec.json").read_text(encoding="utf-8"))
    html = (dist / "map.html").read_text(encoding="utf-8")

    assert (dist / "map_slide_16x9.png").is_file()
    assert not (dist / "map_paper.pdf").exists()
    assert resolved["layers"][0]["style"]["categories"]["未分类 / Missing"] == "#9ca3af"
    assert '"__label":"a"' in html
    assert "Review status" in html
    assert "Ready label" in html
    assert result["report"]["checks"]["portable_bundle"] is False
    assert result["report"]["checks"]["static_font"]["font"]
    warnings = "\n".join(result["report"]["warnings"])
    assert "null display value" in warnings
    assert "null category" in warnings


def test_bundle_sources_deduplicates_and_rebuilds_after_move(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    gpd.GeoDataFrame(
        {"id": ["1"], "name": ["Shared"]},
        geometry=[Point(118.1, 39.6)],
        crs="EPSG:4326",
    ).to_file(project / "shared.geojson", driver="GeoJSON")
    spec = {
        "schema_version": "1.0",
        "template": "multilayer",
        "title": "Bundle",
        "layers": [
            {
                "id": layer_id,
                "name": layer_id.upper(),
                "source": {"path": "shared.geojson"},
                "id_field": "id",
                "label_field": "name",
                "source_note": "Synthetic",
            }
            for layer_id in ("a", "b")
        ],
        "static": {"enabled": False},
    }
    spec_path = project / "map_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")

    dist = tmp_path / "dist"
    result = build_map(spec_path, dist, bundle_sources=True)
    assert result["report"]["checks"]["portable_bundle"] is True
    assert [path.name for path in (dist / "data").iterdir()] == ["shared.geojson"]
    bundled_spec = json.loads((dist / "map_spec.json").read_text(encoding="utf-8"))
    assert {
        layer["source"]["path"] for layer in bundled_spec["layers"]
    } == {"data/shared.geojson"}

    moved = tmp_path / "moved"
    shutil.copytree(dist, moved)
    rebuilt = tmp_path / "rebuilt"
    build_map(moved / "map_spec.json", rebuilt)
    assert verify_dist(rebuilt)["status"] == "pass"
