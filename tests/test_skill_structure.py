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
