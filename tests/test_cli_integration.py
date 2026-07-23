from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from map_builder import build_map, verify_dist


ROOT = Path(__file__).resolve().parents[1]


def test_land_use_demo_build_and_verify_complete_bundle(tmp_path):
    spec = ROOT / "assets" / "examples" / "map-list" / "map_spec.json"
    result = build_map(spec, tmp_path)
    assert result["report"]["status"] == "pass"
    assert result["report"]["template"] == "multilayer"
    assert result["report"]["checks"]["rendered_layer_count"] == 3
    assert result["report"]["performance"]["feature_count"] == 1699

    expected = {
        "map.html",
        "map_slide_16x9.png",
        "map_paper.png",
        "map_paper.svg",
        "map_paper.pdf",
        "map_spec.json",
        "inspection.json",
        "build_report.json",
        "README_使用说明.md",
    }
    assert expected == {path.name for path in tmp_path.iterdir()}

    verification = verify_dist(tmp_path)
    assert verification["status"] == "pass"
    report = json.loads((tmp_path / "build_report.json").read_text(encoding="utf-8"))
    assert report["checks"]["output_counts_consistent"] is True
    assert report["checks"]["html_qa"]["leaflet_embedded"] is True


def test_gpkg_zip_csv_and_excel_build_end_to_end(tmp_path: Path) -> None:
    frame = gpd.GeoDataFrame(
        {"id": ["A", "B"], "name": ["甲", "乙"], "kind": ["一类", "二类"]},
        geometry=[Point(118.1, 39.6), Point(118.2, 39.7)],
        crs="EPSG:4326",
    )
    cases = []

    gpkg_dir = tmp_path / "gpkg"
    gpkg_dir.mkdir()
    gpkg = gpkg_dir / "data.gpkg"
    frame.to_file(gpkg, layer="places", driver="GPKG")
    cases.append(("gpkg", {"path": "data.gpkg", "layer": "places"}))

    zip_dir = tmp_path / "zip"
    zip_dir.mkdir()
    shape_dir = zip_dir / "shape"
    shape_dir.mkdir()
    shape_path = shape_dir / "places.shp"
    frame.to_file(shape_path, driver="ESRI Shapefile", encoding="utf-8")
    archive = zip_dir / "places.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        for path in shape_dir.iterdir():
            handle.write(path, path.name)
    cases.append(("zip", {"path": "places.zip"}))

    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    pd.DataFrame(
        {
            "id": ["A", "B"],
            "name": ["甲", "乙"],
            "longitude": [118.1, 118.2],
            "latitude": [39.6, 39.7],
        }
    ).to_csv(csv_dir / "places.csv", index=False)
    cases.append(
        (
            "csv",
            {
                "path": "places.csv",
                "crs": "EPSG:4326",
                "geometry": {
                    "type": "lonlat",
                    "x_field": "longitude",
                    "y_field": "latitude",
                },
            },
        )
    )

    excel_dir = tmp_path / "excel"
    excel_dir.mkdir()
    pd.DataFrame(
        {
            "id": ["A", "B"],
            "name": ["甲", "乙"],
            "wkt": ["POINT (118.1 39.6)", "POINT (118.2 39.7)"],
        }
    ).to_excel(excel_dir / "places.xlsx", sheet_name="places", index=False)
    cases.append(
        (
            "excel",
            {
                "path": "places.xlsx",
                "sheet": "places",
                "crs": "EPSG:4326",
                "geometry": {"type": "wkt", "wkt_field": "wkt"},
            },
        )
    )

    for name, source in cases:
        case_dir = tmp_path / name
        spec = {
            "schema_version": "1.0",
            "template": "map-list",
            "title": "{} input".format(name),
            "primary_layer": "places",
            "layers": [
                {
                    "id": "places",
                    "name": "Places",
                    "source": source,
                    "id_field": "id",
                    "label_field": "name",
                    "search_fields": ["name"],
                    "style": {"color": "#2563eb"},
                }
            ],
            "static": {"enabled": False},
        }
        spec_path = case_dir / "map_spec.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        result = build_map(spec_path, case_dir / "dist")
        assert result["report"]["checks"]["primary_count"] == 2
        assert (case_dir / "dist" / "map.html").is_file()


def test_graduated_style_is_resolved_once_for_html_and_static_outputs(tmp_path: Path) -> None:
    source = tmp_path / "scores.geojson"
    gpd.GeoDataFrame(
        {
            "id": ["A", "B", "C", "D"],
            "name": ["甲", "乙", "丙", "丁"],
            "score": [1.0, 2.0, 8.0, 10.0],
        },
        geometry=[Point(118.0 + index * 0.05, 39.6) for index in range(4)],
        crs="EPSG:4326",
    ).to_file(source, driver="GeoJSON")
    spec = {
        "schema_version": "1.0",
        "template": "map-list",
        "title": "Graduated",
        "primary_layer": "scores",
        "layers": [
            {
                "id": "scores",
                "name": "Scores",
                "source": {"path": "scores.geojson"},
                "id_field": "id",
                "label_field": "name",
                "style": {
                    "mode": "graduated",
                    "field": "score",
                    "method": "equal_interval",
                    "classes": 3,
                    "colors": ["#eff3ff", "#08519c"],
                },
            }
        ],
    }
    spec_path = tmp_path / "map_spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    dist = tmp_path / "dist"
    result = build_map(spec_path, dist)
    resolved = json.loads((dist / "map_spec.json").read_text(encoding="utf-8"))
    style = resolved["layers"][0]["style"]

    assert style["mode"] == "graduated"
    assert len(style["categories"]) == 3
    assert result["report"]["layers"][0]["style"]["categories"] == style["categories"]
    assert all((dist / name).is_file() for name in ("map.html", "map_paper.svg", "map_paper.pdf"))
