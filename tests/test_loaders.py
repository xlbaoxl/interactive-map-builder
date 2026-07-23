import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from scripts.mapcore.loaders import DataLoadError, load_geodata, load_source


@pytest.fixture
def point_frame():
    return gpd.GeoDataFrame(
        {"name": ["甲", "乙"], "value": [1, 2]},
        geometry=[Point(116.4, 39.9), Point(121.5, 31.2)],
        crs="EPSG:4326",
    )


@pytest.mark.parametrize("suffix,driver", [(".geojson", "GeoJSON"), (".gpkg", "GPKG")])
def test_load_vector_formats(tmp_path, point_frame, suffix, driver):
    source = tmp_path / ("points" + suffix)
    point_frame.to_file(source, driver=driver)

    loaded = load_geodata(source)

    assert loaded["name"].tolist() == ["甲", "乙"]
    assert loaded.crs.to_epsg() == 4326
    assert loaded.geometry.geom_type.tolist() == ["Point", "Point"]


def test_load_shapefile_zip(tmp_path, point_frame):
    shape_dir = tmp_path / "shape"
    shape_dir.mkdir()
    shp = shape_dir / "社区.shp"
    point_frame.to_file(shp, driver="ESRI Shapefile", encoding="utf-8")
    archive = tmp_path / "points.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        for child in shape_dir.iterdir():
            bundle.write(child, "nested/" + child.name)

    loaded = load_geodata(archive, encoding="utf-8")

    assert len(loaded) == 2
    assert loaded.crs.to_epsg() == 4326


def test_shapefile_zip_rejects_path_traversal_before_extracting(tmp_path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../escape.shp", b"not a shapefile")

    with pytest.raises(DataLoadError, match="Unsafe ZIP member"):
        load_geodata(archive)
    assert not (tmp_path / "escape.shp").exists()


def test_shapefile_zip_rejects_multiple_datasets(tmp_path):
    archive = tmp_path / "ambiguous.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("one.shp", b"")
        bundle.writestr("two.shp", b"")

    with pytest.raises(DataLoadError, match="multiple shapefiles"):
        load_geodata(archive)


def test_load_csv_lonlat_requires_explicit_mapping_and_crs(tmp_path):
    source = tmp_path / "points.csv"
    pd.DataFrame({"x": [116.4], "y": [39.9], "name": ["天坛"]}).to_csv(
        source, index=False
    )

    with pytest.raises(DataLoadError, match="geometry must be explicit"):
        load_geodata(source, crs="EPSG:4326")
    with pytest.raises(DataLoadError, match="explicit source CRS"):
        load_geodata(source, lon_field="x", lat_field="y")

    loaded = load_geodata(
        source, lon_field="x", lat_field="y", crs="EPSG:4326"
    )
    assert loaded.geometry.iloc[0].equals(Point(116.4, 39.9))
    assert loaded.crs.to_epsg() == 4326


def test_load_csv_wkt_and_report_bad_rows(tmp_path):
    source = tmp_path / "points.csv"
    pd.DataFrame({"shape": ["POINT (0 1)", ""], "label": ["ok", "empty"]}).to_csv(
        source, index=False
    )
    loaded = load_geodata(source, wkt_field="shape", crs="EPSG:3857")
    assert loaded.geometry.iloc[0].equals(Point(0, 1))
    assert loaded.geometry.iloc[1] is None

    bad = tmp_path / "bad.csv"
    pd.DataFrame({"shape": ["NOT WKT"]}).to_csv(bad, index=False)
    with pytest.raises(DataLoadError, match="Invalid WKT"):
        load_geodata(bad, wkt_field="shape", crs="EPSG:4326")


def test_load_excel_and_mapping_adapter(tmp_path):
    source = tmp_path / "points.xlsx"
    pd.DataFrame({"经度": [120.0], "纬度": [30.0], "名称": ["杭州"]}).to_excel(
        source, index=False
    )

    loaded = load_source(
        {
            "path": source.name,
            "geometry": {
                "type": "lonlat",
                "x_field": "经度",
                "y_field": "纬度",
            },
            "crs": "EPSG:4326",
            "sheet": 0,
        },
        base_dir=tmp_path,
    )

    assert loaded["名称"].iloc[0] == "杭州"
    assert loaded.geometry.iloc[0].equals(Point(120, 30))


def test_unsupported_input_and_unknown_mapping_option(tmp_path):
    source = tmp_path / "data.txt"
    source.write_text("x", encoding="utf-8")
    with pytest.raises(DataLoadError, match="Unsupported input format"):
        load_geodata(source)

    csv_source = tmp_path / "data.csv"
    pd.DataFrame({"x": [0], "y": [0]}).to_csv(csv_source, index=False)
    with pytest.raises(DataLoadError, match="Unknown source option"):
        load_source(
            {
                "path": csv_source,
                "lon_field": "x",
                "lat_field": "y",
                "crs": "EPSG:4326",
                "surprise": True,
            }
        )
