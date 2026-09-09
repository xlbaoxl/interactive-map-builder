# Guided setup

## Preflight

Run `python scripts/update_skill.py --preflight` from the Skill root before inspection. The check
is cached for 24 hours and remains non-blocking when offline, modified, read-only, or installed
from an unsupported source. It never modifies the installation. Applying updates is a separate,
explicit maintenance action; follow [update-policy.md](update-policy.md).

In Codex, optionally mention Plan mode once when a request contains multiple independent layers,
more than one blocking design choice, or several coordinated outputs. Continue immediately whether
or not the user changes mode. Do not recommend it for an unambiguous single-layer request and do
not mention keyboard shortcuts.

## Round 1: inspect

Run `inspect` before asking questions. Report each candidate layer with:

- path and layer or sheet name;
- row count and non-empty geometry count;
- geometry type and CRS;
- likely ID, label, category, region, and numeric fields;
- blocking issues;
- template candidates, whether confirmation is required, and any non-binding primary/context candidates.

Do not ask for facts the inspection already establishes.

## Round 2: resolve intent and genuine blockers

Show and maintain a compact Markdown requirements checklist while choices remain unresolved:

```markdown
- [x] Confirmed: ...
- [~] Inferred: ...
- [ ] Needs confirmation: ...
```

Populate it from the user request and inspection result. Keep inferred decisions visible and
revisable. Do not build while any blocking `[ ]` item remains. When the request is complete,
proceed directly; the checklist is not an extra approval ceremony.

Resolve `multilayer` from a request for independently switchable layers. Resolve `map-list` when
the user has identified a primary record list. Pass these choices to `init-spec` or `run`; do not
ask users to choose technical template names after they have already described the outcome.
Keep CLI `auto` conservative when no conversational intent is available.

Ask once for genuine blockers: missing CRS or geometry mapping, category meanings the user wants
interpreted, an unresolved primary layer, destructive changes, or permission to expose data.
Respect choices the user explicitly reserves. Use reversible presentation defaults for title,
layout, context opacity, and display fields, show them briefly, then build and refine. Unknown
category codes may be displayed literally; scientific meanings must come from the user or source.

Treat HTML as the default output. Enable `slide-16x9` or `paper` only after the user explicitly
requests that deliverable; do not infer static figures from a request for a website or map.

Explain any proposed repair, generated ID, or simplification before building. Never infer
scientific meaning from a numeric field or category code.

Follow the user's conversation language. Choose `en-US` or `zh-CN` for the map independently;
default the map to `en-US` when no audience is specified.

## Delivery boundary

The default result is a portable local HTML file. Do not interpret “share,” “send to colleagues,”
or “open in a browser” as a request for public hosting. Ask about a public URL only after the user
explicitly requests deployment. Treat deployment as a separate workflow and confirm both the
hosting target and permission to expose the embedded data.

## CLI selection

Prefer the installed `interactive-map-builder` command. Package-level `doctor`, `update`, and
`--version` live there. In a source checkout, `python scripts/cli.py doctor` is the supported
fallback. `python scripts/map_builder.py` is only the internal builder command set and must not be
used to decide whether the package provides `doctor`.

## Build and handoff

Write the resolved `map_spec.json`, build, verify, then inspect the HTML interactively. Deliver
the `dist` directory with a concise summary of counts, warnings, network dependencies, and
provenance.
