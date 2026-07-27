#!/usr/bin/env python
"""Safely check for and apply official Interactive Map Builder releases.

The updater is deliberately separate from normal build commands. Agent guidance
may run it at the start of a Skill task, but map construction itself never makes
an implicit network request.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

import requests

from mapcore.version import __version__


REPOSITORY = "xlbaoxl/interactive-map-builder"
RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
CHECKSUM_ASSET = "SHA256SUMS.txt"
CHECK_INTERVAL_SECONDS = 24 * 60 * 60
MAX_SKILL_ARCHIVE_BYTES = 200 * 1024 * 1024
MAX_CHECKSUM_BYTES = 1024 * 1024
CHECK_TIMEOUT = (3.05, 7)
DISABLE_ENV = "IMB_DISABLE_AUTO_UPDATE"
SKILL_DIR_ENV = "INTERACTIVE_MAP_BUILDER_SKILL_DIR"
STATE_ENV = "IMB_UPDATE_STATE"
USER_AGENT = (
    f"interactive-map-builder/{__version__} "
    f"(+https://github.com/{REPOSITORY})"
)
_VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


class UpdateError(RuntimeError):
    """Raised when an available update cannot be trusted or safely applied."""


def parse_version(value: str) -> Tuple[int, int, int]:
    """Parse a stable three-part semantic version."""

    match = _VERSION_PATTERN.fullmatch(str(value).strip())
    if not match:
        raise UpdateError(f"Unsupported release version: {value!r}")
    return tuple(int(part) for part in match.groups())


def _disabled() -> bool:
    return os.environ.get(DISABLE_ENV, "").strip().casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _state_path() -> Path:
    configured = os.environ.get(STATE_ENV)
    if configured:
        return Path(configured).expanduser()
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        root = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return root / "interactive-map-builder" / "update-state.json"


def _read_state(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_state(path: Path, data: Mapping[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(dict(data), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    except OSError:
        # A read-only home directory must not block a map task.
        return


def _cached_result(state: Mapping[str, Any], now: float) -> Optional[Dict[str, Any]]:
    checked_at = state.get("checked_at")
    if not isinstance(checked_at, (int, float)):
        return None
    if now - float(checked_at) >= CHECK_INTERVAL_SECONDS:
        return None
    latest = state.get("latest_version")
    if not isinstance(latest, str):
        return None
    try:
        update_available = parse_version(latest) > parse_version(__version__)
    except UpdateError:
        return None
    return {
        "status": "update_available" if update_available else "current",
        "current_version": __version__,
        "latest_version": latest,
        "release_url": state.get("release_url"),
        "source": "cache",
        "checked_at": checked_at,
        "update_available": update_available,
        "assets": state.get("assets", {}),
    }


def _release_assets(release: Mapping[str, Any], version: str) -> Dict[str, str]:
    expected_zip = f"interactive-map-builder-skill-v{version}.zip"
    assets: Dict[str, str] = {}
    for asset in release.get("assets", []):
        if not isinstance(asset, Mapping):
            continue
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if name and url:
            assets[name] = url
    missing = [name for name in (expected_zip, CHECKSUM_ASSET) if name not in assets]
    if missing:
        raise UpdateError("Release is missing required asset(s): " + ", ".join(missing))
    expected_prefix = f"https://github.com/{REPOSITORY}/releases/download/"
    for name in (expected_zip, CHECKSUM_ASSET):
        if not assets[name].startswith(expected_prefix):
            raise UpdateError(f"Release asset has an unexpected download host: {name}.")
    return {"skill_zip": assets[expected_zip], "checksums": assets[CHECKSUM_ASSET]}


def check_for_update(
    *,
    force: bool = False,
    session: Optional[requests.Session] = None,
    now: Optional[float] = None,
    state_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Check the official latest stable release, using a 24-hour local cache."""

    if _disabled():
        return {
            "status": "disabled",
            "current_version": __version__,
            "update_available": False,
            "source": "environment",
        }

    timestamp = time.time() if now is None else float(now)
    state_file = state_path or _state_path()
    if not force:
        cached = _cached_result(_read_state(state_file), timestamp)
        if cached is not None:
            return cached

    client = session or requests.Session()
    response = client.get(
        RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=CHECK_TIMEOUT,
    )
    response.raise_for_status()
    release = response.json()
    if not isinstance(release, Mapping):
        raise UpdateError("Latest release response is not an object.")
    if release.get("draft") or release.get("prerelease"):
        raise UpdateError("Latest release is not a stable public release.")

    tag = str(release.get("tag_name") or "")
    latest = tag[1:] if tag.startswith("v") else tag
    parse_version(latest)
    assets = _release_assets(release, latest)
    update_available = parse_version(latest) > parse_version(__version__)
    result = {
        "status": "update_available" if update_available else "current",
        "current_version": __version__,
        "latest_version": latest,
        "release_url": str(release.get("html_url") or ""),
        "source": "network",
        "checked_at": timestamp,
        "update_available": update_available,
        "assets": assets,
    }
    _write_state(state_file, result)
    return result


