from __future__ import annotations

import zipfile

import pytest

from mapcore.safe_zip import SafeZipError, safe_member_path, validate_archive_resources


def test_safe_zip_rejects_duplicate_casefold_paths() -> None:
    first = zipfile.ZipInfo("folder/Data.shp")
    second = zipfile.ZipInfo("folder/data.shp")
    with pytest.raises(SafeZipError, match="duplicate"):
        validate_archive_resources([first, second])


def test_safe_zip_rejects_excessive_expansion_ratio() -> None:
    member = zipfile.ZipInfo("data.shp")
    member.file_size = 10_000_000
    member.compress_size = 1
    with pytest.raises(SafeZipError, match="compression-ratio"):
        validate_archive_resources([member], max_compression_ratio=100.0)


def test_safe_zip_rejects_windows_and_parent_paths() -> None:
    for value in ("../escape.shp", r"folder\\..\\escape.shp", "C:/escape.shp"):
        with pytest.raises(SafeZipError):
            safe_member_path(zipfile.ZipInfo(value))
