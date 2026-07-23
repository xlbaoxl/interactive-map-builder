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
        "districts": gpd.read_file(EXAMPLE / "districts.geojson"),
        "routes": gpd.read_file(EXAMPLE / "routes.geojson"),
        "places": gpd.read_file(EXAMPLE / "places.geojson"),
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


def test_renderer_requires_crs_and_required_layers(tmp_path: Path) -> None:
    layers = _example_layers()
    places = layers["places"]
    no_crs = gpd.GeoDataFrame(
        places.drop(columns=places.geometry.name),
        geometry=list(places.geometry),
        crs=None,
    )

    with pytest.raises(ValueError, match="no CRS"):
        render_static_figures({"places": no_crs}, {"layers": []}, tmp_path)

    spec = json.loads((EXAMPLE / "map_spec.json").read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="required layer"):
        render_static_figures({"places": layers["places"]}, spec, tmp_path)


def test_renderer_accepts_color_field_string_categories(tmp_path: Path) -> None:
    layer = _example_layers()["places"]
    spec = {
        "title": "Categorical points",
        "layers": [
            {
                "id": "places",
                "name": "Places",
                "required": True,
                "style": {
                    "color_field": "kind",
                    "categories": {"Civic": "#7b61a8", "Retail": "#d95f59"},
                },
            }
        ],
        "static": {"source_note": "Synthetic test"},
    }

    outputs = render_static_figures({"places": layer}, spec, tmp_path)

    assert outputs["paper_pdf"].exists()
    assert outputs["slide_png"].exists()
