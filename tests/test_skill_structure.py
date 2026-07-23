from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_skill_metadata_is_concise_and_complete():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert set(metadata) == {"name", "description"}
    assert metadata["name"] == "interactive-map-builder"
    assert "TODO" not in text
    assert len(body.splitlines()) < 500


def test_openai_interface_mentions_skill():
    text = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert data["interface"]["display_name"] == "Interactive Map Builder"
    assert "$interactive-map-builder" in data["interface"]["default_prompt"]


def test_behavior_evals_and_bilingual_readme_are_present():
    evals = yaml.safe_load((ROOT / "evals" / "cases.yaml").read_text(encoding="utf-8"))
    assert evals["version"] == 1
    assert len(evals["cases"]) == 7
    invocations = {case["expected"]["invocation"] for case in evals["cases"]}
    assert invocations == {"trigger", "do_not_use"}

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## 中文" in readme
    assert "## English" in readme
    assert "assets/screenshots/map-list.png" in readme
    assert "assets/screenshots/multilayer.png" in readme
