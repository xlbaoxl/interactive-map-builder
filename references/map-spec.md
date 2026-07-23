# Map specification v1

Treat `scripts/mapcore/resources/map-spec.schema.json` as the only machine-readable
contract. Use canonical `snake_case` keys only. Resolve source paths relative to the
specification file; output names are fixed by the builder.

## Minimal map and list

```json
{
  "schema_version": "1.0",
  "template": "map-list",
  "title": "Candidate places",
  "primary_layer": "places",
  "layers": [
    {
      "id": "places",
      "name": "Places",
      "source": {"path": "places.geojson"},
      "id_field": "place_id",
      "label_field": "name",
      "field_labels": {"status": "Review status"},
      "source_note": "Author survey, 2026",
      "style": {
        "mode": "categorical",
        "color_field": "status",
        "categories": {
          "Ready": {"label": "Ready to review", "color": "#0f766e"},
          "Review": "#d97706"
        }
      },
      "tooltip_fields": ["name", "status"],
      "search_fields": ["name"],
      "filter_fields": ["status"],
      "card_fields": ["status", "score"],
      "sort_fields": ["name", "score"]
    }
  ]
}
```

## Minimal multilayer map

```json
{
  "schema_version": "1.0",
  "template": "multilayer",
  "title": "Project context",
  "layers": [
    {
      "id": "sites",
      "name": "Sites",
      "source": {
        "path": "sites.csv",
        "crs": "EPSG:4326",
        "geometry": {
          "type": "lonlat",
          "x_field": "longitude",
          "y_field": "latitude"
        }
      },
      "id_field": "site_id",
      "label_field": "name",
      "source_note": "Synthetic example",
      "style": {"color": "#7c3aed", "radius": 7},
      "tooltip_fields": ["name"],
      "search_fields": ["name"]
    }
  ]
}
```

## Rules

- Use unique ASCII `layers[].id` values.
- Require `primary_layer` for `map-list`; with multiple layers, pass it explicitly to
  `init-spec` or `run`.
- Define every observed non-null category. Null categories use
  `style.missing_label` and `style.missing_color`.
- Use `source.crs` for tabular or CRS-less spatial inputs; never infer CRS from values.
- Omit `source.encoding` to let Shapefile `.cpg`/GDAL decide and to use UTF-8 for CSV.
- Keep tooltip, popup, search, filter, card, and sort fields explicit.
- Use `layers[].link_key` only for an intentional cross-layer relationship.
- Use `layers[].simplify` with `none`, `light`, or `medium`; static figures retain
  unsimplified normalized geometry.
- Define HTTPS basemaps with attribution. An empty list keeps the business geometry usable.

## Static output

Set `static.presets` to `["slide-16x9"]`, `["paper"]`, or both. The slide preset writes
`map_slide_16x9.png`; paper writes `map_paper.png`, `map_paper.svg`, and
`map_paper.pdf`. Use `static.enabled: false` when no static output is needed.

## Build record and portable bundle

Every build writes a resolved `map_spec.json`. A normal build treats it as a build record
whose source paths still refer to the original project layout. Use
`build --bundle-sources` to copy sources into `dist/data`, rewrite those paths, and create
a portable rebuild bundle. The quick `run` command bundles its inputs by default.

## Initialize from inspection

```powershell
interactive-map-builder inspect data.geojson --output inspection.json
interactive-map-builder init-spec inspection.json --template map-list --primary-layer sites --output map_spec.json
```

One inspected layer may use `--template auto`. Multiple layers always require explicit
template confirmation.
