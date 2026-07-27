#!/usr/bin/env python
"""Regenerate deterministic Atlas README screenshots with Chromium."""

from __future__ import annotations

import argparse
import io
import json
import shutil
import re
import tempfile
from pathlib import Path

from demo_projects import prepare_demo_project
from map_builder import build_map

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "assets" / "examples"
MAX_SCREENSHOT_BYTES = 1_700_000
MIN_LOADED_TILES = 8


def _mock_tile_png(url: str) -> bytes:
    """Return a coordinate-aware quiet context tile for deterministic captures."""

    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise SystemExit("Install Pillow before capturing README screenshots.") from exc

    match = re.search(r"/(\d+)/(\d+)/(\d+)\.png(?:\?.*)?$", url)
    if match:
        zoom, tile_x, tile_y = (int(value) for value in match.groups())
    else:
        zoom, tile_x, tile_y = 0, 0, 0
    origin_x = tile_x * 256
    origin_y = tile_y * 256
    seed = (zoom * 73856093) ^ (tile_x * 19349663) ^ (tile_y * 83492791)

    image = Image.new("RGB", (256, 256), "#f7f9f6")
    draw = ImageDraw.Draw(image)
    road_edge = "#dde4e2"
    road_fill = "#fdfefd"
    building_fill = "#eef2ed"
    building_edge = "#e2e8e3"
    park_fill = "#edf4eb"

    # Draw one continuous, low-contrast orthogonal street fabric in world-pixel space.
    vertical_spacing = 78
    horizontal_spacing = 64
    vertical_offset = 17 + (zoom % 5) * 3
    horizontal_offset = 11 + (zoom % 7) * 2
    first_x = ((origin_x - vertical_offset) // vertical_spacing) * vertical_spacing + vertical_offset
    first_y = ((origin_y - horizontal_offset) // horizontal_spacing) * horizontal_spacing + horizontal_offset
    for world_x in range(first_x, origin_x + 256 + vertical_spacing, vertical_spacing):
        local_x = world_x - origin_x
        draw.line((local_x, 0, local_x, 256), fill=road_edge, width=7)
        draw.line((local_x, 0, local_x, 256), fill=road_fill, width=4)
    for world_y in range(first_y, origin_y + 256 + horizontal_spacing, horizontal_spacing):
        local_y = world_y - origin_y
        draw.line((0, local_y, 256, local_y), fill=road_edge, width=7)
        draw.line((0, local_y, 256, local_y), fill=road_fill, width=4)

    # Add varied blocks and occasional green space without repeating an identical tile image.
    block_x = first_x
    while block_x < origin_x + 256:
        block_y = first_y
        while block_y < origin_y + 256:
            cell_seed = seed ^ (block_x * 2654435761) ^ (block_y * 2246822519)
            left = max(3, block_x - origin_x + 9 + (cell_seed % 7))
            top = max(3, block_y - origin_y + 9 + ((cell_seed >> 3) % 7))
            right = min(253, block_x - origin_x + vertical_spacing - 9 - ((cell_seed >> 6) % 7))
            bottom = min(253, block_y - origin_y + horizontal_spacing - 9 - ((cell_seed >> 9) % 7))
            if right > left + 8 and bottom > top + 8:
                if cell_seed % 13 == 0:
                    draw.rounded_rectangle(
                        (left, top, right, bottom),
                        radius=5,
                        fill=park_fill,
                        outline="#e3ece0",
                    )
                else:
                    inset = 2 + (cell_seed % 5)
                    inner_left = left + inset
                    inner_top = top + inset
                    inner_right = right - inset
                    inner_bottom = bottom - inset
                    if inner_right >= inner_left and inner_bottom >= inner_top:
                        draw.rectangle(
                            (inner_left, inner_top, inner_right, inner_bottom),
                            fill=building_fill,
                            outline=building_edge,
                            width=1,
                        )
            block_y += horizontal_spacing
        block_x += vertical_spacing

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
        overview = page.evaluate("window.__interactiveMapBuilderQA.overview")
        active_layer = page.evaluate("window.__interactiveMapBuilderQA.activeLayerId")
        if overview is not True or active_layer:
            raise RuntimeError("The multilayer README capture must use the neutral overview state.")
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
            tile_cache = {}

            def fulfill_tile(route) -> None:
                url = route.request.url
                if url not in tile_cache:
                    tile_cache[url] = _mock_tile_png(url)
                route.fulfill(
                    status=200,
                    body=tile_cache[url],
                    content_type="image/png",
                )

            page.route("https://tiles.invalid/**", fulfill_tile)
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
