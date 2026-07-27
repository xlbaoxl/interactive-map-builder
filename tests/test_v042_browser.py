from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from map_builder import build_map


pytestmark = pytest.mark.browser
sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright


def _write_project(project: Path) -> Path:
    project.mkdir(parents=True)
    water = gpd.GeoDataFrame(
        {
            "id": ["river", "stream", "pond"],
            "water_type": ["river", "stream", "pond"],
        },
        geometry=[
            Polygon([(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01)]),
            Polygon([(0.02, 0), (0.03, 0), (0.03, 0.01), (0.02, 0.01)]),
            Polygon([(0.04, 0), (0.05, 0), (0.05, 0.01), (0.04, 0.01)]),
        ],
        crs="EPSG:4326",
    )
    parking = gpd.GeoDataFrame(
        {"id": ["point-1", "point-2", "area-1"]},
        geometry=[
            Point(0.015, 0.02),
            Point(0.025, 0.02),
            Polygon([(0.03, 0.015), (0.045, 0.015), (0.045, 0.03), (0.03, 0.03)]),
        ],
        crs="EPSG:4326",
    )
    water.to_file(project / "water.geojson", driver="GeoJSON")
    parking.to_file(project / "parking.geojson", driver="GeoJSON")
    spec = {
        "schema_version": "1.1",
        "template": "multilayer",
        "title": "v0.4.2 regression",
        "locale": "en-US",
        "layers": [
            {
                "id": "water",
                "name": "Water bodies",
                "source": {"path": "water.geojson"},
                "id_field": "id",
                "label_field": "water_type",
                "style": {
                    "mode": "categorical",
                    "color_field": "water_type",
                    "categories": {
                        "river": "#4E8587",
                        "stream": "#D39A4A",
                        "pond": "#8C739B",
                    },
                },
            },
            {
                "id": "parking",
                "name": "Parking facilities",
                "source": {"path": "parking.geojson"},
                "id_field": "id",
                "label_field": "id",
                "style": {"mode": "single"},
            },
        ],
        "basemaps": [],
        "map": {
            "controls": {
                "fullscreen": True,
                "scale": True,
                "basemap_switcher": True,
                "layer_control": True,
                "legend": True,
            }
        },
        "static": {"enabled": False},
    }
    spec_path = project / "map_spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return spec_path


def test_semantic_colors_mixed_legend_and_both_panel_toggles(tmp_path: Path) -> None:
    spec_path = _write_project(tmp_path / "project")
    dist = tmp_path / "dist"
    build_map(spec_path, dist)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto((dist / "map.html").resolve().as_uri())
        page.wait_for_function(
            "document.documentElement.dataset.imbReady === 'true'",
            timeout=15_000,
        )
        qa = page.evaluate("window.__interactiveMapBuilderQA")
        assert qa["errors"] == []
        assert qa["legendStyleConsistent"] is True
        assert qa["legendStyleMismatches"] == []
        assert qa["representativeFamilies"]["parking"] == "point"
        assert set(qa["layerFillColors"]["parking"]) == {"#D8892B", "#E2A24D"}
        assert qa["expectedLegendColors"]["water"] == [
            "#2F78BE",
            "#58A5D8",
            "#8CC4E8",
        ]

        right_toggle = page.locator("#imb-controls-collapse")
        assert right_toggle.get_attribute("aria-expanded") == "true"
        right_toggle.click()
        assert page.locator("#imb-app").evaluate(
            "node => node.classList.contains('is-controls-collapsed')"
        )
        assert right_toggle.get_attribute("aria-expanded") == "false"
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.toggleControls(false)"
        )
        assert right_toggle.get_attribute("aria-expanded") == "true"

        left_toggle = page.locator("#imb-collapse")
        assert "imb-sidebar-edge-toggle" in (left_toggle.get_attribute("class") or "")
        left_toggle.click()
        assert page.locator("#imb-app").evaluate(
            "node => node.classList.contains('is-sidebar-collapsed')"
        )
        left_toggle.click()
        assert not page.locator("#imb-app").evaluate(
            "node => node.classList.contains('is-sidebar-collapsed')"
        )
        browser.close()
