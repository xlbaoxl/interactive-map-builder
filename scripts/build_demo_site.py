#!/usr/bin/env python
"""Build localized Pages landing pages and four live map demos."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Sequence

from demo_projects import prepare_demo_project
from map_builder import build_map
from mapcore.locales import SUPPORTED_LOCALES, catalog_value, load_catalog


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "assets" / "examples"
DEMOS = ("map-list", "multilayer")


def _landing_page(
    locale: str,
    *,
    demo_prefix: str,
    alternate_url: str,
) -> str:
    messages = catalog_value(load_catalog(locale), "landing")
    steps = "".join(
        (
            f'<article class="step"><b>{index:02d}</b>'
            f"<h3>{html.escape(str(step[0]))}</h3>"
            f"<p>{html.escape(str(step[1]))}</p></article>"
        )
        for index, step in enumerate(messages["steps"], start=1)
    )
    values = {
        key: html.escape(str(value))
        for key, value in messages.items()
        if not isinstance(value, list)
    }
    map_list_url = f"{demo_prefix}map-list/"
    multilayer_url = f"{demo_prefix}multilayer/"
    alternate_locale = "zh-CN" if locale == "en-US" else "en-US"
    return f"""<!doctype html>
<html lang="{html.escape(locale)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>{values["page_title"]}</title>
  <meta name="description" content="{values["description"]}">
  <style>
    :root{{--ink:#172326;--muted:#66787a;--line:rgba(38,61,64,.14);--accent:#0f766e;--canvas:#e9eef2;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ink);background:var(--canvas)}}*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 12% 0,rgba(15,118,110,.13),transparent 28%),linear-gradient(180deg,#f8fbfa,#e9eef2 72%);line-height:1.5}}a{{color:inherit}}.shell{{width:min(1180px,calc(100% - 36px));margin:auto}}.nav{{display:flex;align-items:center;justify-content:space-between;padding:20px 0}}.brand{{display:flex;align-items:center;gap:10px;font-weight:800}}.mark{{display:grid;width:34px;height:34px;place-items:center;color:#fff;border-radius:11px;background:var(--accent)}}.navlinks{{display:flex;gap:18px;color:var(--muted);font-size:14px}}.navlinks a{{text-decoration:none}}.hero{{display:grid;grid-template-columns:1.12fr .88fr;align-items:center;min-height:560px;padding:64px 0 84px;gap:52px}}.eyebrow{{color:var(--accent);font-size:12px;font-weight:850;letter-spacing:.14em}}.hero h1{{max-width:760px;margin:15px 0 18px;font-size:clamp(42px,6vw,74px);line-height:1.02;letter-spacing:-.048em}}.hero p{{max-width:650px;margin:0;color:var(--muted);font-size:18px}}.actions{{display:flex;flex-wrap:wrap;margin-top:28px;gap:10px}}.button{{display:inline-flex;min-height:44px;align-items:center;padding:9px 16px;border:1px solid var(--line);border-radius:13px;background:#fff;text-decoration:none;font-size:14px;font-weight:760;box-shadow:0 8px 24px rgba(33,50,53,.08)}}.button.primary{{color:#fff;border-color:var(--accent);background:var(--accent)}}.terminal{{padding:28px;border:1px solid rgba(255,255,255,.08);border-radius:22px;color:#c9e9e5;background:#142123;box-shadow:0 28px 80px rgba(27,44,47,.22);font:14px/1.9 ui-monospace,SFMono-Regular,Menlo,monospace;transform:rotate(1.2deg)}}.terminal b{{color:#78decf}}.section{{padding:82px 0}}.section h2{{max-width:760px;margin:0 0 12px;font-size:clamp(30px,4vw,48px);letter-spacing:-.035em}}.lead{{max-width:760px;margin:0 0 36px;color:var(--muted);font-size:17px}}.demos{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}.demo{{position:relative;overflow:hidden;border:1px solid var(--line);border-radius:24px;background:#fff;box-shadow:0 18px 52px rgba(32,49,52,.12)}}.demo-copy{{padding:22px}}.demo-copy b{{color:var(--accent);font-size:11px;letter-spacing:.1em}}.demo-copy h3{{margin:7px 0;font-size:22px}}.demo-copy p{{margin:0;color:var(--muted);font-size:14px}}.frame{{height:350px;border-top:1px solid var(--line);background:#dfe7e7}}.frame iframe{{width:160%;height:160%;border:0;transform:scale(.625);transform-origin:0 0;pointer-events:none}}.demo-link{{position:absolute;inset:0;z-index:2}}.demo-link span{{position:absolute;right:18px;bottom:18px;padding:8px 11px;color:#fff;border-radius:10px;background:rgba(18,35,37,.88);font-size:12px;font-weight:760}}.flow{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}.step{{min-height:150px;padding:18px;border:1px solid var(--line);border-radius:18px;background:rgba(255,255,255,.82)}}.step b{{color:var(--accent);font-size:12px}}.step h3{{margin:8px 0 6px}}.step p{{margin:0;color:var(--muted);font-size:13px}}.footer{{display:flex;justify-content:space-between;padding:28px 0 40px;color:var(--muted);border-top:1px solid var(--line);font-size:13px}}@media(max-width:900px){{.hero{{grid-template-columns:1fr;padding-top:36px}}.terminal{{transform:none}}.demos{{grid-template-columns:1fr}}.flow{{grid-template-columns:1fr 1fr}}}}@media(max-width:560px){{.shell{{width:min(100% - 22px,1180px)}}.navlinks a:not(:last-child){{display:none}}.hero{{min-height:auto;padding-bottom:56px}}.flow{{grid-template-columns:1fr}}.frame{{height:300px}}}}
  </style>
</head>
<body>
  <nav class="shell nav">
    <div class="brand"><span class="mark">⌖</span>Interactive Map Builder</div>
    <div class="navlinks">
      <a href="#demos">{values["nav_demos"]}</a>
      <a href="#workflow">{values["nav_workflow"]}</a>
      <a href="{html.escape(alternate_url)}" hreflang="{alternate_locale}">{values["language_name"]}</a>
      <a href="https://github.com/xlbaoxl/interactive-map-builder">GitHub ↗</a>
    </div>
  </nav>
  <main>
    <section class="shell hero">
      <div>
        <div class="eyebrow">{values["eyebrow"]}</div>
        <h1>{values["hero_title"]}</h1>
        <p>{values["hero_body"]}</p>
        <div class="actions">
          <a class="button primary" href="#demos">{values["explore"]}</a>
          <a class="button" href="https://github.com/xlbaoxl/interactive-map-builder">{values["source"]}</a>
        </div>
      </div>
      <div class="terminal"><b>$</b> interactive-map-builder inspect data.geojson<br>✓ CRS · fields · geometry<br><b>$</b> interactive-map-builder build map_spec.json<br>✓ map.html · PNG · SVG · PDF<br><b>$</b> interactive-map-builder verify --dist dist<br>✓ browser-ready deliverable</div>
    </section>
    <section id="demos" class="section">
      <div class="shell">
        <div class="eyebrow">{values["demo_eyebrow"]}</div>
        <h2>{values["demo_title"]}</h2>
        <p class="lead">{values["demo_body"]}</p>
        <div class="demos">
          <article class="demo">
            <div class="demo-copy"><b>MAP + LIST</b><h3>{values["map_list_title"]}</h3><p>{values["map_list_body"]}</p></div>
            <div class="frame"><iframe title="{values["map_list_title"]}" src="{html.escape(map_list_url)}" loading="lazy"></iframe></div>
            <a class="demo-link" href="{html.escape(map_list_url)}"><span>{values["open_map"]} ↗</span></a>
          </article>
          <article class="demo">
            <div class="demo-copy"><b>MULTILAYER</b><h3>{values["multilayer_title"]}</h3><p>{values["multilayer_body"]}</p></div>
            <div class="frame"><iframe title="{values["multilayer_title"]}" src="{html.escape(multilayer_url)}" loading="lazy"></iframe></div>
            <a class="demo-link" href="{html.escape(multilayer_url)}"><span>{values["open_map"]} ↗</span></a>
          </article>
        </div>
      </div>
    </section>
    <section id="workflow" class="section">
      <div class="shell">
        <div class="eyebrow">{values["workflow_eyebrow"]}</div>
        <h2>{values["workflow_title"]}</h2>
        <p class="lead">{values["workflow_body"]}</p>
        <div class="flow">{steps}</div>
      </div>
    </section>
  </main>
  <footer class="shell footer"><span>{values["footer"]}</span><span>MapSpec 1.1 · en-US / zh-CN</span></footer>
</body>
</html>
"""


def _replace_site(staging: Path, destination: Path) -> None:
    destination = destination.resolve()
    filesystem_root = Path(destination.anchor)
    if destination in {ROOT.resolve(), filesystem_root}:
        raise ValueError("Refusing to replace a repository or filesystem root.")
    if destination.exists():
        if not destination.is_dir():
            raise ValueError(f"Output path exists and is not a directory: {destination}")
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(staging, destination)


def build_demo_site(output_dir: Path = ROOT / "_site") -> Path:
    """Generate a clean localized Pages artifact without editing source examples."""

    with tempfile.TemporaryDirectory(prefix="imb-pages-") as temporary:
        workspace = Path(temporary)
        staging = workspace / "site"
        staging.mkdir()

        for locale in SUPPORTED_LOCALES:
            locale_root = staging / locale
            locale_root.mkdir()
            for demo in DEMOS:
                project = workspace / "projects" / locale / demo
                spec_path = prepare_demo_project(
                    demo,
                    examples_root=EXAMPLES,
                    destination=project,
                    locale=locale,
                )
                spec = json.loads(spec_path.read_text(encoding="utf-8"))
                spec["static"] = {"enabled": False}
                spec_path.write_text(
                    json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

                build_dir = workspace / "build" / locale / demo
                build_map(spec_path, build_dir)
                target_dir = locale_root / demo
                target_dir.mkdir(parents=True)
                shutil.copy2(build_dir / "map.html", target_dir / "index.html")

            alternate = "zh-CN" if locale == "en-US" else "en-US"
            (locale_root / "index.html").write_text(
                _landing_page(
                    locale,
                    demo_prefix="./",
                    alternate_url=f"../{alternate}/",
                ),
                encoding="utf-8",
            )

        (staging / "index.html").write_text(
            _landing_page(
                "en-US",
                demo_prefix="./en-US/",
                alternate_url="./zh-CN/",
            ),
            encoding="utf-8",
        )
        (staging / ".nojekyll").touch()
        _replace_site(staging, output_dir)

    return output_dir.resolve()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build localized landing pages and interactive map demos."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "_site",
        help="Directory to replace with the generated site.",
    )
    args = parser.parse_args(argv)
    output = build_demo_site(args.output)
    print(f"Built localized demo site in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
