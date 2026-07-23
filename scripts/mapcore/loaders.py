"""Input adapters for supported local vector and tabular formats."""

from __future__ import annotations

import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Mapping, Optional, Union

import geopandas as gpd
import pandas as pd
from shapely import wkt

PathLike = Union[str, Path]


class DataLoadError(ValueError):
    """Raised when an input cannot be loaded without guessing its meaning."""


def _validate_zip_member(info: zipfile.ZipInfo) -> None:
    """Reject path traversal, absolute paths, drives, and symbolic links."""

    raw_name = info.filename.replace("\\", "/")
    member = PurePosixPath(raw_name)
    if (
        not raw_name
        or raw_name.startswith("/")
        or member.is_absolute()
        or ".." in member.parts
        or (member.parts and ":" in member.parts[0])
    ):
        raise DataLoadError("Unsafe ZIP member path: {!r}".format(info.filename))

    unix_mode = (info.external_attr >> 16) & 0xFFFF
    if unix_mode and stat.S_ISLNK(unix_mode):
        raise DataLoadError("Symbolic links are not allowed in ZIP inputs: {!r}".format(info.filename))


def _read_shapefile_zip(
    path: Path,
    *,
    encoding: Optional[str] = None,
) -> gpd.GeoDataFrame:
    try:
        archive = zipfile.ZipFile(str(path), "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise DataLoadError("Invalid ZIP archive: {}".format(path)) from exc

    with archive:
        members = archive.infolist()
        for member in members:
            _validate_zip_member(member)
        shapefiles = sorted(
            (member for member in members if member.filename.lower().endswith(".shp")),
            key=lambda member: member.filename.casefold(),
        )
        if not shapefiles:
            raise DataLoadError("ZIP input contains no .shp file: {}".format(path))
        if len(shapefiles) > 1:
            names = ", ".join(member.filename for member in shapefiles)
            raise DataLoadError(
                "ZIP input contains multiple shapefiles; provide one dataset per archive: {}".format(names)
            )

        with tempfile.TemporaryDirectory(prefix="interactive-map-shp-") as temp_dir:
            archive.extractall(temp_dir)
            shp_path = Path(temp_dir).joinpath(*PurePosixPath(shapefiles[0].filename).parts)
            kwargs: Dict[str, Any] = {}
            if encoding:
                kwargs["encoding"] = encoding
            kwargs["engine"] = "pyogrio"
            try:
                return gpd.read_file(str(shp_path), **kwargs)
            except Exception as exc:
                raise DataLoadError("Could not read shapefile ZIP: {}".format(path)) from exc


def _tabular_geometry(
    frame: pd.DataFrame,
    *,
    source: Path,
    lon_field: Optional[str],
    lat_field: Optional[str],
    wkt_field: Optional[str],
    crs: Optional[Union[str, int]],
) -> gpd.GeoDataFrame:
    if crs is None:
        raise DataLoadError(
            "Tabular input requires an explicit source CRS; pass crs (for example, 'EPSG:4326')."
        )

    has_lonlat = lon_field is not None or lat_field is not None
    has_wkt = wkt_field is not None
    if has_lonlat and has_wkt:
        raise DataLoadError("Choose either lon_field/lat_field or wkt_field, not both.")
    if has_lonlat and not (lon_field and lat_field):
        raise DataLoadError("Both lon_field and lat_field are required for coordinate mapping.")
    if not has_lonlat and not has_wkt:
        raise DataLoadError(
            "CSV/Excel geometry must be explicit: pass lon_field and lat_field, or pass wkt_field."
        )

    required = [wkt_field] if has_wkt else [lon_field, lat_field]
    missing = [name for name in required if name not in frame.columns]
    if missing:
        raise DataLoadError(
            "Missing geometry field(s) in {}: {}".format(source, ", ".join(str(name) for name in missing))
        )

    if has_wkt:
        geometries = []
        failures = []
        assert wkt_field is not None
        for index, value in frame[wkt_field].items():
            if pd.isna(value) or not str(value).strip():
                geometries.append(None)
                continue
            try:
                geometries.append(wkt.loads(str(value)))
            except Exception:
                failures.append(index)
                geometries.append(None)
        if failures:
            preview = ", ".join(str(value) for value in failures[:10])
            raise DataLoadError("Invalid WKT at row index(es): {}".format(preview))
        geometry = gpd.GeoSeries(geometries, index=frame.index, crs=crs)
    else:
        assert lon_field is not None and lat_field is not None
        try:
            longitude = pd.to_numeric(frame[lon_field], errors="raise")
            latitude = pd.to_numeric(frame[lat_field], errors="raise")
        except (TypeError, ValueError) as exc:
            raise DataLoadError(
                "Longitude and latitude fields must contain numeric values: {}, {}".format(
                    lon_field, lat_field
                )
            ) from exc
        geometry = gpd.points_from_xy(longitude, latitude, crs=crs)

    return gpd.GeoDataFrame(frame.copy(), geometry=geometry, crs=crs)


def load_geodata(
    path: PathLike,
    *,
    layer: Optional[str] = None,
    lon_field: Optional[str] = None,
    lat_field: Optional[str] = None,
    wkt_field: Optional[str] = None,
    crs: Optional[Union[str, int]] = None,
    encoding: Optional[str] = None,
    sheet_name: Union[str, int] = 0,
) -> gpd.GeoDataFrame:
    """Load a supported local input without inferring tabular geometry or CRS.

    GeoJSON, GeoPackage and Shapefile ZIP inputs retain their declared CRS.
    CSV and Excel inputs require an explicit geometry mapping and source CRS.
    """

    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise DataLoadError("Input does not exist or is not a file: {}".format(source))

    suffix = source.suffix.lower()
    if suffix in {".geojson", ".json", ".gpkg"}:
        if any(value is not None for value in (lon_field, lat_field, wkt_field)):
            raise DataLoadError("Geometry field mappings apply only to CSV and Excel inputs.")
        kwargs: Dict[str, Any] = {}
        if layer is not None:
            kwargs["layer"] = layer
        kwargs["engine"] = "pyogrio"
        try:
            frame = gpd.read_file(str(source), **kwargs)
        except Exception as exc:
            raise DataLoadError("Could not read vector input: {}".format(source)) from exc
    elif suffix == ".zip":
        if layer is not None:
            raise DataLoadError("layer is not supported for Shapefile ZIP inputs.")
        frame = _read_shapefile_zip(source, encoding=encoding)
    elif suffix == ".csv":
        if layer is not None:
            raise DataLoadError("layer is not supported for CSV inputs.")
        try:
            table = pd.read_csv(str(source), encoding=encoding or "utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DataLoadError(
                "Could not decode CSV input as UTF-8. Specify an explicit encoding."
            ) from exc
        except Exception as exc:
            raise DataLoadError("Could not read CSV input: {}".format(source)) from exc
        frame = _tabular_geometry(
            table,
            source=source,
            lon_field=lon_field,
            lat_field=lat_field,
            wkt_field=wkt_field,
            crs=crs,
        )
    elif suffix in {".xlsx", ".xls"}:
        if layer is not None:
            raise DataLoadError("layer is not supported for Excel inputs.")
        try:
            table = pd.read_excel(str(source), sheet_name=sheet_name)
        except Exception as exc:
            raise DataLoadError("Could not read Excel input: {}".format(source)) from exc
        frame = _tabular_geometry(
            table,
            source=source,
            lon_field=lon_field,
            lat_field=lat_field,
            wkt_field=wkt_field,
            crs=crs,
        )
    else:
        raise DataLoadError(
            "Unsupported input format {!r}; use GeoJSON, GeoPackage, Shapefile ZIP, CSV, or Excel.".format(
                suffix or "<none>"
            )
        )

    if not isinstance(frame, gpd.GeoDataFrame):
        frame = gpd.GeoDataFrame(frame)
    return frame


# A concise alias for callers that model the full pipeline as input -> normalize.
load_input = load_geodata


def load_source(
    source: Union[PathLike, Mapping[str, Any]],
    *,
    base_dir: Optional[PathLike] = None,
) -> gpd.GeoDataFrame:
    """Load a path or a map-spec-style source mapping.

    Supported mapping keys mirror :func:`load_geodata`. Relative paths are
    resolved against ``base_dir`` (normally the directory containing the
    map specification).
    """

    if isinstance(source, (str, Path)):
        source_path = Path(source)
        options: Dict[str, Any] = {}
    elif isinstance(source, Mapping):
        options = dict(source)
        source_path_value = options.pop("path", None)
        if source_path_value is None:
            raise DataLoadError("Source mapping requires a 'path' field.")
        source_path = Path(str(source_path_value))
        if "sheet" in options:
            options.setdefault("sheet_name", options.pop("sheet"))
        geometry = options.pop("geometry", None)
        if geometry is not None:
            if not isinstance(geometry, Mapping):
                raise DataLoadError("source.geometry must be a mapping.")
            geometry_options = dict(geometry)
            geometry_type = str(geometry_options.pop("type", "")).lower()
            if geometry_type == "lonlat":
                options.setdefault(
                    "lon_field",
                    geometry_options.pop("x_field", None),
                )
                options.setdefault(
                    "lat_field",
                    geometry_options.pop("y_field", None),
                )
            elif geometry_type == "wkt":
                options.setdefault(
                    "wkt_field",
                    geometry_options.pop("wkt_field", None),
                )
            else:
                raise DataLoadError(
                    "source.geometry.type must be 'lonlat' or 'wkt'."
                )
            if geometry_options:
                raise DataLoadError(
                    "Unknown source.geometry option(s): {}".format(
                        ", ".join(sorted(geometry_options))
                    )
                )
    else:
        raise TypeError("source must be a path or mapping")

    if not source_path.is_absolute() and base_dir is not None:
        source_path = Path(base_dir).expanduser().resolve() / source_path
    try:
        return load_geodata(source_path, **options)
    except TypeError as exc:
        raise DataLoadError("Unknown source option: {}".format(exc)) from exc
