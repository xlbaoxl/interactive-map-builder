from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, Polygon

from mapcore.render_html import _template_assets
from mapcore.semantic_styles import infer_semantic_role
from mapcore.spec_init import init_spec_from_inspection
from mapcore.style import resolve_layer_style
from mapcore.visual_defaults import resolve_visual_plan


def _frame(geometries, **columns):
    count = len(geometries)
    values = {"id": [str(index) for index in range(count)]}
    values.update(columns)
    return gpd.GeoDataFrame(values, geometry=geometries, crs="EPSG:4326")


def test_bilingual_semantic_roles_cover_common_urban_layers() -> None:
    assert infer_semantic_role({"id": "water", "name": "Water bodies", "style": {}}) == "water"
    assert infer_semantic_role({"id": "green", "name": "公园与开放空间", "style": {}}) == "green_space"
    assert infer_semantic_role({"id": "parking", "name": "停车设施", "style": {}}) == "parking"
    assert infer_semantic_role({"id": "shops", "name": "商业与服务设施", "style": {}}) == "commercial"
    assert infer_semantic_role({"id": "walk", "name": "步行网络", "style": {}}) == "pedestrian"
    assert infer_semantic_role({"id": "extent", "name": "研究范围", "style": {}}) == "study_boundary"
    assert infer_semantic_role({"id": "nta", "name": "邻里区", "style": {}}) == "area_boundary"


def test_generated_water_palette_is_replaced_but_custom_palette_is_preserved() -> None:
    frame = _frame(
        [
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(2, 0), (3, 0), (3, 1), (2, 1)]),
            Polygon([(4, 0), (5, 0), (5, 1), (4, 1)]),
        ],
        water_type=["river", "stream", "pond"],
    )
    generated = {
        "id": "water",
        "name": "水体",
        "style": {
            "mode": "categorical",
            "color_field": "water_type",
            "categories": {
                "river": {"label": "河流", "color": "#4E8587"},
                "stream": {"label": "溪流或沟渠", "color": "#D39A4A"},
                "pond": {"label": "池塘", "color": "#8C739B"},
            },
        },
    }
    _, resolved, report = resolve_layer_style(frame, generated)
    assert report["semantic_role"] == "water"
    assert report["semantic_palette_applied"] is True
    assert [
        item["color"] for item in resolved["style"]["categories"].values()
    ] == ["#2F78BE", "#58A5D8", "#8CC4E8"]

    custom = {
        **generated,
        "style": {
            **generated["style"],
            "categories": {
                "river": "#112233",
                "stream": "#445566",
                "pond": "#778899",
            },
        },
    }
    _, custom_resolved, custom_report = resolve_layer_style(frame, custom)
    assert custom_report["semantic_palette_applied"] is False
    assert custom_resolved["style"]["categories"] == custom["style"]["categories"]


def test_mixed_parking_uses_real_point_family_for_legend_and_distinct_semantic_colors() -> None:
    frame = _frame(
        [
            Point(0, 0),
            Point(0.5, 0.5),
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        ]
    )
    spec = {"id": "parking", "name": "停车设施", "style": {"mode": "single"}}
    resolved_frame, resolved_spec, _ = resolve_layer_style(frame, spec)
    plan = resolve_visual_plan(
        resolved_frame,
        resolved_spec,
        template="multilayer",
        primary_layer=None,
        layer_count=4,
        layer_index=2,
        explicit_style=spec["style"],
    )
    assert plan["geometry_family"] == "mixed"
    assert plan["representative_family"] == "point"
    assert plan["semantic_role"] == "parking"
    assert plan["families"]["point"]["fill_color"] == "#D8892B"
    assert plan["families"]["polygon"]["fill_color"] == "#E2A24D"
    assert plan["families"]["point"]["fill_opacity"] >= 0.78
    assert plan["families"]["polygon"]["fill_opacity"] >= 0.40


def test_init_spec_uses_semantic_palette_for_known_water_categories(tmp_path: Path) -> None:
    inspection = {
        "layers": [
            {
                "layer_id": "water",
                "name": "水体",
                "crs": "EPSG:4326",
                "source": {"input_index": 0},
                "fields": [
                    {
                        "name": "water_type",
                        "unique_count": 3,
                        "values": ["river", "stream", "pond"],
                    }
                ],
                "candidates": {
                    "category": ["water_type"],
                    "label": [],
                    "id": [],
                    "search": [],
                    "filter": ["water_type"],
                    "card": [],
                    "numeric": [],
                },
            }
        ],
        "inputs": [{"resolved_path": str(tmp_path / "water.geojson")}],
        "template_recommendation": {
            "recommended": "multilayer",
            "needs_confirmation": False,
        },
    }
    spec = init_spec_from_inspection(
        inspection,
        spec_path=tmp_path / "map_spec.json",
        template="multilayer",
    )
    assert spec["layers"][0]["style"]["categories"] == {
        "river": "#2F78BE",
        "stream": "#58A5D8",
        "pond": "#8CC4E8",
    }


def test_multilayer_assets_include_control_stack_and_visual_qa_only_for_that_template() -> None:
    multilayer = _template_assets("multilayer")
    assert "imb-controls-collapse" in multilayer["javascript"]
    assert "legendStyleConsistent" in multilayer["javascript"]
    assert "is-controls-collapsed" in multilayer["css"]

    map_list = _template_assets("map-list")
    assert "imb-controls-collapse" not in map_list["javascript"]
    assert "is-controls-collapsed" not in map_list["css"]
