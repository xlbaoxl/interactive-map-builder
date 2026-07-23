# Visual and interaction acceptance

## Shared

- Make the map, title, legend, source note, and current selection immediately legible.
- Use the same category colors in HTML, static figures, cards, and linked views.
- Preserve visible focus indicators and keyboard activation.
- Render user text through safe DOM nodes rather than HTML interpolation.
- Keep attribution visible and provide a neutral no-basemap layer.

## Map and list

- Collapse and expand the list without obscuring the map.
- Keep map hover, card hover, map click, and card click synchronized.
- Search across configured fields; combine filters with search; show an explicit empty state.
- Render records in bounded batches and preserve selection across sorting or filtering.

## Multi-layer

- Give every required layer a control, legend entry, tooltip policy, and deterministic style.
- Fit the combined bounds of visible required layers.
- Search the configured layer without silently searching hidden attributes.

## Browser check

Open the built HTML at desktop and narrow widths. Confirm no console errors, no executable input strings, working tile-failure fallback, accurate QA counts, and usable controls at roughly 1000 px and 620 px widths.
