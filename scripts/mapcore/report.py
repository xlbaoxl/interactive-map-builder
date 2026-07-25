"""Build-report helpers."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

from .locales import catalog_value, load_catalog


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


def write_usage_guide(
    path: Path,
    *,
    title: str,
    html_name: str,
    figure_names: Sequence[str],
    basemaps: Sequence[Mapping[str, Any]],
    portable_bundle: bool,
    locale: str,
) -> None:
    """Write a localized portable usage guide without local absolute paths."""

    messages = catalog_value(load_catalog(locale), "usage_guide")
    online = [str(item.get("name") or item.get("url")) for item in basemaps if item.get("url")]
    lines = [
        "# " + str(messages["title"]).format(title=title),
        "",
        "## " + str(messages["open_heading"]),
        "",
        "- " + str(messages["open_html"]).format(html_name=html_name),
        "- " + str(messages["embedded"]),
    ]
    if online:
        lines.append(
            "- "
            + str(messages["online_basemap"]).format(
                basemaps=str(messages["basemap_separator"]).join(online)
            )
        )
    else:
        lines.append("- " + str(messages["offline"]))
    if figure_names:
        lines.extend(["", "## " + str(messages["figures_heading"]), ""])
        descriptions = messages["figure_descriptions"]
        lines.extend(
            "- "
            + str(messages["figure_item"]).format(
                name=name,
                description=descriptions.get(name, messages["figure_default"]),
            )
            for name in figure_names
        )
    lines.extend(
        [
            "",
            "## " + str(messages["verification_heading"]),
            "",
            "- " + str(messages["portable" if portable_bundle else "record_only"]),
            "- " + str(messages["inspection"]),
            "- " + str(messages["report"]),
            "- " + str(messages["verify"]),
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))


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
