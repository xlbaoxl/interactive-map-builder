"""Strict build-stopping validation for normalized geospatial layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import geopandas as gpd
import pandas as pd


class ValidationError(ValueError):
    """Raised with all known validation errors, rather than only the first."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(self.errors))


@dataclass(frozen=True)
class ValidationReport:
    layer_name: str
    feature_count: int
    crs: str
    geometry_types: Tuple[str, ...]
    id_field: str
    required_fields: Tuple[str, ...]
    category_field: Optional[str]
    category_values: Tuple[Any, ...]

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["geometry_types"] = list(self.geometry_types)
        result["required_fields"] = list(self.required_fields)
        result["category_values"] = list(self.category_values)
        return result


def _display_indices(indices: Iterable[Any], limit: int = 10) -> str:
    values = list(indices)
    text = ", ".join(str(value) for value in values[:limit])
    if len(values) > limit:
        text += " (+{} more)".format(len(values) - limit)
    return text


def _is_epsg_4326(frame: gpd.GeoDataFrame) -> bool:
    if frame.crs is None:
        return False
    try:
        return frame.crs.to_epsg() == 4326
    except Exception:
        return False


def validate_geodata(
    frame: gpd.GeoDataFrame,
    *,
    id_field: str = "feature_id",
    required_fields: Sequence[str] = (),
    category_field: Optional[str] = None,
    allowed_categories: Optional[Iterable[Any]] = None,
    layer_name: str = "layer",
) -> ValidationReport:
    """Validate the invariants required before rendering a map."""

    if not isinstance(frame, gpd.GeoDataFrame):
        raise TypeError("frame must be a GeoDataFrame")

    errors: List[str] = []
    if len(frame) == 0:
        errors.append("{} is empty".format(layer_name))

    if frame.crs is None:
        errors.append("{} has no declared CRS".format(layer_name))
    elif not _is_epsg_4326(frame):
        errors.append(
            "{} must be normalized to EPSG:4326 (found {})".format(layer_name, frame.crs)
        )

    geometry_name = frame.geometry.name if hasattr(frame, "geometry") else None
    if geometry_name is None or geometry_name not in frame.columns:
        errors.append("{} has no active geometry column".format(layer_name))
        missing_geometry = []
        empty_geometry = []
        invalid_geometry = []
    else:
        missing_geometry = frame.index[frame.geometry.isna()].tolist()
        empty_geometry = [
            index
            for index, geometry in frame.geometry.items()
            if geometry is not None and geometry.is_empty
        ]
        invalid_geometry = [
            index
            for index, geometry in frame.geometry.items()
            if geometry is not None and not geometry.is_empty and not geometry.is_valid
        ]
        if missing_geometry:
            errors.append(
                "{} has null geometry at index(es): {}".format(
                    layer_name, _display_indices(missing_geometry)
                )
            )
        if empty_geometry:
            errors.append(
                "{} has empty geometry at index(es): {}".format(
                    layer_name, _display_indices(empty_geometry)
                )
            )
        if invalid_geometry:
            errors.append(
                "{} has invalid geometry at index(es): {}".format(
                    layer_name, _display_indices(invalid_geometry)
                )
            )

    required = tuple(dict.fromkeys(required_fields))
    missing_fields = [field for field in required if field not in frame.columns]
    if missing_fields:
        errors.append(
            "{} is missing required field(s): {}".format(layer_name, ", ".join(missing_fields))
        )
    for field in required:
        if field in frame.columns:
            null_indices = frame.index[frame[field].isna()].tolist()
            if null_indices:
                errors.append(
                    "{} field {!r} is null at index(es): {}".format(
                        layer_name, field, _display_indices(null_indices)
                    )
                )

    if id_field not in frame.columns:
        errors.append("{} is missing ID field {!r}".format(layer_name, id_field))
    else:
        id_text = frame[id_field].map(lambda value: "" if pd.isna(value) else str(value).strip())
        blank_indices = frame.index[id_text == ""].tolist()
        if blank_indices:
            errors.append(
                "{} has blank ID at index(es): {}".format(
                    layer_name, _display_indices(blank_indices)
                )
            )
        duplicate_mask = id_text.ne("") & id_text.duplicated(keep=False)
        duplicate_values = sorted(set(id_text[duplicate_mask].tolist()))
        if duplicate_values:
            errors.append(
                "{} has duplicate ID value(s): {}".format(
                    layer_name, ", ".join(duplicate_values[:10])
                )
            )

    category_values: Tuple[Any, ...] = ()
    if category_field is not None:
        if category_field not in frame.columns:
            errors.append(
                "{} is missing category field {!r}".format(layer_name, category_field)
            )
        else:
            category_values = tuple(
                sorted(
                    (value for value in frame[category_field].dropna().unique().tolist()),
                    key=lambda value: str(value),
                )
            )
            null_categories = frame.index[frame[category_field].isna()].tolist()
            if null_categories:
                errors.append(
                    "{} has null category at index(es): {}".format(
                        layer_name, _display_indices(null_categories)
                    )
                )
            if allowed_categories is not None:
                if isinstance(allowed_categories, Mapping):
                    allowed_text = {str(value) for value in allowed_categories.keys()}
                    unknown = [value for value in category_values if str(value) not in allowed_text]
                else:
                    allowed = set(allowed_categories)
                    unknown = [value for value in category_values if value not in allowed]
                if unknown:
                    errors.append(
                        "{} has unknown categor{} in {!r}: {}".format(
                            layer_name,
                            "y" if len(unknown) == 1 else "ies",
                            category_field,
                            ", ".join(str(value) for value in unknown),
                        )
                    )

    if errors:
        raise ValidationError(errors)

    geometry_types = tuple(sorted(frame.geometry.geom_type.dropna().unique().tolist()))
    return ValidationReport(
        layer_name=layer_name,
        feature_count=len(frame),
        crs=frame.crs.to_string(),
        geometry_types=geometry_types,
        id_field=id_field,
        required_fields=required,
        category_field=category_field,
        category_values=category_values,
    )


def ensure_count_consistency(**counts: int) -> int:
    """Require input/map/list/layer counts to agree and return that count."""

    if not counts:
        raise ValueError("At least one named count is required.")
    invalid = {name: value for name, value in counts.items() if not isinstance(value, int) or value < 0}
    if invalid:
        raise ValidationError(
            [
                "Counts must be non-negative integers: {}".format(
                    ", ".join("{}={!r}".format(name, value) for name, value in invalid.items())
                )
            ]
        )
    unique = set(counts.values())
    if len(unique) != 1:
        raise ValidationError(
            [
                "Feature count mismatch: {}".format(
                    ", ".join("{}={}".format(name, value) for name, value in counts.items())
                )
            ]
        )
    return next(iter(unique))
