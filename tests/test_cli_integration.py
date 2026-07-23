from __future__ import annotations

import json
from pathlib import Path

from map_builder import build_map, verify_dist


ROOT = Path(__file__).resolve().parents[1]


def test_map_list_build_and_verify_complete_bundle(tmp_path):
    spec = ROOT / "assets" / "examples" / "map-list" / "map_spec.json"
    result = build_map(spec, tmp_path)
    assert result["report"]["status"] == "pass"
    assert result["report"]["checks"]["primary_count"] == 3

    expected = {
        "map.html",
        "map_slide_16x9.png",
        "map_paper.png",
        "map_paper.svg",
        "map_paper.pdf",
        "map_spec.json",
        "build_report.json",
    }
    assert expected == {path.name for path in tmp_path.iterdir()}

    verification = verify_dist(tmp_path)
    assert verification["status"] == "pass"
    report = json.loads((tmp_path / "build_report.json").read_text(encoding="utf-8"))
    assert report["checks"]["output_counts_consistent"] is True
    assert report["checks"]["html_qa"]["leaflet_embedded"] is True
