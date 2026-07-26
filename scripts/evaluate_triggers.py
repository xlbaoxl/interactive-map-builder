#!/usr/bin/env python
"""Validate and score the evaluator-neutral trigger suite."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "evals" / "cases.yaml"
INVOCATIONS = {"trigger", "do_not_use"}
CATEGORIES = {"explicit", "implicit", "ambiguous", "do_not_use"}


class EvalError(RuntimeError):
    """Raised when the trigger suite or result file is malformed."""


def load_suite(path: Path = DEFAULT_CASES) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise EvalError("Evaluation suite must be a mapping.")
    return data


def validate_suite(data: Mapping[str, Any]) -> Dict[str, Any]:
    if data.get("version") != 2:
        raise EvalError("Evaluation suite version must be 2.")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise EvalError("Evaluation suite must contain cases.")

    seen = set()
    categories: Counter[str] = Counter()
    invocations: Counter[str] = Counter()
    locales: Counter[str] = Counter()
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            raise EvalError(f"Case {index} must be a mapping.")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise EvalError(f"Case {index} has no valid id.")
        if case_id in seen:
            raise EvalError(f"Duplicate case id: {case_id}")
        seen.add(case_id)
        category = case.get("category")
        if category not in CATEGORIES:
            raise EvalError(f"{case_id}: unsupported category {category!r}.")
        locale = case.get("locale")
        if locale not in {"en-US", "zh-CN"}:
            raise EvalError(f"{case_id}: unsupported locale {locale!r}.")
        prompt = case.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise EvalError(f"{case_id}: prompt is required.")
        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise EvalError(f"{case_id}: expected mapping is required.")
        invocation = expected.get("invocation")
        if invocation not in INVOCATIONS:
            raise EvalError(f"{case_id}: unsupported invocation {invocation!r}.")
        for field in ("ask_user", "direct_build"):
            if not isinstance(expected.get(field), bool):
                raise EvalError(f"{case_id}: expected.{field} must be boolean.")
        if not isinstance(expected.get("behavior"), str) or not expected["behavior"].strip():
            raise EvalError(f"{case_id}: expected.behavior is required.")
        if invocation == "do_not_use" and (expected["ask_user"] or expected["direct_build"]):
            raise EvalError(f"{case_id}: do_not_use cases cannot ask or build.")
        categories[category] += 1
        invocations[invocation] += 1
        locales[locale] += 1

    return {
        "status": "pass",
        "version": data["version"],
        "case_count": len(cases),
        "categories": dict(sorted(categories.items())),
        "invocations": dict(sorted(invocations.items())),
        "locales": dict(sorted(locales.items())),
    }


def _load_results(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    runs = data.get("runs") if isinstance(data, dict) else None
    if not isinstance(runs, list):
        raise EvalError("Result file must contain a runs array.")
    return runs


def _ratio(numerator: int, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def score_suite(
    suite: Mapping[str, Any],
    runs: Iterable[Mapping[str, Any]],
    *,
    require_complete: bool = False,
) -> Dict[str, Any]:
    validate_suite(suite)
    cases = {case["id"]: case for case in suite["cases"]}
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    counters: Counter[str] = Counter()

    for position, run in enumerate(runs, start=1):
        case_id = run.get("case_id")
        if case_id not in cases:
            raise EvalError(f"Run {position} references unknown case {case_id!r}.")
        actual = run.get("actual")
        if not isinstance(actual, dict):
            raise EvalError(f"Run {position} has no actual mapping.")
        invocation = actual.get("invocation")
        if invocation not in INVOCATIONS:
            raise EvalError(f"Run {position} has unsupported invocation {invocation!r}.")
        for field in ("ask_user", "direct_build", "behavior_ok"):
            if not isinstance(actual.get(field), bool):
                raise EvalError(f"Run {position}: actual.{field} must be boolean.")

        expected = cases[case_id]["expected"]
        grouped[case_id].append(run)
        counters["runs"] += 1
        counters["invocation_correct"] += invocation == expected["invocation"]
        counters["ask_correct"] += actual["ask_user"] == expected["ask_user"]
        counters["build_correct"] += actual["direct_build"] == expected["direct_build"]
        counters["behavior_correct"] += actual["behavior_ok"]
        if expected["invocation"] == "trigger":
            counters["expected_trigger"] += 1
            counters["true_trigger"] += invocation == "trigger"
            counters["false_negative"] += invocation != "trigger"
        else:
            counters["expected_do_not_use"] += 1
            counters["true_rejection"] += invocation == "do_not_use"
            counters["false_positive"] += invocation == "trigger"

    missing = sorted(set(cases) - set(grouped))
    if require_complete and missing:
        raise EvalError("Missing results for: " + ", ".join(missing))

    repeated = 0
    stable = 0
    for case_id, case_runs in grouped.items():
        if len(case_runs) < 2:
            continue
        repeated += 1
        expected = cases[case_id]["expected"]["invocation"]
        invocations = {run["actual"]["invocation"] for run in case_runs}
        if invocations == {expected}:
            stable += 1

    total = counters["runs"]
    return {
        "status": "pass",
        "case_count": len(cases),
        "covered_cases": len(grouped),
        "coverage": _ratio(len(grouped), len(cases)),
        "missing_cases": missing,
        "run_count": total,
        "metrics": {
            "invocation_accuracy": _ratio(counters["invocation_correct"], total),
            "trigger_recall": _ratio(counters["true_trigger"], counters["expected_trigger"]),
            "false_negative_rate": _ratio(
                counters["false_negative"], counters["expected_trigger"]
            ),
            "false_positive_rate": _ratio(
                counters["false_positive"], counters["expected_do_not_use"]
            ),
            "ask_user_accuracy": _ratio(counters["ask_correct"], total),
            "direct_build_accuracy": _ratio(counters["build_correct"], total),
            "behavior_accuracy": _ratio(counters["behavior_correct"], total),
            "stable_repeated_cases": _ratio(stable, repeated),
        },
        "repeated_case_count": repeated,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="Validate the case manifest and print its coverage.")
    score = subparsers.add_parser("score", help="Score recorded Agent runs from a JSON file.")
    score.add_argument("results", type=Path)
    score.add_argument("--require-complete", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        suite = load_suite(args.cases)
        if args.command == "validate":
            result = validate_suite(suite)
        else:
            result = score_suite(
                suite,
                _load_results(args.results),
                require_complete=args.require_complete,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (EvalError, OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
