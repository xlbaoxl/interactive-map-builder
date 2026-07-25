# Visual and interaction acceptance

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
