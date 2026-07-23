# Supported inputs

| Format | Required mapping | Notes |
|---|---|---|
| GeoJSON | CRS unless the file follows RFC 7946 | Treated as EPSG:4326 only when RFC 7946 semantics are explicit. |
| GeoPackage | Layer name when more than one layer exists | Preserve the stored CRS. |
| Shapefile ZIP | Selected `.shp` when more than one exists | Reject absolute paths and `..` archive members. |
| CSV | `lonlat` fields or WKT field, plus CRS | Coordinates alone are not geocoded. |
| Excel | Sheet plus `lonlat` fields or WKT field, plus CRS | Read values only; formulas are not evaluated. |

Declare tabular geometry under `source.geometry`:

```json
{"type": "lonlat", "x_field": "longitude", "y_field": "latitude"}
```

or:

```json
{"type": "wkt", "wkt_field": "geometry_wkt"}
```

Omit encoding for Shapefile ZIP so GDAL and `.cpg` metadata can decide. CSV defaults to
UTF-8 with BOM support; use `--encoding` only for a legacy encoding. Treat missing CRS,
empty data, non-finite coordinates, unsupported geometry, or absent configured fields as
blocking errors.

The inspector recognizes common exact coordinate aliases such as `longitude`, `lon`, `lng`, `x`, `经度`, `latitude`, `lat`, `y`, `纬度`, plus `wkt`, `geometry`, `geom`, and `几何`. It reports all plausible candidates. `init-spec` uses them only when one unambiguous geometry mapping and an explicit CRS are available.

When the inspection report recommends simplification, set `simplify` to `light` or
`medium` after explaining that only the interactive geometry copy changes.
