import json
import re
from pathlib import Path

import pytest

from scripts.mapcore.render_html import render_html


LEAFLET_JS = "window.L = window.L || {version: '1.9.4'};"
LEAFLET_CSS = ".leaflet-container{position:relative;overflow:hidden}"


def _feature(identifier, name, geometry, **properties):
    return {
        "type": "Feature",
        "id": identifier,
        "properties": {
            "__feature_id": identifier,
            "name": name,
            **properties,
        },
        "geometry": geometry,
    }


def _prepared_layer(layer_spec, features, records=None):
    return {
        "spec": layer_spec,
        "feature_collection": {
            "type": "FeatureCollection",
            "features": features,
        },
        "records": records
        if records is not None
        else [feature["properties"] for feature in features],
        "count": len(features),
        "bounds": [116.0, 39.0, 117.0, 40.0],
    }


def _payload_from(html):
    match = re.search(
        r'<script id="imb-data" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert match, "rendered HTML did not include its JSON payload"
    return json.loads(match.group(1))


def test_map_list_renders_single_safe_html(tmp_path):
    attack = '中文 "</script><script>window.pwned=true</script>&'
    features = [
        _feature(
            "a-1",
            attack,
            {"type": "Point", "coordinates": [116.4, 39.9]},
            district="路北区",
            score=float("nan"),
        ),
        _feature(
            "a-2",
            "第二居住区",
            {"type": "Polygon", "coordinates": [[[116.3, 39.8], [116.5, 39.8], [116.5, 40.0], [116.3, 39.8]]]},
            district="路南区",
            score=2,
        ),
    ]
    spec = {
        "template": "map-list",
        "title": attack,
        "subtitle": "地图—清单双向联动",
        "primary_layer": "homes",
        "list_batch_size": 20,
        "basemap": {"attribution": "测试数据"},
    }
    layer_spec = {
        "id": "homes",
        "title": "历史居住区",
        "id_field": "__feature_id",
        "label_field": "name",
        "category_field": "district",
        "search_fields": ["name", "district"],
        "filter_fields": [{"field": "district", "label": "行政区"}],
        "sort_fields": ["name", "score"],
        "card_fields": [{"field": "district", "label": "行政区"}],
        "tooltip_fields": ["name"],
        "popup_fields": ["name", "district"],
        "categories": {
            "路北区": {"label": "路北区", "color": "#1668dc"},
            "路南区": {"label": "路南区", "color": "#dc5a2a"},
        },
    }
    output = tmp_path / "map.html"

    result = render_html(
        spec,
        [_prepared_layer(layer_spec, features)],
        output,
        LEAFLET_JS,
        LEAFLET_CSS,
    )

    assert result == {
        "path": "map.html",
        "template": "map-list",
        "single_file": True,
        "leaflet_embedded": True,
        "qa_interface": "__interactiveMapBuilderQA",
        "feature_count": 2,
        "layer_counts": {"homes": 2},
    }
    html = output.read_text(encoding="utf-8")
    assert html.count("<!doctype html>") == 1
    assert "<title>Interactive map</title>" not in html
    assert attack not in html
    assert "\\u003c/script\\u003e\\u003cscript\\u003e" in html
    assert "\\u0026" in html
    assert ".innerHTML" not in html
    assert "textContent" in html
    assert "window.link_by_id" in html
    assert "window.__interactiveMapBuilderQA" in html
    assert "list_batch_size" in html
    assert "data-feature-id" in html
    assert "https://unpkg" not in html
    assert "cdn.jsdelivr" not in html

    payload = _payload_from(html)
    assert payload["template"] == "map-list"
    assert payload["layers"][0]["count"] == 2
    assert payload["layers"][0]["feature_collection"]["features"][0]["properties"]["name"] == attack
    assert payload["layers"][0]["feature_collection"]["features"][0]["properties"]["score"] is None


def test_multilayer_contains_safe_point_line_polygon_controls(tmp_path):
    layers = [
        _prepared_layer(
            {
                "id": "places",
                "title": "地点",
                "required": True,
                "label_field": "name",
                "search_fields": ["name"],
                "tooltip_fields": ["name"],
                "style": {"radius": 6, "color": "#1668dc"},
            },
            [
                _feature(
                    "p-1",
                    "中心点",
                    {"type": "Point", "coordinates": [116.4, 39.9]},
                )
            ],
        ),
        _prepared_layer(
            {
                "id": "routes",
                "title": "道路",
                "required": True,
                "label_field": "name",
                "popup_fields": ["name"],
                "style": {"color": "#dc5a2a", "weight": 3},
            },
            [
                _feature(
                    "l-1",
                    "主路",
                    {
                        "type": "LineString",
                        "coordinates": [[116.3, 39.8], [116.5, 40.0]],
                    },
                )
            ],
        ),
        _prepared_layer(
            {
                "id": "districts",
                "title": "分区",
                "required": True,
                "label_field": "name",
                "category_field": "kind",
                "categories": [
                    {"value": "core", "label": "核心区", "color": "#16856b"}
                ],
            },
            [
                _feature(
                    "g-1",
                    "核心区",
                    {
                        "type": "Polygon",
                        "coordinates": [
                            [[116.2, 39.7], [116.6, 39.7], [116.6, 40.1], [116.2, 39.7]]
                        ],
                    },
                    kind="core",
                )
            ],
        ),
    ]
    spec = {
        "template": "multilayer",
        "title": "点线面综合图",
        "layers": [layer["spec"] for layer in layers],
    }

    result = render_html(
        spec,
        layers,
        tmp_path / "map.html",
        LEAFLET_JS,
        LEAFLET_CSS,
    )
    output = tmp_path / "map.html"
    html = output.read_text(encoding="utf-8")

    assert result["feature_count"] == 3
    assert result["layer_counts"] == {"places": 1, "routes": 1, "districts": 1}
    assert "imb-layer-control" in html
    assert "imb-legend-groups" in html
    assert "pointToLayer" in html
    assert "bindTooltip" in html
    assert "bindPopup" in html
    assert "toggleLayer" in html
    assert "link_by_id" in html
    assert ".innerHTML" not in html

    payload = _payload_from(html)
    assert [layer["spec"]["id"] for layer in payload["layers"]] == [
        "places",
        "routes",
        "districts",
    ]
    assert sum(layer["count"] for layer in payload["layers"]) == 3


def test_render_accepts_leaflet_asset_paths_and_layer_mapping(tmp_path):
    js_path = tmp_path / "leaflet.js"
    css_path = tmp_path / "leaflet.css"
    js_path.write_text("window.LEAFLET_PATH_SENTINEL = true;", encoding="utf-8")
    css_path.write_text(".LEAFLET_PATH_SENTINEL{display:block}", encoding="utf-8")
    layer = _prepared_layer(
        {"id": "items", "label_field": "name"},
        [
            _feature(
                "x-1",
                "项目",
                {"type": "Point", "coordinates": [0.0, 0.0]},
            )
        ],
    )

    result = render_html(
        {"template": "map-list", "title": "Path assets"},
        {"items": layer},
        tmp_path / "nested" / "map.html",
        js_path,
        css_path,
    )
    output = tmp_path / "nested" / "map.html"
    html = output.read_text(encoding="utf-8")

    assert result["path"] == "map.html"
    assert "LEAFLET_PATH_SENTINEL = true" in html
    assert ".LEAFLET_PATH_SENTINEL" in html


def test_inline_vendor_source_cannot_close_its_element(tmp_path):
    layer = _prepared_layer(
        {"id": "items", "label_field": "name"},
        [
            _feature(
                "x-1",
                "项目",
                {"type": "Point", "coordinates": [0.0, 0.0]},
            )
        ],
    )
    malicious_js = "window.L={}; /* </script><script>alert(1)</script> */"
    malicious_css = "/* </style><script>alert(2)</script> */"

    render_html(
        {"template": "map-list", "title": "Safe vendor assets"},
        [layer],
        tmp_path / "map.html",
        malicious_js,
        malicious_css,
    )
    output = tmp_path / "map.html"
    html = output.read_text(encoding="utf-8")

    assert "/* <\\/script><script>alert(1)<\\/script> */" in html
    assert "/* <\\/style><script>alert(2)</script> */" in html


def test_rejects_unknown_template(tmp_path):
    with pytest.raises(ValueError, match="Unsupported HTML template"):
        render_html(
            {"template": "unknown"},
            [
                _prepared_layer(
                    {"id": "items"},
                    [
                        _feature(
                            "x-1",
                            "项目",
                            {"type": "Point", "coordinates": [0.0, 0.0]},
                        )
                    ],
                )
            ],
            tmp_path / "map.html",
            LEAFLET_JS,
            LEAFLET_CSS,
        )


def test_multilayer_rejects_missing_required_layer(tmp_path):
    present = _prepared_layer(
        {"id": "places"},
        [
            _feature(
                "x-1",
                "项目",
                {"type": "Point", "coordinates": [0.0, 0.0]},
            )
        ],
    )
    spec = {
        "template": "multilayer",
        "layers": [
            {"id": "places", "required": True},
            {"id": "roads", "required": True},
        ],
    }

    with pytest.raises(ValueError, match="roads"):
        render_html(
            spec,
            [present],
            tmp_path / "map.html",
            LEAFLET_JS,
            LEAFLET_CSS,
        )
