from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "scripts" / "mapcore" / "resources" / "templates"


def test_shared_map_controls_follow_document_locale() -> None:
    text = (TEMPLATES / "shared.js").read_text(encoding="utf-8")
    assert 'var basemapLabel = isChinese ? "底图" : "Basemap";' in text
    assert 'var fullscreenLabel = isChinese ? "全屏地图" : "Fullscreen map";' in text
    assert 'select.setAttribute("aria-label", basemapLabel);' in text
    assert 'button.title = fullscreenLabel;' in text


def test_multilayer_has_chinese_and_english_ui_dictionary() -> None:
    text = (TEMPLATES / "multilayer.html.j2").read_text(encoding="utf-8")
    assert 'search: "跨图层搜索"' in text
    assert 'search: "Search across layers"' in text
    assert 'visible_layers: "Visible layers"' in text
    assert 'function label(key, fallback)' in text
