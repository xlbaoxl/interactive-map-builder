# Intent-trigger evaluation

This directory measures whether an Agent recognizes Interactive Map Builder from the user's goal,
not only from file extensions or the Skill name. The suite is evaluator-neutral: Codex, Claude Code,
or another Agent Skills client can run the same prompts and record results in one common format.

## Case manifest

`cases.yaml` contains 44 English and Chinese cases across four categories:

- `explicit`: the prompt names a supported format or map behavior;
- `implicit`: the prompt describes the desired outcome without GIS or Skill terminology;
- `ambiguous`: the task is in scope, but blocking choices, optional Codex planning, or delivery
  boundaries must be confirmed before a build;
- `do_not_use`: a nearby task should be routed to geocoding, analysis, WebGIS, 3D, charting, or
  general software engineering instead.

Every case declares:

- the expected invocation decision;
- the expected high-level behavior;
- whether the Agent should ask the user a consolidated clarification question;
- whether the request is complete enough to build after inspection without another user turn;
- whether local-file sharing, public deployment, and optional Plan mode are handled as declared.

Validate the manifest after changing metadata or cases:

```bash
python scripts/evaluate_triggers.py validate
```

## Recording real runs

Run each prompt in a clean Agent session without naming this repository outside the prompt itself.
For stability checks, repeat important cases at least three times. Save observations as JSON:

```json
{
  "runs": [
    {
      "case_id": "natural-language-no-gis",
      "run": 1,
      "client": "codex",
      "model": "record-the-tested-model",
      "actual": {
        "invocation": "trigger",
        "ask_user": true,
        "direct_build": false,
        "behavior_ok": true
      },
      "notes": "Recognized the browser, search, filter, and sharing intent."
    }
  ]
}
```

`behavior_ok` is a human or harness judgment against the case's `expected.behavior`; it should not
be inferred from the invocation decision alone.

Score a result file with:

```bash
python scripts/evaluate_triggers.py score path/to/results.json
python scripts/evaluate_triggers.py score path/to/results.json --require-complete
```

The report includes suite coverage, invocation accuracy, trigger recall, false-negative and
false-positive rates, clarification accuracy, direct-build accuracy, behavior accuracy, and
stability for cases with repeated runs.

Raw experimental results are not treated as product usage counts. Record the Agent client, tested
model, date, and run conditions before comparing releases.

## Task quality and added value

Trigger accuracy is not evidence that the Skill improves map delivery. Compare three arms using
one fixed Agent/model, the same source data and request, and equal time/tool budgets:

- A: normal development environment and standard libraries, without this project;
- B: the packaged engine plus minimal CLI usage, without the Skill conversation instructions;
- C: the same engine plus the full Skill and its referenced guidance.

Use the repository CSV points and multilayer examples, then include a missing-CRS case and a
follow-up request that changes filters or replaces source records. Predefine expected IDs, counts,
field meanings, requested interactions, and a follow-up edit before running any arm. A renderer
choice is not itself a pass criterion. Verify the delivered artifact independently of each arm's
own build report, and judge visual quality without showing the evaluator which arm produced it.
Record total elapsed time, time to first usable map, user-intervention turns, correctness failures,
rework, and tool/token cost. Separate clean installation from already-installed execution; repeat
and alternate the order of runs. Record the commit, environment, dependencies, model and date.

B versus A measures engine reuse; C versus B measures the incremental instructions. Publish real
observations and their limitations, not fabricated model runs or conclusions inferred from the
number of tests. No A/B/C outcome is asserted by this repository change.
