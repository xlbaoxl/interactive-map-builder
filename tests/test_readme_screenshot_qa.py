from __future__ import annotations

from pathlib import Path

import pytest

from build_demo_site import build_demo_site


pytestmark = pytest.mark.browser
sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright


CASES = (
    ("en-US", "map-list", ("Site A", "Site B")),
    ("en-US", "multilayer", ("Site A", "Site B")),
    ("zh-CN", "map-list", ("场地 A", "场地 B")),
    ("zh-CN", "multilayer", ("场地 A", "场地 B")),
)


def test_generate_current_readme_screenshots(tmp_path: Path) -> None:
    site = build_demo_site(tmp_path / "_site")
    output = Path("readme-screenshot-qa")
    output.mkdir(exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for locale, demo, names in CASES:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto((site / locale / demo / "index.html").resolve().as_uri())
            page.wait_for_function(
                "document.documentElement.dataset.imbReady === 'true'",
                timeout=20_000,
            )
            page.wait_for_function(
                "window.__interactiveMapBuilderQA"
                " && window.__interactiveMapBuilderQA.savedViews"
                " && window.__interactiveMapBuilderQA.savedViews.overviewCaptured === true",
                timeout=10_000,
            )

            # README screenshots must show a real online basemap, not the no-basemap
            # fixture used by Saved Views functional tests. Fail instead of silently
            # producing a blank grey map when tiles are unavailable.
            page.wait_for_function(
                """() => {
                    const tiles = Array.from(document.querySelectorAll('.leaflet-tile-loaded'));
                    return tiles.filter((tile) => tile.complete && tile.naturalWidth > 0).length >= 4;
                }""",
                timeout=25_000,
            )

            page.evaluate("window.__interactiveMapBuilderQA.actions.clearSavedViews()")
            current = page.evaluate("window.__interactiveMapBuilderQA.savedViews")
            center = current["currentCenter"]
            zoom = current["currentZoom"]
            assert center[0] is not None and center[1] is not None and zoom is not None

            first = page.evaluate(
                "([name, center, zoom]) => window.__interactiveMapBuilderQA.actions.saveView(name, center, zoom)",
                [names[0], [center[0] + 0.002, center[1] - 0.002], zoom],
            )
            second = page.evaluate(
                "([name, center, zoom]) => window.__interactiveMapBuilderQA.actions.saveView(name, center, zoom)",
                [names[1], [center[0] - 0.002, center[1] + 0.002], zoom],
            )
            assert first and second
            assert page.evaluate("window.__interactiveMapBuilderQA.actions.goToView('overview')")
            page.wait_for_timeout(800)

            # Re-check tiles after the final Overview navigation because Leaflet may
            # request a fresh tile set during the fly animation.
            page.wait_for_function(
                """() => {
                    const tiles = Array.from(document.querySelectorAll('.leaflet-tile-loaded'));
                    return tiles.filter((tile) => tile.complete && tile.naturalWidth > 0).length >= 4;
                }""",
                timeout=15_000,
            )

            assert page.locator("#imb-saved-view-list .imb-saved-view-chip").count() == 2
            assert page.locator("#imb-saved-view-overview").is_visible()
            assert page.locator("#imb-saved-view-add").is_visible()

            page.screenshot(
                path=str(output / f"{locale}-{demo}.png"),
                full_page=True,
            )
            page.close()
        browser.close()
