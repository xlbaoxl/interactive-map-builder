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

Use explicit encodings for legacy CSV or Shapefile attributes. Treat missing CRS, empty data, non-finite coordinates, unsupported geometry, or absent required fields as blocking errors.

When simplification is appropriate, set `simplify_tolerance` on the layer only after explaining that the value is in EPSG:4326 degrees in the interactive output.
