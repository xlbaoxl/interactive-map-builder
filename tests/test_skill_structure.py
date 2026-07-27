from __future__ import annotations

import struct
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_skill_metadata_is_concise_complete_and_intent_driven():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    assert set(metadata) == {"name", "description"}
    assert metadata["name"] == "interactive-map-builder"
    assert "TODO" not in text
    assert len(metadata["description"]) <= 1024
    assert len(body.splitlines()) < 500
    for expected in (
        "even when they do not mention GIS",
        "single-file HTML",
        "Excel/CSV coordinates",
        "Prefer this deterministic Skill",
    ):
        assert expected in metadata["description"]
    assert "The user does not need to say GIS" in body
    assert "one-off Folium" in body
    assert "local HTML file, not a public URL" in metadata["description"]
    assert "interactive-map-builder update --auto" in body
    assert "Plan mode" in body
    assert "Do not offer, promise, or ask about a public URL" in body
    assert "Atlas Studio Light" in body
    assert "not as an automatic design service" in body
    assert "Never expand an HTML-only request into static files" in body
    assert "python scripts/cli.py doctor" in body


def test_openai_interface_mentions_skill_and_user_intent():
    text = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    interface = data["interface"]
    assert interface["display_name"] == "Interactive Map Builder"
    assert "$interactive-map-builder" in interface["default_prompt"]
    assert "even if they do not mention GIS" in interface["default_prompt"]
    assert "ad hoc Folium or Leaflet" in interface["default_prompt"]
    assert "public URL only when explicitly requested" in interface["default_prompt"]
    assert "Plan mode" in interface["default_prompt"]
    assert "Atlas Studio Light" in interface["default_prompt"]
    assert "never add slide or paper figures unless explicitly requested" in interface["default_prompt"]
    assert len(interface["short_description"]) <= 80


def test_behavior_evals_and_localized_readmes_are_present():
    evals = yaml.safe_load((ROOT / "evals" / "cases.yaml").read_text(encoding="utf-8"))
    assert evals["version"] == 2
    assert len(evals["cases"]) == 40
    invocations = {case["expected"]["invocation"] for case in evals["cases"]}
    assert invocations == {"trigger", "do_not_use"}
    categories = {case["category"] for case in evals["cases"]}
    assert categories == {"explicit", "implicit", "ambiguous", "do_not_use"}
    assert {case["locale"] for case in evals["cases"]} == {"en-US", "zh-CN"}
    for case in evals["cases"]:
        assert isinstance(case["expected"]["ask_user"], bool)
        assert isinstance(case["expected"]["direct_build"], bool)
        assert case["expected"]["behavior"]

    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    assert "[中文说明](README.zh-CN.md)" in readme_en
    assert "[English](README.md)" in readme_zh
    assert "assets/screenshots/en-US/map-list.png" in readme_en
    assert "assets/screenshots/en-US/multilayer.png" in readme_en
    assert "assets/screenshots/zh-CN/map-list.png" in readme_zh
    assert "assets/screenshots/zh-CN/multilayer.png" in readme_zh

    for readme in (readme_en, readme_zh):
        assert "$skill-installer" in readme
        assert "$HOME\\.agents\\skills" in readme
        assert "interactive-map-builder doctor" in readme
        assert "interactive-map-builder-skill-vX.Y.Z.zip" in readme
        assert "Plan mode" in readme
        assert "interactive-map-builder update --check" in readme
        assert "public" in readme.casefold() or "公网" in readme
        assert "/plan" not in readme
        assert "Shift+Tab" not in readme

    assert "## Quick start" in readme_en
    assert "## 快速开始" in readme_zh
    assert "## Ask for the outcome, not the tool" in readme_en
    assert "## 直接描述成果，不必记住工具名称" in readme_zh
    assert "## Atlas Studio Light" in readme_en
    assert "## Atlas Studio Light 视觉系统" in readme_zh
    assert "v0.4.3" in readme_en
    assert "v0.4.3" in readme_zh
    assert "## 中文" not in readme_en
    assert "## English" not in readme_en


def test_readme_example_provenance_is_documented():
    sources = (ROOT / "assets" / "examples" / "SOURCES.md").read_text(encoding="utf-8")
    for dataset_id in (
        "i38t-6if2",
        "64uk-42ks",
        "9nt8-h7nd",
        "mzxg-pwib",
        "i9wp-a4ja",
    ):
        assert dataset_id in sources
    assert "2026-07-24" in sources
    assert "EPSG:4326" in sources


def test_readme_screenshots_have_fixed_dimensions_and_fit_the_size_budget():
    for locale in ("en-US", "zh-CN"):
        for name in ("map-list.png", "multilayer.png"):
            payload = (ROOT / "assets" / "screenshots" / locale / name).read_bytes()
            assert payload.startswith(b"\x89PNG\r\n\x1a\n")
            assert struct.unpack(">II", payload[16:24]) == (1600, 900)
            assert len(payload) <= 1_700_000


def test_skill_uses_cross_agent_requirements_checklist():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    wizard = (ROOT / "references" / "wizard-flow.md").read_text(encoding="utf-8")
    for expected in ("[x] Confirmed", "[~] Inferred", "[ ] Needs confirmation"):
        assert expected in skill
        assert expected in wizard
    assert "no blocking `[ ]` item remains." in skill
    assert "Plan mode" in skill
    assert "Plan mode" in wizard
    assert "public URL" in skill
    assert "public URL" in wizard
    assert "/plan" not in skill
    assert "Shift+Tab" not in skill
    assert "Shift+Tab" not in wizard


def test_verified_update_policy_is_packaged_and_linked():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    policy = (ROOT / "references" / "update-policy.md").read_text(encoding="utf-8")
    assert "references/update-policy.md" in skill
    for expected in (
        "SHA256SUMS.txt",
        "PACKAGE_MANIFEST.json",
        "Transaction and rollback",
        "IMB_DISABLE_AUTO_UPDATE=1",
    ):
        assert expected in policy


def test_atlas_visual_guidance_is_documented_without_expanding_mapspec():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    design = (ROOT / "references" / "design-guidelines.md").read_text(encoding="utf-8")
    spec = (ROOT / "references" / "map-spec.md").read_text(encoding="utf-8")
    schema = (ROOT / "scripts" / "mapcore" / "resources" / "map-spec.schema.json").read_text(encoding="utf-8")
    assert "Atlas Studio Light" in skill
    assert "coarse density" in design
    assert "Explicit MapSpec values always win" in spec
    assert '"schema_version": {"const": "1.1"}' in schema
    assert "MapSpec 1.2" not in spec
