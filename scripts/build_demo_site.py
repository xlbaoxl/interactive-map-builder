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
    capabilities = "".join(
        (
            f'<article class="capability"><b>{index:02d}</b>'
            f"<h3>{html.escape(str(item[0]))}</h3>"
            f"<p>{html.escape(str(item[1]))}</p></article>"
        )
        for index, item in enumerate(messages["capabilities"], start=1)
    )
    journey = "".join(
        (
            f'<article class="journey-card"><span class="journey-index">{index:02d}</span>'
            f'<div class="journey-label">{html.escape(str(item[0]))}</div>'
            f"<h3>{html.escape(str(item[1]))}</h3>"
            f"<p>{html.escape(str(item[2]))}</p></article>"
        )
        for index, item in enumerate(messages["journey"], start=1)
    )
    steps = "".join(
        (
            f'<article class="step"><b>{index:02d}</b>'
            f"<h3>{html.escape(str(step[0]))}</h3>"
            f"<p>{html.escape(str(step[1]))}</p></article>"
        )
        for index, step in enumerate(messages["steps"], start=1)
    )
    hero_badges = "".join(
        f"<span>{html.escape(str(label))}</span>" for label in messages["hero_badges"]
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
    :root{{--ink:#172326;--ink-soft:#33484b;--muted:#66787a;--line:rgba(38,61,64,.14);--line-strong:rgba(38,61,64,.24);--accent:#0f766e;--accent-dark:#0a5f59;--accent-soft:#e4f3f0;--canvas:#e9eef2;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ink);background:var(--canvas)}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:radial-gradient(circle at 12% 0,rgba(15,118,110,.13),transparent 28%),linear-gradient(180deg,#f8fbfa,#e9eef2 72%);line-height:1.5}}a{{color:inherit}}.shell{{width:min(1180px,calc(100% - 36px));margin:auto}}.nav{{display:flex;align-items:center;justify-content:space-between;padding:20px 0}}.brand{{display:flex;align-items:center;gap:10px;font-weight:800}}.mark{{display:grid;width:34px;height:34px;place-items:center;color:#fff;border-radius:11px;background:var(--accent)}}.navlinks{{display:flex;gap:18px;color:var(--muted);font-size:14px}}.navlinks a{{text-decoration:none}}.navlinks a:hover{{color:var(--ink)}}.hero{{display:grid;grid-template-columns:.86fr 1.14fr;align-items:center;min-height:620px;padding:58px 0 82px;gap:50px}}.eyebrow{{color:var(--accent);font-size:12px;font-weight:850;letter-spacing:.14em}}.hero h1{{max-width:690px;margin:15px 0 18px;font-size:clamp(42px,5.7vw,70px);line-height:1.02;letter-spacing:-.048em}}.hero p{{max-width:620px;margin:0;color:var(--muted);font-size:18px}}.actions{{display:flex;flex-wrap:wrap;margin-top:28px;gap:10px}}.button{{display:inline-flex;min-height:44px;align-items:center;padding:9px 16px;border:1px solid var(--line);border-radius:13px;background:#fff;text-decoration:none;font-size:14px;font-weight:760;box-shadow:0 8px 24px rgba(33,50,53,.08)}}.button.primary{{color:#fff;border-color:var(--accent);background:var(--accent)}}.button:hover{{transform:translateY(-1px)}}.hero-visual{{position:relative;overflow:hidden;border:1px solid var(--line-strong);border-radius:24px;background:#dfe7e7;box-shadow:0 28px 80px rgba(27,44,47,.2)}}.hero-frame{{height:448px;overflow:hidden;background:#dfe7e7}}.hero-frame iframe{{width:142%;height:142%;border:0;transform:scale(.7043);transform-origin:0 0;pointer-events:none}}.hero-caption{{position:absolute;left:16px;right:16px;bottom:14px;display:flex;flex-wrap:wrap;gap:7px;pointer-events:none}}.hero-caption span{{padding:7px 10px;border:1px solid rgba(255,255,255,.4);border-radius:999px;color:#fff;background:rgba(18,35,37,.84);backdrop-filter:blur(8px);font-size:11px;font-weight:760}}.section{{padding:82px 0}}.section.compact{{padding-top:48px}}.section h2{{max-width:820px;margin:0 0 12px;font-size:clamp(30px,4vw,48px);letter-spacing:-.035em}}.lead{{max-width:800px;margin:0 0 36px;color:var(--muted);font-size:17px}}.capabilities{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.capability{{min-height:200px;padding:22px;border:1px solid var(--line);border-radius:20px;background:rgba(255,255,255,.86);box-shadow:0 12px 34px rgba(32,49,52,.06)}}.capability b{{color:var(--accent);font-size:11px;letter-spacing:.12em}}.capability h3{{margin:28px 0 8px;font-size:20px;letter-spacing:-.02em}}.capability p{{margin:0;color:var(--muted);font-size:14px}}.demos{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}.demo{{position:relative;overflow:hidden;border:1px solid var(--line);border-radius:24px;background:#fff;box-shadow:0 18px 52px rgba(32,49,52,.12)}}.demo-copy{{padding:22px}}.demo-copy b{{color:var(--accent);font-size:11px;letter-spacing:.1em}}.demo-copy h3{{margin:7px 0;font-size:22px}}.demo-copy p{{margin:0;color:var(--muted);font-size:14px}}.frame{{height:350px;border-top:1px solid var(--line);background:#dfe7e7}}.frame iframe{{width:160%;height:160%;border:0;transform:scale(.625);transform-origin:0 0;pointer-events:none}}.demo-link{{position:absolute;inset:0;z-index:2}}.demo-link span{{position:absolute;right:18px;bottom:18px;padding:8px 11px;color:#fff;border-radius:10px;background:rgba(18,35,37,.88);font-size:12px;font-weight:760}}.journey-track{{display:grid;grid-template-columns:repeat(3,1fr);gap:42px}}.journey-card{{position:relative;min-height:230px;padding:24px;border:1px solid var(--line);border-radius:22px;background:#fff;box-shadow:0 14px 38px rgba(32,49,52,.08)}}.journey-card:not(:last-child)::after{{content:"→";position:absolute;right:-32px;top:50%;width:22px;color:var(--accent);font-size:24px;font-weight:800;text-align:center;transform:translateY(-50%)}}.journey-index{{display:inline-grid;width:34px;height:34px;place-items:center;border-radius:11px;color:var(--accent-dark);background:var(--accent-soft);font-size:12px;font-weight:850}}.journey-label{{margin-top:26px;color:var(--accent);font-size:11px;font-weight:850;letter-spacing:.13em}}.journey-card h3{{margin:7px 0 8px;font-size:23px;letter-spacing:-.025em}}.journey-card p{{margin:0;color:var(--muted);font-size:14px}}.reliability{{display:grid;grid-template-columns:1fr .66fr;align-items:start;gap:24px}}.flow{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}.step{{min-height:160px;padding:18px;border:1px solid var(--line);border-radius:18px;background:rgba(255,255,255,.82)}}.step b{{color:var(--accent);font-size:12px}}.step h3{{margin:8px 0 6px}}.step p{{margin:0;color:var(--muted);font-size:13px}}.terminal{{padding:23px;border:1px solid rgba(255,255,255,.08);border-radius:20px;color:#c9e9e5;background:#142123;box-shadow:0 20px 60px rgba(27,44,47,.18);font:13px/1.9 ui-monospace,SFMono-Regular,Menlo,monospace}}.terminal b{{color:#78decf}}.workflow-wrap{{display:grid;gap:22px}}.cta{{display:flex;align-items:center;justify-content:space-between;padding:34px;border:1px solid var(--line);border-radius:24px;background:#172326;color:#fff;gap:28px}}.cta h2{{margin:0 0 8px;color:#fff;font-size:clamp(28px,4vw,42px)}}.cta p{{max-width:680px;margin:0;color:#b9cacb}}.cta .actions{{margin:0;flex:0 0 auto}}.cta .button:not(.primary){{color:var(--ink)}}.cta .button{{box-shadow:none}}.footer{{display:flex;justify-content:space-between;padding:28px 0 40px;color:var(--muted);border-top:1px solid var(--line);font-size:13px}}@media(max-width:980px){{.hero{{grid-template-columns:1fr;min-height:auto;padding-top:36px}}.hero-visual{{max-width:820px}}.capabilities{{grid-template-columns:1fr 1fr}}.reliability{{grid-template-columns:1fr}}.flow{{grid-template-columns:repeat(3,1fr)}}.cta{{align-items:flex-start;flex-direction:column}}}}@media(max-width:760px){{.demos{{grid-template-columns:1fr}}.journey-track{{grid-template-columns:1fr;gap:16px}}.journey-card:not(:last-child)::after{{content:"↓";right:24px;top:auto;bottom:-25px;transform:none}}.flow{{grid-template-columns:1fr 1fr}}.hero-frame{{height:390px}}}}@media(max-width:560px){{.shell{{width:min(100% - 22px,1180px)}}.navlinks a:not(:last-child){{display:none}}.hero{{padding-bottom:56px}}.capabilities,.flow{{grid-template-columns:1fr}}.frame{{height:300px}}.hero-frame{{height:330px}}.section{{padding:62px 0}}.cta{{padding:26px}}}}
  </style>
</head>
<body>
  <nav class="shell nav">
    <div class="brand"><span class="mark">⌖</span>Interactive Map Builder</div>
    <div class="navlinks">
      <a href="#capabilities">{values["nav_features"]}</a>
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
      <div class="hero-visual" aria-label="{values["hero_visual_label"]}">
        <div class="hero-frame"><iframe title="{values["multilayer_title"]}" src="{html.escape(multilayer_url)}" loading="eager"></iframe></div>
        <div class="hero-caption">{hero_badges}</div>
      </div>
    </section>

    <section id="capabilities" class="section compact">
      <div class="shell">
        <div class="eyebrow">{values["capabilities_eyebrow"]}</div>
        <h2>{values["capabilities_title"]}</h2>
        <p class="lead">{values["capabilities_body"]}</p>
        <div class="capabilities">{capabilities}</div>
      </div>
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

    <section id="journey" class="section">
      <div class="shell">
        <div class="eyebrow">{values["journey_eyebrow"]}</div>
        <h2>{values["journey_title"]}</h2>
        <p class="lead">{values["journey_body"]}</p>
        <div class="journey-track">{journey}</div>
      </div>
    </section>

    <section id="workflow" class="section">
      <div class="shell workflow-wrap">
        <div>
          <div class="eyebrow">{values["workflow_eyebrow"]}</div>
          <h2>{values["workflow_title"]}</h2>
          <p class="lead">{values["workflow_body"]}</p>
        </div>
        <div class="flow">{steps}</div>
        <div class="terminal"><b>$</b> interactive-map-builder inspect data.geojson<br>✓ CRS · fields · geometry<br><b>$</b> interactive-map-builder build --spec map_spec.json --out dist<br>✓ map.html · build report · delivery manifest<br><b>$</b> interactive-map-builder verify --dist dist<br>✓ browser-ready deliverable</div>
      </div>
    </section>

    <section class="section compact">
      <div class="shell cta">
        <div><h2>{values["cta_title"]}</h2><p>{values["cta_body"]}</p></div>
        <div class="actions">
          <a class="button primary" href="#demos">{values["cta_primary"]}</a>
          <a class="button" href="https://github.com/xlbaoxl/interactive-map-builder">{values["cta_secondary"]}</a>
        </div>
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
