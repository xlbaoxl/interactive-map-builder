from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

import map_builder
from map_builder import BuildError, build_map, verify_dist
from mapcore.delivery import DELIVERY_MANIFEST_NAME
from mapcore.spec import SpecError, current_schema_version, validate_spec


def _project(root: Path, *, static=None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    source = root / "places.geojson"
    gpd.GeoDataFrame(
        {"id": ["A"], "name": ["Place A"]},
        geometry=[Point(118.1, 39.6)],
        crs="EPSG:4326",
    ).to_file(source, driver="GeoJSON")
    spec = {
        "schema_version": current_schema_version(),
        "template": "map-list",
        "title": "Transactional delivery",
        "primary_layer": "places",
        "layers": [
            {
                "id": "places",
                "name": "Places",
                "source": {"path": "places.geojson"},
                "id_field": "id",
                "label_field": "name",
                "source_note": "Synthetic",
            }
        ],
    }
    if static is not None:
        spec["static"] = static
    path = root / "map_spec.json"
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return path


def test_reused_delivery_removes_stale_static_and_preserves_unmanaged_files(tmp_path: Path) -> None:
    project = tmp_path / "project"
    dist = tmp_path / "dist"
    build_map(_project(project, static={"enabled": True, "presets": ["slide-16x9"]}), dist)
    assert (dist / "map_slide_16x9.png").is_file()
    (dist / "user-notes.txt").write_text("keep", encoding="utf-8")

    build_map(_project(project, static={"enabled": False}), dist)

    assert not (dist / "map_slide_16x9.png").exists()
    assert (dist / "user-notes.txt").read_text(encoding="utf-8") == "keep"
    assert (dist / DELIVERY_MANIFEST_NAME).is_file()
    assert verify_dist(dist)["status"] == "pass"


def test_failed_staging_build_leaves_previous_delivery_untouched(monkeypatch, tmp_path: Path) -> None:
    spec = _project(tmp_path / "project", static={"enabled": False})
    dist = tmp_path / "dist"
    build_map(spec, dist)
    before = (dist / "map.html").read_bytes()

    def fail_after_partial(_spec, out_dir, **_kwargs):
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / "map.html").write_text("partial", encoding="utf-8")
        raise BuildError("synthetic staged failure")

    monkeypatch.setattr(map_builder, "_build_map_in_place", fail_after_partial)
    with pytest.raises(BuildError, match="synthetic staged failure"):
        build_map(spec, dist)

    assert (dist / "map.html").read_bytes() == before
    assert verify_dist(dist)["status"] == "pass"


def test_verify_requires_core_outputs_even_when_report_does_not_list_them(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    build_map(_project(tmp_path / "project", static={"enabled": False}), dist)
    (dist / "README_USAGE.md").unlink()
    with pytest.raises(BuildError, match="required delivery output"):
        verify_dist(dist)


def test_verify_rejects_unsafe_report_paths(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    build_map(_project(tmp_path / "project", static={"enabled": False}), dist)
    report_path = dist / "build_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["outputs"][0]["path"] = "../escape.html"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with pytest.raises(BuildError, match="Unsafe delivery path"):
        verify_dist(dist)


def test_bundled_source_tampering_is_detected(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    build_map(
        _project(tmp_path / "project", static={"enabled": False}),
        dist,
        bundle_sources=True,
    )
    bundled = next((dist / "data").glob("*.geojson"))
    bundled.write_text("{}", encoding="utf-8")
    with pytest.raises(BuildError, match="Managed delivery"):
        verify_dist(dist)


def test_static_enabled_requires_explicit_presets() -> None:
    spec = {
        "schema_version": current_schema_version(),
        "template": "map-list",
        "title": "Static contract",
        "primary_layer": "places",
        "layers": [{"id": "places", "name": "Places", "source": {"path": "places.geojson"}}],
        "static": {"enabled": True},
    }
    with pytest.raises(SpecError, match="presets"):
        validate_spec(spec)
