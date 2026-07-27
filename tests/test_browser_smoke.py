from __future__ import annotations

import base64
import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

from demo_projects import prepare_demo_project
from map_builder import build_map


pytestmark = pytest.mark.browser
sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TRANSPARENT_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M/wHwAF"
    "gAI/ScL6WQAAAABJRU5ErkJggg=="
)


def _wait_ready(page) -> dict:
    page.wait_for_function(
        "document.documentElement.dataset.imbReady === 'true'",
        timeout=15_000,
    )
    qa = page.evaluate("window.__interactiveMapBuilderQA")
    assert qa["ready"] is True
    assert qa["errors"] == []
    return qa


def _copy_example(name: str, destination: Path) -> Path:
    spec_path = prepare_demo_project(
        name,
        examples_root=ROOT / "assets" / "examples",
        destination=destination,
    )
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["static"] = {"enabled": False}
    spec["basemaps"] = []
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return spec_path


def test_searchable_land_use_browser_smoke(tmp_path: Path) -> None:
    project = tmp_path / "project"
    spec_path = _copy_example("map-list", project)
    dist = tmp_path / "dist"
    build_map(spec_path, dist)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto((dist / "map.html").resolve().as_uri())
        initial = _wait_ready(page)
        assert initial["recordCount"] == 1699
        assert initial["mapFeatureCount"] == 1699
        assert initial["rangeFilterCount"] >= 3
        assert initial["visualSystem"] == "atlas-studio-light"
        assert initial["visualPlans"]["parcels"]["role"] == "primary"

        page.evaluate("window.__interactiveMapBuilderQA.actions.setSearch('BROADWAY')")
        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") == 184
        assert page.evaluate("window.__interactiveMapBuilderQA.mapFeatureCount") == 1699

        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.toggleCategory('category_code', 'residential')"
        )
        assert page.evaluate("window.__interactiveMapBuilderQA.activeFilterCount") == 2
        page.evaluate("window.__interactiveMapBuilderQA.actions.resetFilters()")
        assert page.evaluate("window.__interactiveMapBuilderQA.activeFilterCount") == 0

        page.evaluate("window.__interactiveMapBuilderQA.actions.setSearch('BROADWAY')")
        page.locator("#imb-collapse").click()
        assert page.locator("#imb-app").evaluate(
            "node => node.classList.contains('is-sidebar-collapsed')"
        )

        page.locator("#imb-collapse").click()
        page.get_by_text("1 BROADWAY", exact=True).click()
        assert page.evaluate("Boolean(window.__interactiveMapBuilderQA.selectedId)")
        assert page.evaluate("window.__interactiveMapBuilderQA.detailOpen") is True
        assert page.locator("#imb-list [aria-selected='true']").count() == 1
        assert page.locator("#imb-detail").is_visible()

        page.set_viewport_size({"width": 390, "height": 844})
        assert page.locator("#imb-app").evaluate(
            "node => node.scrollWidth <= node.clientWidth"
        )
        browser.close()


def test_multilayer_business_search_and_line_colors(tmp_path: Path) -> None:
    project = tmp_path / "project"
    spec_path = _copy_example("multilayer", project)
    dist = tmp_path / "dist"
    build_map(spec_path, dist)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto((dist / "map.html").resolve().as_uri())
        initial = _wait_ready(page)

        assert initial["recordCount"] == 56
        assert page.locator("#imb-overview-button").inner_text() == "Overview"
        assert page.locator("#imb-overview-button").get_attribute("aria-pressed") == "true"
        assert page.locator("#imb-feature-type-select option").all_inner_texts() == [
            "Layer",
            "Neighborhood areas · 4",
            "Bicycle routes · 36",
            "Subway stations · 16",
        ]
        assert page.evaluate("window.__interactiveMapBuilderQA.activeLayerId") == ""
        assert page.evaluate("window.__interactiveMapBuilderQA.overview") is True
        assert page.evaluate("window.__interactiveMapBuilderQA.layerVisualStates") == {
            "neighborhoods": "base",
            "bike_routes": "base",
            "subway_stations": "base",
        }
        assert page.locator("#imb-search-field").is_hidden()
        page.locator("#imb-feature-type-select").select_option("subway_stations")
        assert page.evaluate("window.__interactiveMapBuilderQA.activeLayerId") == "subway_stations"
        assert page.locator("#imb-search-field").is_visible()
        page.evaluate("window.__interactiveMapBuilderQA.actions.setSearch('Jay')")
        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") == 1
        assert page.evaluate("window.__interactiveMapBuilderQA.mapFeatureCount") == 41

        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.setFeatureType('bike_routes')"
        )
        page.evaluate("window.__interactiveMapBuilderQA.actions.setSearch('VANDERBILT')")
        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") == 1
        line_colors = page.evaluate(
            "window.__interactiveMapBuilderQA.layerStyleColors.bike_routes"
        )
        for expected in ("#287D7C", "#5A8A70", "#B98245"):
            assert expected in line_colors

        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.setFeatureType('neighborhoods')"
        )
        page.evaluate(
            "window.__interactiveMapBuilderQA.actions.setSearch('Brooklyn Heights')"
        )
        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") == 1
        page.locator("#imb-overview-button").click()
        assert page.evaluate("window.__interactiveMapBuilderQA.overview") is True
        assert page.evaluate("window.__interactiveMapBuilderQA.layerVisualStates") == {
            "neighborhoods": "base",
            "bike_routes": "base",
            "subway_stations": "base",
        }

        page.set_viewport_size({"width": 390, "height": 844})
        assert page.locator("#imb-app").evaluate(
            "node => node.scrollWidth <= node.clientWidth"
        )
        browser.close()


