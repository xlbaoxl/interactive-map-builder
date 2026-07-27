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
    def __init__(self, payload): self._payload = payload
    def raise_for_status(self): return None
    def json(self): return self._payload

class FakeSession:
    def __init__(self, payload): self.payload = payload; self.calls = 0
    def get(self, *args, **kwargs): self.calls += 1; return FakeResponse(self.payload)

class FakeDownloadResponse:
    def __init__(self, payload: bytes): self.payload = payload; self.headers = {"Content-Length": str(len(payload))}
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def raise_for_status(self): return None
    def iter_content(self, chunk_size: int):
        for start in range(0, len(self.payload), chunk_size): yield self.payload[start:start+chunk_size]

class FakeDownloadSession:
    def __init__(self, payloads): self.payloads = payloads
    def get(self, url, *args, **kwargs): return FakeDownloadResponse(self.payloads[url])


def _release(version: str) -> dict:
    base = f"https://github.com/xlbaoxl/interactive-map-builder/releases/download/v{version}"
    return {
        "tag_name": f"v{version}", "html_url": f"https://github.com/xlbaoxl/interactive-map-builder/releases/tag/v{version}",
        "draft": False, "prerelease": False,
        "assets": [
            {"name": f"interactive-map-builder-skill-v{version}.zip", "browser_download_url": f"{base}/interactive-map-builder-skill-v{version}.zip"},
            {"name": "SHA256SUMS.txt", "browser_download_url": f"{base}/SHA256SUMS.txt"},
        ],
    }


