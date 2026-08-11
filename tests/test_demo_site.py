from __future__ import annotations

from pathlib import Path

from build_demo_site import build_demo_site


ROOT = Path(__file__).resolve().parents[1]
PAGES_URL = "https://xlbaoxl.github.io/interactive-map-builder"


def test_demo_site_builds_atlas_landing_without_changing_source_assets(tmp_path: Path) -> None:
    source_paths = [
        ROOT / "assets" / "examples" / "multilayer" / "map_spec.json",
        *sorted((ROOT / "assets" / "examples" / "map-list").glob("*.geojson")),
    ]
    original_assets = {path: path.read_bytes() for path in source_paths}

    site = build_demo_site(tmp_path / "_site")

    expected_titles = {
        ("en-US", "map-list"): "Lower Manhattan Parcels and Land Use",
        ("zh-CN", "map-list"): "Lower Manhattan 地块与用地",
        ("en-US", "multilayer"): "Downtown Brooklyn Cycling and Transit",
        ("zh-CN", "multilayer"): "Downtown Brooklyn 骑行与公共交通",
    }
    for locale in ("en-US", "zh-CN"):
        for demo in ("map-list", "multilayer"):
            html_path = site / locale / demo / "index.html"
            assert html_path.is_file()
            assert html_path.stat().st_size > 10_000
            html = html_path.read_text(encoding="utf-8")
            assert f'<html lang="{locale}">' in html
            assert expected_titles[(locale, demo)] in html
            assert "Leaflet" in html
            assert '"FeatureCollection"' in html
            assert "window.__interactiveMapBuilderQA" in html
            assert "dataset.imbReady" in html
            if demo == "map-list":
                assert "1 BROADWAY" in html
                assert '"template":"map-list"' in html
                assert '"search_behavior":"highlight"' in html
                assert "imb-detail-panel" in html
                assert "rangeFilterCount" in html
            else:
                assert "Jay St-MetroTech" in html
                assert "imb-feature-types" in html
                assert "setFeatureType" in html
                assert "imb-saved-views" in html

    assert (site / ".nojekyll").is_file()
    root_html = (site / "index.html").read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' not in root_html
    assert "Spatial data in. Map product out." in root_html
    assert 'class="hero-visual"' in root_html
    assert 'src="./en-US/multilayer/" loading="eager"' in root_html
    assert "CORE PRODUCT CAPABILITIES" in root_html
    assert "Search &amp; Filter" in root_html
    assert "Saved Views" in root_html
    assert "Portable Delivery" in root_html
    assert "EXPLORE → FOCUS → PRESENT" in root_html
    assert "BUILT FOR RELIABLE HANDOFF" in root_html
    assert 'src="./en-US/map-list/"' in root_html
    assert 'src="./en-US/multilayer/"' in root_html
    assert "Downtown Brooklyn mobility context" in root_html
    assert 'href="./zh-CN/"' in root_html

    english_landing = (site / "en-US" / "index.html").read_text(encoding="utf-8")
    chinese_landing = (site / "zh-CN" / "index.html").read_text(encoding="utf-8")
    assert 'href="../zh-CN/"' in english_landing
    assert 'href="../en-US/"' in chinese_landing
    assert "输入空间数据，交付地图产品。" in chinese_landing
    assert "搜索与筛选" in chinese_landing
    assert "探索 → 聚焦 → 汇报" in chinese_landing
    assert "保存视角" in chinese_landing
    assert original_assets == {path: path.read_bytes() for path in source_paths}


def test_localized_readmes_link_to_their_interactive_demos() -> None:
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    assert f"{PAGES_URL}/en-US/map-list/" in readme_en
    assert f"{PAGES_URL}/en-US/multilayer/" in readme_en
    assert f"{PAGES_URL}/zh-CN/map-list/" in readme_zh
    assert f"{PAGES_URL}/zh-CN/multilayer/" in readme_zh

    for expected in (
        "## Core product capabilities",
        "**Search & filter.**",
        "**Layer control.**",
        "**Saved Views.**",
        "**Portable delivery.**",
        "## Explore → Focus → Present",
        "## Two map products",
        "**Map + list.**",
        "**Multilayer.**",
        "## Quick start",
    ):
        assert expected in readme_en

    for expected in (
        "## 核心产品能力",
        "**搜索与筛选。**",
        "**图层控制。**",
        "**保存视角。**",
        "**成果交付。**",
        "## 探索 → 聚焦 → 汇报",
        "## 两种地图产品",
        "**地图＋清单。**",
        "**多图层。**",
        "## 快速开始",
    ):
        assert expected in readme_zh


def test_pages_workflow_uses_official_actions_and_permissions() -> None:
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(
        encoding="utf-8"
    )
    for expected in (
        "workflow_dispatch:",
        "contents: read",
        "pages: write",
        "id-token: write",
        "actions/configure-pages@v5",
        "actions/upload-pages-artifact@v3",
        "actions/deploy-pages@v5",
        "python scripts/build_demo_site.py --output _site",
        "scripts/demo_projects.py",
        "path: _site",
    ):
        assert expected in workflow
