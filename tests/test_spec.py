from __future__ import annotations

import pytest

from mapcore.spec import SpecError, validate_spec


def minimal_spec(template: str = "map-list"):
    spec = {
        "schema_version": "1.0",
        "template": template,
        "title": "测试地图",
        "layers": [
            {
                "id": "places",
                "name": "地点",
                "source": {"path": "places.geojson"},
            }
        ],
    }
    if template == "map-list":
        spec["primary_layer"] = "places"
    return spec


def test_defaults_are_applied():
    resolved = validate_spec(minimal_spec())
    assert resolved["locale"] == "zh-CN"
    assert resolved["layers"][0]["visible"] is True
    assert resolved["layers"][0]["required"] is True


def test_map_list_requires_primary_layer():
    spec = minimal_spec()
    del spec["primary_layer"]
    with pytest.raises(SpecError, match="primary_layer"):
        validate_spec(spec)


def test_rejects_duplicate_layer_ids():
    spec = minimal_spec("multilayer")
    spec["layers"].append(dict(spec["layers"][0]))
    with pytest.raises(SpecError, match="unique"):
        validate_spec(spec)


def test_rejects_unknown_top_level_key():
    spec = minimal_spec()
    spec["surprise"] = True
    with pytest.raises(SpecError, match="surprise"):
        validate_spec(spec)


def test_rejects_absolute_sources_and_removed_outputs():
    spec = minimal_spec()
    spec["layers"][0]["source"]["path"] = "C:/private/data.geojson"
    with pytest.raises(SpecError, match="Source paths must be relative"):
        validate_spec(spec)

    spec = minimal_spec()
    spec["layers"][0]["source"]["path"] = "/private/data.geojson"
    with pytest.raises(SpecError, match="Source paths must be relative"):
        validate_spec(spec)

    spec = minimal_spec()
    spec["outputs"] = {"html": "map.html"}
    with pytest.raises(SpecError, match="outputs"):
        validate_spec(spec)
