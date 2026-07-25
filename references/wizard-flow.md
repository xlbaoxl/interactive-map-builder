# Guided setup

## Planning recommendation

In the first response, non-blockingly recommend Plan mode with `/plan` or `Shift+Tab` when the
request includes multiple layers, an undecided template, unclear CRS or field semantics, or
several design trade-offs. Do not repeat the recommendation in Plan mode. Skip it for a clear
single-layer request.

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

When the user remains outside Plan mode, show and maintain a Markdown requirements checklist:

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

Explain any proposed repair, generated ID, or simplification before building. Never infer scientific meaning from a numeric field or category code.

Follow the user's conversation language. Choose `en-US` or `zh-CN` for the map independently;
default the map to `en-US` when no audience is specified.

## Build and handoff

Write the resolved `map_spec.json`, build, verify, then inspect the HTML interactively. Deliver the `dist` directory with a concise summary of counts, warnings, network dependencies, and provenance.
