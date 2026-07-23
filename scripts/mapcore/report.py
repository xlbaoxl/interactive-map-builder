"""Build-report helpers."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, Iterable


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_versions(names: Iterable[str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for name in names:
        try:
            result[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            result[name] = "not-installed"
    return result


def environment_report() -> Dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": package_versions(
            ["geopandas", "pandas", "shapely", "pyogrio", "jinja2", "matplotlib"]
        ),
    }


def output_entry(path: Path) -> Dict[str, Any]:
    return {
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def write_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def validate_file_signature(path: Path) -> bool:
    prefix = path.read_bytes()[:16]
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return prefix.startswith(b"%PDF-")
    if suffix == ".png":
        return prefix.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix == ".svg":
        return b"<svg" in path.read_bytes()[:512].lower()
    if suffix == ".html":
        return b"<!doctype html" in path.read_bytes()[:512].lower()
    if suffix == ".json":
        try:
            json.loads(path.read_text(encoding="utf-8"))
            return True
        except (OSError, json.JSONDecodeError):
            return False
    return path.stat().st_size > 0
