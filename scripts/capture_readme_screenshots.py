#!/usr/bin/env python
"""Regenerate deterministic Atlas README screenshots with Chromium."""

from __future__ import annotations

import argparse
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


def _capture(page, example_name: str, output: Path, work_root: Path) -> None:
    project = work_root / example_name
    spec_path = prepare_demo_project(
        example_name,
        examples_root=EXAMPLES,
        destination=project,
    )
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["static"] = {"enabled": False}
    spec_path.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    dist = work_root / f"{example_name}-dist"
    build_map(spec_path, dist)
    page.goto((dist / "map.html").resolve().as_uri())
    _wait_for_map(page)

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
        page.get_by_text("Fulton St (A-C) MTA Restroom", exact=True).first.click()
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
    output_dir.mkdir(parents=True, exist_ok=True)

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
            _capture(page, "map-list", output_dir / "map-list.png", work_root)
            _capture(page, "multilayer", output_dir / "multilayer.png", work_root)
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
