from __future__ import annotations

import struct
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
    assert "$skill-installer" in readme
    assert "$HOME\\.agents\\skills" in readme
    assert "三分钟开始" not in readme
    assert "Three-minute quick start" not in readme


def test_readme_example_provenance_is_documented():
    sources = (ROOT / "assets" / "examples" / "SOURCES.md").read_text(encoding="utf-8")
    for dataset_id in ("enfh-gkve", "gthc-hcne", "mzxg-pwib", "i7jb-7jku"):
        assert dataset_id in sources
    assert "2026-07-23" in sources
    assert "EPSG:4326" in sources


def test_readme_screenshots_have_fixed_dimensions_and_fit_the_size_budget():
    for name in ("map-list.png", "multilayer.png"):
        payload = (ROOT / "assets" / "screenshots" / name).read_bytes()
        assert payload.startswith(b"\x89PNG\r\n\x1a\n")
        assert struct.unpack(">II", payload[16:24]) == (1600, 900)
        assert len(payload) <= 1_500_000
