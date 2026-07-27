from __future__ import annotations

import io

from PIL import Image

from capture_readme_screenshots import _mock_tile_png


def test_mock_tiles_are_valid_coordinate_aware_pngs() -> None:
    payloads = []
    for x in range(4):
        for y in range(4):
            payload = _mock_tile_png(f"https://tiles.invalid/atlas/13/{x}/{y}.png")
            assert payload.startswith(b"\x89PNG\r\n\x1a\n")
            with Image.open(io.BytesIO(payload)) as image:
                assert image.size == (256, 256)
                assert image.mode == "RGB"
            payloads.append(payload)
    assert len(set(payloads)) > 8
