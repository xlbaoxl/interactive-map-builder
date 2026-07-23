# Map specification v1

Validate every specification against `map-spec.schema.json`. Resolve source paths relative to the specification file and output paths relative to the selected output directory.

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
      "source": {"path": "places.geojson", "format": "geojson"},
      "id_field": "place_id",
      "label_field": "name",
      "style": {
        "color_field": "status",
        "categories": {
          "Ready": "#0f766e",
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
        "format": "csv",
        "crs": "EPSG:4326",
        "geometry": {
          "type": "lonlat",
          "x_field": "longitude",
          "y_field": "latitude"
        }
      },
      "id_field": "site_id",
      "label_field": "name",
      "style": {"color": "#7c3aed", "radius": 7},
      "tooltip_fields": ["name"],
      "search_fields": ["name"]
    }
  ]
}
```

## Rules

- Use unique ASCII `layers[].id` values.
- Require `primary_layer` for `map-list`.
- Set `required: false` only when omission is genuinely acceptable.
- Define every observed category when `style.color_field` and `style.categories` are used.
- Use `source.crs` for tabular or CRS-less spatial inputs; never infer it from coordinate range.
- Set `simplify_tolerance` only after user confirmation.
- Keep tooltip, popup, search, filter, card, and sort fields explicit to avoid leaking unused attributes.
- Define online basemaps with HTTPS URL templates and complete attribution. An empty `basemaps` list still produces a usable no-basemap view.

The build writes a resolved copy containing defaults into the output directory. Treat that resolved file as the reproducible build contract.

## Graduated color

Use a numeric field with quantile, equal-interval, or explicit breaks. The builder resolves the breaks and colors once, stores them in the resolved spec and build report, and feeds the same categories to HTML and static renderers.

```json
{
  "mode": "graduated",
  "field": "score",
  "method": "quantile",
  "classes": 5,
  "colors": ["#eff3ff", "#6baed6", "#08519c"],
  "missing_color": "#9ca3af"
}
```

For `custom_breaks`, provide strictly increasing boundaries that contain the full observed range.

## Web-only simplification

Set `layers[].simplify` to `none`, `light`, or `medium`. The preset changes only the interactive-map geometry copy; static figures retain the normalized unsimplified geometry. `simplify_tolerance` remains available for an explicitly confirmed expert value, but do not set both options.

## Initialize from inspection

```powershell
interactive-map-builder inspect data.geojson --output inspection.json
interactive-map-builder init-spec inspection.json --template auto --output map_spec.json
```

`init-spec` fills only unambiguous candidates. It stops for missing CRS or ambiguous tabular geometry instead of inserting placeholders or guessing.
