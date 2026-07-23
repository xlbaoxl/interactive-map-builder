from __future__ import annotations

from pathlib import Path

from build_demo_site import build_demo_site


ROOT = Path(__file__).resolve().parents[1]
PAGES_URL = "https://xlbaoxl.github.io/interactive-map-builder"


def test_demo_site_builds_without_changing_source_specs(tmp_path: Path) -> None:
    spec_paths = [
        ROOT / "assets" / "examples" / demo / "map_spec.json"
        for demo in ("map-list", "multilayer")
    ]
    original_specs = {path: path.read_bytes() for path in spec_paths}

    site = build_demo_site(tmp_path / "_site")

    for demo in ("map-list", "multilayer"):
        html_path = site / demo / "index.html"
        assert html_path.is_file()
        assert html_path.stat().st_size > 10_000
        html = html_path.read_text(encoding="utf-8")
        assert "Leaflet" in html
        assert '"FeatureCollection"' in html
        assert "window.__interactiveMapBuilderQA" in html
        assert "dataset.imbReady" in html
        if demo == "map-list":
            assert "1 BROADWAY" in html
            assert '"search_behavior":"highlight"' in html

    assert (site / ".nojekyll").is_file()
    root_html = (site / "index.html").read_text(encoding="utf-8")
    assert "./map-list/" in root_html
    assert original_specs == {path: path.read_bytes() for path in spec_paths}


def test_readme_links_to_both_interactive_demos() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"{PAGES_URL}/map-list/" in readme
    assert f"{PAGES_URL}/multilayer/" in readme
    assert "正在搜索 Broadway" in readme


def test_pages_workflow_uses_official_actions_and_permissions() -> None:
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(
        encoding="utf-8"
    )
    for expected in (
        "workflow_dispatch:",
        "contents: read",
        "pages: write",
        "id-token: write",
        "actions/configure-pages@v5",
        "actions/upload-pages-artifact@v3",
        "actions/deploy-pages@v5",
        "python scripts/build_demo_site.py --output _site",
        "path: _site",
    ):
        assert expected in workflow
