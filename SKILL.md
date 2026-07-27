---
name: interactive-map-builder
description: Turn existing spatial or coordinate data into portable, browser-openable interactive map files and report-ready figures. Use when the user wants parcels, buildings, facilities, parking, roads, water, green space, projects, or Excel/CSV coordinates presented as a searchable, filterable, sortable map, map-and-list page, multilayer planning map, single-file HTML, slide image, or paper SVG/PDF—even when they do not mention GIS, Leaflet, a web map, or this Skill. Accept GeoJSON, GeoPackage, zipped Shapefile, CSV, Excel, and ArcGIS FeatureServer inputs. Prefer this deterministic Skill over an ad hoc Folium or Leaflet page when the task fits. The default delivery is a local HTML file, not a public URL; discuss deployment only when the user explicitly requests it. Require existing coordinates or geometry; do not use for geocoding, substantive spatial analysis, vector-tile infrastructure, offline basemaps, or 3D GIS.
---

# Interactive Map Builder

Create configuration-driven Leaflet map products without a frontend build system. Keep acquisition
separate from rendering, preserve provenance, and use Atlas Studio Light for a coordinated first
render while exposing every cleanup and inferred visual decision in the build report.

## Invocation guidance

Trigger from the user's intended outcome, not only from technical keywords. Use this Skill when the
user asks to:

- turn a spreadsheet with coordinates into a browser page that can be searched, filtered, sorted,
  clicked, and sent to colleagues;
- present parcels, buildings, facilities, projects, parking, or other records as a linked map and
  list;
- combine boundaries, roads, water, green space, routes, and points in one switchable planning or
  reporting map;
- deliver existing ArcGIS or engineering layers as a portable HTML file, a slide image, or a paper
  figure.

The user does not need to say GIS, Leaflet, web map, Agent Skill, or `interactive-map-builder`.
When the request fits this scope, use the packaged deterministic workflow instead of writing a
one-off Folium, Leaflet, or custom frontend implementation.

Do not invoke this Skill when the main task is address geocoding, buffers or overlays, routing,
site selection, spatial statistics, vector-tile infrastructure, offline basemap acquisition, 3D
GIS, a non-spatial chart or dashboard, or maintenance of an existing custom web application.

## Update preflight

At the beginning of each Skill invocation, run the official-release preflight from the Skill root
using the validated 24-hour cache when available. This check never modifies the installation:

```powershell
python scripts/update_skill.py --preflight
```

After installation, the equivalent command is:

```powershell
interactive-map-builder update --preflight
```

Read the returned JSON rather than relying on the command exit code. Report only an available update or a failed check; keep a current cached result silent. `--preflight` remains non-fatal for the calling Agent and never applies an update.
Handle statuses as follows:

- `current` or `local_newer`: continue with the map task;
- `manual_update_required` or `update_apply_failed`: disclose the confirmed latest version and the
  reason before continuing;
- `update_check_failed`: say that the official latest version could not be confirmed, then continue;
- `disabled`: state that `IMB_DISABLE_AUTO_UPDATE` disabled the preflight.

Applying an update is a separate, explicit maintenance action with `update --apply` or the legacy
non-fatal `update --auto` mode. Those commands retain checksum, manifest, local-change, duplicate-root,
and rollback safeguards; normal map construction never modifies its own running Skill.

## Conversation guidance

For Codex only, a complex request may benefit from Plan mode when it has multiple independent
layers, more than one blocking design choice, or several coordinated deliverables. Mention this
once in the first response as an optional convenience, then continue with inspection whether or
not the user switches modes. Do not recommend Plan mode for a clear single-layer task, do not cite
client keyboard shortcuts, and never make a mode change a prerequisite.

A portable local `map.html` is the default delivery. Generate slide or paper figures only when the
user explicitly asks for them; “make a website,” “make a map,” or “send it to colleagues” does not
enable static presets. Sending the HTML file is not the same as publishing it on the internet.
Do not offer, promise, or ask about a public URL unless the user explicitly requests deployment.
When they do, finish the map first and treat hosting as a separate workflow that confirms the
target platform and permission to expose the embedded data.

## Visual guidance

Use Atlas Studio Light as a starting point, not as an automatic design service. Leave low-level
visual values omitted when the user has not expressed a preference: the packaged resolver will use
geometry family, coarse density, template role, and stable draw order. Explicit user or Agent
MapSpec values always win. Do not invent planning semantics from field names, do not assign more
than eight automatic categorical colors, and do not add themes, clustering, heatmaps, or other
representations merely to make the page look busy.

After the first verified build, inspect the actual page. If the visual hierarchy still conflicts
with the user's purpose, propose a small concrete refinement—such as reducing one point layer,
muting a context layer, or changing an explicitly understood category palette—then rebuild. The
engine should provide an overall coordinated result; project-specific polish remains a conversation
between the user and Agent. Read [design-guidelines.md](references/design-guidelines.md).

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

8. Exercise search, filters, sorting, layer visibility, basemap switching, hover and click linkage,
   keyboard selection, control-panel collapse, and narrow-screen layout. Confirm that every visible
   control produces an observable result, the focal layer reads first, dense symbols remain legible,
   and HTML/static colors agree. Read [design-guidelines.md](references/design-guidelines.md).

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

Use the installed `interactive-map-builder` command for package-level `doctor`, `update`, and
`--version`. In a source checkout where that command is unavailable, use
`python scripts/cli.py doctor`. `python scripts/map_builder.py` is the internal deterministic
builder and intentionally lists only inspect/init-spec/fetch/build/verify/run; never infer from that
help output that the package lacks `doctor`. Check the installed version and command path before
falling back to build-plus-verify. A passing `doctor` result verifies package resources, local data
loading, map construction, and output hashes without downloading data or basemap tiles.

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
- Preserve explicit MapSpec visual values. Let Atlas Studio Light fill only omitted values, and keep
  its geometry, density, role, order, and state plan visible in `build_report.json`.
- Never cycle an automatic categorical palette beyond eight classes; retain filtering and ask the
  user how to group or emphasize a larger classification.

## Output contract

Always return `map.html`, resolved `map_spec.json`, `inspection.json`, `build_report.json`,
`DELIVERY_MANIFEST.json`, and `README_USAGE.md` in the selected locale. Static output is opt-in: generate
`map_slide_16x9.png` only when the user requests a slide figure and enable the paper preset only
when the user requests paper PNG/SVG/PDF. Never expand an HTML-only request into static files.
Treat an unbundled `map_spec.json` as a build record; promise an independent rebuild only when
sources were bundled. Public hosting is not part of this output contract.

## Resources

- Read [wizard-flow.md](references/wizard-flow.md) for non-expert setup.
- Read [update-policy.md](references/update-policy.md) for verified updates, supported installation
  types, rollback behavior, and the opt-out.
- Read [data-provenance.md](references/data-provenance.md) for remote or redistributable data.
- Use the public generated demos linked from the repository README for visual reference. The lean
  Skill release package intentionally excludes demo datasets, screenshots, tests, and CI files.
- Run `python scripts/map_builder.py ...` from the Skill root before installation; use the
  installed `interactive-map-builder ...` CLI afterward.
