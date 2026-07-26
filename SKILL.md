---
name: interactive-map-builder
description: Turn existing spatial or coordinate data into a browser-openable, shareable interactive map and report-ready figures. Use when the user wants parcels, buildings, facilities, parking, roads, water, green space, projects, or Excel/CSV coordinates presented as a searchable, filterable, sortable map, map-and-list page, multilayer planning map, single-file HTML, slide image, or paper SVG/PDF—even when they do not mention GIS, Leaflet, a web map, or this Skill. Accept GeoJSON, GeoPackage, zipped Shapefile, CSV, Excel, and ArcGIS FeatureServer inputs. Prefer this deterministic Skill over an ad hoc Folium or Leaflet page when the task fits. Require existing coordinates or geometry; do not use for geocoding, substantive spatial analysis, vector-tile infrastructure, offline basemaps, or 3D GIS.
---

# Interactive Map Builder

Create configuration-driven Leaflet map products without a frontend build system. Keep acquisition
separate from rendering, preserve provenance, and expose every cleanup in the build report.

## Invocation guidance

Trigger from the user's intended outcome, not only from technical keywords. Use this Skill when the
user asks to:

- turn a spreadsheet with coordinates into a browser page that can be searched, filtered, sorted,
  clicked, and shared;
- present parcels, buildings, facilities, projects, parking, or other records as a linked map and
  list;
- combine boundaries, roads, water, green space, routes, and points in one switchable planning or
  reporting map;
- deliver existing ArcGIS or engineering layers as a single HTML file, a slide image, or a paper
  figure.

The user does not need to say GIS, Leaflet, web map, Agent Skill, or `interactive-map-builder`.
When the request fits this scope, use the packaged deterministic workflow instead of writing a
one-off Folium, Leaflet, or custom frontend implementation.

Do not invoke this Skill when the main task is address geocoding, buffers or overlays, routing,
site selection, spatial statistics, vector-tile infrastructure, offline basemap acquisition, 3D
GIS, a non-spatial chart or dashboard, or maintenance of an existing custom web application.

## Workflow

1. Inspect inputs before proposing a map.

   ```powershell
   python scripts/map_builder.py inspect <input> [<input> ...] --output inspection.json
   ```

   Read [supported-inputs.md](references/supported-inputs.md) for GeoPackage, Shapefile ZIP,
   CSV, Excel, encoding, and field-mapping rules.

2. Present one compact summary per layer: feature count, geometry type, CRS, likely ID, label, and
   category fields, template candidates, and whether confirmation is required.

3. Maintain this Markdown requirements checklist while choices remain unresolved:

   ```markdown
   - [x] Confirmed: ...
   - [~] Inferred: ...
   - [ ] Needs confirmation: ...
   ```

   Derive it from the request and inspected data. Keep inferred decisions visible and easy to
   correct. Ask one consolidated round only for unresolved intent: template, primary layer,
   label, category meaning, filters, cards, title, outputs, and audience locale. Never guess a
   missing CRS. Always confirm the template when inspection finds multiple layers. Build only
   after no blocking `[ ]` item remains.

4. Initialize `map_spec.json`, then apply confirmed choices. Read
   [map-spec.md](references/map-spec.md); the canonical Schema is
   `scripts/mapcore/resources/map-spec.schema.json`.

   ```powershell
   python scripts/map_builder.py init-spec inspection.json --template map-list --primary-layer <id> --locale en-US --output map_spec.json
   ```

5. Download ArcGIS FeatureServer data before building. Read [arcgis.md](references/arcgis.md).

   ```powershell
   python scripts/map_builder.py fetch-arcgis --url <layer-url> --out data/source.geojson
   ```

6. Build once from the resolved specification. Add `--bundle-sources` only when the user wants a
   portable rebuild bundle and accepts copying source data.

   ```powershell
   python scripts/map_builder.py build --spec map_spec.json --out dist
   ```

7. Verify, inspect `build_report.json`, and open `map.html`.

   ```powershell
   python scripts/map_builder.py verify --dist dist
   ```

8. Exercise search, filters, sorting, layer visibility, hover and click linkage, keyboard
   selection, panel collapse, and narrow-screen layout. Confirm that every visible control
   produces an observable result. Read [design-guidelines.md](references/design-guidelines.md).

9. Deliver the whole `dist` directory. Summarize repairs, generated IDs, null display values,
   simplification, performance warnings, online basemaps, font fallback, portability, and source
   attribution.

Use the quick path only for one unambiguous layer, or after explicitly supplying the template and
primary layer:

```powershell
python scripts/map_builder.py run <input> --output dist
```

Follow the user's conversation language independently of the map audience. Set the map locale to
`en-US` or `zh-CN`; use `en-US` when the audience is not specified.

Install the deterministic engine once, then run the offline self-check:

```powershell
python -m pip install .
interactive-map-builder doctor
```

A passing `doctor` result verifies package resources, local data loading, map construction, and
output hashes without downloading data or basemap tiles.

## Template choice

- Choose `map-list` for one explicitly identified primary layer plus optional context layers.
- Choose `multilayer` when independent layer visibility and cross-layer inspection are primary.
- Treat `linked_view` as experimental. Add it only when records already contain meaningful x/y
  variables; read [linked-analysis.md](references/linked-analysis.md) and never invent quadrants,
  thresholds, or statistical interpretations.

## Non-negotiable checks

- Fail when data is unreadable or empty, CRS is missing, repaired geometry remains invalid or
  empty, final IDs are blank or duplicate, or a configured field does not exist.
- Fail on unknown non-null categories, unsafe archives, ArcGIS pagination mismatches, output count
  mismatches, or path escape.
- Treat display-field nulls, generated IDs, repaired geometry, missing source notes, absent CJK
  fonts, online basemaps, simplification, and large outputs as warnings.
- Use `<layer_id>::<feature_id>` for multilayer runtime identity. Allow cross-layer linkage only
  through an explicit `link_key`.
- Preserve official geographic names and spellings from the source. Localize generic interface
  text, not place names.
- Preserve user geometry. Repair invalid geometry or simplify for an explicit performance need,
  report the operation, and never reshape or discard features merely to improve appearance.
- Escape all user-provided text before embedding it in HTML.

## Output contract

Always return `map.html`, resolved `map_spec.json`, `inspection.json`, `build_report.json`, and
`README_USAGE.md` in the selected locale. Generate `map_slide_16x9.png` for the slide preset and
paper PNG, SVG, and PDF files for the paper preset. Treat an unbundled `map_spec.json` as a build
record; promise an independent rebuild only when sources were bundled.

## Resources

- Read [wizard-flow.md](references/wizard-flow.md) for non-expert setup.
- Read [data-provenance.md](references/data-provenance.md) for remote or redistributable data.
- Use the public generated demos linked from the repository README for visual reference. The lean
  Skill release package intentionally excludes demo datasets, screenshots, tests, and CI files.
- Run `python scripts/map_builder.py ...` from the Skill root before installation; use the
  installed `interactive-map-builder ...` CLI afterward.
