from __future__ import annotations

from pathlib import Path

from evaluate_triggers import load_suite, score_suite, validate_suite


ROOT = Path(__file__).resolve().parents[1]


def test_trigger_suite_has_balanced_intent_and_boundary_coverage():
    summary = validate_suite(load_suite(ROOT / "evals" / "cases.yaml"))
    assert summary == {
        "status": "pass",
        "version": 2,
        "case_count": 36,
        "categories": {
            "ambiguous": 7,
            "do_not_use": 10,
            "explicit": 9,
            "implicit": 10,
        },
        "invocations": {"do_not_use": 10, "trigger": 26},
        "locales": {"en-US": 17, "zh-CN": 19},
    }


def test_trigger_scorer_reports_accuracy_coverage_and_stability():
    suite = load_suite(ROOT / "evals" / "cases.yaml")
    runs = [
        {
            "case_id": "natural-language-no-gis",
            "run": 1,
            "actual": {
                "invocation": "trigger",
                "ask_user": True,
                "direct_build": False,
                "behavior_ok": True,
            },
        },
        {
            "case_id": "natural-language-no-gis",
            "run": 2,
            "actual": {
                "invocation": "trigger",
                "ask_user": True,
                "direct_build": False,
                "behavior_ok": True,
            },
        },
        {
            "case_id": "address-geocoding",
            "run": 1,
            "actual": {
                "invocation": "do_not_use",
                "ask_user": False,
                "direct_build": False,
                "behavior_ok": True,
            },
        },
    ]
    result = score_suite(suite, runs)
    assert result["covered_cases"] == 2
    assert result["run_count"] == 3
    assert result["metrics"]["invocation_accuracy"] == 1.0
    assert result["metrics"]["false_positive_rate"] == 0.0
    assert result["metrics"]["stable_repeated_cases"] == 1.0
    assert len(result["missing_cases"]) == 34
