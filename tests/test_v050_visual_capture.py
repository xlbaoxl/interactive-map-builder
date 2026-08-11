from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, Polygon

from map_builder import build_map


pytestmark = pytest.mark.browser
sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright


SCREENSHOT_DIR = Path("qa-screenshots")


def _write_map_list(project: Path) -> Path:
    project.mkdir(parents=True)
    sites = gpd.GeoDataFrame(
        {
            "id": ["a", "b", "c", "d", "e", "f"],
            "name": ["North Gate", "Library", "Community Hall", "Market", "Clinic", "South Park"],
            "kind": ["Access", "Civic", "Civic", "Retail", "Health", "Open space"],
        },
        geometry=[
            Point(116.390, 39.910),
            Point(116.405, 39.918),
            Point(116.420, 39.915),
            Point(116.432, 39.904),
            Point(116.413, 39.896),
            Point(116.395, 39.898),
        ],
        crs="EPSG:4326",
    )
    context = gpd.GeoDataFrame(
        {"id": ["study-area"], "name": ["Study area"]},
        geometry=[Polygon([(116.382, 39.890), (116.440, 39.890), (116.440, 39.924), (116.382, 39.924)])],
        crs="EPSG:4326",
    )
    sites.to_file(project / "sites.geojson", driver="GeoJSON")
    context.to_file(project / "context.geojson", driver="GeoJSON")
    spec = {
        "schema_version": "1.1",
        "template": "map-list",
        "title": "Community Facilities Review",
        "subtitle": "Saved Views visual QA · v0.5.0",
        "locale": "en-US",
        "primary_layer": "sites",
        "layers": [
            {
                "id": "sites",
                "name": "Facilities",
                "source": {"path": "sites.geojson"},
                "id_field": "id",
                "label_field": "name",
                "search_fields": ["name", "kind"],
                "filter_fields": ["kind"],
                "card_fields": ["kind"],
                "sort_fields": ["name"],
            },
            {
                "id": "context",
                "name": "Study area",
                "source": {"path": "context.geojson"},
                "id_field": "id",
                "label_field": "name",
                "visible": True,
            },
        ],
        "basemaps": [],
        "map": {"controls": {"fullscreen": True, "scale": True, "basemap_switcher": True, "layer_control": True, "legend": True}},
        "static": {"enabled": False},
    }
    path = project / "map_spec.json"
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_multilayer(project: Path) -> Path:
    project.mkdir(parents=True)
    neighborhoods = gpd.GeoDataFrame(
        {"id": ["west", "east"], "name": ["西片区", "东片区"]},
        geometry=[
            Polygon([(116.382, 39.890), (116.411, 39.890), (116.411, 39.924), (116.382, 39.924)]),
            Polygon([(116.411, 39.890), (116.440, 39.890), (116.440, 39.924), (116.411, 39.924)]),
        ],
        crs="EPSG:4326",
    )
    routes = gpd.GeoDataFrame(
        {"id": ["r1", "r2"], "name": ["东西主轴", "南北联系"]},
        geometry=[
            LineString([(116.385, 39.907), (116.438, 39.907)]),
            LineString([(116.412, 39.893), (116.412, 39.922)]),
        ],
        crs="EPSG:4326",
    )
    sites = gpd.GeoDataFrame(
        {"id": ["s1", "s2", "s3", "s4"], "name": ["北入口", "文化中心", "市场", "南公园"]},
        geometry=[
            Point(116.392, 39.918),
            Point(116.410, 39.914),
            Point(116.430, 39.904),
            Point(116.400, 39.897),
        ],
        crs="EPSG:4326",
    )
    neighborhoods.to_file(project / "neighborhoods.geojson", driver="GeoJSON")
    routes.to_file(project / "routes.geojson", driver="GeoJSON")
    sites.to_file(project / "sites.geojson", driver="GeoJSON")
    spec = {
        "schema_version": "1.1",
        "template": "multilayer",
        "title": "社区更新重点场地",
        "subtitle": "v0.5.0 保存视角视觉验收",
        "locale": "zh-CN",
        "layers": [
            {"id": "neighborhoods", "name": "片区边界", "source": {"path": "neighborhoods.geojson"}, "id_field": "id", "label_field": "name", "search_fields": ["name"]},
            {"id": "routes", "name": "联系轴线", "source": {"path": "routes.geojson"}, "id_field": "id", "label_field": "name", "search_fields": ["name"]},
            {"id": "sites", "name": "重点场地", "source": {"path": "sites.geojson"}, "id_field": "id", "label_field": "name", "search_fields": ["name"]},
        ],
        "basemaps": [],
        "map": {"controls": {"fullscreen": True, "scale": True, "basemap_switcher": True, "layer_control": True, "legend": True}},
        "static": {"enabled": False},
    }
    path = project / "map_spec.json"
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _prepare_views(page) -> None:
    page.wait_for_function(
        "document.documentElement.dataset.imbReady === 'true' && window.__interactiveMapBuilderQA.savedViews && window.__interactiveMapBuilderQA.savedViews.overviewCaptured",
        timeout=15_000,
    )
    page.evaluate("window.__interactiveMapBuilderQA.actions.clearSavedViews()")
    page.evaluate("window.__interactiveMapBuilderQA.actions.saveView('Site 1', [39.918, 116.392], 15)")
    page.evaluate("window.__interactiveMapBuilderQA.actions.saveView('Site 2', [39.907, 116.412], 15)")
    page.evaluate("window.__interactiveMapBuilderQA.actions.saveView('Site 3', [39.898, 116.430], 15)")
    page.evaluate("window.__interactiveMapBuilderQA.actions.goToView('Site 2')")
    page.wait_for_timeout(800)


