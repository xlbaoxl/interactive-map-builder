import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from scripts.mapcore.normalize import normalize_geodata, stable_feature_id
from scripts.mapcore.validate import (
    ValidationError,
    ensure_count_consistency,
    validate_geodata,
)


def test_normalize_requires_declared_crs():
    frame = gpd.GeoDataFrame({"name": ["x"]}, geometry=[Point(0, 0)])
    with pytest.raises(ValueError, match="CRS is missing"):
        normalize_geodata(frame)


def test_normalize_transforms_repairs_and_generates_stable_ids():
    # Self-intersection is invalid and make_valid converts it without dropping it.
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    frame = gpd.GeoDataFrame(
        {"name": ["测试"], "feature_id": [None]},
        geometry=[bowtie],
        crs="EPSG:3857",
    )

    normalized, report = normalize_geodata(frame, id_attributes=["name"])
    normalized_again, _ = normalize_geodata(frame, id_attributes=["name"])

    assert normalized.crs.to_epsg() == 4326
    assert normalized.geometry.iloc[0].is_valid
    assert report.repaired_geometry_indices == (0,)
    assert report.generated_id_indices == (0,)
    assert normalized["feature_id"].iloc[0] == normalized_again["feature_id"].iloc[0]
    assert normalized["feature_id"].iloc[0].startswith("feature_")


def test_stable_id_uses_canonical_geometry_and_sorted_properties():
    forward = Polygon([(0, 0), (2, 0), (2, 2), (0, 0)])
    reversed_ring = Polygon([(0, 0), (2, 2), (2, 0), (0, 0)])

    first = stable_feature_id(forward, {"中文": "值", "n": 2})
    second = stable_feature_id(reversed_ring, {"n": 2, "中文": "值"})

    assert first == second


def test_normalize_reports_empty_geometry_without_dropping():
    frame = gpd.GeoDataFrame(
        {"name": ["null", "empty"]},
        geometry=[None, Point()],
        crs="EPSG:4326",
    )

    normalized, report = normalize_geodata(frame)

    assert len(normalized) == 2
    assert report.empty_geometry_indices == (0, 1)
    assert report.generated_id_count == 2


def test_validation_accepts_complete_normalized_layer():
    frame = gpd.GeoDataFrame(
        {
            "feature_id": ["a", "b"],
            "name": ["甲", "乙"],
            "category": ["居住", "商业"],
        },
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326",
    )

    report = validate_geodata(
        frame,
        required_fields=["name"],
        category_field="category",
        allowed_categories={"居住": "#fff", "商业": "#000"},
        layer_name="sites",
    )

    assert report.feature_count == 2
    assert report.geometry_types == ("Point",)
    assert report.category_values == ("商业", "居住")


def test_validation_collects_geometry_id_field_and_category_errors():
    invalid = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    frame = gpd.GeoDataFrame(
        {
            "feature_id": ["same", "same", ""],
            "name": ["one", None, "three"],
            "category": ["known", "unknown", None],
        },
        geometry=[invalid, None, Point()],
        crs="EPSG:3857",
    )

    with pytest.raises(ValidationError) as captured:
        validate_geodata(
            frame,
            required_fields=["name", "missing"],
            category_field="category",
            allowed_categories=["known"],
            layer_name="primary",
        )

    message = str(captured.value)
    assert "EPSG:4326" in message
    assert "null geometry" in message
    assert "empty geometry" in message
    assert "invalid geometry" in message
    assert "missing required field" in message
    assert "duplicate ID" in message
    assert "blank ID" in message
    assert "unknown category" in message
    assert len(captured.value.errors) >= 8


def test_numeric_categories_match_json_object_keys():
    frame = gpd.GeoDataFrame(
        {"feature_id": ["one", "two"], "category": [1, 2]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326",
    )
    report = validate_geodata(
        frame,
        id_field="feature_id",
        category_field="category",
        allowed_categories={"1": "#fff", "2": "#000"},
    )
    assert report.category_values == (1, 2)


def test_required_display_fields_may_be_null_and_are_reported():
    frame = gpd.GeoDataFrame(
        {"feature_id": ["one", "two"], "name": [None, "Beta"]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326",
    )
    report = validate_geodata(frame, required_fields=["name"])
    assert report.null_field_counts == {"name": 1}


def test_validation_fails_if_id_field_is_absent():
    frame = gpd.GeoDataFrame({"name": ["x"]}, geometry=[Point(0, 0)], crs=4326)
    with pytest.raises(ValidationError, match="missing ID field"):
        validate_geodata(frame)


def test_count_consistency():
    assert ensure_count_consistency(input=5, map=5, list=5) == 5
    with pytest.raises(ValidationError, match="count mismatch"):
        ensure_count_consistency(input=5, map=4)
    with pytest.raises(ValidationError, match="non-negative integers"):
        ensure_count_consistency(input=-1)
