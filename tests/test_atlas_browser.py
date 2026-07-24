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
        "schema_version": "1.0",
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
                "popup_fields": ["category", "year", "floors", "area"],
                "sort_fields": ["name", "year", "floors"],
                "field_labels": {
                    "name": "Name",
                    "category": "Category",
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
        browser.close()