def _prepare_max_views(page) -> None:
    page.evaluate("window.__interactiveMapBuilderQA.actions.clearSavedViews()")
    for index in range(8):
        page.evaluate(
            "([name, offset]) => window.__interactiveMapBuilderQA.actions.saveView(name, [39.90 + offset, 116.40 + offset], 14)",
            [f"Site {index + 1}", index * 0.001],
        )
    page.wait_for_timeout(300)


def test_capture_saved_views_visuals(tmp_path: Path) -> None:
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    map_list_spec = _write_map_list(tmp_path / "map-list")
    multilayer_spec = _write_multilayer(tmp_path / "multilayer")
    map_list_dist = tmp_path / "map-list-dist"
    multilayer_dist = tmp_path / "multilayer-dist"
    build_map(map_list_spec, map_list_dist)
    build_map(multilayer_spec, multilayer_dist)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto((map_list_dist / "map.html").resolve().as_uri())
        _prepare_views(page)
        assert page.evaluate("window.__interactiveMapBuilderQA.errors") == []
        page.screenshot(path=str(SCREENSHOT_DIR / "map-list-en-1440.png"), full_page=True)
        page.set_viewport_size({"width": 1100, "height": 760})
        page.wait_for_timeout(300)
        page.screenshot(path=str(SCREENSHOT_DIR / "map-list-en-1100.png"), full_page=True)
        _prepare_max_views(page)
        page.screenshot(path=str(SCREENSHOT_DIR / "map-list-en-1100-max8.png"), full_page=True)
        page.close()

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto((multilayer_dist / "map.html").resolve().as_uri())
        _prepare_views(page)
        assert page.evaluate("window.__interactiveMapBuilderQA.errors") == []
        page.screenshot(path=str(SCREENSHOT_DIR / "multilayer-zh-1440.png"), full_page=True)
        page.set_viewport_size({"width": 1100, "height": 760})
        page.wait_for_timeout(300)
        page.screenshot(path=str(SCREENSHOT_DIR / "multilayer-zh-1100.png"), full_page=True)
        browser.close()
