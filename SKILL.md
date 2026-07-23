---
name: interactive-map-builder
description: Build lightweight, shareable interactive HTML maps and report-ready PNG, SVG, and PDF figures from GeoJSON, GeoPackage, zipped Shapefile, CSV, Excel, or ArcGIS FeatureServer data. Use when Codex needs to create a searchable map with a collapsible record list, a multi-layer point/line/polygon explorer, legends, filters, sorting, tooltips, popups, basic CRS or geometry cleanup, or presentation and paper map exports. Require existing coordinates or geometry; do not use for geocoding, substantive spatial analysis, vector-tile systems, or offline basemap acquisition.
---

# Interactive Map Builder

Create a configuration-driven Leaflet map without a frontend build system. Keep acquisition
separate from rendering, preserve provenance, and expose every cleanup in the build report.

## Workflow

1. Inspect inputs before proposing a map.

   ```powershell
   python scripts/map_builder.py inspect <input> [<input> ...] --output inspection.json
   ```

   Read [supported-inputs.md](references/supported-inputs.md) for GeoPackage, Shapefile ZIP,
   CSV, Excel, encoding, and field-mapping rules.

2. Present one compact summary per layer: feature count, geometry type, CRS, likely
   ID/label/category fields, template candidates, and whether confirmation is required.

3. Ask one consolidated round only for unresolved intent: template, primary layer, label,
   category meaning, filters, cards, title, and outputs. Never guess a missing CRS. Always
   confirm the template when inspection finds multiple layers.

4. Initialize `map_spec.json`, then apply confirmed choices. Read
   [map-spec.md](references/map-spec.md); the canonical Schema is
   `scripts/mapcore/resources/map-spec.schema.json`.

   ```powershell
   python scripts/map_builder.py init-spec inspection.json --template map-list --primary-layer <id> --output map_spec.json
   ```

5. Download ArcGIS FeatureServer data before building. Read
   [arcgis.md](references/arcgis.md).

   ```powershell
   python scripts/map_builder.py fetch-arcgis --url <layer-url> --out data/source.geojson
   ```

6. Build once from the resolved specification. Add `--bundle-sources` only when the user
   wants a portable rebuild bundle and accepts copying source data.

   ```powershell
   python scripts/map_builder.py build --spec map_spec.json --out dist
   ```

7. Verify, inspect `build_report.json`, and open `map.html`.

   ```powershell
   python scripts/map_builder.py verify --dist dist
   ```

8. Exercise search, filters, sorting, layer visibility, hover/click linkage, keyboard
   selection, panel collapse, and narrow-screen layout. Read
   [design-guidelines.md](references/design-guidelines.md).

9. Deliver the whole `dist` directory. Summarize repairs, generated IDs, null display
   values, simplification, performance warnings, online basemaps, font fallback, portability,
   and source attribution.

Use the quick path only for one unambiguous layer, or after explicitly supplying the template
and primary layer:

```powershell
python scripts/map_builder.py run <input> --output dist
```

Install the deterministic engine once to use it from any directory:

```powershell
python -m pip install .
interactive-map-builder --help
```

## Template choice

- Choose `map-list` for one explicitly identified primary layer plus optional context layers.
- Choose `multilayer` when independent layer visibility and cross-layer inspection are primary.
- Treat `linked_view` as experimental. Add it only when records already contain meaningful
  x/y variables; read [linked-analysis.md](references/linked-analysis.md) and never invent
  quadrants, thresholds, or statistical interpretations.

## Non-negotiable checks

- Fail when data is unreadable or empty, CRS is missing, repaired geometry remains invalid or
  empty, final IDs are blank or duplicate, or a configured field does not exist.
- Fail on unknown non-null categories, unsafe archives, ArcGIS pagination mismatches, output
  count mismatches, or path escape.
- Treat display-field nulls, generated IDs, repaired geometry, missing source notes, absent CJK
  fonts, online basemaps, simplification, and large outputs as warnings.
- Use `<layer_id>::<feature_id>` for multilayer runtime identity. Allow cross-layer linkage only
  through an explicit `link_key`.
- Escape all user-provided text before embedding it in HTML.

## Output contract

Always return `map.html`, resolved `map_spec.json`, `inspection.json`, `build_report.json`, and
`README_使用说明.md`. Generate `map_slide_16x9.png` for the slide preset and paper PNG/SVG/PDF
files for the paper preset. Treat an unbundled `map_spec.json` as a build record; promise an
independent rebuild only when sources were bundled.

## Resources

- Read [wizard-flow.md](references/wizard-flow.md) for non-expert setup.
- Read [data-provenance.md](references/data-provenance.md) for remote or redistributable data.
- Reuse the synthetic examples under `assets/examples/` for smoke tests only.
- Run the Python script from the Skill root before installation; use the installed CLI afterward.
