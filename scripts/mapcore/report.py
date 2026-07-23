"""Build-report helpers."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence


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
) -> None:
    """Write a portable Chinese usage note without local absolute paths."""

    online = [str(item.get("name") or item.get("url")) for item in basemaps if item.get("url")]
    lines = [
        "# {}：使用说明".format(title),
        "",
        "## 打开交互地图",
        "",
        "- 双击 `{}`，使用现代浏览器打开。".format(html_name),
        "- 页面逻辑、Leaflet、样式和业务几何均已内嵌在单个 HTML 中。",
    ]
    if online:
        lines.append(
            "- 联网时可加载在线底图（{}）；断网时业务几何、搜索、筛选和图层控件仍可使用。"
            .format("、".join(online))
        )
    else:
        lines.append("- 当前配置不依赖在线底图，可直接查看业务几何和控件。")
    if figure_names:
        lines.extend(
            [
                "",
                "## 静态图",
                "",
                "- `map_slide_16x9.png`：1920×1080 汇报图。",
                "- `map_paper.png`、`map_paper.svg`、`map_paper.pdf`：论文与排版用途。",
            ]
        )
    lines.extend(
        [
            "",
            "## 复现与核验",
            "",
            "- `map_spec.json` 是已经解析默认值的最终构建配置。",
            "- `inspection.json` 记录输入图层、字段候选、CRS 和模板推荐。",
            "- `build_report.json` 记录要素数量、几何修复、生成 ID、警告及输出哈希。",
            "- 在 Skill 根目录运行 `python scripts/map_builder.py verify --dist <本目录>` 可复核成果。",
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
