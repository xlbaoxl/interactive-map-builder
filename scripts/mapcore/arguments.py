"""Dependency-free argument parser shared by the package CLI and builder."""

from __future__ import annotations

import argparse


def build_parser(*, prog: str = "python scripts/map_builder.py") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Build lightweight interactive maps and optional report-ready figures.",
        epilog=(
            "This is the deterministic builder command set. For package-level "
            "doctor, update, and version commands, use the installed "
            "interactive-map-builder CLI or python scripts/cli.py."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect", help="Inspect one or more supported local inputs."
    )
    inspect_parser.add_argument("inputs", nargs="+")
    inspect_parser.add_argument("--layer")
    inspect_parser.add_argument("--sheet")
    inspect_parser.add_argument("--crs")
    inspect_parser.add_argument("--x")
    inspect_parser.add_argument("--y")
    inspect_parser.add_argument("--wkt")
    inspect_parser.add_argument("--encoding")
    inspect_parser.add_argument("--output", "--out", dest="output")

    init_parser = subparsers.add_parser(
        "init-spec", help="Create a minimal MapSpec from inspection JSON."
    )
    init_parser.add_argument("inspection", nargs="?")
    init_parser.add_argument("--inspection", dest="inspection_option")
    init_parser.add_argument(
        "--template", choices=("auto", "map-list", "multilayer"), default="auto"
    )
    init_parser.add_argument("--title")
    init_parser.add_argument("--primary-layer")
    init_parser.add_argument("--locale", choices=("en-US", "zh-CN"), default="en-US")
    init_parser.add_argument("--output", "--out", dest="output", default="map_spec.json")

    fetch_parser = subparsers.add_parser(
        "fetch-arcgis", help="Download a FeatureServer layer to local GeoJSON."
    )
    fetch_parser.add_argument("--url", required=True)
    fetch_parser.add_argument("--out", required=True)
    fetch_parser.add_argument("--where", default="1=1")
    fetch_parser.add_argument("--out-fields", default="*")
    fetch_parser.add_argument("--batch-size", type=int, default=200)
    fetch_parser.add_argument("--provenance")

    build_parser = subparsers.add_parser("build", help="Build from a map specification.")
    build_parser.add_argument("spec_path", nargs="?")
    build_parser.add_argument("--spec", dest="spec_option")
    build_parser.add_argument("--output", "--out", dest="output", default="dist")
    build_parser.add_argument(
        "--bundle-sources",
        action="store_true",
        help="Copy source files into dist/data and rewrite MapSpec paths.",
    )

    verify_parser = subparsers.add_parser("verify", help="Verify a built output directory.")
    verify_parser.add_argument("--dist", default="dist")

    run_parser = subparsers.add_parser(
        "run", help="Inspect, initialize, and build when choices are unambiguous."
    )
    run_parser.add_argument("inputs", nargs="+")
    run_parser.add_argument(
        "--template", choices=("auto", "map-list", "multilayer"), default="auto"
    )
    run_parser.add_argument("--title")
    run_parser.add_argument("--primary-layer")
    run_parser.add_argument("--locale", choices=("en-US", "zh-CN"), default="en-US")
    run_parser.add_argument("--layer")
    run_parser.add_argument("--sheet")
    run_parser.add_argument("--crs")
    run_parser.add_argument("--x")
    run_parser.add_argument("--y")
    run_parser.add_argument("--wkt")
    run_parser.add_argument("--encoding")
    run_parser.add_argument("--output", "--out", dest="output", default="dist")
    return parser
