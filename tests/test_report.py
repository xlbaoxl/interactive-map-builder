from __future__ import annotations

from mapcore.report import sha256_file, validate_file_signature


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