def resolve_skill_root(value: Optional[Path] = None) -> Optional[Path]:
    """Find the Skill root without guessing unrelated project directories."""

    candidates = []
    if value is not None:
        candidates.append(Path(value).expanduser())
    configured = os.environ.get(SKILL_DIR_ENV)
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.append(Path(__file__).resolve().parents[1])
    current = Path.cwd().resolve()
    candidates.extend([current, *current.parents])

    seen = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        skill = resolved / "SKILL.md"
        if not skill.is_file():
            continue
        try:
            text = skill.read_text(encoding="utf-8")
        except OSError:
            continue
        if "name: interactive-map-builder" in text:
            return resolved
    return None


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def _official_remote(value: str) -> bool:
    normalized = value.strip().rstrip("/").removesuffix(".git").casefold()
    return normalized in {
        f"https://github.com/{REPOSITORY}".casefold(),
        f"git@github.com:{REPOSITORY}".casefold(),
        f"ssh://git@github.com/{REPOSITORY}".casefold(),
    }


def _install_engine(skill_root: Path) -> None:
    _run(
        [sys.executable, "-m", "pip", "install", "--upgrade", str(skill_root)],
        cwd=skill_root,
    )


def _doctor_after_update(skill_root: Path) -> Dict[str, Any]:
    result = _run(
        [
            sys.executable,
            "-c",
            (
                "import json; "
                "from cli import run_doctor; "
                "print(json.dumps(run_doctor(), ensure_ascii=False))"
            ),
        ],
        cwd=skill_root,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise UpdateError("Updated package did not return a valid doctor result.") from exc
    if not isinstance(payload, Mapping) or payload.get("status") != "pass":
        raise UpdateError("Updated package failed its offline doctor check.")
    return dict(payload)


def _update_git_checkout(skill_root: Path, version: str) -> Dict[str, Any]:
    git = shutil.which("git")
    if not git:
        raise UpdateError("This installation is a Git checkout, but git is unavailable.")
    status = _run([git, "status", "--porcelain"], cwd=skill_root)
    if status.stdout.strip():
        raise UpdateError(
            "The Skill checkout has local changes. Commit, discard, or preserve them before updating."
        )
    remote = _run([git, "remote", "get-url", "origin"], cwd=skill_root).stdout.strip()
    if not _official_remote(remote):
        raise UpdateError("Automatic updates are limited to the official repository remote.")
    branch = _run([git, "branch", "--show-current"], cwd=skill_root).stdout.strip()
    if branch != "main":
        raise UpdateError("Automatic Git updates require the clean main branch.")

    tag = f"v{version}"
    previous = _run([git, "rev-parse", "HEAD"], cwd=skill_root).stdout.strip()
    try:
        _run([git, "fetch", "origin", f"refs/tags/{tag}:refs/tags/{tag}"], cwd=skill_root)
        _run([git, "merge", "--ff-only", tag], cwd=skill_root)
        _install_engine(skill_root)
        doctor = _doctor_after_update(skill_root)
    except Exception as exc:
        _run([git, "reset", "--hard", previous], cwd=skill_root, check=False)
        _run(
            [sys.executable, "-m", "pip", "install", "--upgrade", str(skill_root)],
            cwd=skill_root,
            check=False,
        )
        raise UpdateError(
            "Git update failed; the checkout was restored to its previous commit."
        ) from exc
    return {
        "method": "git-fast-forward",
        "tag": tag,
        "previous_commit": previous,
        "doctor": doctor,
    }


def _safe_member_path(member: zipfile.ZipInfo) -> PurePosixPath:
    raw = str(member.filename)
    path = PurePosixPath(raw)
    if (
        not raw
        or "\\" in raw
        or "\x00" in raw
        or re.match(r"^[A-Za-z]:", raw)
        or path.is_absolute()
        or ".." in path.parts
        or not path.parts
    ):
        raise UpdateError(f"Unsafe ZIP member path: {member.filename!r}")
    mode = (member.external_attr >> 16) & 0o170000
    if mode == 0o120000:
        raise UpdateError(f"Symlinks are not allowed in the Skill archive: {member.filename!r}")
    return path


def _download(
    url: str,
    destination: Path,
    session: requests.Session,
    *,
    maximum_bytes: int,
) -> None:
    with session.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
        stream=True,
    ) as response:
        response.raise_for_status()
        declared = response.headers.get("Content-Length")
        if declared is not None:
            try:
                if int(declared) > maximum_bytes:
                    raise UpdateError("Release asset exceeds the allowed download size.")
            except ValueError:
                pass
        written = 0
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    written += len(chunk)
                    if written > maximum_bytes:
                        raise UpdateError("Release asset exceeds the allowed download size.")
                    handle.write(chunk)


