# Visual and interaction acceptance

## Atlas Studio Light defaults

- Treat the resolved visual plan as a coordinated starting point, not a complete design service.
  Explicit MapSpec colors, sizes, weights, and opacities always override inferred defaults.
- Resolve point, line, and polygon values separately. Use coarse density only to prevent obvious
  crowding; do not perform substantive spatial analysis or silently change the data representation.
- Keep one clear visual focus. In `map-list`, the primary layer leads and context layers recede. In
  `multilayer`, the active business layer receives focus while other visible layers remain readable
  spatial context.
- Preserve a stable polygon-line-point draw order across initial render, layer toggles, search, and
  selection. A selected feature must remain legible without turning every feature into a heavy halo.
- Use the restrained eight-color Atlas categorical palette only when all categories are known and
  the class count fits. Do not cycle colors beyond eight classes; keep filters available and ask the
  user how to group or emphasize a larger classification.
- Keep HTML, legends, list accents, PNG, SVG, and PDF on the same resolved visual plan. Record the
  geometry, density, role, order, explicit overrides, and reasons in `build_report.json`.
- The first build should be broadly balanced and presentation-ready. Refine remaining project-
  specific issues with one or two concrete changes after visually inspecting the actual output.

## Shared

- Make the map, title, legend, source note, and current selection immediately legible.
- Use the same category colors in HTML, static figures, cards, and linked views.
- Preserve official place names from the data source; localize only generic interface text.
- Preserve visible focus indicators and keyboard activation.
- Require every visible control to change an observable state, result, or view.
- Render user text through safe DOM nodes rather than HTML interpolation.
- Keep attribution visible and provide a neutral no-basemap layer.

## Map and list

- Collapse and expand the list without obscuring the map.
- Keep map hover, card hover, map click, and card click synchronized.
- Search across configured fields; combine filters with search; show an explicit empty state.
- Place list sorting beside the list it controls. Show useful configured card fields, keep
  technical IDs out of the card title, and highlight the active sort field in its normal
  position instead of adding a duplicate sort-value row.
- Reuse legend colors as subtle card borders or backgrounds while retaining an accessible
  category name.
- Keep range-filter panels visibly attached to their trigger, within the viewport, mutually
  exclusive, keyboard reachable, dismissible with outside click or `Escape`, and focused back
  on the trigger after keyboard dismissal.
- Render records in bounded batches and preserve selection across sorting or filtering.

## Multi-layer

- Give every required layer a control, legend entry, tooltip policy, and deterministic style.
- Label layers with business names such as `Subway stations`, `Bicycle routes`, and
  `Neighborhood areas`, not raw geometry terms such as point, line, or polygon.
- Search one selected business layer at a time when layers represent different entities. Keep
  the other layers visible as spatial context and update the field label, placeholder, result
  noun, and count when the selected layer changes.
- Make categorical line colors visibly distinct on the map and identical to their legend
  colors; do not encode line classes only in the legend.
- Fit the combined bounds of visible required layers.
- Search the configured layer without silently searching hidden attributes.

## Browser check

Open the built HTML at desktop and narrow widths. Confirm no console errors, no executable input
strings, working tile-failure fallback, accurate QA counts, wrapped tooltip text inside its
boundary, and usable controls at roughly 1000 px and 620 px widths.

## Control stacking and basemaps

- In multilayer maps, keep visibility switches in a fixed upper section and the legend below them
  within one bounded control stack. A long legend must scroll internally rather than cover layer
  switches or other controls.
- Make the legend collapsible and start it collapsed at narrow widths. Keep every layer checkbox
  visible, keyboard reachable, and pointer clickable at desktop and mobile viewports.
- New maps should expose CARTO Positron, OpenStreetMap Standard, and a neutral no-basemap state.
  Preserve provider-specific attribution whenever an online layer is active. Add authenticated
  imagery only from a user-authorized provider configuration; never commit or invent credentials.
- Verify control bounding boxes at desktop, approximately 1000 px, and approximately 390 px widths;
  DOM presence alone is not sufficient when controls overlap.
