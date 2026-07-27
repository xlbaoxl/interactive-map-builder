"""Shared resource limits and path-safe ZIP extraction."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence

DEFAULT_MAX_MEMBERS = 4096
DEFAULT_MAX_MEMBER_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 1024 * 1024 * 1024
DEFAULT_MAX_COMPRESSION_RATIO = 200.0


class SafeZipError(ValueError):
    """Raised when a ZIP archive exceeds resource or path-safety limits."""


def safe_member_path(member: zipfile.ZipInfo) -> PurePosixPath:
    raw = str(member.filename)
    path = PurePosixPath(raw)
    mode = (member.external_attr >> 16) & 0o170000
    if (
        not raw
        or "\\" in raw
        or "\x00" in raw
        or path.is_absolute()
        or ".." in path.parts
        or not path.parts
        or (path.parts and ":" in path.parts[0])
    ):
        raise SafeZipError(f"Unsafe ZIP member path: {member.filename!r}")
    if mode == 0o120000:
        raise SafeZipError(f"Symbolic links are not allowed in ZIP archives: {member.filename!r}")
    return path


def validate_archive_resources(
    members: Sequence[zipfile.ZipInfo],
    *,
    max_members: int = DEFAULT_MAX_MEMBERS,
    max_member_bytes: int = DEFAULT_MAX_MEMBER_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_compression_ratio: float = DEFAULT_MAX_COMPRESSION_RATIO,
) -> None:
    if len(members) > max_members:
        raise SafeZipError(f"ZIP archive contains too many members: {len(members)} > {max_members}.")
    total = 0
    folded = set()
    for member in members:
        safe = safe_member_path(member)
        key = safe.as_posix().casefold()
        if key in folded:
            raise SafeZipError(f"ZIP archive contains duplicate member paths: {safe.as_posix()}.")
        folded.add(key)
        size = int(member.file_size)
        compressed = int(member.compress_size)
        if size < 0 or compressed < 0:
            raise SafeZipError(f"ZIP member has invalid size metadata: {safe.as_posix()}.")
        if size > max_member_bytes:
            raise SafeZipError(f"ZIP member exceeds the uncompressed size limit: {safe.as_posix()}.")
        total += size
        if total > max_total_bytes:
            raise SafeZipError("ZIP archive exceeds the total uncompressed size limit.")
        if size > 0:
            ratio = size / max(compressed, 1)
            if ratio > max_compression_ratio:
                raise SafeZipError(f"ZIP member exceeds the compression-ratio limit: {safe.as_posix()}.")


def extract_members(
    archive: zipfile.ZipFile,
    destination: Path,
    members: Iterable[zipfile.ZipInfo],
) -> None:
    root = destination.resolve()
    for member in members:
        safe = safe_member_path(member)
        target = destination.joinpath(*safe.parts)
        try:
            target.resolve(strict=False).relative_to(root)
        except (OSError, ValueError) as exc:
            raise SafeZipError(f"ZIP member escapes the extraction root: {safe.as_posix()}.") from exc
        if member.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(member, "r") as source, target.open("wb") as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)


__all__ = [
    "DEFAULT_MAX_COMPRESSION_RATIO",
    "DEFAULT_MAX_MEMBER_BYTES",
    "DEFAULT_MAX_MEMBERS",
    "DEFAULT_MAX_TOTAL_BYTES",
    "SafeZipError",
    "extract_members",
    "safe_member_path",
    "validate_archive_resources",
]
