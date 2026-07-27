from __future__ import annotations

import pytest

from mapcore.spec import SpecError, current_schema_version, validate_spec


def minimal_spec(template: str = "map-list"):
    spec = {
        "schema_version": current_schema_version(),
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


def test_current_schema_version_comes_from_packaged_contract():
    assert current_schema_version() == "1.1"


def test_defaults_are_applied():
    resolved = validate_spec(minimal_spec())
    assert resolved["locale"] == "en-US"
    assert resolved["layers"][0]["visible"] is True
    assert resolved["layers"][0]["required"] is True
    assert resolved["layers"][0]["style"]["missing_label"] == "Missing"
    assert "static" not in resolved


@pytest.mark.parametrize(
    ("locale", "missing_label"),
    (("en-US", "Missing"), ("zh-CN", "未分类")),
)
def test_supported_locales_apply_localized_missing_label(locale, missing_label):
    spec = minimal_spec()
    spec["locale"] = locale
    resolved = validate_spec(spec)
    assert resolved["locale"] == locale
    assert resolved["layers"][0]["style"]["missing_label"] == missing_label


def test_rejects_any_unsupported_schema_version_through_schema_validation():
    spec = minimal_spec()
    spec["schema_version"] = "unsupported"
    with pytest.raises(SpecError, match="schema_version"):
        validate_spec(spec)


def test_rejects_unsupported_locale():
    spec = minimal_spec()
    spec["locale"] = "fr-FR"
    with pytest.raises(SpecError, match="locale"):
        validate_spec(spec)


def test_multilayer_accepts_highlight_search_and_optional_legend():
    spec = minimal_spec("multilayer")
    spec["map"] = {
        "search_behavior": "highlight",
        "controls": {"legend": False},
    }
    resolved = validate_spec(spec)
    assert resolved["map"]["search_behavior"] == "highlight"
    assert resolved["map"]["controls"]["legend"] is False


def test_rejects_unknown_search_behavior():
    spec = minimal_spec("multilayer")
    spec["map"] = {"search_behavior": "remove-everything"}
    with pytest.raises(SpecError, match="search_behavior"):
        validate_spec(spec)


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
