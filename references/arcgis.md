# ArcGIS FeatureServer adapter

Keep remote retrieval outside the renderer. Pass a layer endpoint such as:

```text
https://example.org/arcgis/rest/services/example/FeatureServer/0
```

The adapter must:

- read layer metadata and the object-ID field;
- request all IDs first, sort them, and fetch deterministic chunks;
- request GeoJSON in EPSG:4326;
- reject ArcGIS `error` payloads, duplicate IDs, and count mismatches;
- retry transient requests with bounded backoff;
- save a provenance JSON beside the GeoJSON with URL, retrieval time, count, object-ID field, and SHA-256.

Use `--where` and `--out-fields` to limit public data. Never place authentication tokens in a specification, output, or committed file.
