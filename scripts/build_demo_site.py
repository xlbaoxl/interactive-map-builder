#!/usr/bin/env python
"""Build an Atlas product landing page and the two live map demos."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Sequence

from demo_projects import prepare_demo_project
from map_builder import build_map

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "assets" / "examples"
DEMOS = ("map-list", "multilayer")


def _landing_page() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Interactive Map Builder — spatial data to polished map products</title>
  <meta name="description" content="An Agent Skill that inspects spatial data, builds polished interactive maps, verifies them in a browser, and exports report-ready figures.">
  <style>
    :root{--ink:#172326;--muted:#66787a;--line:rgba(38,61,64,.14);--accent:#0f766e;--soft:#e4f4f1;--paper:#fbfcfc;--canvas:#e9eef2;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ink);background:var(--canvas)}
    *{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 12% 0,rgba(15,118,110,.13),transparent 28%),linear-gradient(180deg,#f8fbfa,#e9eef2 72%);line-height:1.5}a{color:inherit}.shell{width:min(1180px,calc(100% - 36px));margin:auto}.nav{display:flex;align-items:center;justify-content:space-between;padding:20px 0}.brand{display:flex;align-items:center;gap:10px;font-weight:800}.mark{display:grid;width:34px;height:34px;place-items:center;color:#fff;border-radius:11px;background:var(--accent);box-shadow:0 9px 24px rgba(15,118,110,.24)}.navlinks{display:flex;gap:18px;color:var(--muted);font-size:14px}.navlinks a{text-decoration:none}.hero{display:grid;grid-template-columns:1.05fr .95fr;align-items:center;min-height:560px;padding:64px 0 84px;gap:52px}.eyebrow{color:var(--accent);font-size:12px;font-weight:850;letter-spacing:.14em}.hero h1{max-width:760px;margin:15px 0 18px;font-size:clamp(42px,6vw,74px);line-height:1.02;letter-spacing:-.048em}.hero p{max-width:650px;margin:0;color:var(--muted);font-size:18px}.actions{display:flex;flex-wrap:wrap;margin-top:28px;gap:10px}.button{display:inline-flex;min-height:44px;align-items:center;padding:9px 16px;border:1px solid var(--line);border-radius:13px;background:#fff;text-decoration:none;font-size:14px;font-weight:760;box-shadow:0 8px 24px rgba(33,50,53,.08)}.button.primary{color:#fff;border-color:var(--accent);background:var(--accent)}.terminal{overflow:hidden;border:1px solid var(--line);border-radius:22px;background:#142123;box-shadow:0 28px 80px rgba(27,44,47,.22);transform:rotate(1.2deg)}.terminal-head{display:flex;padding:12px 15px;gap:6px;border-bottom:1px solid rgba(255,255,255,.08)}.terminal-head i{width:9px;height:9px;border-radius:50%;background:#6f8587}.terminal pre{min-height:290px;margin:0;padding:26px;color:#c9e9e5;white-space:pre-wrap;font:13px/1.75 ui-monospace,SFMono-Regular,Menlo,monospace}.terminal .accent{color:#78decf}.section{padding:86px 0}.section h2{max-width:760px;margin:0 0 12px;font-size:clamp(30px,4vw,48px);letter-spacing:-.035em}.lead{max-width:720px;margin:0 0 36px;color:var(--muted);font-size:17px}.demos{display:grid;grid-template-columns:1fr 1fr;gap:22px}.demo{position:relative;overflow:hidden;border:1px solid var(--line);border-radius:24px;background:#fff;box-shadow:0 18px 52px rgba(32,49,52,.12)}.demo-copy{padding:20px 21px 18px}.demo-copy span{color:var(--accent);font-size:11px;font-weight:850;letter-spacing:.1em}.demo-copy h3{margin:6px 0 6px;font-size:22px}.demo-copy p{margin:0;color:var(--muted);font-size:14px}.frame{position:relative;height:360px;border-top:1px solid var(--line);background:#dfe7e7}.frame iframe{width:160%;height:160%;border:0;transform:scale(.625);transform-origin:0 0;pointer-events:none}.demo-link{position:absolute;inset:0;z-index:2;border-radius:24px}.demo-link span{position:absolute;right:18px;bottom:18px;padding:8px 11px;color:#fff;border-radius:10px;background:rgba(18,35,37,.86);font-size:12px;font-weight:760}.flow{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}.step{position:relative;min-height:145px;padding:18px;border:1px solid var(--line);border-radius:18px;background:rgba(255,255,255,.78)}.step b{display:block;margin-bottom:8px;color:var(--accent);font-size:12px}.step h3{margin:0 0 6px;font-size:17px}.step p{margin:0;color:var(--muted);font-size:13px}.step:not(:last-child)::after{position:absolute;top:50%;right:-9px;z-index:3;width:16px;height:16px;content:"→";color:var(--accent);font-weight:900}.proof{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.proof article{padding:23px;border:1px solid var(--line);border-radius:20px;background:#fff}.proof strong{display:block;margin-bottom:8px;font-size:20px}.proof p{margin:0;color:var(--muted);font-size:14px}.cta{display:flex;align-items:center;justify-content:space-between;margin:60px 0 90px;padding:32px;border-radius:26px;color:#fff;background:#142b2d;box-shadow:0 24px 70px rgba(25,44,46,.22)}.cta h2{margin:0 0 5px;font-size:30px}.cta p{margin:0;color:#bcd0d1}.footer{display:flex;justify-content:space-between;padding:24px 0 38px;color:var(--muted);border-top:1px solid var(--line);font-size:13px}@media(max-width:900px){.hero{grid-template-columns:1fr;padding-top:36px}.terminal{transform:none}.demos{grid-template-columns:1fr}.flow{grid-template-columns:1fr 1fr}.step::after{display:none}.proof{grid-template-columns:1fr}.cta{display:grid;gap:18px}}@media(max-width:560px){.shell{width:min(100% - 22px,1180px)}.navlinks{display:none}.hero{min-height:auto;padding-bottom:56px}.hero h1{font-size:43px}.terminal pre{min-height:250px;padding:18px;font-size:11px}.flow{grid-template-columns:1fr}.frame{height:300px}.cta{padding:24px}.footer{display:grid;gap:8px}}
  </style>
</head>
<body>
  <nav class="shell nav"><div class="brand"><span class="mark">⌖</span>Interactive Map Builder</div><div class="navlinks"><a href="#demos">Demos</a><a href="#workflow">Workflow</a><a href="https://github.com/xlbaoxl/interactive-map-builder">GitHub ↗</a></div></nav>
  <main>
    <section class="shell hero">
      <div><div class="eyebrow">AN AGENT SKILL FOR POLISHED MAP DELIVERY</div><h1>Spatial data in.<br>Map product out.</h1><p>Turn Excel, CSV, GeoJSON, GeoPackage and Shapefiles into searchable interactive maps, slide-ready images and publication figures—with inspection, provenance and browser verification built in.</p><div class="actions"><a class="button primary" href="#demos">Explore live demos</a><a class="button" href="https://github.com/xlbaoxl/interactive-map-builder">View source on GitHub</a></div></div>
      <div class="terminal"><div class="terminal-head"><i></i><i></i><i></i></div><pre><span class="accent">$</span> Use $interactive-map-builder to inspect
  these spatial files and build a searchable map.

✓ 1,699 features inspected
✓ CRS normalized to EPSG:4326
✓ map-list recommended
✓ category + numeric filters configured
✓ browser interactions verified

<span class="accent">dist/</span>
  map.html
  map_slide_16x9.png
  map_paper.svg
  build_report.json</pre></div>
    </section>

    <section id="demos" class="section"><div class="shell"><div class="eyebrow">REAL DATA · REAL GENERATED HTML</div><h2>Two map products, not two screenshots.</h2><p class="lead">Both demos are built from fixed NYC Open Data snapshots by the same deterministic engine shipped in the repository.</p><div class="demos">
      <article class="demo"><div class="demo-copy"><span>MAP + LIST</span><h3>Lower Manhattan parcel explorer</h3><p>Search addresses, toggle land-use classes, filter year, floors and FAR, then inspect the selected parcel in a dedicated detail drawer.</p></div><div class="frame"><iframe title="Lower Manhattan parcel explorer" src="./map-list/" loading="lazy"></iframe></div><a class="demo-link" href="./map-list/"><span>Open live map ↗</span></a></article>
      <article class="demo"><div class="demo-copy"><span>MULTILAYER</span><h3>Manhattan mobility context</h3><p>Inspect boundary, bicycle routes and public facilities with independent visibility, cross-layer search and consistent map controls.</p></div><div class="frame"><iframe title="Manhattan multilayer explorer" src="./multilayer/" loading="lazy"></iframe></div><a class="demo-link" href="./multilayer/"><span>Open live map ↗</span></a></article>
    </div></div></section>

    <section id="workflow" class="section"><div class="shell"><div class="eyebrow">WHY IT IS MORE THAN A TEMPLATE</div><h2>One auditable path from intent to delivery.</h2><p class="lead">The Agent resolves ambiguity; the Python engine owns deterministic data handling and rendering.</p><div class="flow">
      <article class="step"><b>01</b><h3>Inspect</h3><p>Discover layers, geometry, CRS, field roles and blocking issues.</p></article>
      <article class="step"><b>02</b><h3>Confirm</h3><p>Ask one grouped round only for choices the data cannot answer.</p></article>
      <article class="step"><b>03</b><h3>Specify</h3><p>Write a reusable MapSpec instead of generating disposable code.</p></article>
      <article class="step"><b>04</b><h3>Build</h3><p>Create a single-file Leaflet app plus slide and paper figures.</p></article>
      <article class="step"><b>05</b><h3>Verify</h3><p>Run browser interactions, count checks, hashes and provenance reports.</p></article>
    </div></div></section>

    <section class="section"><div class="shell"><div class="proof"><article><strong>Portable by default</strong><p>UI code and business geometry are embedded in one HTML file. Only configured online tiles require a network.</p></article><article><strong>Research-ready</strong><p>The same visual encoding drives HTML, PNG, SVG and PDF outputs, with source notes and a build report.</p></article><article><strong>Agent-friendly</strong><p>A compact Skill workflow, strict MapSpec and behavioral evals keep Codex and other agents on the same path.</p></article></div><div class="cta"><div><h2>Bring your own spatial data.</h2><p>Clone the Skill, attach a file, and describe the map you need.</p></div><a class="button primary" href="https://github.com/xlbaoxl/interactive-map-builder">Start on GitHub ↗</a></div></div></section>
  </main>
  <footer class="shell footer"><span>Interactive Map Builder · MIT License</span><span>Built for Codex and other Agent Skills</span></footer>
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
    """Generate a clean Pages artifact without changing checked-in snapshots."""

    with tempfile.TemporaryDirectory(prefix="interactive-map-builder-pages-") as temp_value:
        temp_dir = Path(temp_value)
        staging = temp_dir / "_site"
        staging.mkdir()

        for demo in DEMOS:
            working_example = temp_dir / "examples" / demo
            spec_path = prepare_demo_project(
                demo,
                examples_root=EXAMPLES,
                destination=working_example,
            )
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            static = dict(spec.get("static", {}))
            static["enabled"] = False
            spec["static"] = static
            spec_path.write_text(
                json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            build_dir = temp_dir / "build" / demo
            build_map(spec_path, build_dir)
            target_dir = staging / demo
            target_dir.mkdir(parents=True)
            shutil.copy2(build_dir / "map.html", target_dir / "index.html")

        (staging / "index.html").write_text(_landing_page(), encoding="utf-8")
        (staging / ".nojekyll").touch()
        _replace_site(staging, output_dir)

    return output_dir.resolve()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the Atlas landing page and interactive map demos."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "_site",
        help="Directory to replace with the generated site (default: repository _site).",
    )
    args = parser.parse_args(argv)
    output = build_demo_site(args.output)
    print(f"Built Atlas demo site in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
