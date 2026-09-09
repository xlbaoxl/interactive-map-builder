# Portable view state

## User workflow

After exploring either template, open **Share view** in the header. **Download map HTML** creates
`map-view.html`, which opens directly with the current view. It remains a local file; the button
never uploads data or publishes a URL. **Export view JSON** creates `map-view.json` for later import
into the same map. Importing a state changes the current view; it does not rewrite the source file.

The snapshot restores center and zoom, basemap choice, search, current selection, and sidebar and
legend state. Map-list also restores category, select and numeric filters, ascending/descending
sort, and the detail drawer. Multilayer also restores the focused layer, each layer's visibility,
and the control-panel collapse state. Empty results, an empty category selection, and all layers
hidden are valid states. Leaflet may round camera positions to screen pixels. A different screen
size naturally shows a different extent around the saved center at the saved zoom.

Named local bookmarks remain local. Hover, scroll position, transient popups, fullscreen mode,
and browser history are not exported. The exported HTML can be renamed, moved, and exported again.

## Data and provenance boundaries

An HTML snapshot contains **all data already embedded in the map**, including hidden layers and
filtered-out records. Filtering is not redaction or access control. View JSON contains no geometry
or full feature table but can contain search terms, categories and selected object IDs. Confirm
that recipients may receive that information. These files are not encrypted or authenticated.

The existing online-basemap behavior is unchanged: tiles may need network access and may fall back
to no basemap. The HTML embeds the original map data and application resources, not cached tiles.

A browser snapshot is a separate artifact, not a replacement for the manifest-controlled
`dist/map.html`. Original build hashes do not verify a later browser export. Keep the original
build directory, reports and any rebuild sources unchanged. This feature does not make an
unbundled MapSpec independently rebuildable or export new static figures.

## Versioned contract

View JSON uses `format: interactive-map-builder-view` and integer `version: 1`. Its other required
fields are `map_key`, `template`, `map`, `panels`, and the template-specific `view`. The HTML renderer
computes `map_key` as SHA-256 of the complete serialized payload before adding that key. This binds
geometry, attributes, style, fields, locale and configuration. File-system location of the delivered
HTML is not part of the identity. Data changes with the same IDs and counts still invalidate an
old view file. This is a compatibility check, not a security signature.

The importer enforces the 1 MiB limit before parsing, validates exact structural keys and types,
and checks selected IDs, layer IDs, categorical values and sort fields against the current map.
It rejects mismatches before modifying the view. Unexpected synchronous application failures
attempt to restore the previous view. Invalid embedded state opens the sharing dialog with an
error and leaves the normal initial map usable. No HTML from an imported state is executed.

Snapshots serialize a clean source DOM captured before runtime initialization, then insert one
escaped JSON state block. They do not serialize a running Leaflet tree or browser-local bookmarks.
Template adapters call the existing search/filter/selection logic; product execution does not
call test actions. `captureViewState`, `restoreViewState` and `exportViewHTML` are available through
the existing QA interface for regression testing.

MapSpec remains version 1.1. Portable-view version 1 is a browser-state format, not a new MapSpec.