def _write_multilayer_project(project: Path, *, linked: bool) -> Path:
    project.mkdir(parents=True)
    for layer_id, name, longitude in (
        ("a", "Alpha", 118.1),
        ("b", "Beta", 118.2),
    ):
        gpd.GeoDataFrame(
            {
                "id": ["1"],
                "name": [name],
                "shared": ["project-1"],
                "category": ["Category 0"],
            },
            geometry=[Point(longitude, 39.6)],
            crs="EPSG:4326",
        ).to_file(project / f"{layer_id}.geojson", driver="GeoJSON")

    layers = []
    for layer_id, name in (("a", "Layer A"), ("b", "Layer B")):
        layer = {
            "id": layer_id,
            "name": name,
            "source": {"path": f"{layer_id}.geojson"},
            "id_field": "id",
            "label_field": "name",
            "search_fields": ["name"],
            "field_labels": {"name": "Name", "category": "Category"},
            "source_note": "Synthetic browser test",
            "style": {
                "color_field": "category",
                "categories": {
                    f"Category {index}": f"#{(index * 2654435761) & 0xFFFFFF:06x}"
                    for index in range(30)
                },
            },
        }
        if linked:
            layer["link_key"] = "shared"
        layers.append(layer)
    spec = {
        "schema_version": "1.1",
        "template": "multilayer",
        "title": "Duplicate ID test",
        "locale": "en-US",
        "layers": layers,
        "basemaps": [
            {
                "name": "One",
                "url": "https://tiles.invalid/one/{z}/{x}/{y}.png",
                "attribution": "Synthetic",
                "visible": True,
            },
            {
                "name": "Two",
                "url": "https://tiles.invalid/two/{z}/{x}/{y}.png",
                "attribution": "Synthetic",
                "visible": False,
            },
            {
                "name": "Three",
                "url": "https://tiles.invalid/three/{z}/{x}/{y}.png",
                "attribution": "Synthetic",
                "visible": False,
            },
            {
                "name": "Broken",
                "url": "https://tiles.invalid/broken/{z}/{x}/{y}.png",
                "attribution": "Synthetic",
                "visible": False,
            },
        ],
        "static": {"enabled": False},
    }
    spec_path = project / "map_spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return spec_path