def _write_managed_package(root: Path, version: str, files: dict[str, bytes]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    entries=[]
    for relative,payload in files.items():
        path=root/relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(payload)
        entries.append({"path":relative,"bytes":len(payload),"sha256":hashlib.sha256(payload).hexdigest()})
    (root/"PACKAGE_MANIFEST.json").write_text(json.dumps({"name":"interactive-map-builder","version":version,"format":1,"files":entries}), encoding="utf-8")


def _release_payloads(tmp_path: Path, version: str, files: dict[str, bytes]):
    package=tmp_path/"source"/"interactive-map-builder"; _write_managed_package(package,version,files)
    archive=tmp_path/f"interactive-map-builder-skill-v{version}.zip"
    with zipfile.ZipFile(archive,"w") as handle:
        for path in sorted(package.rglob("*")):
            if path.is_file(): handle.write(path,path.relative_to(package.parent).as_posix())
    archive_bytes=archive.read_bytes()
    checksums=(hashlib.sha256(archive_bytes).hexdigest()+f"  {archive.name}\n").encode()
    return {"skill":archive_bytes,"checksums":checksums}


def test_parse_version():
    assert update_skill.parse_version("0.3.2") == (0,3,2)
    assert update_skill.parse_version("v1.4.0") == (1,4,0)
    with pytest.raises(update_skill.UpdateError): update_skill.parse_version("0.3.2-beta")


def test_network_then_cache(tmp_path):
    state=tmp_path/"state.json"; session=FakeSession(_release("0.4.4"))
    first=update_skill.check_for_update(session=session,now=1000,state_path=state)
    assert first["status"]=="update_available" and session.calls==1
    cached=update_skill.check_for_update(session=FakeSession({"not":"used"}),now=1100,state_path=state)
    assert cached["source"]=="cache"


def test_bad_host(tmp_path):
    release=_release("0.4.4"); release["assets"][0]["browser_download_url"]="https://example.invalid/skill.zip"
    with pytest.raises(update_skill.UpdateError, match="unexpected download host"):
        update_skill.check_for_update(force=True,session=FakeSession(release),now=1000,state_path=tmp_path/"state.json")


def test_disabled_and_offline(monkeypatch,tmp_path):
    monkeypatch.setenv("IMB_DISABLE_AUTO_UPDATE","1")
    assert update_skill.check_for_update(force=True,state_path=tmp_path/"state.json")["status"]=="disabled"
    monkeypatch.delenv("IMB_DISABLE_AUTO_UPDATE")
    class OfflineSession:
        def get(self,*args,**kwargs): raise requests.ConnectionError("offline")
    result=update_skill.auto_update(session=OfflineSession(),force=True)
    assert result["status"]=="update_check_failed" and result["non_blocking"] is True and result["update_available"] is False


def test_checksum_and_zip_guard():
    digest="a"*64
    assert update_skill._expected_checksum(f"{digest}  package.zip\n","package.zip")==digest
    with pytest.raises(update_skill.UpdateError): update_skill._expected_checksum(f"{digest} other.zip\n","package.zip")
    with pytest.raises(update_skill.UpdateError): update_skill._safe_member_path(zipfile.ZipInfo("../escape.txt"))
    with pytest.raises(update_skill.UpdateError): update_skill._safe_member_path(zipfile.ZipInfo(r"folder\..\escape.txt"))


def test_manifest_validation(tmp_path):
    package=tmp_path/"interactive-map-builder"; package.mkdir(); skill=package/"SKILL.md"; skill.write_text("name: interactive-map-builder\n")
    payload=skill.read_bytes(); manifest={"name":"interactive-map-builder","version":"0.3.2","format":1,"files":[{"path":"SKILL.md","bytes":len(payload),"sha256":hashlib.sha256(payload).hexdigest()}]}
    (package/"PACKAGE_MANIFEST.json").write_text(json.dumps(manifest))
    assert update_skill._validate_extracted_package(package,"0.3.2")["files"]==["SKILL.md"]
    skill.write_text("modified")
    with pytest.raises(update_skill.UpdateError,match="size mismatch|hash mismatch"): update_skill._validate_extracted_package(package,"0.3.2")


def test_backup_restore(tmp_path):
    root=tmp_path/"skill"; backup=tmp_path/"backup"; files={"SKILL.md":b"old skill\n","scripts/tool.py":b"print('old')\n"}; _write_managed_package(root,"0.3.1",files)
    old=update_skill._backup_managed_install(root,backup); (root/"SKILL.md").write_text("broken\n"); (root/"scripts/tool.py").unlink(); (root/"scripts/new.py").write_text("new\n")
    update_skill._restore_managed_install(root,backup,old,{"SKILL.md","scripts/tool.py","scripts/new.py"})
    assert (root/"SKILL.md").read_bytes()==files["SKILL.md"] and not (root/"scripts/new.py").exists()


def test_managed_update(monkeypatch,tmp_path):
    root=tmp_path/"installed"; _write_managed_package(root,"0.3.1",{"SKILL.md":b"old\n","scripts/obsolete.py":b"old\n"}); (root/"user-project.txt").write_text("keep me")
    payloads=_release_payloads(tmp_path,"0.3.2",{"SKILL.md":b"new\n","scripts/new.py":b"new\n"})
    monkeypatch.setattr(update_skill,"_install_engine",lambda _root:None); monkeypatch.setattr(update_skill,"_doctor_after_update",lambda _root:{"status":"pass","package_version":"0.3.2"})
    result=update_skill._update_managed_install(root,"0.3.2",{"skill_zip":"skill","checksums":"checksums"},FakeDownloadSession(payloads))
    assert result["method"]=="verified-release-zip" and (root/"SKILL.md").read_bytes()==b"new\n" and not (root/"scripts/obsolete.py").exists() and (root/"user-project.txt").read_text()=="keep me"


def test_managed_rollback(monkeypatch,tmp_path):
    root=tmp_path/"installed"; old={"SKILL.md":b"old\n","scripts/tool.py":b"old tool\n"}; _write_managed_package(root,"0.3.1",old)
    payloads=_release_payloads(tmp_path,"0.3.2",{"SKILL.md":b"new\n","scripts/new.py":b"new\n"})
    monkeypatch.setattr(update_skill,"_install_engine",lambda _root:None); monkeypatch.setattr(update_skill,"_doctor_after_update",lambda _root:(_ for _ in ()).throw(update_skill.UpdateError("doctor failed"))); monkeypatch.setattr(update_skill,"_run",lambda *args,**kwargs:subprocess.CompletedProcess(args[0],0,"",""))
    with pytest.raises(update_skill.UpdateError,match="restored"):
        update_skill._update_managed_install(root,"0.3.2",{"skill_zip":"skill","checksums":"checksums"},FakeDownloadSession(payloads))
    assert (root/"SKILL.md").read_bytes()==old["SKILL.md"] and (root/"scripts/tool.py").read_bytes()==old["scripts/tool.py"] and not (root/"scripts/new.py").exists()


def test_cache_is_invalidated_when_running_version_changes(monkeypatch, tmp_path: Path):
    state = tmp_path / "state.json"
    root = tmp_path / "skill"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\nname: interactive-map-builder\n---\n", encoding="utf-8"
    )
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
    manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "0.4.2"
    assert (root / "user-project.txt").read_text(encoding="utf-8") == "keep"


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
    (root / "SKILL.md").write_text(
        "---\nname: interactive-map-builder\n---\n", encoding="utf-8"
    )
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
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            update_skill.UpdateError("dirty checkout")
        ),
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
    (root / "SKILL.md").write_text(
        "---\nname: interactive-map-builder\n---\n", encoding="utf-8"
    )
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


