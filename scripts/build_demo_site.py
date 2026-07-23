#!/usr/bin/env python
"""Build the two README examples as a GitHub Pages site."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Sequence

from map_builder import build_map


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "assets" / "examples"
DEMOS = ("map-list", "multilayer")


def _write_root_page(site_dir: Path) -> None:
    (site_dir / "index.html").write_text(
        """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0; url=./map-list/">
  <link rel="canonical" href="./map-list/">
  <title>Interactive Map Builder demos</title>
</head>
<body>
  <p><a href="./map-list/">打开可交互地图 / Open the interactive map</a></p>
  <script>window.location.replace("./map-list/");</script>
</body>
</html>
""",
        encoding="utf-8",
    )
    (site_dir / ".nojekyll").touch()


def _replace_site(staging: Path, destination: Path) -> None:
    destination = destination.resolve()
    filesystem_root = Path(destination.anchor)
    if destination in {ROOT.resolve(), filesystem_root}:
        raise ValueError("Refusing to replace a repository or filesystem root.")
    if destination.exists():
        if not destination.is_dir():
            raise ValueError(f"Output path exists and is not a directory: {destination}")
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(staging, destination)


def build_demo_site(output_dir: Path = ROOT / "_site") -> Path:
    """Generate a clean Pages artifact without changing the source examples."""

    with tempfile.TemporaryDirectory(prefix="interactive-map-builder-pages-") as temp_value:
        temp_dir = Path(temp_value)
        staging = temp_dir / "_site"
        staging.mkdir()

        for demo in DEMOS:
            source_example = EXAMPLES / demo
            working_example = temp_dir / "examples" / demo
            shutil.copytree(source_example, working_example)

            spec_path = working_example / "map_spec.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            static = dict(spec.get("static", {}))
            static["enabled"] = False
            spec["static"] = static
            spec_path.write_text(
                json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            build_dir = temp_dir / "build" / demo
            build_map(spec_path, build_dir)
            target_dir = staging / demo
            target_dir.mkdir(parents=True)
            shutil.copy2(build_dir / "map.html", target_dir / "index.html")

        _write_root_page(staging)
        _replace_site(staging, output_dir)

    return output_dir.resolve()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the map-list and multilayer GitHub Pages demos."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "_site",
        help="Directory to replace with the generated site (default: repository _site).",
    )
    args = parser.parse_args(argv)
    output = build_demo_site(args.output)
    print(f"Built GitHub Pages demos in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
