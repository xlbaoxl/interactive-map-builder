#!/usr/bin/env python
"""Regenerate deterministic Atlas README screenshots with Chromium."""

from __future__ import annotations

import argparse
import io
import json
import shutil
import tempfile
from pathlib import Path

from demo_projects import prepare_demo_project
from map_builder import build_map

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "assets" / "examples"
MAX_SCREENSHOT_BYTES = 1_700_000
MIN_LOADED_TILES = 8


def _mock_tile_png() -> bytes:
    """Return a quiet deterministic planning-context tile for README captures."""

    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise SystemExit("Install Pillow before capturing README screenshots.") from exc

    image = Image.new("RGB", (256, 256), "#f7f9f6")
    draw = ImageDraw.Draw(image)
    building_fill = "#f0f3ef"
    building_edge = "#e1e7e2"
    for x in range(10, 250, 44):
        for y in range(8, 250, 48):
            width = 25 + ((x + y) // 4) % 11
            height = 16 + ((x * 3 + y) // 7) % 10
            draw.rectangle(
                (x, y, min(252, x + width), min(252, y + height)),
                fill=building_fill,
                outline=building_edge,
                width=1,
            )
    road = "#dbe2e1"
    road_edge = "#cfd8d7"
    for offset in (-100, 30, 160):
        draw.line((offset, 256, offset + 300, -44), fill=road_edge, width=8)
        draw.line((offset, 256, offset + 300, -44), fill=road, width=5)
    for y in (72, 196):
        draw.line((0, y, 256, y), fill="#e6ebe8", width=3)
    payload = io.BytesIO()
    image.save(payload, format="PNG", optimize=True)
    return payload.getvalue()


def _wait_for_map(page) -> None:
    page.wait_for_function(
        "document.documentElement.dataset.imbReady === 'true'",
        timeout=20_000,
    )
    page.wait_for_function(
        """minimum => {
          const tiles = Array.from(document.querySelectorAll('img.leaflet-tile'));
          return tiles.length >= minimum
            && tiles.every(tile => tile.complete && tile.naturalWidth > 0);
        }""",
        arg=MIN_LOADED_TILES,
        timeout=30_000,
    )


def _capture(
    page,
    example_name: str,
    locale: str,
    output: Path,
    work_root: Path,
) -> None:
    project = work_root / locale / example_name
    spec_path = prepare_demo_project(
        example_name,
        examples_root=EXAMPLES,
        destination=project,
        locale=locale,
    )
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["static"] = {"enabled": False}
    spec["basemaps"] = [
        {
            "name": "CARTO Positron",
            "url": "https://tiles.invalid/atlas/{z}/{x}/{y}.png",
            "attribution": "© OpenStreetMap contributors © CARTO",
            "visible": True,
        }
    ]
    spec_path.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    dist = work_root / locale / f"{example_name}-dist"
    build_map(spec_path, dist)
    page.goto((dist / "map.html").resolve().as_uri())
    _wait_for_map(page)
    rendered_locale = page.locator("html").get_attribute("lang")
    if rendered_locale != locale:
        raise RuntimeError(
            f"Expected {locale} map before capture, received {rendered_locale!r}."
        )

    if example_name == "map-list":
        page.evaluate("window.__interactiveMapBuilderQA.actions.setSearch('BROADWAY')")
        page.evaluate(
            "window.__interactiveMapBuilderQA.actions.setRange('year_built', 1880, 2005)"
        )
        result = page.get_by_text("1 BROADWAY", exact=True)
        if result.count() != 1:
            raise RuntimeError(f"Expected one 1 BROADWAY result, found {result.count()}.")
        result.click()
        page.locator("#imb-detail:not([hidden])").wait_for(state="visible", timeout=10_000)
    elif example_name == "multilayer":
        page.get_by_text("Jay St-MetroTech", exact=True).first.click()
        page.locator(".leaflet-popup").wait_for(state="visible", timeout=10_000)
    else:
        raise ValueError(f"Unsupported README screenshot example: {example_name}")

    page.wait_for_function(
        """minimum => {
          const tiles = Array.from(document.querySelectorAll('img.leaflet-tile'));
          return !document.querySelector('.leaflet-zoom-anim')
            && tiles.length >= minimum
            && tiles.every(tile => tile.complete && tile.naturalWidth > 0);
        }""",
        arg=MIN_LOADED_TILES,
        timeout=30_000,
    )
    page.wait_for_timeout(3_000)
    page.screenshot(path=str(output), full_page=False)

    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("Install Pillow before capturing README screenshots.") from exc
    with Image.open(output) as image:
        image.save(output, format="PNG", optimize=True, compress_level=9)
    if output.stat().st_size > MAX_SCREENSHOT_BYTES:
        raise RuntimeError(
            f"{output.name} is {output.stat().st_size:,} bytes; "
            f"the README budget is {MAX_SCREENSHOT_BYTES:,} bytes."
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "assets" / "screenshots"),
    )
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()
    for locale in ("en-US", "zh-CN"):
        (output_dir / locale).mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Install development dependencies and Chromium before capturing screenshots."
        ) from exc

    with tempfile.TemporaryDirectory(prefix="imb-atlas-screenshots-") as temporary:
        work_root = Path(temporary)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(
                viewport={"width": args.width, "height": args.height},
                device_scale_factor=1,
            )
            tile_png = _mock_tile_png()
            page.route(
                "https://tiles.invalid/**",
                lambda route: route.fulfill(
                    status=200,
                    body=tile_png,
                    content_type="image/png",
                ),
            )
            for locale in ("en-US", "zh-CN"):
                for example_name in ("map-list", "multilayer"):
                    _capture(
                        page,
                        example_name,
                        locale,
                        output_dir / locale / f"{example_name}.png",
                        work_root,
                    )
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
