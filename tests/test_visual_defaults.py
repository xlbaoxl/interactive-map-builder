from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, Polygon

from map_builder import build_map
from mapcore.spec_init import init_spec_from_inspection
from mapcore.visual_defaults import (
    CATEGORICAL_PALETTE,
    density_class,
    resolve_visual_plan,
)


def _frame(geometries):
    return gpd.GeoDataFrame(
        {"id": [str(index) for index in range(len(geometries))]},
        geometry=geometries,
        crs="EPSG:4326",
    )


def test_density_classes_are_coarse_and_geometry_aware() -> None:
    assert density_class("point", 40, 40) == "sparse"
    assert density_class("point", 300, 300) == "normal"
    assert density_class("point", 751, 751) == "dense"
    assert density_class("point", 1500, 1500) == "very_dense"
    assert density_class("line", 20, 2000) == "normal"
    assert density_class("polygon", 10, 1200) == "sparse"


def test_visual_plan_sets_roles_panes_and_density_defaults() -> None:
    point_frame = _frame([Point(index * 0.001, 0) for index in range(751)])
    primary = resolve_visual_plan(
        point_frame,
        {"id": "facilities", "style": {}},
        template="map-list",
        primary_layer="facilities",
        layer_count=2,
        layer_index=1,
        explicit_style={},
    )
    assert primary["system"] == "atlas-studio-light"
    assert primary["role"] == "primary"
    assert primary["density"] == "dense"
    assert primary["families"]["point"]["radius"] == 3.2
    assert primary["families"]["point"]["pane"] == "imb-primary-point"

    polygon = _frame([Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])])
    context = resolve_visual_plan(
        polygon,
        {"id": "boundary", "style": {}},
        template="map-list",
        primary_layer="facilities",
        layer_count=2,
        layer_index=0,
        explicit_style={},
    )
    assert context["role"] == "context"
    assert context["families"]["polygon"]["fill_opacity"] <= 0.14
    assert context["families"]["polygon"]["pane"] == "imb-context-polygon"
    assert (
        context["families"]["polygon"]["draw_order"]
        < primary["families"]["point"]["draw_order"]
    )


def test_explicit_visual_values_override_defaults_without_disabling_hierarchy() -> None:
    frame = _frame([Point(0, 0), Point(1, 1)])
    style = {
        "color": "#123456",
        "radius": 8,
        "opacity": 0.5,
        "fill_opacity": 0.6,
    }
    plan = resolve_visual_plan(
        frame,
        {"id": "places", "style": style},
        template="multilayer",
        primary_layer=None,
        layer_count=1,
        layer_index=0,
        explicit_style=style,
    )
    point = plan["families"]["point"]
    assert point["fill_color"] == "#123456"
    assert point["stroke_color"] == "#123456"
    assert point["radius"] == 8
    assert point["opacity"] == 0.5
    assert point["fill_opacity"] == 0.6
    assert point["pane"] == "imb-primary-point"


def test_auto_categories_stop_before_the_palette_repeats(tmp_path: Path) -> None:
    values = [f"type-{index}" for index in range(len(CATEGORICAL_PALETTE) + 1)]
    inspection = {
        "layers": [
            {
                "layer_id": "places",
                "name": "Places",
                "crs": "EPSG:4326",
                "source": {"input_index": 0},
                "fields": [
                    {
                        "name": "kind",
                        "unique_count": len(values),
                        "values": values,
                    }
                ],
                "candidates": {
                    "category": ["kind"],
                    "label": [],
                    "id": [],
                    "search": [],
                    "filter": ["kind"],
                    "card": [],
                    "numeric": [],
                },
            }
        ],
        "inputs": [{"resolved_path": str(tmp_path / "places.geojson")}],
        "template_recommendation": {
            "recommended": "map-list",
            "needs_confirmation": False,
        },
    }
    spec = init_spec_from_inspection(
        inspection,
        spec_path=tmp_path / "map_spec.json",
        template="map-list",
        primary_layer="places",
    )
    assert "categories" not in spec["layers"][0]["style"]
    assert spec["layers"][0]["filter_fields"] == ["kind"]


def test_build_report_and_html_share_the_resolved_visual_plan(tmp_path: Path) -> None:
    source = tmp_path / "places.geojson"
    _frame([Point(0, 0), Point(0.1, 0.1)]).to_file(source, driver="GeoJSON")
    spec = {
        "schema_version": "1.1",
        "template": "map-list",
        "title": "Visual plan",
        "locale": "en-US",
        "primary_layer": "places",
        "layers": [
            {
                "id": "places",
                "name": "Places",
                "source": {"path": "places.geojson"},
                "id_field": "id",
                "label_field": "id",
            }
        ],
        "basemaps": [],
        "static": {"enabled": False},
    }
    spec_path = tmp_path / "map_spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    dist = tmp_path / "dist"
    result = build_map(spec_path, dist)

    report = result["report"]
    visual = report["layers"][0]["visual"]
    assert report["visual_system"] == "atlas-studio-light"
    assert visual["families"]["point"]["radius"] == 5.0
    html = (dist / "map.html").read_text(encoding="utf-8")
    assert '"system":"atlas-studio-light"' in html
    assert '"pane":"imb-primary-point"' in html
    assert "Atlas Studio Light" in html
