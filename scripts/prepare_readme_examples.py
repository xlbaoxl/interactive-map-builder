#!/usr/bin/env python
"""Download and freeze the NYC Open Data used by the README examples."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import geopandas as gpd
import pandas as pd
import requests
from shapely import make_valid, set_precision
from shapely.geometry import mapping
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "assets" / "examples"
SOCRATA_ROOT = "https://data.cityofnewyork.us/resource"
LOCAL_CRS = "EPSG:2263"
OUTPUT_CRS = "EPSG:4326"
RETRIEVED = "2026-07-24"
LAND_USE_BBOX = (-74.0150, 40.7040, -73.9950, 40.7215)

DATASETS = {
    "tax_lots": "i38t-6if2",
    "pluto": "64uk-42ks",
    "boroughs": "gthc-hcne",
    "bike_routes": "mzxg-pwib",
    "restrooms": "i7jb-7jku",
}

BIKE_CLASS_NAMES = {
    "I": "Class I bike routes",
    "II": "Class II bike routes",
    "III": "Class III bike routes",
    "L": "Bike links",
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
        f"{SOCRATA_ROOT}/{dataset_id}.geojson",
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
        f"{SOCRATA_ROOT}/{DATASETS['pluto']}.json",
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


def _simplify(frame: gpd.GeoDataFrame, tolerance_feet: float) -> gpd.GeoDataFrame:
    local = frame.to_crs(LOCAL_CRS)
    local.geometry = local.geometry.simplify(tolerance_feet, preserve_topology=True)
    local.geometry = local.geometry.map(make_valid)
    local = local[local.geometry.notna() & ~local.geometry.is_empty].copy()
    return local.to_crs(OUTPUT_CRS)


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
    borough = _fetch(DATASETS["boroughs"], "boroname='Manhattan'")
    if len(borough) != 1:
        raise RuntimeError(f"Expected one Manhattan boundary, received {len(borough)}.")
    borough = borough.rename(columns={"borocode": "borough_code", "boroname": "name"})
    borough["id"] = "manhattan"
    borough["borough_code"] = borough["borough_code"].astype(str)
    borough_local = borough.to_crs(LOCAL_CRS)
    boundary = borough_local.geometry.iloc[0]
    borough_output = _simplify(borough, 15)
    _write_geojson(
        borough_output,
        EXAMPLES / "multilayer" / "boundary.geojson",
        fields=("id", "name", "borough_code"),
    )

    bike_routes = _fetch(
        DATASETS["bike_routes"],
        "boro=1 AND status='Current'",
    ).to_crs(LOCAL_CRS)
    bike_routes.geometry = bike_routes.geometry.intersection(boundary)
    bike_routes = bike_routes[
        bike_routes.geometry.map(
            lambda geometry: geometry is not None and not geometry.is_empty
        )
        & bike_routes["facilitycl"].isin(BIKE_CLASS_NAMES)
    ].copy()
    bike_features = []
    for bike_class in BIKE_CLASS_NAMES:
        group = bike_routes[bike_routes["facilitycl"] == bike_class]
        geometry = unary_union(list(group.geometry)).simplify(
            15,
            preserve_topology=True,
        )
        bike_features.append(
            {
                "id": f"bike-class-{bike_class.lower()}",
                "name": BIKE_CLASS_NAMES[bike_class],
                "facility_class": bike_class,
                "segment_count": int(len(group)),
                "geometry": geometry,
            }
        )
    bike_output = gpd.GeoDataFrame(bike_features, crs=LOCAL_CRS).to_crs(OUTPUT_CRS)
    _write_geojson(
        bike_output,
        EXAMPLES / "multilayer" / "bike_routes.geojson",
        fields=("id", "name", "facility_class", "segment_count"),
    )

    restrooms = _fetch(
        DATASETS["restrooms"],
        "status='Operational'",
    ).to_crs(LOCAL_CRS)
    restrooms = restrooms[
        restrooms.geometry.within(boundary)
        & restrooms["facility_name"].notna()
        & restrooms["location_type"].notna()
        & (restrooms["location_type"].str.casefold() != "park")
    ].copy()
    if len(restrooms) != 56:
        raise RuntimeError(
            f"Expected 56 operational non-park Manhattan restrooms, received {len(restrooms)}."
        )
    restrooms = restrooms.rename(
        columns={
            "facility_name": "name",
            "location_type": "facility_type",
        }
    )
    restrooms = restrooms.to_crs(OUTPUT_CRS)
    restrooms["id"] = restrooms.apply(
        lambda row: "facility-"
        + hashlib.sha1(
            (
                f"{row['name']}|{row.geometry.x:.7f}|{row.geometry.y:.7f}|"
                f"{row['facility_type']}"
            ).encode("utf-8")
        ).hexdigest()[:12],
        axis=1,
    )
    if not restrooms["id"].is_unique:
        raise RuntimeError("Generated restroom IDs are not unique.")
    restrooms = restrooms.sort_values(["facility_type", "name", "id"])
    _write_geojson(
        restrooms,
        EXAMPLES / "multilayer" / "facilities.geojson",
        fields=("id", "name", "facility_type", "operator", "open", "accessibility"),
    )


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
