from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

import pytest
import requests
import update_skill

from update_skill import (
    UpdateError,
    _backup_managed_install,
    _expected_checksum,
    _manifest_file_set,
    _restore_managed_install,
    _safe_member_path,
    _update_managed_install,
    _validate_extracted_package,
    auto_update,
    check_for_update,
    parse_version,
)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        return FakeResponse(self.payload)


class FakeDownloadResponse:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size: int):
        for start in range(0, len(self.payload), chunk_size):
            yield self.payload[start : start + chunk_size]


class FakeDownloadSession:
    def __init__(self, payloads: dict[str, bytes]):
        self.payloads = payloads

    def get(self, url, *args, **kwargs):
        return FakeDownloadResponse(self.payloads[url])


def _release(version: str) -> dict:
    base = (
        "https://github.com/xlbaoxl/interactive-map-builder/"
        f"releases/download/v{version}"
    )
    return {
        "tag_name": f"v{version}",
        "html_url": f"https://github.com/xlbaoxl/interactive-map-builder/releases/tag/v{version}",
        "draft": False,
        "prerelease": False,
        "assets": [
            {
                "name": f"interactive-map-builder-skill-v{version}.zip",
                "browser_download_url": (
                    f"{base}/interactive-map-builder-skill-v{version}.zip"
                ),
            },
            {
                "name": "SHA256SUMS.txt",
                "browser_download_url": f"{base}/SHA256SUMS.txt",
            },
        ],
    }


def test_parse_version_accepts_stable_tags_and_rejects_other_forms():
    assert parse_version("0.3.2") == (0, 3, 2)
    assert parse_version("v1.4.0") == (1, 4, 0)
    with pytest.raises(UpdateError):
        parse_version("0.3.2-beta")


def test_update_check_uses_network_then_24_hour_cache(tmp_path: Path):
    state = tmp_path / "state.json"
    session = FakeSession(_release("0.3.3"))
    first = check_for_update(
        force=False,
        session=session,
        now=1000,
        state_path=state,
    )
    assert first["status"] == "update_available"
    assert first["latest_version"] == "0.3.3"
    assert first["source"] == "network"
    assert session.calls == 1

    cached = check_for_update(
        force=False,
        session=FakeSession({"not": "used"}),
        now=1100,
        state_path=state,
    )
    assert cached["status"] == "update_available"
    assert cached["source"] == "cache"


def test_update_check_rejects_release_assets_from_an_unexpected_host(tmp_path: Path):
    release = _release("0.3.3")
    release["assets"][0]["browser_download_url"] = "https://example.invalid/skill.zip"
    with pytest.raises(UpdateError, match="unexpected download host"):
        check_for_update(
            force=True,
            session=FakeSession(release),
            now=1000,
            state_path=tmp_path / "state.json",
        )


