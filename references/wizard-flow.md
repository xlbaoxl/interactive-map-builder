# Guided setup

## Round 1: inspect

Run `inspect` before asking questions. Report each candidate layer with:

- path and layer or sheet name;
- row count and non-empty geometry count;
- geometry type and CRS;
- likely ID, label, category, region, and numeric fields;
- blocking issues;
- recommended `map-list` or `multilayer` template.

Do not ask for facts the inspection already establishes.

## Round 2: confirm intent

Ask one compact group of questions covering only unresolved choices:

1. Which layer is primary?
2. Which field names each feature?
3. Which field controls color, and what do its values mean?
4. Which fields should be searchable, filterable, sortable, or visible on cards?
5. What title, subtitle, source note, and outputs are needed?

Explain any proposed repair, generated ID, or simplification before building. Never infer scientific meaning from a numeric field or category code.

## Build and handoff

Write the resolved `map_spec.json`, build, verify, then inspect the HTML interactively. Deliver the `dist` directory with a concise summary of counts, warnings, network dependencies, and provenance.
