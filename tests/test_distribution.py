from __future__ import annotations

import json
import zipfile
from pathlib import Path

from build_skill_package import build_skill_package, project_version
from cli import main as cli_main
from cli import package_version, run_doctor
from map_builder import _parser as builder_parser
from mapcore.version import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_package_version_and_cli_version_are_current(capsys):
    assert project_version() == __version__
    assert f"The current stable release is **v{__version__}**" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"当前稳定版本为 **v{__version__}**" in (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    assert package_version() == __version__
    assert cli_main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_doctor_runs_an_offline_build_and_verification():
    result = run_doctor()
    assert result["status"] == "pass"
    assert result["package_version"] == __version__
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


def test_internal_builder_help_points_to_the_complete_cli():
    output = builder_parser().format_help()
    assert "usage: python scripts/map_builder.py" in output
    assert "python scripts/cli.py" in output
    assert "package-level doctor" in output


def test_skill_package_is_lean_complete_and_deterministic(tmp_path: Path):
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    first_result = build_skill_package(first)
    second_result = build_skill_package(second)
    assert first_result["version"] == __version__
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
        "interactive-map-builder/scripts/mapcore/resources/templates/basemap-layer.js",
        "interactive-map-builder/scripts/mapcore/resources/vendor/maplibre-gl-5.6.2/maplibre-gl.js",
        "interactive-map-builder/scripts/mapcore/resources/vendor/maplibre-gl-5.6.2/LICENSE.txt",
        "interactive-map-builder/scripts/mapcore/resources/vendor/maplibre-gl-leaflet-0.1.4/leaflet-maplibre-gl.js",
        "interactive-map-builder/scripts/mapcore/resources/vendor/maplibre-gl-leaflet-0.1.4/LICENSE",
        "interactive-map-builder/scripts/mapcore/delivery.py",
        "interactive-map-builder/scripts/mapcore/safe_zip.py",
        "interactive-map-builder/scripts/mapcore/version.py",
        "interactive-map-builder/scripts/mapcore/arguments.py",
        "interactive-map-builder/scripts/mapcore/resources/templates/view-state.js",
        "interactive-map-builder/scripts/mapcore/resources/templates/view-state.css",
        "interactive-map-builder/references/view-state.md",
        "interactive-map-builder/scripts/mapcore/semantic_styles.py",
        "interactive-map-builder/scripts/mapcore/resources/map-spec.schema.json",
        "interactive-map-builder/scripts/mapcore/resources/templates/atlas-studio-light.css",
        "interactive-map-builder/scripts/mapcore/resources/templates/multilayer-enhancements.css",
        "interactive-map-builder/scripts/mapcore/resources/templates/multilayer-enhancements.js",
        "interactive-map-builder/scripts/mapcore/resources/templates/saved-views.css",
        "interactive-map-builder/scripts/mapcore/resources/templates/saved-views.js",
        "interactive-map-builder/scripts/mapcore/visual_defaults.py",
        "interactive-map-builder/scripts/mapcore/resources/vendor/leaflet-1.9.4/leaflet.js",
        "interactive-map-builder/PACKAGE_MANIFEST.json",
    }
    assert required <= names
    assert manifest["version"] == __version__
    assert not any("/tests/" in name for name in names)
    assert not any("/assets/" in name for name in names)
    assert not any("/.github/" in name for name in names)
    assert not any("/evals/" in name for name in names)