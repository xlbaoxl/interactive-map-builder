from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

import pytest
import requests
import update_skill


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
                "browser_download_url": f"{base}/interactive-map-builder-skill-v{version}.zip",
            },
            {
                "name": "SHA256SUMS.txt",
                "browser_download_url": f"{base}/SHA256SUMS.txt",
            },
        ],
    }


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
    return {"skill": archive_bytes, "checksums": checksums}


def test_cache_is_invalidated_when_running_version_changes(monkeypatch, tmp_path: Path):
    state = tmp_path / "state.json"
    root = tmp_path / "skill"
    root.mkdir()
    (root / "SKILL.md").write_text("---\nname: interactive-map-builder\n---\n", encoding="utf-8")
    state.write_text(
        json.dumps(
            {
                "checked_at": 1000,
                "current_version": "0.4.0",
                "latest_version": "0.4.0",
                "release_url": "old",
                "assets": {},
                "skill_root": str(root.resolve()),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(update_skill, "__version__", "0.4.1")
    session = FakeSession(_release("0.4.2"))
    result = update_skill.check_for_update(
        now=1100,
        state_path=state,
        skill_root=root,
        session=session,
    )
    assert session.calls == 1
    assert result["source"] == "network"
    assert result["latest_version"] == "0.4.2"
    assert result["status"] == "update_available"


def test_cache_is_invalidated_for_a_different_skill_root(tmp_path: Path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps(
            {
                "checked_at": 1000,
                "current_version": update_skill.__version__,
                "latest_version": update_skill.__version__,
                "release_url": "old",
                "assets": {},
                "skill_root": str(first.resolve()),
            }
        ),
        encoding="utf-8",
    )
    session = FakeSession(_release(update_skill.__version__))
    result = update_skill.check_for_update(
        now=1100,
        state_path=state,
        skill_root=second,
        session=session,
    )
    assert session.calls == 1
    assert result["source"] == "network"


def test_unmanaged_exact_release_copy_is_adopted(tmp_path: Path):
    root = tmp_path / "installed"
    files = {
        "SKILL.md": b"---\nname: interactive-map-builder\n---\n",
        "scripts/tool.py": b"print('official')\n",
    }
    for relative, payload in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    (root / "user-project.txt").write_text("keep", encoding="utf-8")
    payloads = _release_payloads(tmp_path, "0.4.2", files)
    result = update_skill._adopt_unmanaged_install(
        root,
        "0.4.2",
        {"skill_zip": "skill", "checksums": "checksums"},
        FakeDownloadSession(payloads),
    )
    assert result["method"] == "verified-release-adoption"
    assert json.loads((root / "PACKAGE_MANIFEST.json").read_text())["version"] == "0.4.2"
    assert (root / "user-project.txt").read_text() == "keep"


def test_unmanaged_modified_copy_is_not_adopted(tmp_path: Path):
    root = tmp_path / "installed"
    official = {
        "SKILL.md": b"---\nname: interactive-map-builder\n---\n",
        "scripts/tool.py": b"print('official')\n",
    }
    for relative, payload in official.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    (root / "scripts/tool.py").write_text("print('modified')\n", encoding="utf-8")
    payloads = _release_payloads(tmp_path, "0.4.2", official)
    with pytest.raises(update_skill.UpdateError, match="does not exactly match"):
        update_skill._adopt_unmanaged_install(
            root,
            "0.4.2",
            {"skill_zip": "skill", "checksums": "checksums"},
            FakeDownloadSession(payloads),
        )
    assert not (root / "PACKAGE_MANIFEST.json").exists()


def test_apply_failure_preserves_confirmed_update_metadata(monkeypatch, tmp_path: Path):
    root = tmp_path / "skill"
    root.mkdir()
    (root / "SKILL.md").write_text("---\nname: interactive-map-builder\n---\n", encoding="utf-8")
    (root / ".git").mkdir()
    checked = {
        "status": "update_available",
        "current_version": "0.4.2",
        "latest_version": "0.4.3",
        "release_url": "https://example.invalid/release",
        "source": "network",
        "checked_at": 1000,
        "update_available": True,
        "assets": {"skill_zip": "skill", "checksums": "checksums"},
    }
    monkeypatch.setattr(update_skill, "resolve_skill_root", lambda _value=None: root)
    monkeypatch.setattr(update_skill, "check_for_update", lambda **_kwargs: dict(checked))
    monkeypatch.setattr(
        update_skill,
        "apply_update",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(update_skill.UpdateError("dirty checkout")),
    )
    result = update_skill.auto_update(force=True)
    assert result["status"] == "manual_update_required"
    assert result["phase"] == "apply"
    assert result["latest_version"] == "0.4.3"
    assert result["update_available"] is True
    assert result["source"] == "network"


def test_successful_update_rewrites_cache_for_installed_version(monkeypatch, tmp_path: Path):
    root = tmp_path / "skill"
    root.mkdir()
    (root / "SKILL.md").write_text("---\nname: interactive-map-builder\n---\n", encoding="utf-8")
    (root / ".git").mkdir()
    state = tmp_path / "state.json"
    checked = {
        "status": "update_available",
        "current_version": "0.4.2",
        "latest_version": "0.4.3",
        "release_url": "release",
        "source": "network",
        "checked_at": 1000,
        "update_available": True,
        "assets": {"skill_zip": "skill", "checksums": "checksums"},
    }
    monkeypatch.setattr(update_skill, "resolve_skill_root", lambda _value=None: root)
    monkeypatch.setattr(update_skill, "check_for_update", lambda **_kwargs: dict(checked))
    monkeypatch.setattr(
        update_skill,
        "apply_update",
        lambda result, **_kwargs: {
            **result,
            "status": "updated",
            "installed_version": "0.4.3",
            "update_available": False,
        },
    )
    result = update_skill.auto_update(force=True, state_path=state)
    assert result["status"] == "updated"
    cached = json.loads(state.read_text(encoding="utf-8"))
    assert cached["current_version"] == "0.4.3"
    assert cached["latest_version"] == "0.4.3"
    assert cached["update_available"] is False
