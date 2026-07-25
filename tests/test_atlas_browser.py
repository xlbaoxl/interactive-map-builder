from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from map_builder import build_map

pytestmark = pytest.mark.browser
sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright


def _project(tmp_path: Path, *, locale: str = "en-US") -> Path:
    project = tmp_path / "project"
    project.mkdir()
    frame = gpd.GeoDataFrame(
        {
            "id": ["one", "two", "three", "four"],
            "name": ["One Broadway", "Two Broadway", "Three Water", "Four Pine"],
            "category": ["Residential", "Commercial", "Residential", "Civic"],
            "description": [
                "38 LAFAYETTE STREET / IDENTIFIERWITHOUTBREAKS0123456789ABCDEFGHIJKLMN",
                "Second parcel",
                "Third parcel",
                "Fourth parcel",
            ],
            "year": [1910, 1950, 2000, 2020],
            "floors": [8, 20, 4, 12],
            "area": [1000, 5000, 900, 2500],
        },
        geometry=[
            Polygon(
                [
                    (-74.01 + index * 0.002, 40.70),
                    (-74.009 + index * 0.002, 40.70),
                    (-74.009 + index * 0.002, 40.701),
                    (-74.01 + index * 0.002, 40.70),
                ]
            )
            for index in range(4)
        ],
        crs="EPSG:4326",
    )
    frame.to_file(project / "parcels.geojson", driver="GeoJSON")
    spec = {
        "schema_version": "1.1",
        "template": "map-list",
        "title": "Atlas browser test",
        "subtitle": "Range filters and details",
        "locale": locale,
        "primary_layer": "parcels",
        "layers": [
            {
                "id": "parcels",
                "name": "Parcels",
                "source": {"path": "parcels.geojson"},
                "id_field": "id",
                "label_field": "name",
                "search_fields": ["name"],
                "filter_fields": ["category", "year", "floors"],
                "card_fields": ["category", "year", "floors"],
                "tooltip_fields": ["name", "description"],
                "popup_fields": ["category", "year", "floors", "area"],
                "sort_fields": ["name", "year", "floors", "area"],
                "field_labels": {
                    "name": "Name",
                    "category": "Category",
                    "description": "Description",
                    "year": "Year",
                    "floors": "Floors",
                    "area": "Area",
                },
                "style": {
                    "color_field": "category",
                    "categories": {
                        "Residential": "#2f7f83",
                        "Commercial": "#e39a3b",
                        "Civic": "#8b68a6",
                    },
                },
            }
        ],
        "basemaps": [],
        "map": {"search_behavior": "highlight"},
        "list": {
            "summary_metrics": [
                {"type": "count", "label": "Matches"},
                {"type": "sum", "field": "area", "label": "Area"},
                {"type": "median", "field": "year", "label": "Median year"},
            ]
        },
        "static": {"enabled": False},
    }
    spec_path = project / "map_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return spec_path


def _ready(page) -> dict:
    page.wait_for_function(
        "document.documentElement.dataset.imbReady === 'true'",
        timeout=15_000,
    )
    qa = page.evaluate("window.__interactiveMapBuilderQA")
    assert qa["ready"] is True
    assert qa["errors"] == []
    return qa


