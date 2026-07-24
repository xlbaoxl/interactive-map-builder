#!/usr/bin/env python
"""Download and freeze the NYC Open Data used by the README examples."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import geopandas as gpd
import pandas as pd
import requests
from shapely import make_valid, set_precision
from shapely.geometry import Point, mapping
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "assets" / "examples"
NYC_SOCRATA_ROOT = "https://data.cityofnewyork.us/resource"
NY_SOCRATA_ROOT = "https://data.ny.gov/resource"
LOCAL_CRS = "EPSG:2263"
OUTPUT_CRS = "EPSG:4326"
RETRIEVED = "2026-07-24"
LAND_USE_BBOX = (-74.0150, 40.7040, -73.9950, 40.7215)
MULTILAYER_NTA_IDS = ("BK0201", "BK0202", "BK0203", "BK0204")
MULTILAYER_BUFFER_FEET = 450

DATASETS = {
    "tax_lots": "i38t-6if2",
    "pluto": "64uk-42ks",
    "neighborhoods": "9nt8-h7nd",
    "bike_routes": "mzxg-pwib",
    "subway_entrances": "i9wp-a4ja",
}

LAND_USE_LABELS = {
    "1": "一至二户住宅",
    "2": "多户无电梯住宅",
    "3": "多户电梯住宅",
    "4": "住宅与商业混合",
    "5": "商业与办公",
    "6": "工业与制造",
    "7": "交通与公用设施",
    "8": "公共设施与机构",
    "9": "开放空间与游憩",
    "10": "停车设施",
    "11": "空置地",
}


def _bbox_where(
    field: str,
    bbox: tuple[float, float, float, float],
) -> str:
    west, south, east, north = bbox
    return f"within_box({field},{north},{west},{south},{east})"


def _fetch(dataset_id: str, where: str) -> gpd.GeoDataFrame:
    response = requests.get(
        f"{NYC_SOCRATA_ROOT}/{dataset_id}.geojson",
        params={"$where": where, "$limit": 50_000},
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    frame = gpd.GeoDataFrame.from_features(payload["features"], crs=OUTPUT_CRS)
    if frame.empty:
        raise RuntimeError(f"NYC Open Data dataset {dataset_id} returned no features.")
    frame.geometry = frame.geometry.map(make_valid)
    frame = frame[frame.geometry.notna() & ~frame.geometry.is_empty].copy()
    return frame


def _fetch_rows(root: str, dataset_id: str, where: str) -> Sequence[Mapping[str, Any]]:
    response = requests.get(
        f"{root}/{dataset_id}.json",
        params={"$where": where, "$limit": 50_000},
        timeout=120,
    )
    response.raise_for_status()
    rows = response.json()
    if not rows:
        raise RuntimeError(f"Open Data dataset {dataset_id} returned no records.")
    return rows


def _fetch_pluto(
    bbox: tuple[float, float, float, float],
) -> Sequence[Mapping[str, Any]]:
    west, south, east, north = bbox
    where = (
        f"latitude between {south} and {north} "
        f"AND longitude between {west} and {east} AND borough='MN'"
    )
    fields = (
        "bbl,address,zonedist1,landuse,lotarea,bldgarea,"
        "numfloors,yearbuilt,builtfar,latitude,longitude"
    )
    response = requests.get(
        f"{NYC_SOCRATA_ROOT}/{DATASETS['pluto']}.json",
        params={"$where": where, "$select": fields, "$limit": 50_000},
        timeout=120,
    )
    response.raise_for_status()
    rows = response.json()
    if not rows:
        raise RuntimeError("NYC PLUTO returned no records.")
    return rows


def _bbl(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        return str(int(Decimal(str(value))))
    except (InvalidOperation, ValueError):
        return str(value).strip()


def _number(value: Any, digits: int = 1) -> Any:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not numeric:
        return None
    return round(numeric, digits)


def _year(value: Any) -> Any:
    try:
        numeric = int(float(value))
    except (TypeError, ValueError):
        return None
    return numeric if 1600 <= numeric <= 2026 else None


def _round_coordinates(value: Any, digits: int = 7) -> Any:
    if isinstance(value, (list, tuple)):
        return [_round_coordinates(item, digits) for item in value]
    if isinstance(value, float):
        return round(value, digits)
    return value


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _write_geojson(
    frame: gpd.GeoDataFrame,
    output: Path,
    *,
    fields: Iterable[str],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    features = []
    for _, row in frame.iterrows():
        precise_geometry = set_precision(
            row.geometry,
            grid_size=0.0000001,
            mode="valid_output",
        )
        geometry = mapping(precise_geometry)
        geometry["coordinates"] = _round_coordinates(geometry["coordinates"])
        features.append(
            {
                "type": "Feature",
                "properties": {field: _json_value(row[field]) for field in fields},
                "geometry": geometry,
            }
        )
    payload = {
        "type": "FeatureCollection",
        "name": output.stem,
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": features,
    }
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _prepare_land_use() -> dict[str, int]:
    lots = _fetch(
        DATASETS["tax_lots"],
        _bbox_where("the_geom", LAND_USE_BBOX),
    )
    lots["__join_bbl"] = lots["bbl"].map(_bbl)
    lots = lots[lots["__join_bbl"] != ""].dissolve(
        by="__join_bbl",
        as_index=False,
    )
    pluto = {_bbl(row.get("bbl")): row for row in _fetch_pluto(LAND_USE_BBOX)}

    records = []
    for _, row in lots.iterrows():
        bbl = str(row.get("__join_bbl") or "")
        info = pluto.get(bbl)
        if not info:
            continue
        code = str(info.get("landuse") or "").strip()
        if code in {"1", "2", "3"}:
            category = "居住用地"
            file_name = "residential.geojson"
        elif code in {"4", "5"}:
            category = "混合与商业用地"
            file_name = "mixed-commercial.geojson"
        else:
            category = "公共与其他用地"
            file_name = "civic-other.geojson"
        address = str(info.get("address") or "").strip()
        records.append(
            {
                "id": f"lot-{bbl}",
                "name": address or f"地块 BBL {bbl}",
                "address": address or "—",
                "category": category,
                "land_use": LAND_USE_LABELS.get(code, "未分类"),
                "zoning": str(info.get("zonedist1") or "—"),
                "lot_area_sqft": _number(info.get("lotarea"), 0),
                "building_area_sqft": _number(info.get("bldgarea"), 0),
                "built_far": _number(info.get("builtfar"), 2),
                "floors": _number(info.get("numfloors")),
                "year_built": _year(info.get("yearbuilt")),
                "bbl": bbl,
                "file_name": file_name,
                "geometry": row.geometry,
            }
        )

    frame = gpd.GeoDataFrame(records, geometry="geometry", crs=OUTPUT_CRS)
    if frame.empty or not frame["id"].is_unique:
        raise RuntimeError("Prepared land-use lots are empty or have duplicate IDs.")

    output_fields = (
        "id",
        "name",
        "address",
        "category",
        "land_use",
        "zoning",
        "lot_area_sqft",
        "building_area_sqft",
        "built_far",
        "floors",
        "year_built",
        "bbl",
    )
    counts: dict[str, int] = {}
    for file_name in (
        "residential.geojson",
        "mixed-commercial.geojson",
        "civic-other.geojson",
    ):
        subset = frame[frame["file_name"] == file_name].copy()
        subset = subset.sort_values(["name", "bbl"])
        _write_geojson(
            subset,
            EXAMPLES / "map-list" / file_name,
            fields=output_fields,
        )
        counts[file_name] = len(subset)
    return counts


def _prepare_multilayer() -> None:
    identifiers = ", ".join(f"'{value}'" for value in MULTILAYER_NTA_IDS)
    neighborhoods = _fetch(
        DATASETS["neighborhoods"],
        f"nta2020 in ({identifiers})",
    )
    neighborhoods = neighborhoods[
        neighborhoods["nta2020"].isin(MULTILAYER_NTA_IDS)
    ].copy()
    if len(neighborhoods) != len(MULTILAYER_NTA_IDS):
        raise RuntimeError(
            "Expected four Downtown Brooklyn neighborhood areas, "
            f"received {len(neighborhoods)}."
        )
    neighborhoods["id"] = neighborhoods["nta2020"]
    neighborhoods["name"] = neighborhoods["ntaname"]
    neighborhoods["borough"] = neighborhoods["boroname"]
    neighborhoods_local = neighborhoods.to_crs(LOCAL_CRS)
    neighborhoods["area_sqmi"] = (
        neighborhoods_local.geometry.area / 27_878_400
    ).round(2)
    neighborhoods = neighborhoods[
        ["id", "name", "borough", "area_sqmi", "geometry"]
    ].sort_values("id")
    study_area = unary_union(
        list(neighborhoods_local.geometry)
    ).buffer(MULTILAYER_BUFFER_FEET)
    _write_geojson(
        neighborhoods,
        EXAMPLES / "multilayer" / "neighborhoods.geojson",
        fields=("id", "name", "borough", "area_sqmi"),
    )

    bike_routes = _fetch(
        DATASETS["bike_routes"],
        "boro='3' AND status='Current'",
    )
    bike_routes = bike_routes[
        bike_routes.geometry.notna() & ~bike_routes.geometry.is_empty
    ].copy()
    bike_routes["street"] = (
        bike_routes["street"].fillna("UNNAMED ROUTE").astype(str)
    )
    bike_routes["facility_class"] = (
        bike_routes["facilitycl"].fillna("OTHER").astype(str)
    )
    bike_routes = bike_routes[
        bike_routes["facility_class"].isin({"I", "II", "III"})
    ].copy()
    bike_routes["segment_count"] = 1
    bike_routes = gpd.clip(bike_routes.to_crs(LOCAL_CRS), study_area)
    bike_routes = bike_routes[
        bike_routes.geometry.notna()
        & ~bike_routes.geometry.is_empty
        & bike_routes.geometry.geom_type.isin(["LineString", "MultiLineString"])
        & (bike_routes.geometry.length >= 100)
    ].copy()
    bike_routes = bike_routes.dissolve(
        by=["street", "facility_class"],
        aggfunc={"segment_count": "sum"},
        as_index=False,
    )
    bike_routes["length_mi"] = (bike_routes.geometry.length / 5_280).round(2)
    bike_routes = bike_routes.sort_values(
        ["length_mi", "street"],
        ascending=[False, True],
    ).head(36)
    if len(bike_routes) != 36:
        raise RuntimeError(
            f"Expected 36 Downtown Brooklyn bike routes, received {len(bike_routes)}."
        )
    bike_routes["id"] = [
        f"bike-{index + 1}" for index in range(len(bike_routes))
    ]
    bike_routes["name"] = bike_routes["street"]
    bike_routes = bike_routes.to_crs(OUTPUT_CRS)
    _write_geojson(
        bike_routes,
        EXAMPLES / "multilayer" / "bike_routes.geojson",
        fields=(
            "id",
            "name",
            "facility_class",
            "length_mi",
            "segment_count",
        ),
    )

    subway_rows = _fetch_rows(
        NY_SOCRATA_ROOT,
        DATASETS["subway_entrances"],
        "borough='B'",
    )
    subway_table = pd.DataFrame(subway_rows)
    subway_table["latitude"] = pd.to_numeric(
        subway_table["entrance_latitude"],
        errors="coerce",
    )
    subway_table["longitude"] = pd.to_numeric(
        subway_table["entrance_longitude"],
        errors="coerce",
    )
    subway_table = subway_table.dropna(
        subset=["latitude", "longitude", "stop_name", "complex_id"]
    )
    subway_points = gpd.GeoDataFrame(
        subway_table,
        geometry=[
            Point(longitude, latitude)
            for longitude, latitude in zip(
                subway_table["longitude"],
                subway_table["latitude"],
            )
        ],
        crs=OUTPUT_CRS,
    ).to_crs(LOCAL_CRS)
    subway_points = gpd.clip(subway_points, study_area)
    station_records = []
    for (complex_id, stop_name), group in subway_points.groupby(
        ["complex_id", "stop_name"]
    ):
        station_records.append(
            {
                "id": f"station-{complex_id}",
                "name": stop_name,
                "routes": " ".join(
                    sorted(
                        {
                            route
                            for value in group["daytime_routes"].dropna().astype(str)
                            for route in value.split()
                        }
                    )
                ),
                "entrance_count": int(len(group)),
                "entrance_types": ", ".join(
                    sorted(set(group["entrance_type"].dropna().astype(str)))
                ),
                "geometry": Point(
                    group.geometry.x.mean(),
                    group.geometry.y.mean(),
                ),
            }
        )
    stations = gpd.GeoDataFrame(station_records, crs=LOCAL_CRS)
    stations = stations.sort_values(["name", "id"]).to_crs(OUTPUT_CRS)
    if len(stations) != 16 or not stations["id"].is_unique:
        raise RuntimeError(
            "Expected 16 unique Downtown Brooklyn subway stations, "
            f"received {len(stations)}."
        )
    _write_geojson(
        stations,
        EXAMPLES / "multilayer" / "subway_stations.geojson",
        fields=("id", "name", "routes", "entrance_count", "entrance_types"),
    )

    for retired_name in ("boundary.geojson", "facilities.geojson"):
        retired_path = EXAMPLES / "multilayer" / retired_name
        if retired_path.exists():
            retired_path.unlink()


def main() -> int:
    land_use_counts = _prepare_land_use()
    _prepare_multilayer()
    print(
        f"Prepared README examples from NYC Open Data ({RETRIEVED}): "
        f"{land_use_counts}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
