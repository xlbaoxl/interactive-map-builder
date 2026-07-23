---
name: interactive-map-builder
description: Build lightweight, shareable interactive HTML maps and report-ready PNG, SVG, and PDF figures from GeoJSON, GeoPackage, zipped Shapefile, CSV, Excel, or ArcGIS FeatureServer data. Use when Codex needs to create a map with a collapsible searchable list, a multi-layer point/line/polygon explorer, linked map and chart selections, legends, filters, sorting, tooltips, popups, basic CRS or geometry cleanup, or presentation and paper map exports. Require existing coordinates or geometry; do not use for geocoding, substantive spatial analysis, vector-tile systems, or offline basemap acquisition.
---

# Interactive Map Builder

Create a configuration-driven map without a frontend build system. Keep acquisition separate from rendering, preserve data provenance, and make every cleanup visible in the build report.

## Workflow

1. Inspect inputs before proposing a map.

   ```powershell
   python scripts/map_builder.py inspect <input> [<input> ...] --output inspection.json
   ```

   For GeoPackage, zipped Shapefile, CSV, Excel, and field-mapping details, read [supported-inputs.md](references/supported-inputs.md).

2. Present one compact inspection summary per candidate layer: feature count, geometry type, CRS, likely ID/label/category fields, and recommended template.

3. Ask one consolidated round of questions only for unresolved intent: primary layer, label, color category, filters, card fields, title, and requested outputs. Never guess a missing CRS.

4. Initialize `map_spec.json` from the inspection, then apply the confirmed choices. Read [map-spec.md](references/map-spec.md) and validate against `references/map-spec.schema.json`.

   ```powershell
   python scripts/map_builder.py init-spec inspection.json --template auto --output map_spec.json
   ```

5. If the source is ArcGIS FeatureServer, download it first and then build from the saved GeoJSON. Read [arcgis.md](references/arcgis.md).

   ```powershell
   python scripts/map_builder.py fetch-arcgis --url <layer-url> --out data/source.geojson
   ```

6. Build once from the resolved specification.

   ```powershell
   python scripts/map_builder.py build --spec map_spec.json --out dist
   ```

7. Verify outputs, inspect `build_report.json`, and open `map.html` in a browser.

   ```powershell
   python scripts/map_builder.py verify --dist dist
   ```

8. Exercise search, filters, sorting, layer visibility, hover/click linkage, keyboard selection, panel collapse, and narrow-screen layout. Read [design-guidelines.md](references/design-guidelines.md) for the visual acceptance checklist.

9. Deliver the whole `dist` directory and summarize repairs, discarded geometries, generated IDs, warnings, online basemap dependencies, and source attribution.

Use the quick path only when the inspected fields, CRS, geometry mapping, and template are unambiguous:

```powershell
python scripts/map_builder.py run <input> --output dist
```

For a reusable command available from any working directory, install the Skill engine once from its root:

```powershell
python -m pip install .
interactive-map-builder --help
```

## Template choice

- Choose `map-list` for one primary layer whose records need browsing, filtering, sorting, and map-to-card selection.
- Choose `multilayer` for mixed point, line, or polygon layers where layer visibility and cross-layer inspection are primary.
- Add `linked_view` only when records already contain meaningful x/y variables. Read [linked-analysis.md](references/linked-analysis.md); do not invent quadrant or statistical interpretations.

## Non-negotiable checks

- Fail when data cannot be read or is empty.
- Require a declared CRS and normalize geometry to EPSG:4326.
- Repair invalid geometry with `make_valid`, report every repair or drop, and never simplify silently.
- Require a unique primary-layer ID; generate a deterministic ID only when the user has not provided one and report that choice.
- Match input, normalized, rendered-map, list-record, and declared-layer counts.

Also fail on missing required fields, unknown configured categories, unsafe archive paths, or ArcGIS pagination mismatches. Escape all user-provided text before placing it in HTML.

## Output contract

The normal build returns `map.html`, `map_slide_16x9.png`, paper PNG/SVG/PDF figures, the resolved `map_spec.json`, `inspection.json`, `build_report.json`, and `README_使用说明.md`. The HTML embeds Leaflet and all UI code; only configured online basemap tiles require a network connection.

## Resources

- Read [wizard-flow.md](references/wizard-flow.md) when leading a non-expert through setup.
- Read [data-provenance.md](references/data-provenance.md) when remote or redistributable data is involved.
- Reuse the synthetic `map-list`, `multilayer`, `csv-points`, and `linked-by-id` specifications under `assets/examples/` for smoke tests; do not substitute them for the user's data.
- Before installation, run the Python script from the Skill root; after installation, use `interactive-map-builder` from any working directory.