def test_atlas_filters_kpis_detail_drawer_and_english_ui(tmp_path: Path) -> None:
    spec_path = _project(tmp_path)
    dist = tmp_path / "dist"
    build_map(spec_path, dist)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 860})
        page.goto((dist / "map.html").resolve().as_uri())
        initial = _ready(page)

        assert initial["recordCount"] == 4
        assert initial["rangeFilterCount"] == 2
        assert page.locator("#imb-search").get_attribute("placeholder").startswith("Search")
        assert page.get_by_text("ATLAS DATA EXPLORER", exact=True).is_visible()
        assert page.locator(".imb-kpi").count() == 3
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.hoverFeature('one')"
        )
        tooltip = page.locator(".leaflet-tooltip")
        tooltip.wait_for(state="visible")
        assert "38 LAFAYETTE STREET" in tooltip.inner_text()
        assert tooltip.evaluate(
            """node => {
              const content = node.querySelector('.imb-tooltip');
              const outer = node.getBoundingClientRect();
              const inner = content.getBoundingClientRect();
              return getComputedStyle(node).whiteSpace === 'normal'
                && inner.left >= outer.left - 1
                && inner.right <= outer.right + 1
                && content.scrollWidth <= content.clientWidth + 1;
            }"""
        )
        sort_shell = page.locator(".imb-sort-shell")
        assert sort_shell.is_visible()
        assert sort_shell.evaluate("node => node.closest('#imb-sidebar') !== null")
        assert page.get_by_text("List order", exact=True).is_visible()
        page.locator("#imb-sort").select_option("area")
        assert page.locator("#imb-sort-status").get_by_text(
            "Current: Area · Ascending", exact=True
        ).is_visible()
        first_card = page.locator(".imb-list-card").first
        assert first_card.locator(".imb-card-badge").count() == 0
        assert first_card.locator(".imb-card-id").count() == 0
        assert first_card.evaluate(
            "node => node.style.getPropertyValue('--imb-card-category-color')"
        ) == "#2f7f83"
        assert first_card.locator(".imb-card-sort").count() == 0
        active_sort_item = first_card.locator(".imb-card-meta-item").filter(
            has_text="Area"
        )
        assert active_sort_item.locator(".imb-card-meta-key").get_by_text(
            "Area", exact=True
        ).is_visible()
        assert active_sort_item.locator(".imb-card-meta-value.is-sort-active").get_by_text(
            "900", exact=True
        ).is_visible()
        assert first_card.locator(".imb-card-meta-item").count() == 3
        page.locator("#imb-sort-direction").click()
        assert page.locator("#imb-sort-status").get_by_text(
            "Current: Area · Descending", exact=True
        ).is_visible()
        assert page.locator(".imb-list-card").first.locator(
            ".imb-card-meta-value.is-sort-active"
        ).get_by_text("5000", exact=True).is_visible()

        year_filter = page.locator(".imb-range-filter").filter(has_text="Year")
        assert year_filter.locator("summary").get_attribute("aria-expanded") == "false"
        year_filter.locator("summary").click()
        year_panel = page.locator(".imb-range-inputs").filter(has_text="Year")
        assert year_panel.is_visible()
        assert year_filter.locator("summary").get_attribute("aria-expanded") == "true"
        panel_box = year_panel.bounding_box()
        assert panel_box is not None
        assert panel_box["x"] >= 0
        assert panel_box["y"] >= 0
        assert panel_box["x"] + panel_box["width"] <= 1440
        assert panel_box["y"] + panel_box["height"] <= 860
        page.get_by_label("Year Max").fill("1930")
        page.locator("#imb-result-count").click()
        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") == 1

        floors_filter = page.locator(".imb-range-filter").filter(has_text="Floors")
        floors_filter.locator("summary").click()
        floors_panel = page.locator(".imb-range-inputs").filter(has_text="Floors")
        assert floors_panel.is_visible()
        assert not year_panel.is_visible()
        assert year_filter.locator("summary").get_attribute("aria-expanded") == "false"
        assert floors_filter.locator("summary").get_attribute("aria-expanded") == "true"
        page.keyboard.press("Escape")
        assert not floors_panel.is_visible()
        assert floors_filter.locator("summary").get_attribute("aria-expanded") == "false"
        assert floors_filter.locator("summary").evaluate(
            "node => node === document.activeElement"
        )

        page.evaluate("window.__interactiveMapBuilderQA.actions.resetFilters()")
        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") == 4
        page.evaluate("window.__interactiveMapBuilderQA.actions.setSearch('Broadway')")
        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") == 2
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.setRange('year', 1900, 1930)"
        )
        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") == 1
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.selectFeature('one')"
        )
        assert page.evaluate("window.__interactiveMapBuilderQA.detailOpen") is True
        assert page.locator("#imb-detail").is_visible()
        assert page.locator("#imb-detail-title").get_by_text(
            "One Broadway", exact=True
        ).is_visible()
        assert page.locator("#imb-detail-body").get_by_text(
            "Area", exact=True
        ).is_visible()

        page.evaluate("window.__interactiveMapBuilderQA.actions.resetFilters()")
        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") == 4
        page.evaluate("window.__interactiveMapBuilderQA.actions.closeDetail()")
        assert page.evaluate("window.__interactiveMapBuilderQA.detailOpen") is False

        page.set_viewport_size({"width": 390, "height": 844})
        assert page.locator("#imb-app").evaluate(
            "node => node.scrollWidth <= node.clientWidth"
        )
        assert sort_shell.is_visible()
        mobile_sort_box = sort_shell.bounding_box()
        mobile_list_box = page.locator("#imb-list").bounding_box()
        assert mobile_sort_box is not None
        assert mobile_list_box is not None
        assert mobile_sort_box["y"] + mobile_sort_box["height"] <= mobile_list_box["y"]
        year_filter.locator("summary").click()
        assert year_panel.is_visible()
        mobile_panel_box = year_panel.bounding_box()
        assert mobile_panel_box is not None
        assert mobile_panel_box["x"] >= 0
        assert mobile_panel_box["y"] >= 0
        assert mobile_panel_box["x"] + mobile_panel_box["width"] <= 390
        assert mobile_panel_box["y"] + mobile_panel_box["height"] <= 844
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.clearHover('one')"
        )
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.hoverFeature('one')"
        )
        tooltip.wait_for(state="visible")
        assert tooltip.evaluate(
            """node => {
              const box = node.getBoundingClientRect();
              return box.left >= 0 && box.right <= window.innerWidth;
            }"""
        )
        browser.close()


def test_atlas_chinese_ui_and_aria_labels(tmp_path: Path) -> None:
    spec_path = _project(tmp_path, locale="zh-CN")
    dist = tmp_path / "dist"
    build_map(spec_path, dist)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1000, "height": 760})
        page.goto((dist / "map.html").resolve().as_uri())
        _ready(page)

        assert page.locator("html").get_attribute("lang") == "zh-CN"
        assert page.get_by_text("ATLAS 数据浏览器", exact=True).is_visible()
        assert page.locator("#imb-search").get_attribute("placeholder").startswith("搜索")
        assert page.locator(".imb-command-bar").get_attribute("aria-label") == "地图筛选"
        assert page.locator("#imb-sidebar").get_attribute("aria-label") == "地图对象"
        assert page.locator(".imb-map-tool-button").get_attribute("title") == "全屏地图"
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.locator("#imb-app").evaluate(
            "node => node.scrollWidth <= node.clientWidth"
        )
        browser.close()