def _expected_checksum(text: str, filename: str) -> str:
    for raw_line in text.splitlines():
        parts = raw_line.strip().split(maxsplit=1)
        if len(parts) != 2:
            continue
        digest, listed = parts
        listed = listed.lstrip("*./")
        if listed == filename and re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            return digest.casefold()
    raise UpdateError(f"Checksum file does not contain {filename!r}.")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_manifest_path(value: Any) -> PurePosixPath:
    raw = str(value or "").strip()
    relative = PurePosixPath(raw)
    if (
        not raw
        or raw == "."
        or "\\" in raw
        or "\x00" in raw
        or re.match(r"^[A-Za-z]:", raw)
        or relative.is_absolute()
        or ".." in relative.parts
        or not relative.parts
    ):
        raise UpdateError(f"Skill manifest contains an unsafe path: {raw!r}.")
    return relative


def _manifest_file_set_from_data(manifest: Mapping[str, Any]) -> set[str]:
    if manifest.get("name") != "interactive-map-builder":
        raise UpdateError("Managed Skill manifest has the wrong package name.")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise UpdateError("Managed Skill manifest has no files.")
    files: set[str] = set()
    folded: set[str] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise UpdateError("Managed Skill manifest contains an invalid file entry.")
        relative = _safe_manifest_path(entry.get("path")).as_posix()
        if relative in files or relative.casefold() in folded:
            raise UpdateError(f"Skill manifest contains a duplicate path: {relative}.")
        files.add(relative)
        folded.add(relative.casefold())
    return files


def _manifest_target(root: Path, relative: str) -> Path:
    safe = _safe_manifest_path(relative)
    resolved_root = root.resolve()
    target = root.joinpath(*safe.parts)
    try:
        target.resolve(strict=False).relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise UpdateError(f"Managed Skill path escapes its root: {relative!r}.") from exc
    return target


def _validate_extracted_package(package_root: Path, version: str) -> Dict[str, Any]:
    manifest_path = package_root / "PACKAGE_MANIFEST.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateError("Skill archive has no readable package manifest.") from exc
    if str(manifest.get("version")) != version:
        raise UpdateError("Skill archive version does not match the release tag.")
    files = manifest.get("files")
    expected_files = _manifest_file_set_from_data(manifest)

    normalized = []
    for entry in files:
        if not isinstance(entry, Mapping):
            raise UpdateError("Skill archive manifest contains an invalid file entry.")
        relative = _safe_manifest_path(entry.get("path"))
        path = _manifest_target(package_root, relative.as_posix())
        if not path.is_file():
            raise UpdateError(f"Skill archive is missing {relative.as_posix()}.")
        if path.stat().st_size != int(entry.get("bytes", -1)):
            raise UpdateError(f"Skill archive size mismatch: {relative.as_posix()}.")
        if _sha256(path) != str(entry.get("sha256") or "").casefold():
            raise UpdateError(f"Skill archive hash mismatch: {relative.as_posix()}.")
        normalized.append(relative.as_posix())
    actual_files = {
        path.relative_to(package_root).as_posix()
        for path in package_root.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
    }
    if actual_files != expected_files:
        extras = sorted(actual_files - expected_files)
        missing = sorted(expected_files - actual_files)
        details = []
        if extras:
            details.append("unexpected: " + ", ".join(extras[:5]))
        if missing:
            details.append("missing: " + ", ".join(missing[:5]))
        raise UpdateError("Skill archive contents do not match its manifest (" + "; ".join(details) + ").")
    return {"manifest": manifest, "files": normalized}