def test_multilayer_browser_smoke_and_link_isolation(tmp_path: Path) -> None:
    plain_spec = _write_multilayer_project(tmp_path / "plain", linked=False)
    plain_dist = tmp_path / "plain-dist"
    build_map(plain_spec, plain_dist)

    linked_spec = _write_multilayer_project(tmp_path / "linked", linked=True)
    linked_dist = tmp_path / "linked-dist"
    build_map(linked_spec, linked_dist)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.route(
            "https://tiles.invalid/**",
            lambda route: route.fulfill(
                status=500 if "/broken/" in route.request.url else 200,
                body=b"" if "/broken/" in route.request.url else TRANSPARENT_PNG,
                content_type="image/png",
            ),
        )
        page.goto((plain_dist / "map.html").resolve().as_uri())
        plain = _wait_ready(page)
        assert plain["linkGroupSizes"] == {"a::1": 1, "b::1": 1}
        assert plain["visualSystem"] == "atlas-studio-light"
        assert plain["layerDrawOrder"] == ["a", "b"]
        assert plain["layerVisualStates"] == {"a": "base", "b": "base"}
        assert plain["activeLayerId"] == ""
        assert plain["overview"] is True
        assert page.locator("#imb-feature-type-label").inner_text() == "Browse map"
        assert page.locator("#imb-overview-button").get_attribute("aria-pressed") == "true"
        assert page.locator("#imb-feature-type-select option").all_inner_texts() == [
            "Layer",
            "Layer A · 1",
            "Layer B · 1",
        ]
        assert page.locator("#imb-search-field").is_hidden()
        assert page.locator("#imb-overview-message").is_visible()
        assert page.locator("#imb-layer-title").inner_text() == "Layers"
        basemap_select = page.locator("#imb-basemap-control .imb-basemap-select")
        assert basemap_select.get_attribute("aria-label") == "Basemap"
        assert basemap_select.locator("option").all_inner_texts() == [
            "One",
            "Two",
            "Three",
            "Broken",
            "No basemap",
        ]
        assert page.locator(".imb-map-tool-button").get_attribute("title") == "Fullscreen map"

        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") == 0
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.setFeatureType('a')"
        )
        assert page.locator("#imb-search-label").inner_text() == "Name"
        page.evaluate("window.__interactiveMapBuilderQA.actions.setSearch('Alpha')")
        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") == 1
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.setFeatureType('b')"
        )
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.layerVisualStates"
        ) == {"a": "dimmed", "b": "focus"}
        page.evaluate("window.__interactiveMapBuilderQA.actions.setSearch('Alpha')")
        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") == 0
        page.evaluate("window.__interactiveMapBuilderQA.actions.setSearch('Beta')")
        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") == 1

        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.toggleLayer('a', false)"
        )
        assert not page.locator("input[data-layer-id='a']").is_checked()
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.setFeatureType('a')"
        )
        assert page.locator("input[data-layer-id='a']").is_checked()
        assert page.evaluate("window.__interactiveMapBuilderQA.activeLayerId") == "a"
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.toggleLayer('a', false)"
        )
        assert page.evaluate("window.__interactiveMapBuilderQA.overview") is True
        assert page.evaluate("window.__interactiveMapBuilderQA.activeLayerId") == ""
        assert not page.locator("input[data-layer-id='a']").is_checked()
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.setFeatureType('a')"
        )
        assert page.locator("input[data-layer-id='a']").is_checked()
        assert page.evaluate("window.__interactiveMapBuilderQA.actions.setOverview()")
        assert page.evaluate("window.__interactiveMapBuilderQA.activeLayerId") == ""
        assert page.evaluate("window.__interactiveMapBuilderQA.layerVisualStates") == {
            "a": "base",
            "b": "base",
        }
        assert page.evaluate("window.__interactiveMapBuilderQA.actions.setBasemap('Three')")
        assert page.evaluate("window.__interactiveMapBuilderQA.activeBasemap") == "Three"
        assert page.evaluate("window.__interactiveMapBuilderQA.actions.setBasemap('Broken')")
        page.wait_for_function(
            "window.__interactiveMapBuilderQA.basemapFallback === true",
            timeout=10_000,
        )
        assert page.evaluate("window.__interactiveMapBuilderQA.activeBasemap") == "No basemap"
        assert page.locator("#imb-map-message").is_visible()
        assert page.evaluate("window.__interactiveMapBuilderQA.actions.setBasemap('Three')")
        assert page.evaluate("window.__interactiveMapBuilderQA.basemapFallback") is False
        assert not page.locator("#imb-map-message").is_visible()
        assert page.evaluate("window.__interactiveMapBuilderQA.actions.setBasemap('No basemap')")
        assert page.evaluate("window.__interactiveMapBuilderQA.activeBasemap") == "No basemap"
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.selectFeature('a::1')"
        )
        assert page.evaluate("window.__interactiveMapBuilderQA.selectedLinkId") == "a::1"

        page.set_viewport_size({"width": 390, "height": 844})
        page.goto((linked_dist / "map.html").resolve().as_uri())
        linked = _wait_ready(page)
        assert linked["linkGroupSizes"] == {"link::project-1": 2}
        assert page.locator("#imb-app").evaluate(
            "node => node.scrollWidth <= node.clientWidth"
        )

        legend_toggle = page.locator("#imb-legend-toggle")
        layer_control = page.locator("#imb-layer-control")
        legend = page.locator("#imb-legend")
        layer_checkbox = page.locator("input[data-layer-id='a']")
        assert legend_toggle.get_attribute("aria-expanded") == "false"
        assert layer_checkbox.is_visible()
        layer_box = layer_control.bounding_box()
        legend_box = legend.bounding_box()
        assert layer_box is not None and legend_box is not None
        assert layer_box["y"] + layer_box["height"] <= legend_box["y"] + 1

        layer_checkbox.click()
        assert not layer_checkbox.is_checked()
        legend_toggle.click()
        assert legend_toggle.get_attribute("aria-expanded") == "true"
        assert layer_checkbox.is_visible()
        assert page.locator("#imb-legend-groups").evaluate(
            "node => node.scrollHeight > node.clientHeight"
        )
        browser.close()
