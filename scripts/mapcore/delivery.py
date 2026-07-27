"""Transactional delivery manifests and path-safe handoff helpers."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Set, Tuple

DELIVERY_MANIFEST_NAME = "DELIVERY_MANIFEST.json"
DELIVERY_MANIFEST_FORMAT = 1
CORE_OUTPUTS: Tuple[str, ...] = (
    "map.html",
    "map_spec.json",
    "inspection.json",
    "README_USAGE.md",
    "build_report.json",
    DELIVERY_MANIFEST_NAME,
)
KNOWN_STATIC_OUTPUTS: Tuple[str, ...] = (
    "map_slide_16x9.png",
    "map_paper.png",
    "map_paper.svg",
    "map_paper.pdf",
)
_LEGACY_MANAGED_TOP_LEVEL = set(CORE_OUTPUTS) | set(KNOWN_STATIC_OUTPUTS)


class DeliveryError(RuntimeError):
    """Raised when a delivery manifest or managed output is unsafe or inconsistent."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative_path(value: Any) -> str:
    raw = str(value or "").strip()
    posix = PurePosixPath(raw)
    windows = PureWindowsPath(raw)
    if (
        not raw
        or raw == "."
        or "\\" in raw
        or "\x00" in raw
        or posix.is_absolute()
        or windows.is_absolute()
        or ".." in posix.parts
        or not posix.parts
        or (posix.parts and ":" in posix.parts[0])
    ):
        raise DeliveryError(f"Unsafe delivery path: {raw!r}.")
    return posix.as_posix()


def target_path(root: Path, relative: Any) -> Path:
    safe = safe_relative_path(relative)
    resolved_root = root.resolve()
    target = root.joinpath(*PurePosixPath(safe).parts)
    try:
        target.resolve(strict=False).relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise DeliveryError(f"Delivery path escapes its root: {safe!r}.") from exc
    return target


def relative_path(root: Path, path: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError) as exc:
        raise DeliveryError(f"Managed file is outside the delivery root: {path}.") from exc
    return safe_relative_path(relative)


def file_entry(root: Path, path: Path) -> Dict[str, Any]:
    return {
        "path": relative_path(root, path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def write_delivery_manifest(
    root: Path,
    managed_paths: Iterable[Path],
    *,
    engine_version: str,
    built_at: Optional[str],
    preserved_unmanaged_files: int = 0,
) -> Dict[str, Any]:
    unique: Dict[str, Path] = {}
    folded: Set[str] = set()
    for path in managed_paths:
        if not path.is_file():
            raise DeliveryError(f"Managed delivery file is missing: {path}.")
        relative = relative_path(root, path)
        if relative == DELIVERY_MANIFEST_NAME:
            continue
        if relative in unique or relative.casefold() in folded:
            raise DeliveryError(f"Duplicate managed delivery path: {relative}.")
        unique[relative] = path
        folded.add(relative.casefold())
    payload = {
        "name": "interactive-map-builder-delivery",
        "format": DELIVERY_MANIFEST_FORMAT,
        "engine_version": str(engine_version),
        "built_at": built_at,
        "preserved_unmanaged_files": int(preserved_unmanaged_files),
        "files": [file_entry(root, unique[key]) for key in sorted(unique)],
    }
    destination = root / DELIVERY_MANIFEST_NAME
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return payload


def load_delivery_manifest(root: Path) -> Dict[str, Any]:
    path = root / DELIVERY_MANIFEST_NAME
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeliveryError(f"Delivery manifest is unreadable: {path}.") from exc
    if not isinstance(payload, dict):
        raise DeliveryError("Delivery manifest must be a JSON object.")
    if payload.get("name") != "interactive-map-builder-delivery":
        raise DeliveryError("Delivery manifest has an unexpected name.")
    if payload.get("format") != DELIVERY_MANIFEST_FORMAT:
        raise DeliveryError("Delivery manifest has an unsupported format.")
    if not isinstance(payload.get("files"), list):
        raise DeliveryError("Delivery manifest files must be an array.")
    return payload


def verify_delivery_manifest(root: Path) -> Tuple[Dict[str, Any], Set[str], Sequence[str]]:
    errors = []
    try:
        payload = load_delivery_manifest(root)
    except DeliveryError as exc:
        return {}, set(), [str(exc)]
    paths: Set[str] = set()
    folded: Set[str] = set()
    for entry in payload.get("files", []):
        if not isinstance(entry, Mapping):
            errors.append("Delivery manifest contains a non-object file entry.")
            continue
        try:
            relative = safe_relative_path(entry.get("path"))
            path = target_path(root, relative)
        except DeliveryError as exc:
            errors.append(str(exc))
            continue
        if relative in paths or relative.casefold() in folded:
            errors.append(f"Delivery manifest contains a duplicate path: {relative}.")
            continue
        paths.add(relative)
        folded.add(relative.casefold())
        if not path.is_file() or path.is_symlink():
            errors.append(f"Managed delivery file is missing or unsafe: {relative}.")
            continue
        try:
            expected_bytes = int(entry.get("bytes", -1))
        except (TypeError, ValueError):
            expected_bytes = -1
        if path.stat().st_size != expected_bytes:
            errors.append(f"Managed delivery size mismatch: {relative}.")
        expected_sha = str(entry.get("sha256") or "").casefold()
        if len(expected_sha) != 64 or sha256_file(path) != expected_sha:
            errors.append(f"Managed delivery SHA-256 mismatch: {relative}.")
    return payload, paths, errors


def _legacy_managed(relative: str) -> bool:
    parts = PurePosixPath(relative).parts
    return bool(parts and parts[0] in _LEGACY_MANAGED_TOP_LEVEL)


def copy_unmanaged_files(
    existing_root: Path,
    staging_root: Path,
    new_managed_paths: Iterable[str],
) -> int:
    if not existing_root.is_dir():
        return 0
    new_managed = {safe_relative_path(value) for value in new_managed_paths}
    old_managed: Set[str] = set()
    try:
        _manifest, old_managed, errors = verify_delivery_manifest(existing_root)
        if errors:
            old_managed = set()
    except DeliveryError:
        old_managed = set()

    copied = 0
    for source in sorted(existing_root.rglob("*")):
        if not source.is_file() or source.is_symlink():
            continue
        relative = relative_path(existing_root, source)
        if (
            relative == DELIVERY_MANIFEST_NAME
            or relative in old_managed
            or _legacy_managed(relative)
            or relative in new_managed
        ):
            continue
        destination = target_path(staging_root, relative)
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1
    return copied


__all__ = [
    "CORE_OUTPUTS",
    "DELIVERY_MANIFEST_FORMAT",
    "DELIVERY_MANIFEST_NAME",
    "DeliveryError",
    "KNOWN_STATIC_OUTPUTS",
    "copy_unmanaged_files",
    "file_entry",
    "load_delivery_manifest",
    "relative_path",
    "safe_relative_path",
    "sha256_file",
    "target_path",
    "verify_delivery_manifest",
    "write_delivery_manifest",
]
