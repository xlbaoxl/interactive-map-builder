from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HAN = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
ALLOWED_FILES = {
    ROOT / "README.md",
    ROOT / "CHANGELOG.md",
    ROOT / "scripts" / "mapcore" / "resources" / "locales" / "zh-CN.json",
}
ALLOWED_DIRECTORIES = {
    ROOT / "assets" / "examples",
    ROOT / "evals",
    ROOT / "tests",
}
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".j2",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".yaml",
    ".yml",
}


def _is_allowed(path: Path) -> bool:
    if path in ALLOWED_FILES:
        return True
    return any(directory in path.parents for directory in ALLOWED_DIRECTORIES)


def test_han_characters_are_confined_to_approved_content() -> None:
    violations = []
    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or path.suffix.lower() not in TEXT_SUFFIXES
            or ".git" in path.parts
            or _is_allowed(path)
        ):
            continue
        text = path.read_text(encoding="utf-8")
        match = HAN.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            violations.append(f"{path.relative_to(ROOT)}:{line}")
    assert violations == []