class RoutedResponse:
    def __init__(self, *, payload=None, data: bytes | None = None):
        self._payload = payload
        self._data = data
        self.headers = {"Content-Length": str(len(data or b""))}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload

    def iter_content(self, chunk_size: int):
        data = self._data or b""
        for start in range(0, len(data), chunk_size):
            yield data[start : start + chunk_size]


class RoutedSession:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, *args, **kwargs):
        self.calls.append(url)
        response = self.routes[url]
        if isinstance(response, bytes):
            return RoutedResponse(data=response)
        return RoutedResponse(payload=response)


def test_auto_adopts_exact_copy_then_applies_newer_release(monkeypatch, tmp_path: Path):
    root = tmp_path / "installed"
    current_files = {
        "SKILL.md": b"---\nname: interactive-map-builder\n---\n",
        "scripts/tool.py": b"print('current')\n",
    }
    next_files = {
        "SKILL.md": b"---\nname: interactive-map-builder\n---\n",
        "scripts/tool.py": b"print('next')\n",
        "scripts/new.py": b"print('new')\n",
    }
    for relative, payload in current_files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    (root / "user-project.txt").write_text("preserve", encoding="utf-8")

    current_payloads = _release_payloads(
        tmp_path / "current-release", update_skill.__version__, current_files
    )
    next_version = "0.4.4"
    next_payloads = _release_payloads(
        tmp_path / "next-release", next_version, next_files
    )
    latest_release = _release(next_version)
    current_release = _release(update_skill.__version__)
    routes = {
        update_skill.RELEASE_API: latest_release,
        update_skill.RELEASE_TAG_API.format(version=update_skill.__version__): current_release,
        latest_release["assets"][0]["browser_download_url"]: next_payloads["skill"],
        latest_release["assets"][1]["browser_download_url"]: next_payloads["checksums"],
        current_release["assets"][0]["browser_download_url"]: current_payloads["skill"],
        current_release["assets"][1]["browser_download_url"]: current_payloads["checksums"],
    }
    session = RoutedSession(routes)
    monkeypatch.setattr(update_skill, "_install_engine", lambda _root: None)
    monkeypatch.setattr(
        update_skill,
        "_doctor_after_update",
        lambda _root: {"status": "pass", "package_version": next_version},
    )

    state = tmp_path / "state.json"
    result = update_skill.auto_update(
        skill_dir=root,
        force=True,
        session=session,
        state_path=state,
    )

    assert result["status"] == "updated"
    assert result["installed_version"] == next_version
    assert result["adoption"]["method"] == "verified-release-adoption"
    assert (root / "scripts" / "tool.py").read_bytes() == next_files["scripts/tool.py"]
    assert (root / "scripts" / "new.py").read_bytes() == next_files["scripts/new.py"]
    assert (root / "user-project.txt").read_text(encoding="utf-8") == "preserve"
    manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["version"] == next_version
    cached = json.loads(state.read_text(encoding="utf-8"))
    assert cached["current_version"] == next_version
    assert cached["update_available"] is False
