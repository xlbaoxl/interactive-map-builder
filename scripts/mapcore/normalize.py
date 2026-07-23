"""Deterministic geometry and identifier normalization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry.base import BaseGeometry


@dataclass(frozen=True)
class NormalizationReport:
    """Auditable facts recorded while normalizing one layer."""

    source_crs: str
    target_crs: str
    input_count: int
    output_count: int
    repaired_geometry_indices: Tuple[Any, ...]
    unrepairable_geometry_indices: Tuple[Any, ...]
    empty_geometry_indices: Tuple[Any, ...]
    generated_id_indices: Tuple[Any, ...]
    id_field: str

    @property
    def repaired_count(self) -> int:
        return len(self.repaired_geometry_indices)

    @property
    def generated_id_count(self) -> int:
        return len(self.generated_id_indices)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        for key, value in list(result.items()):
            if key.endswith("_indices"):
                result[key] = list(value)
        result["repaired_count"] = self.repaired_count
        result["generated_id_count"] = self.generated_id_count
        return result


def _json_value(value: Any) -> Any:
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _canonical_geometry_hex(geometry: Optional[BaseGeometry]) -> Optional[str]:
    if geometry is None:
        return None
    normalized = shapely.normalize(geometry)
    return shapely.to_wkb(normalized, hex=True, byte_order=1, include_srid=False)


def stable_feature_id(
    geometry: Optional[BaseGeometry],
    properties: Optional[Mapping[str, Any]] = None,
    *,
    prefix: str = "feature",
) -> str:
    """Create a deterministic ID from canonical geometry and selected fields."""

    payload = {
        "geometry_wkb": _canonical_geometry_hex(geometry),
        "properties": {
            str(key): _json_value(value)
            for key, value in sorted((properties or {}).items(), key=lambda item: str(item[0]))
        },
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "{}_{}".format(prefix, hashlib.sha256(serialized).hexdigest()[:24])


def _repair_geometry(geometry: Optional[BaseGeometry]) -> Optional[BaseGeometry]:
    if geometry is None or geometry.is_empty or geometry.is_valid:
        return geometry
    return shapely.make_valid(geometry)


def normalize_geodata(
    frame: gpd.GeoDataFrame,
    *,
    id_field: str = "feature_id",
    id_attributes: Optional[Sequence[str]] = None,
    target_crs: str = "EPSG:4326",
    repair_invalid: bool = True,
    id_prefix: str = "feature",
) -> Tuple[gpd.GeoDataFrame, NormalizationReport]:
    """Normalize CRS/geometries and fill missing IDs deterministically.

    This function never guesses a missing CRS and never drops a record.
    Remaining empty or invalid geometries are recorded for the validation
    stage, where they cause a build-stopping error.
    """

    if not isinstance(frame, gpd.GeoDataFrame):
        raise TypeError("frame must be a GeoDataFrame")
    if frame.crs is None:
        raise ValueError("Input CRS is missing; provide the source CRS explicitly.")
    if not id_field or not isinstance(id_field, str):
        raise ValueError("id_field must be a non-empty string")

    attributes = tuple(id_attributes or ())
    missing_attributes = [field for field in attributes if field not in frame.columns]
    if missing_attributes:
        raise ValueError(
            "ID attribute field(s) not found: {}".format(", ".join(missing_attributes))
        )

    source_crs = frame.crs.to_string()
    try:
        normalized = frame.to_crs(target_crs).copy()
    except Exception as exc:
        raise ValueError(
            "Could not transform CRS from {} to {}.".format(source_crs, target_crs)
        ) from exc

    invalid_before: List[Any] = []
    repaired: List[Any] = []
    unrepairable: List[Any] = []
    if repair_invalid:
        values = []
        for index, geometry in normalized.geometry.items():
            if geometry is not None and not geometry.is_empty and not geometry.is_valid:
                invalid_before.append(index)
                try:
                    result = _repair_geometry(geometry)
                except Exception:
                    result = geometry
                if result is not None and not result.is_empty and result.is_valid:
                    repaired.append(index)
                else:
                    unrepairable.append(index)
                values.append(result)
            else:
                values.append(geometry)
        normalized = normalized.set_geometry(
            gpd.GeoSeries(values, index=normalized.index, crs=normalized.crs)
        )
    else:
        unrepairable = [
            index
            for index, geometry in normalized.geometry.items()
            if geometry is not None and not geometry.is_empty and not geometry.is_valid
        ]

    empty_indices = tuple(
        index
        for index, geometry in normalized.geometry.items()
        if geometry is None or geometry.is_empty
    )

    if id_field not in normalized.columns:
        normalized[id_field] = None

    generated: List[Any] = []
    id_values = []
    for index, row in normalized.iterrows():
        current = row[id_field]
        missing_id = pd.isna(current) or not str(current).strip()
        if missing_id:
            properties = {field: row[field] for field in attributes}
            current = stable_feature_id(row.geometry, properties, prefix=id_prefix)
            generated.append(index)
        else:
            current = str(current).strip()
        id_values.append(current)
    normalized[id_field] = id_values

    report = NormalizationReport(
        source_crs=source_crs,
        target_crs=normalized.crs.to_string(),
        input_count=len(frame),
        output_count=len(normalized),
        repaired_geometry_indices=tuple(repaired),
        unrepairable_geometry_indices=tuple(unrepairable),
        empty_geometry_indices=empty_indices,
        generated_id_indices=tuple(generated),
        id_field=id_field,
    )
    return normalized, report
