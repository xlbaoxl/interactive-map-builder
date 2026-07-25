from __future__ import annotations

from mapcore.report import sha256_file, validate_file_signature, write_usage_guide


def test_signatures_and_hashes(tmp_path):
    pdf = tmp_path / "map.pdf"
    pdf.write_bytes(b"%PDF-1.7\nexample")
    assert validate_file_signature(pdf)
    assert len(sha256_file(pdf)) == 64

    bad = tmp_path / "map.png"
    bad.write_bytes(b"not a png")
    assert not validate_file_signature(bad)


def test_json_signature(tmp_path):
    report = tmp_path / "report.json"
    report.write_text('{"ok": true}', encoding="utf-8")
    assert validate_file_signature(report)


def test_usage_guide_is_written_in_selected_locale(tmp_path):
    for locale, expected in (
        ("en-US", "Open the interactive map"),
        ("zh-CN", "打开交互地图"),
    ):
        output = tmp_path / locale / "README_USAGE.md"
        write_usage_guide(
            output,
            title="Example",
            html_name="map.html",
            figure_names=["map_paper.svg"],
            basemaps=[],
            portable_bundle=True,
            locale=locale,
        )
        text = output.read_text(encoding="utf-8")
        assert expected in text
        assert "map_paper.svg" in text
