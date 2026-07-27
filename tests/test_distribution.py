from __future__ import annotations

import json
import zipfile
from pathlib import Path

from build_skill_package import build_skill_package
from cli import main as cli_main
from cli import package_version, run_doctor


ROOT = Path(__file__).resolve().parents[1]


def test_package_version_and_cli_version_are_v032(capsys):
    assert package_version() == "0.3.2"
    assert cli_main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "0.3.2"


def test_doctor_runs_an_offline_build_and_verification():
    result = run_doctor()
    assert result["status"] == "pass"
    assert result["package_version"] == "0.3.2"
    assert result["feature_count"] == 2
    assert result["network_used"] is False
    assert result["checks"]["leaflet_embedded"] is True
    assert result["checks"]["verification_passed"] is True
    assert result["verified_outputs"] >= 4


def test_cli_help_surfaces_doctor_without_changing_existing_commands(capsys):
    assert cli_main(["--help"]) == 0
    output = capsys.readouterr().out
    for command in ("inspect", "init-spec", "build", "verify", "run", "doctor", "update"):
        assert command in output


def test_skill_package_is_lean_complete_and_deterministic(tmp_path: Path):
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    first_result = build_skill_package(first)
    second_result = build_skill_package(second)
    assert first_result["version"] == "0.3.2"
    assert first_result["sha256"] == second_result["sha256"]

    with zipfile.ZipFile(first) as archive:
        names = set(archive.namelist())
        manifest = json.loads(
            archive.read("interactive-map-builder/PACKAGE_MANIFEST.json").decode("utf-8")
        )

    required = {
        "interactive-map-builder/SKILL.md",
        "interactive-map-builder/LICENSE",
        "interactive-map-builder/pyproject.toml",
        "interactive-map-builder/agents/openai.yaml",
        "interactive-map-builder/scripts/cli.py",
        "interactive-map-builder/scripts/map_builder.py",
        "interactive-map-builder/scripts/update_skill.py",
        "interactive-map-builder/scripts/mapcore/basemaps.py",
        "interactive-map-builder/scripts/mapcore/version.py",
        "interactive-map-builder/scripts/mapcore/resources/map-spec.schema.json",
        "interactive-map-builder/scripts/mapcore/resources/vendor/leaflet-1.9.4/leaflet.js",
        "interactive-map-builder/PACKAGE_MANIFEST.json",
    }
    assert required <= names
    assert manifest["version"] == "0.3.2"
    assert not any("/tests/" in name for name in names)
    assert not any("/assets/" in name for name in names)
    assert not any("/.github/" in name for name in names)
    assert not any("/evals/" in name for name in names)
