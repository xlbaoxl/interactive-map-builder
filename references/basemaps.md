# Basemap delivery policy

## Presets and limits

New maps use OpenFreeMap Positron (light analysis) and Liberty (street context). They are two styles
of the same provider, not independent failover services. The public service needs no key as of
2026-09-15; it provides no SLA. Keep OpenMapTiles and OpenStreetMap attribution visible.

The original Leaflet business data, filters, selection, saved views, and sharing remain unchanged.
Pinned MapLibre GL JS 5.6.2 and MapLibre GL Leaflet 0.1.4 are embedded only in HTML that declares a
vector basemap. License notices travel with the standalone HTML and distribution archives.
This adds roughly 1 MB uncompressed to vector-enabled HTML; a raster-only/plain map omits it.
This is an output-size tradeoff, not a measured token saving. No frontend build is needed by users.
Styles, vector tiles, glyphs and sprites are fetched online. This is not an offline basemap bundle.
WebGL must be available. Third-party service availability is not guaranteed, including in China.

## Contract and existing projects

MapSpec 1.2 adds optional basemap `kind` (`raster` or `vector`). The existing HTTPS `url` is a raster
XYZ template unless `kind: "vector"` specifies a MapLibre style URL. Version 1.1 inputs are accepted
and normalized; older engines cannot consume 1.2. An empty basemap list stays empty.

To migrate only the two exact anonymous default URLs shipped in v0.6.0:

```bash
interactive-map-builder migrate-basemaps --spec map_spec.json --out map_spec_migrated.json
interactive-map-builder build --spec map_spec_migrated.json --out dist_migrated
```

Migration is opt-in, keeps order/visibility and business-layer settings, rebases relative data paths
if the output spec moves, preserves custom/credential-bearing URLs, and refuses to overwrite a file.
It does not copy/recover missing source data. HTML generated earlier must be rebuilt. Old view JSON
is tied to the old data/configuration payload and is rejected after a basemap migration; re-export it.
Browser-local bookmarks are not migrated or exported by this command.

## Authorized raster sources

CARTO now requires an authorized `key` query parameter. Missing keys and obvious placeholders are
reported by build and blocked before a tile request. A nonempty key is not proof of valid authorization.
Never embed personal keys in this repository or share a credential-bearing HTML without approval.
OSM's public tile endpoint is not requested from file:// or opaque-origin pages; hosted HTTP(S) use
still requires compliance with attribution, caching, traffic and Referer policies. No request-header
spoofing, image-watermark removal or server-block evasion is implemented. Other authorized raster
services may be configured with their provider URL and attribution, subject to their terms.

## Failure and acceptance

Business layers remain functional if WebGL cannot start or the provider is unavailable. The selector
falls back to the plain background and explains missing-key/local-origin/WebGL/network/timeout
failures. Selecting an available configured basemap retries. Old asynchronous responses cannot
activate a removed layer or clobber a newly selected one. The initial load deadline is 20 seconds.

`build` and `verify` are offline integrity checks. Reports state `basemap_live_check: not_performed`.
An image load or HTTP 200 alone is insufficient: services may return watermarked or denial images.
Known unusable configurations are blocked before rendering; arbitrary error images are not classified.

Deterministic browser tests use a mocked style and validate rendering, lifecycle, failure and sharing.
The separate opt-in live check uses synthetic public coordinates, actual file:// Chromium, both
presets, downloaded snapshots in a fresh browser context, resource status, rendered-feature counts,
and screenshots. Run it in a network-capable environment before publishing a provider change:

```bash
python scripts/check_live_basemaps.py --out /tmp/imb-live-basemaps
```

A successful CI run is evidence for its browser/network at its test time, not every recipient's network.

## Primary references (checked 2026-09-15)

- OpenFreeMap service and attribution: https://openfreemap.org/
- Official Leaflet integration: https://openfreemap.org/quick_start/
- CARTO key policy: https://carto.com/basemaps/apikey/
- OSM tile policy: https://operations.osmfoundation.org/policies/tiles/
