from __future__ import annotations

import json
import struct
from pathlib import Path

import geopandas as gpd
import pytest

from mapcore.render_figure import OUTPUT_NAMES, render_static_figures


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "assets" / "examples" / "multilayer"


def _png_size(path: Path) -> tuple:
    payload = path.read_bytes()
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    return struct.unpack(">II", payload[16:24])


def _example_layers() -> dict:
    return {
        "boundary": gpd.read_file(EXAMPLE / "boundary.geojson"),
        "bike_routes": gpd.read_file(EXAMPLE / "bike_routes.geojson"),
        "facilities": gpd.read_file(EXAMPLE / "facilities.geojson"),
    }


def test_render_static_bundle_has_fixed_names_dimensions_and_signatures(tmp_path: Path) -> None:
    spec = json.loads((EXAMPLE / "map_spec.json").read_text(encoding="utf-8"))

    outputs = render_static_figures(_example_layers(), spec, tmp_path)

    assert {key: path.name for key, path in outputs.items()} == OUTPUT_NAMES
    assert _png_size(outputs["slide_png"]) == (1920, 1080)
    assert _png_size(outputs["paper_png"]) == (2160, 1620)
    assert outputs["paper_svg"].read_text(encoding="utf-8").lstrip().startswith("<?xml")
    assert "<svg" in outputs["paper_svg"].read_text(encoding="utf-8")[:1000]
    assert outputs["paper_pdf"].read_bytes().startswith(b"%PDF-")
    assert all(path.stat().st_size > 1000 for path in outputs.values())
    assert outputs.font_report["font"]
    assert "cjk_font_found" in outputs.font_report


def test_renderer_requires_crs_and_required_layers(tmp_path: Path) -> None:
    layers = _example_layers()
    facilities = layers["facilities"]
    no_crs = gpd.GeoDataFrame(
        facilities.drop(columns=facilities.geometry.name),
        geometry=list(facilities.geometry),
        crs=None,
    )

    with pytest.raises(ValueError, match="no CRS"):
        render_static_figures({"facilities": no_crs}, {"layers": []}, tmp_path)

    spec = json.loads((EXAMPLE / "map_spec.json").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="required layer"):
        render_static_figures({"facilities": layers["facilities"]}, spec, tmp_path)


def test_renderer_accepts_color_field_string_categories(tmp_path: Path) -> None:
    layer = _example_layers()["facilities"]
    spec = {
        "title": "Categorical points",
        "layers": [
            {
                "id": "facilities",
                "name": "Facilities",
                "required": True,
                "style": {
                    "color_field": "facility_type",
                    "categories": {
                        "Library": "#d1495b",
                        "Privately Owned Public Space": "#edae49",
                        "Transit": "#6a4c93",
                        "Public Plaza": "#00798c",
                    },
                },
            }
        ],
        "static": {"source_note": "Synthetic test"},
    }

    outputs = render_static_figures({"facilities": layer}, spec, tmp_path)

    assert outputs["paper_pdf"].exists()
    assert outputs["slide_png"].exists()


def test_static_presets_control_generated_files(tmp_path: Path) -> None:
    spec = json.loads((EXAMPLE / "map_spec.json").read_text(encoding="utf-8"))
    spec["static"]["presets"] = ["paper"]
    outputs = render_static_figures(_example_layers(), spec, tmp_path)
    assert set(outputs) == {"paper_png", "paper_svg", "paper_pdf"}
    assert not (tmp_path / "map_slide_16x9.png").exists()