def test_disabled_and_offline_auto_checks_are_non_blocking(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("IMB_DISABLE_AUTO_UPDATE", "1")
    disabled = check_for_update(force=True, state_path=tmp_path / "state.json")
    assert disabled["status"] == "disabled"
    monkeypatch.delenv("IMB_DISABLE_AUTO_UPDATE")

    class OfflineSession:
        def get(self, *args, **kwargs):
            raise requests.ConnectionError("offline")

    result = auto_update(session=OfflineSession(), force=True)
    assert result["status"] == "update_check_failed"
    assert result["non_blocking"] is True
    assert result["update_available"] is False


def test_checksum_parser_and_zip_member_guard():
    digest = "a" * 64
    assert _expected_checksum(f"{digest}  package.zip\n", "package.zip") == digest
    with pytest.raises(UpdateError):
        _expected_checksum(f"{digest}  other.zip\n", "package.zip")
    with pytest.raises(UpdateError):
        _safe_member_path(zipfile.ZipInfo("../escape.txt"))
    with pytest.raises(UpdateError):
        _safe_member_path(zipfile.ZipInfo(r"folder\..\escape.txt"))


def test_package_manifest_validation_checks_every_file(tmp_path: Path):
    package = tmp_path / "interactive-map-builder"
    package.mkdir()
    skill = package / "SKILL.md"
    skill.write_text("name: interactive-map-builder\n", encoding="utf-8")
    payload = skill.read_bytes()
    manifest = {
        "name": "interactive-map-builder",
        "version": "0.3.2",
        "format": 1,
        "files": [
            {
                "path": "SKILL.md",
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        ],
    }
    (package / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    result = _validate_extracted_package(package, "0.3.2")
    assert result["files"] == ["SKILL.md"]

    skill.write_text("modified", encoding="utf-8")
    with pytest.raises(UpdateError, match="size mismatch|hash mismatch"):
        _validate_extracted_package(package, "0.3.2")


def test_package_manifest_rejects_unlisted_and_unsafe_files(tmp_path: Path):
    package = tmp_path / "interactive-map-builder"
    package.mkdir()
    skill = package / "SKILL.md"
    skill.write_text("name: interactive-map-builder\n", encoding="utf-8")
    payload = skill.read_bytes()
    manifest = {
        "name": "interactive-map-builder",
        "version": "0.3.2",
        "format": 1,
        "files": [
            {
                "path": "SKILL.md",
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        ],
    }
    (package / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (package / "unlisted.py").write_text("raise SystemExit\n", encoding="utf-8")
    with pytest.raises(UpdateError, match="do not match"):
        _validate_extracted_package(package, "0.3.2")

    manifest["files"][0]["path"] = "../outside.txt"
    (package / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    with pytest.raises(UpdateError, match="unsafe path"):
        _manifest_file_set(package)


def test_managed_install_backup_and_restore_are_transactional(tmp_path: Path):
    skill_root = tmp_path / "skill"
    backup_root = tmp_path / "backup"
    skill_root.mkdir()
    files = {
        "SKILL.md": b"old skill\n",
        "scripts/tool.py": b"print('old')\n",
    }
    entries = []
    for relative, payload in files.items():
        path = skill_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        entries.append(
            {
                "path": relative,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    manifest = {
        "name": "interactive-map-builder",
        "version": "0.3.1",
        "format": 1,
        "files": entries,
    }
    (skill_root / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    old_files = _backup_managed_install(skill_root, backup_root)
    (skill_root / "SKILL.md").write_text("broken\n", encoding="utf-8")
    (skill_root / "scripts" / "tool.py").unlink()
    (skill_root / "scripts" / "new.py").write_text("new\n", encoding="utf-8")

    _restore_managed_install(
        skill_root,
        backup_root,
        old_files,
        {"SKILL.md", "scripts/tool.py", "scripts/new.py"},
    )
    assert (skill_root / "SKILL.md").read_bytes() == files["SKILL.md"]
    assert (skill_root / "scripts" / "tool.py").read_bytes() == files[
        "scripts/tool.py"
    ]
    assert not (skill_root / "scripts" / "new.py").exists()
    restored = json.loads(
        (skill_root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8")
    )
    assert restored["version"] == "0.3.1"


def _write_managed_package(root: Path, version: str, files: dict[str, bytes]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    entries = []
    for relative, payload in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        entries.append(
            {
                "path": relative,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    (root / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(
            {
                "name": "interactive-map-builder",
                "version": version,
                "format": 1,
                "files": entries,
            }
        ),
        encoding="utf-8",
    )


def _release_payloads(tmp_path: Path, version: str, files: dict[str, bytes]):
    package = tmp_path / "source" / "interactive-map-builder"
    _write_managed_package(package, version, files)
    archive = tmp_path / f"interactive-map-builder-skill-v{version}.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                handle.write(path, path.relative_to(package.parent).as_posix())
    archive_bytes = archive.read_bytes()
    checksums = (
        hashlib.sha256(archive_bytes).hexdigest()
        + f"  {archive.name}\n"
    ).encode("utf-8")
    return {
        "skill": archive_bytes,
        "checksums": checksums,
    }


def test_managed_release_update_replaces_only_manifest_files(monkeypatch, tmp_path: Path):
    root = tmp_path / "installed"
    _write_managed_package(
        root,
        "0.3.1",
        {"SKILL.md": b"old\n", "scripts/obsolete.py": b"old\n"},
    )
    (root / "user-project.txt").write_text("keep me\n", encoding="utf-8")
    payloads = _release_payloads(
        tmp_path,
        "0.3.2",
        {"SKILL.md": b"new\n", "scripts/new.py": b"new\n"},
    )
    urls = {"skill_zip": "skill", "checksums": "checksums"}
    monkeypatch.setattr(update_skill, "_install_engine", lambda _root: None)
    monkeypatch.setattr(
        update_skill,
        "_doctor_after_update",
        lambda _root: {"status": "pass", "package_version": "0.3.2"},
    )

    result = _update_managed_install(
        root,
        "0.3.2",
        urls,
        FakeDownloadSession(payloads),
    )
    assert result["method"] == "verified-release-zip"
    assert (root / "SKILL.md").read_bytes() == b"new\n"
    assert (root / "scripts" / "new.py").read_bytes() == b"new\n"
    assert not (root / "scripts" / "obsolete.py").exists()
    assert (root / "user-project.txt").read_text(encoding="utf-8") == "keep me\n"


def test_managed_release_update_rolls_back_when_doctor_fails(monkeypatch, tmp_path: Path):
    root = tmp_path / "installed"
    old_files = {"SKILL.md": b"old\n", "scripts/tool.py": b"old tool\n"}
    _write_managed_package(root, "0.3.1", old_files)
    payloads = _release_payloads(
        tmp_path,
        "0.3.2",
        {"SKILL.md": b"new\n", "scripts/new.py": b"new\n"},
    )
    monkeypatch.setattr(update_skill, "_install_engine", lambda _root: None)
    monkeypatch.setattr(
        update_skill,
        "_doctor_after_update",
        lambda _root: (_ for _ in ()).throw(UpdateError("doctor failed")),
    )
    monkeypatch.setattr(
        update_skill,
        "_run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", ""),
    )

    with pytest.raises(UpdateError, match="restored"):
        _update_managed_install(
            root,
            "0.3.2",
            {"skill_zip": "skill", "checksums": "checksums"},
            FakeDownloadSession(payloads),
        )
    assert (root / "SKILL.md").read_bytes() == old_files["SKILL.md"]
    assert (root / "scripts" / "tool.py").read_bytes() == old_files["scripts/tool.py"]
    assert not (root / "scripts" / "new.py").exists()
    restored = json.loads(
        (root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8")
    )
    assert restored["version"] == "0.3.1"
