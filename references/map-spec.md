# Map specification 1.2

Treat `scripts/mapcore/resources/map-spec.schema.json` as the only machine-readable
contract. Use canonical `snake_case` keys only. Resolve source paths relative to the
specification file; output names are fixed by the builder.

Set `schema_version` to the constant declared by the packaged Schema. The current accepted
value is `1.2`; the loader accepts and normalizes existing `1.1` inputs. Other versions fail validation. Set `locale` to `en-US` or
`zh-CN`; the default is `en-US`.

## Minimal map and list

```json
{
  "schema_version": "1.2",
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
  "schema_version": "1.2",
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
      "tooltip_fields": ["name"],
      "search_fields": ["name"]
    }
  ]
}
```

## Rules

- Use unique ASCII `layers[].id` values.
- Set `id_field` to a stable, non-empty, unique identifier used for runtime identity and
  linkage. Set `label_field` to the human-readable title shown in cards, tooltips, and results;
  do not substitute a technical ID when a meaningful address or name exists.
- Require `primary_layer` for `map-list`; with multiple layers, pass it explicitly to
  `init-spec` or `run`.
- Define every observed non-null category. Null categories use
  `style.missing_label` and `style.missing_color`.
- Use `source.crs` for tabular or CRS-less spatial inputs; never infer CRS from values.
- Omit `source.encoding` to let Shapefile `.cpg`/GDAL decide and to use UTF-8 for CSV.
- Keep tooltip, popup, search, filter, card, and sort fields explicit.
- Put the useful attributes users need for comparison in `card_fields`. A sort field may also
  appear there and should be highlighted in place; it does not require a separate display row.
- Use `layers[].link_key` only for an intentional cross-layer relationship.
- Use `layers[].simplify` with `none`, `light`, or `medium`; static figures retain
  unsimplified normalized geometry.
- Define HTTPS basemaps with attribution. An empty list keeps the business geometry usable.

## Atlas Studio Light visual defaults

MapSpec 1.2 is the current contract; the loader also accepts and normalizes 1.1 inputs. Version 0.4 does not add required visual keys. When a
layer omits `color`, `fill_color`, `weight`, `opacity`, `fill_opacity`, or `radius`, the builder
resolves a lightweight visual plan from:

- point, line, polygon, or mixed geometry;
- coarse feature and coordinate density;
- `map-list` primary/context role or `multilayer` layer role;
- stable polygon-line-point draw order;
- the existing categorical or graduated style, when present.

Explicit MapSpec values always win. The resolver does not infer planning meaning from a field name,
does not perform clustering or heatmapping, and does not replace later user/Agent refinement. The
same plan drives HTML, legends, list accents, PNG, SVG, and PDF. Each layer's resolved plan and
reasons are written to `build_report.json` under `layers[].visual`; the root report identifies
`visual_system: "atlas-studio-light"`.

`init-spec` automatically colors a categorical field only when all observed values are known and
there are at most eight classes. Larger or incomplete classifications remain searchable/filterable
without cycling colors; ask the user which classes should be grouped or emphasized.

## Basemap defaults and provider credentials

`init-spec` and `run` use OpenFreeMap Positron and Liberty vector styles. Basemaps may set
`kind: "vector"` to interpret the HTTPS `url` as a MapLibre style; omitted kind keeps the existing
raster XYZ behavior. See [basemaps.md](basemaps.md) for policy, migration, dependencies and acceptance.

## Interactive controls

For a `multilayer` map, `map.search_behavior` may be `filter` (the default, which removes
nonmatching features from the map) or `highlight` (which keeps the full spatial context and
dims nonmatching features). Set `map.controls.legend` to `false` when the checkbox layer
control already explains the same classes and a second legend would be redundant.

## Static output

Static output is disabled by default. Set `static.enabled: true` and `static.presets` to
`["slide-16x9"]`, `["paper"]`, or both only when the user explicitly requests those files. The
slide preset writes `map_slide_16x9.png`; paper writes `map_paper.png`, `map_paper.svg`, and
`map_paper.pdf`. HTML-only requests should keep `static.enabled: false` or omit `static`.

## Build record and portable bundle

Every build writes a resolved `map_spec.json`. A normal build treats it as a build record
whose source paths still refer to the original project layout. Use
`build --bundle-sources` to copy sources into `dist/data`, rewrite those paths, and create
a portable rebuild bundle. The quick `run` command bundles its inputs by default.

## Initialize from inspection

```powershell
interactive-map-builder inspect data.geojson --output inspection.json
interactive-map-builder init-spec inspection.json --template map-list --primary-layer sites --locale en-US --output map_spec.json
```

One inspected layer may use `--template auto`. For multiple layers, the Agent resolves an explicit
user intent to `map-list` or `multilayer`; ask only when the intended expression is still ambiguous.
The CLI itself has no conversation context and keeps multi-layer auto selection conservative.
