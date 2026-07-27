#!/usr/bin/env python
"""Installed CLI wrapper for Interactive Map Builder.

The deterministic builder remains in :mod:`map_builder`. This wrapper adds
package-level commands that are useful after installation without changing the
existing build command contract.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, version as distribution_version
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import map_builder
from mapcore.spec import current_schema_version
from mapcore.version import __version__


PACKAGE_NAME = "interactive-map-builder"
PACKAGE_VERSION_FALLBACK = __version__


def package_version() -> str:
    """Return the installed package version, with a source-tree fallback."""

    try:
        return distribution_version(PACKAGE_NAME)
    except PackageNotFoundError:
        return PACKAGE_VERSION_FALLBACK


def _doctor_spec() -> Dict[str, Any]:
    return {
        "schema_version": current_schema_version(),
        "template": "map-list",
        "title": "Interactive Map Builder installation check",
        "locale": "en-US",
        "primary_layer": "places",
        "layers": [
            {
                "id": "places",
                "name": "Places",
                "source": {
                    "path": "places.csv",
                    "crs": "EPSG:4326",
                    "geometry": {
                        "type": "lonlat",
                        "x_field": "longitude",
                        "y_field": "latitude",
                    },
                },
                "id_field": "id",
                "label_field": "name",
                "search_fields": ["name", "category"],
                "filter_fields": ["category"],
                "style": {"color": "#2563eb"},
                "source_note": "Generated locally by the offline installation check.",
            }
        ],
        "static": {"enabled": False},
    }


def run_doctor() -> Dict[str, Any]:
    """Run an offline end-to-end build and verification smoke test."""

    with tempfile.TemporaryDirectory(prefix="interactive-map-builder-doctor-") as temp_dir:
        root = Path(temp_dir)
        source = root / "places.csv"
        source.write_text(
            "id,name,category,longitude,latitude\n"
            "A,North Gate,entry,118.1000,39.6000\n"
            "B,Community Center,service,118.1020,39.6015\n",
            encoding="utf-8",
        )
        spec_path = root / "map_spec.json"
        spec_path.write_text(
            json.dumps(_doctor_spec(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        dist = root / "dist"
        build = map_builder.build_map(spec_path, dist)
        verification = map_builder.verify_dist(dist)
        report = build["report"]

        expected = {
            "map.html",
            "map_spec.json",
            "inspection.json",
            "README_USAGE.md",
            "build_report.json",
        }
        actual = {path.name for path in dist.iterdir() if path.is_file()}
        missing = sorted(expected - actual)
        if missing:
            raise RuntimeError("Doctor build is missing: " + ", ".join(missing))

        checks = {
            "data_readable_and_nonempty": bool(
                report["checks"]["data_readable_and_nonempty"]
            ),
            "geometry_valid_and_nonempty": bool(
                report["checks"]["geometry_valid_and_nonempty"]
            ),
            "unique_ids": bool(report["checks"]["unique_ids"]),
            "leaflet_embedded": bool(report["checks"]["html_qa"]["leaflet_embedded"]),
            "verification_passed": verification["status"] == "pass",
            "offline_smoke_build": True,
        }
        if not all(checks.values()):
            failed = sorted(key for key, value in checks.items() if not value)
            raise RuntimeError("Doctor checks failed: " + ", ".join(failed))

        return {
            "status": "pass",
            "package_version": package_version(),
            "engine_version": str(report.get("engine_version", "unknown")),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "checks": checks,
            "feature_count": int(report["performance"]["feature_count"]),
            "verified_outputs": int(verification["verified_outputs"]),
            "network_used": False,
        }


def _doctor_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="interactive-map-builder doctor",
        description="Run an offline installation, build, and verification self-check.",
    )
    parser.add_argument(
        "--output",
        help="Optionally write the JSON result to this path.",
    )
    return parser


def _print_root_help() -> None:
    map_builder._parser(prog="interactive-map-builder").print_help()
    print()
    print("package commands:")
    print("  doctor              Run an offline installation and build self-check.")
    print("  update              Check or apply a verified official release update.")
    print("  --version           Print the installed package version.")


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments in (["-h"], ["--help"]):
        _print_root_help()
        return 0
    if arguments in (["-V"], ["--version"]):
        print(package_version())
        return 0
    if arguments[0] == "update":
        from update_skill import main as update_main

        return update_main(arguments[1:])
    if arguments[0] == "doctor":
        parser = _doctor_parser()
        args = parser.parse_args(arguments[1:])
        try:
            result = run_doctor()
            payload = json.dumps(result, ensure_ascii=False, indent=2)
            print(payload)
            if args.output:
                output = Path(args.output)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(payload + "\n", encoding="utf-8")
            return 0
        except Exception as exc:  # the command must report any installation failure clearly
            print(
                json.dumps(
                    {
                        "status": "fail",
                        "package_version": package_version(),
                        "error": str(exc),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 2
    return map_builder.main(arguments, prog="interactive-map-builder")


if __name__ == "__main__":
    raise SystemExit(main())
