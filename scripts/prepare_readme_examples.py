#!/usr/bin/env python
"""Download and freeze the NYC Open Data used by the README examples."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

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

DATASETS = {
    "parks": "enfh-gkve",
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


def _prepare_parks() -> None:
    parks = _fetch(
        DATASETS["parks"],
        "borough='M' AND retired=false AND acres>=20",
    )
    if len(parks) != 18:
        raise RuntimeError(f"Expected 18 Manhattan parks, received {len(parks)}.")
    parks = parks.rename(
        columns={
            "gisobjid": "id",
            "signname": "name",
            "typecategory": "park_type",
        }
    )
    parks["id"] = parks["id"].astype(str)
    parks["acres"] = pd.to_numeric(parks["acres"]).round(3)
    parks["waterfront"] = parks["waterfront"].map(
        lambda value: "Yes" if bool(value) else "No"
    )
    parks = _simplify(parks, 15)
    parks = parks.sort_values(["acres", "name"], ascending=[False, True])
    _write_geojson(
        parks,
        EXAMPLES / "map-list" / "parks.geojson",
        fields=("id", "name", "park_type", "acres", "waterfront", "location"),
    )


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
    _prepare_parks()
    _prepare_multilayer()
    print("Prepared README examples from NYC Open Data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
