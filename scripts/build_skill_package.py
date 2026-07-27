#!/usr/bin/env python
"""Build a lean, deterministic Agent Skill distribution ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = "interactive-map-builder"
FIXED_TIMESTAMP = (2026, 1, 1, 0, 0, 0)
ROOT_FILES = (
    "SKILL.md",
    "LICENSE",
    "CHANGELOG.md",
    "pyproject.toml",
    "requirements.txt",
)
DIRECTORIES = (
    "agents",
    "references",
    "scripts/mapcore",
)
SCRIPT_FILES = (
    "scripts/cli.py",
    "scripts/map_builder.py",
    "scripts/update_skill.py",
)


def project_version(root: Path = ROOT) -> str:
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', text, flags=re.MULTILINE)
    if not match:
        raise RuntimeError("pyproject.toml does not declare a static project version.")
    return match.group(1)


def _is_distributable(path: Path) -> bool:
    return (
        path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
        and not path.name.startswith(".")
    )


def iter_package_files(root: Path = ROOT) -> Iterable[Path]:
    for relative in ROOT_FILES + SCRIPT_FILES:
        path = root / relative
        if not path.is_file():
            raise RuntimeError("Required distribution file is missing: {}".format(relative))
        yield path
    for relative in DIRECTORIES:
        directory = root / relative
        if not directory.is_dir():
            raise RuntimeError("Required distribution directory is missing: {}".format(relative))
        for path in sorted(directory.rglob("*")):
            if _is_distributable(path):
                yield path


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def build_skill_package(output: Path, root: Path = ROOT) -> Dict[str, object]:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(set(iter_package_files(root)), key=lambda path: path.relative_to(root).as_posix())
    manifest_files: List[Dict[str, object]] = []

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
            archive.writestr(_zip_info(f"{PACKAGE_ROOT}/{relative}"), data)
            manifest_files.append(
                {
                    "path": relative,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        manifest = {
            "name": PACKAGE_ROOT,
            "version": project_version(root),
            "format": 1,
            "files": manifest_files,
        }
        manifest_data = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        archive.writestr(
            _zip_info(f"{PACKAGE_ROOT}/PACKAGE_MANIFEST.json"),
            manifest_data,
        )

    return {
        "status": "pass",
        "output": str(output),
        "version": project_version(root),
        "file_count": len(manifest_files) + 1,
        "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }


def _parser() -> argparse.ArgumentParser:
    version = project_version()
    parser = argparse.ArgumentParser(
        description="Build a lean Agent Skill ZIP without demos, tests, screenshots, or CI files."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / f"interactive-map-builder-skill-v{version}.zip",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    result = build_skill_package(args.output)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
