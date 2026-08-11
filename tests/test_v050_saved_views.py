from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

from map_builder import build_map


pytestmark = pytest.mark.browser
sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright


def _write_project(project: Path, template: str, locale: str) -> Path:
    project.mkdir(parents=True)
    places = gpd.GeoDataFrame(
        {
            "id": ["a", "b", "c"],
            "name": ["Alpha", "Bravo", "Charlie"],
            "kind": ["A", "B", "A"],
        },
        geometry=[
            Point(116.38, 39.90),
            Point(116.42, 39.92),
            Point(116.46, 39.94),
        ],
        crs="EPSG:4326",
    )
    places.to_file(project / "places.geojson", driver="GeoJSON")

    layer = {
        "id": "places",
        "name": "Places",
        "source": {"path": "places.geojson"},
        "id_field": "id",
        "label_field": "name",
        "search_fields": ["name"],
        "filter_fields": ["kind"],
        "card_fields": ["kind"],
        "sort_fields": ["name"],
    }
    spec = {
        "schema_version": "1.1",
        "template": template,
        "title": "Saved Views Test",
        "locale": locale,
        "layers": [layer],
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
    if template == "map-list":
        spec["primary_layer"] = "places"

    spec_path = project / "map_spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return spec_path


@pytest.mark.parametrize(
    ("template", "locale", "overview_label", "save_label"),
    [
        ("map-list", "en-US", "Overview", "+ Save view"),
        ("multilayer", "zh-CN", "总览", "+ 保存视角"),
    ],
)
def test_saved_views_navigation_persistence_and_management(
    tmp_path: Path,
    template: str,
    locale: str,
    overview_label: str,
    save_label: str,
) -> None:
    spec_path = _write_project(tmp_path / template, template, locale)
    dist = tmp_path / (template + "-dist")
    build_map(spec_path, dist)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto((dist / "map.html").resolve().as_uri())
        page.wait_for_function(
            "document.documentElement.dataset.imbReady === 'true'",
            timeout=15_000,
        )
        page.wait_for_function(
            "window.__interactiveMapBuilderQA.savedViews"
            " && window.__interactiveMapBuilderQA.savedViews.overviewCaptured === true",
            timeout=5_000,
        )

        qa = page.evaluate("window.__interactiveMapBuilderQA")
        assert qa["errors"] == []
        assert qa["savedViews"]["max"] == 8
        assert qa["savedViews"]["persistent"] is True
        assert page.locator("#imb-saved-view-overview").inner_text() == overview_label
        assert page.locator("#imb-saved-view-add").inner_text() == save_label

        assert page.evaluate("window.__interactiveMapBuilderQA.actions.clearSavedViews()")
        view_id = page.evaluate(
            "window.__interactiveMapBuilderQA.actions.saveView"
            "('Site 1', [39.925, 116.425], 14)"
        )
        assert isinstance(view_id, str) and view_id
        assert page.locator("#imb-saved-view-list .imb-saved-view-chip").inner_text() == "Site 1"

        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.goToView('Site 1')"
        )
        page.wait_for_function(
            "Math.abs(window.__interactiveMapBuilderQA.savedViews.currentZoom - 14) < 0.01"
            " && Math.abs(window.__interactiveMapBuilderQA.savedViews.currentCenter[0] - 39.925) < 0.001"
            " && Math.abs(window.__interactiveMapBuilderQA.savedViews.currentCenter[1] - 116.425) < 0.001",
            timeout=5_000,
        )

        page.reload()
        page.wait_for_function(
            "document.documentElement.dataset.imbReady === 'true'",
            timeout=15_000,
        )
        page.wait_for_function(
            "window.__interactiveMapBuilderQA.actions"
            " && typeof window.__interactiveMapBuilderQA.actions.listSavedViews === 'function'",
            timeout=5_000,
        )
        persisted = page.evaluate(
            "window.__interactiveMapBuilderQA.actions.listSavedViews()"
        )
        assert [item["name"] for item in persisted] == ["Site 1"]
        persisted_id = persisted[0]["id"]

        assert page.evaluate(
            "([id]) => window.__interactiveMapBuilderQA.actions.renameView(id, 'Site A')",
            [persisted_id],
        )
        assert page.locator("#imb-saved-view-list .imb-saved-view-chip").inner_text() == "Site A"
        assert page.evaluate(
            "([id]) => window.__interactiveMapBuilderQA.actions.deleteView(id)",
            [persisted_id],
        )
        assert page.locator("#imb-saved-view-list .imb-saved-view-chip").count() == 0

        assert page.evaluate("window.__interactiveMapBuilderQA.actions.clearSavedViews()")
        for index in range(8):
            saved = page.evaluate(
                "([name, offset]) => window.__interactiveMapBuilderQA.actions.saveView"
                "(name, [39.90 + offset, 116.40 + offset], 13)",
                [f"View {index + 1}", index * 0.001],
            )
            assert saved
        assert page.evaluate(
            "window.__interactiveMapBuilderQA.actions.saveView"
            "('View 9', [39.99, 116.49], 13)"
        ) is False
        assert page.locator("#imb-saved-view-list .imb-saved-view-chip").count() == 8
        assert page.locator("#imb-saved-view-add").is_disabled()

        page.set_viewport_size({"width": 1100, "height": 760})
        page.wait_for_timeout(200)
        layout = page.evaluate(
            """() => {
                const strip = document.querySelector('.imb-saved-view-strip');
                const list = document.getElementById('imb-saved-view-list');
                const add = document.getElementById('imb-saved-view-add');
                const manage = document.getElementById('imb-saved-view-manage');
                const root = document.getElementById('imb-saved-views');
                const listRect = list.getBoundingClientRect();
                const addRect = add.getBoundingClientRect();
                const manageRect = manage.getBoundingClientRect();
                const rootRect = root.getBoundingClientRect();
                return {
                    scrollWidth: list.scrollWidth,
                    clientWidth: list.clientWidth,
                    listRight: listRect.right,
                    addLeft: addRect.left,
                    addRight: addRect.right,
                    manageLeft: manageRect.left,
                    manageRight: manageRect.right,
                    rootLeft: rootRect.left,
                    rootRight: rootRect.right,
                    listOverflowX: getComputedStyle(list).overflowX,
                    stripOverflowX: getComputedStyle(strip).overflowX,
                };
            }"""
        )
        assert layout["scrollWidth"] > layout["clientWidth"]
        assert layout["listOverflowX"] in {"auto", "scroll"}
        assert layout["stripOverflowX"] == "hidden"
        assert layout["listRight"] <= layout["addLeft"] + 1
        assert layout["addRight"] <= layout["manageLeft"] + 1
        assert layout["addLeft"] >= layout["rootLeft"] - 1
        assert layout["manageRight"] <= layout["rootRight"] + 1

        page.evaluate(
            """() => {
                const list = document.getElementById('imb-saved-view-list');
                list.scrollLeft = list.scrollWidth;
            }"""
        )
        page.wait_for_timeout(100)
        list_box = page.locator("#imb-saved-view-list").bounding_box()
        last_box = page.locator("#imb-saved-view-list .imb-saved-view-chip").nth(7).bounding_box()
        assert list_box is not None and last_box is not None
        assert last_box["left"] >= list_box["left"] - 1
        assert last_box["right"] <= list_box["right"] + 1
        browser.close()