def _managed_files_are_clean(skill_root: Path) -> Iterable[str]:
    manifest_path = skill_root / "PACKAGE_MANIFEST.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateError("The managed Skill install has no readable package manifest.") from exc
    expected = _manifest_file_set_from_data(manifest)
    entries = {
        _safe_manifest_path(entry.get("path")).as_posix(): entry
        for entry in manifest.get("files", [])
        if isinstance(entry, Mapping)
    }
    changed = []
    for relative in sorted(expected):
        entry = entries[relative]
        path = _manifest_target(skill_root, relative)
        if (
            path.is_symlink()
            or not path.is_file()
            or _sha256(path) != str(entry.get("sha256") or "").casefold()
        ):
            changed.append(relative)
    return changed


def _manifest_file_set(root: Path) -> set[str]:
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if manifest_path.is_symlink():
        raise UpdateError("Managed Skill manifest must not be a symlink.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateError("Managed Skill manifest is unreadable.") from exc
    return _manifest_file_set_from_data(manifest)


def _backup_managed_install(skill_root: Path, backup_root: Path) -> set[str]:
    files = _manifest_file_set(skill_root)
    for relative in sorted(files):
        source = _manifest_target(skill_root, relative)
        if source.is_symlink() or not source.is_file():
            raise UpdateError(f"Managed Skill file is missing before update: {relative}.")
        destination = backup_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    backup_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        skill_root / "PACKAGE_MANIFEST.json",
        backup_root / "PACKAGE_MANIFEST.json",
    )
    return files


def _restore_managed_install(
    skill_root: Path,
    backup_root: Path,
    old_files: Iterable[str],
    new_files: Iterable[str],
) -> None:
    old_set = set(old_files)
    for relative in set(new_files) - old_set:
        target = _manifest_target(skill_root, relative)
        if target.is_file():
            target.unlink()
    for relative in sorted(old_set):
        source = _manifest_target(backup_root, relative)
        destination = _manifest_target(skill_root, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".restore-tmp")
        shutil.copy2(source, temporary)
        temporary.replace(destination)
    shutil.copy2(
        backup_root / "PACKAGE_MANIFEST.json",
        skill_root / "PACKAGE_MANIFEST.json",
    )


def _replace_managed_install(
    skill_root: Path, package_root: Path
) -> Tuple[set[str], set[str]]:
    old_files = _manifest_file_set(skill_root)
    new_files = _manifest_file_set(package_root)

    for relative in sorted(new_files):
        source = _manifest_target(package_root, relative)
        destination = _manifest_target(skill_root, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".update-tmp")
        shutil.copy2(source, temporary)
        temporary.replace(destination)
    shutil.copy2(package_root / "PACKAGE_MANIFEST.json", skill_root / "PACKAGE_MANIFEST.json")

    for relative in sorted(old_files - new_files, reverse=True):
        target = _manifest_target(skill_root, relative)
        if target.is_file():
            target.unlink()
        parent = target.parent
        while parent != skill_root:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    return old_files, new_files


