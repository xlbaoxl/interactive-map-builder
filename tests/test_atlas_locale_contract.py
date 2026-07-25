from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "scripts" / "mapcore" / "resources"
TEMPLATES = RESOURCES / "templates"
HAN = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")


def test_shared_map_controls_use_locale_catalog_messages() -> None:
    text = (TEMPLATES / "shared.js").read_text(encoding="utf-8")
    assert 'firstDefined(labels.basemap, "Basemap")' in text
    assert 'firstDefined(labels.fullscreen, "Fullscreen map")' in text
    assert 'select.setAttribute("aria-label", basemapLabel);' in text
    assert 'button.title = fullscreenLabel;' in text
    assert HAN.search(text) is None


def test_templates_use_catalog_without_embedded_language_dictionaries() -> None:
    for name, section in (
        ("map-list.html.j2", "payload.catalog.map_list"),
        ("multilayer.html.j2", "payload.catalog.multilayer"),
    ):
        text = (TEMPLATES / name).read_text(encoding="utf-8")
        assert section in text
        assert "var strings = {" not in text
        assert HAN.search(text) is None


def test_locale_catalogs_define_distinct_complete_interface_copy() -> None:
    english = json.loads((RESOURCES / "locales" / "en-US.json").read_text(encoding="utf-8"))
    chinese = json.loads((RESOURCES / "locales" / "zh-CN.json").read_text(encoding="utf-8"))
    assert english["locale"] == "en-US"
    assert chinese["locale"] == "zh-CN"
    assert english["shared"].keys() == chinese["shared"].keys()
    assert english["map_list"].keys() == chinese["map_list"].keys()
    assert english["multilayer"].keys() == chinese["multilayer"].keys()
    assert english["shared"]["basemap"] == "Basemap"
    assert chinese["shared"]["basemap"] == "底图"
