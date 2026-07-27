# Guided setup

## Preflight

Run `python scripts/update_skill.py --auto` from the Skill root before inspection. The check is
cached for 24 hours and must remain non-blocking when offline, modified, read-only, or installed
from an unsupported source. If an update is applied, re-read `SKILL.md` before continuing.

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

## Round 2: confirm intent

Show and maintain a compact Markdown requirements checklist while choices remain unresolved:

```markdown
- [x] Confirmed: ...
- [~] Inferred: ...
- [ ] Needs confirmation: ...
```

Populate it from the user request and inspection result. Keep inferred decisions visible and
revisable. Do not build while any blocking `[ ]` item remains.

Ask one compact group of questions covering only unresolved choices:

1. Which layer is primary?
2. Which field names each feature?
3. Which field controls color, and what do its values mean?
4. Which fields should be searchable, filterable, sortable, or visible on cards?
5. What title, subtitle, source note, outputs, and audience locale are needed?

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