def _update_managed_install(
    skill_root: Path,
    version: str,
    assets: Mapping[str, str],
    session: requests.Session,
) -> Dict[str, Any]:
    changed = list(_managed_files_are_clean(skill_root))
    if changed:
        preview = ", ".join(changed[:5])
        suffix = "…" if len(changed) > 5 else ""
        raise UpdateError(
            "Managed Skill files were modified locally: " + preview + suffix
        )

    with tempfile.TemporaryDirectory(prefix="interactive-map-builder-update-") as temp_dir:
        temp = Path(temp_dir)
        archive_name = f"interactive-map-builder-skill-v{version}.zip"
        archive_path = temp / archive_name
        checksums_path = temp / CHECKSUM_ASSET
        skill_zip_url = str(assets.get("skill_zip") or "")
        checksums_url = str(assets.get("checksums") or "")
        if not skill_zip_url or not checksums_url:
            raise UpdateError("Update metadata does not include required release asset URLs.")
        _download(
            skill_zip_url,
            archive_path,
            session,
            maximum_bytes=MAX_SKILL_ARCHIVE_BYTES,
        )
        _download(
            checksums_url,
            checksums_path,
            session,
            maximum_bytes=MAX_CHECKSUM_BYTES,
        )
        expected = _expected_checksum(
            checksums_path.read_text(encoding="utf-8"), archive_name
        )
        actual = _sha256(archive_path)
        if actual != expected:
            raise UpdateError("Downloaded Skill ZIP failed SHA-256 verification.")

        extract_root = temp / "extract"
        extract_root.mkdir()
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            member_names = set()
            for member in members:
                safe = _safe_member_path(member)
                if safe.parts[0] != "interactive-map-builder":
                    raise UpdateError("Skill archive contains files outside its package root.")
                folded = safe.as_posix().casefold()
                if folded in member_names:
                    raise UpdateError("Skill archive contains duplicate member paths.")
                member_names.add(folded)
            archive.extractall(extract_root)
        package_root = extract_root / "interactive-map-builder"
        validated = _validate_extracted_package(package_root, version)
        backup_root = temp / "backup"
        old_files = _backup_managed_install(skill_root, backup_root)
        new_files = set(validated["files"])
        try:
            _replace_managed_install(skill_root, package_root)
            _install_engine(skill_root)
            doctor = _doctor_after_update(skill_root)
        except Exception as exc:
            _restore_managed_install(
                skill_root, backup_root, old_files, new_files
            )
            _run(
                [sys.executable, "-m", "pip", "install", "--upgrade", str(skill_root)],
                cwd=skill_root,
                check=False,
            )
            raise UpdateError(
                "Managed update failed; all package files were restored."
            ) from exc

    return {
        "method": "verified-release-zip",
        "sha256": actual,
        "doctor": doctor,
    }


def apply_update(
    result: Mapping[str, Any],
    *,
    skill_root: Path,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """Apply an already checked update to a supported, clean installation."""

    if not result.get("update_available"):
        return dict(result)
    version = str(result.get("latest_version") or "")
    parse_version(version)
    root = skill_root.resolve()
    if not os.access(root, os.W_OK):
        raise UpdateError(f"Skill directory is not writable: {root}")

    if (root / ".git").exists():
        details = _update_git_checkout(root, version)
    elif (root / "PACKAGE_MANIFEST.json").is_file():
        assets = result.get("assets")
        if not isinstance(assets, Mapping):
            raise UpdateError("Update metadata does not include release assets.")
        details = _update_managed_install(
            root,
            version,
            assets,
            session or requests.Session(),
        )
    else:
        raise UpdateError(
            "Automatic update is supported for the official clean Git checkout or a "
            "versioned Skill ZIP install. Reinstall this copy from an official Release."
        )

    return {
        **dict(result),
        "status": "updated",
        "previous_version": __version__,
        "installed_version": version,
        "update_available": False,
        "skill_root": str(root),
        "update": details,
    }


def auto_update(
    *,
    skill_dir: Optional[Path] = None,
    force: bool = False,
    apply: bool = True,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """Check and optionally apply an update without blocking a map task on failure."""

    try:
        result = check_for_update(force=force, session=session)
        root = resolve_skill_root(skill_dir)
        if root is not None:
            result["skill_root"] = str(root)
        if apply and result.get("update_available"):
            if root is None:
                return {
                    **result,
                    "status": "manual_update_required",
                    "reason": "Skill root could not be located safely.",
                }
            return apply_update(result, skill_root=root, session=session)
        return result
    except (
        UpdateError,
        requests.RequestException,
        OSError,
        subprocess.SubprocessError,
        ValueError,
        KeyError,
        zipfile.BadZipFile,
    ) as exc:
        return {
            "status": "update_check_failed",
            "current_version": __version__,
            "update_available": False,
            "reason": str(exc),
            "non_blocking": True,
        }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check and safely apply official Interactive Map Builder releases."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Check only; do not modify the Skill installation.",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Apply an available update and report failures with a non-zero exit code.",
    )
    mode.add_argument(
        "--auto",
        action="store_true",
        help="Apply when safe, but never block the calling Agent when offline or modified.",
    )
    parser.add_argument("--force", action="store_true", help="Ignore the 24-hour check cache.")
    parser.add_argument("--skill-dir", type=Path, help="Explicit Skill root directory.")
    parser.add_argument("--output", type=Path, help="Optionally write the JSON result.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    apply = bool(args.apply or args.auto)
    result = auto_update(
        skill_dir=args.skill_dir,
        force=args.force,
        apply=apply,
    )
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(payload)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    if args.auto:
        return 0
    if result["status"] in {"update_check_failed", "manual_update_required"}:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
