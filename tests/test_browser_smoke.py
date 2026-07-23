from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

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
    source = ROOT / "assets" / "examples" / name
    shutil.copytree(source, destination)
    spec_path = destination / "map_spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["static"] = {"enabled": False}
    spec["basemaps"] = []
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return spec_path


def test_map_list_browser_smoke(tmp_path: Path) -> None:
    project = tmp_path / "project"
    spec_path = _copy_example("map-list", project)
    dist = tmp_path / "dist"
    build_map(spec_path, dist)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto((dist / "map.html").resolve().as_uri())
        initial = _wait_ready(page)
        assert initial["recordCount"] == 3

        page.evaluate("window.__interactiveMapBuilderQA.actions.setSearch('Renewal')")
        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") < 3

        page.evaluate("window.__interactiveMapBuilderQA.actions.toggleSidebar()")
        assert page.locator("#imb-app").evaluate(
            "node => node.classList.contains('is-sidebar-collapsed')"
        )

        page.evaluate("window.__interactiveMapBuilderQA.actions.toggleSidebar()")
        page.locator("#imb-list [data-feature-id]").first.click()
        assert page.evaluate("Boolean(window.__interactiveMapBuilderQA.selectedId)")
        assert page.locator("#imb-list [aria-selected='true']").count() == 1

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
            {"id": ["1"], "name": [name], "shared": ["project-1"]},
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
            "source_note": "Synthetic browser test",
            "style": {"color": "#2563eb"},
        }
        if linked:
            layer["link_key"] = "shared"
        layers.append(layer)
    spec = {
        "schema_version": "1.0",
        "template": "multilayer",
        "title": "Duplicate ID test",
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
                status=200,
                body=TRANSPARENT_PNG,
                content_type="image/png",
            ),
        )
        page.goto((plain_dist / "map.html").resolve().as_uri())
        plain = _wait_ready(page)
        assert plain["linkGroupSizes"] == {"a::1": 1, "b::1": 1}

        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.toggleLayer('a', false)"
        )
        assert not page.locator("input[data-layer-id='a']").is_checked()
        page.evaluate("window.__interactiveMapBuilderQA.actions.setSearch('Alpha')")
        assert page.evaluate("window.__interactiveMapBuilderQA.visibleRecordCount") == 1
        assert page.evaluate("window.__interactiveMapBuilderQA.actions.setBasemap('Two')")
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.selectFeature('a::1')"
        )
        assert page.evaluate("window.__interactiveMapBuilderQA.selectedLinkId") == "a::1"

        page.goto((linked_dist / "map.html").resolve().as_uri())
        linked = _wait_ready(page)
        assert linked["linkGroupSizes"] == {"link::project-1": 2}

        page.set_viewport_size({"width": 390, "height": 844})
        assert page.locator("#imb-app").evaluate(
            "node => node.scrollWidth <= node.clientWidth"
        )
        browser.close()
