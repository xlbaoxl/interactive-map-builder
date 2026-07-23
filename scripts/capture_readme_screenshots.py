#!/usr/bin/env python
"""Regenerate deterministic README screenshots with Playwright Chromium."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from map_builder import build_map


ROOT = Path(__file__).resolve().parents[1]


def _capture(page, example_name: str, output: Path, work_root: Path) -> None:
    source = ROOT / "assets" / "examples" / example_name
    project = work_root / example_name
    shutil.copytree(source, project)
    spec_path = project / "map_spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["static"] = {"enabled": False}
    spec["basemaps"] = []
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    dist = work_root / f"{example_name}-dist"
    build_map(spec_path, dist)
    page.goto((dist / "map.html").resolve().as_uri())
    page.wait_for_function(
        "document.documentElement.dataset.imbReady === 'true'",
        timeout=15_000,
    )
    page.screenshot(path=str(output))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "assets" / "screenshots"),
    )
    parser.add_argument("--width", type=int, default=1440)
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

    with tempfile.TemporaryDirectory(prefix="imb-screenshots-") as temporary:
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
