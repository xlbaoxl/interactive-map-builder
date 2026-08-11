from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

import pytest

from build_demo_site import build_demo_site


pytestmark = pytest.mark.browser
sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright


def test_product_homepage_visual_qa(tmp_path: Path) -> None:
    site = build_demo_site(tmp_path / "_site")
    output = Path("qa-screenshots")
    output.mkdir(exist_ok=True)

    handler = partial(SimpleHTTPRequestHandler, directory=str(site))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for locale in ("en-US", "zh-CN"):
                for width in (1440, 900):
                    page = browser.new_page(viewport={"width": width, "height": 900})
                    page.goto(f"{base_url}/{locale}/", wait_until="networkidle")
                    page.wait_for_selector(".hero-visual iframe")
                    page.wait_for_timeout(800)
                    page.screenshot(
                        path=output / f"homepage-{locale}-{width}.png",
                        full_page=True,
                    )
                    page.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
