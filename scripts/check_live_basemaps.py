#!/usr/bin/env python
"""Opt-in live basemap acceptance using synthetic data, never a user's upload.

Runs actual file:// Chromium, not mocked responses. A failure fails the command.
Regular unit/browser tests remain independent of public provider availability.
"""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from map_builder import build_map
from mapcore.basemaps import default_basemaps
from mapcore.spec import current_schema_version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = args.out.resolve(); root.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--enable-unsafe-swiftshader'])
        try:
            for template, locale in [('map-list', 'en-US'), ('multilayer', 'zh-CN')]:
                directory = root / template; directory.mkdir(exist_ok=True)
                features = [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-73.96+i*.002, 40.72]},
                             'properties': {'id': str(i), 'name': 'Synthetic site '+str(i), 'group': 'demo'}} for i in range(3)]
                (directory/'sites.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features}))
                layer = {'id':'sites','name':'Synthetic sites', 'source':{'path':'sites.geojson'},
                         'id_field':'id','label_field':'name','search_fields':['name'], 'source_note':'Synthetic QA data'}
                spec = {'schema_version':current_schema_version(), 'title':'Live basemap acceptance',
                        'locale':locale,'template':template, 'layers':[layer], 'basemaps':default_basemaps()}
                if template=='map-list':spec['primary_layer']='sites'
                path=directory/'spec.json';path.write_text(json.dumps(spec))
                build_map(path,directory/'dist')
                context=browser.new_context(viewport={'width':1360,'height':850})
                page=context.new_page(); statuses=[]; failures=[]; fatal=[]
                page.on('response',lambda r: statuses.append({'status':r.status,'host':r.url.split('/')[2]}) if r.url.startswith('https://') else None)
                page.on('requestfailed',lambda r:failures.append({'failure':r.failure,'host':r.url.split('/')[2]}) if r.url.startswith('https://') else None)
                page.on('pageerror',lambda e:fatal.append(str(e)[:200]))
                start=time.monotonic()
                try:
                    page.goto((directory/'dist/map.html').as_uri(),wait_until='domcontentloaded')
                    page.wait_for_function('window.__interactiveMapBuilderQA && window.__interactiveMapBuilderQA.ready')
                    for index in (0,1):
                        page.evaluate('(i)=>window.__interactiveMapBuilderQA.actions.setBasemap(String(i))',index)
                        page.wait_for_function('window.__interactiveMapBuilderQA.basemapStatus === "ready"',timeout=30000)
                        summary=page.evaluate('window.__interactiveMapBuilderQA.basemapSummary()')
                        assert summary and summary['loaded'] and summary['rendered_features']>20, summary
                        assert page.locator('.maplibregl-canvas').count()==1
                        page.screenshot(path=str(directory/f'live-{index}.png'))
                        results.append({'template':template,'style':spec['basemaps'][index]['name'],
                                        'protocol':page.evaluate('location.protocol'),'summary':summary})
                    # Download through the real control, then reopen in a clean context.
                    page.locator('#imb-share-view').click()
                    with page.expect_download() as download:
                        page.locator('#imb-download-view-html').click()
                    target=directory/'renamed-snapshot.html';download.value.save_as(target)
                    fresh=browser.new_context(viewport={'width':390,'height':844})
                    reopened=fresh.new_page();reopened.goto(target.as_uri(),wait_until='domcontentloaded')
                    reopened.wait_for_function('window.__interactiveMapBuilderQA.basemapStatus === "ready"',timeout=30000)
                    assert reopened.evaluate('window.__interactiveMapBuilderQA.actions.captureViewState().map.basemap')==1
                    assert reopened.evaluate('window.__interactiveMapBuilderQA.basemapSummary().rendered_features')>20
                    assert reopened.evaluate('window.__interactiveMapBuilderQA.errors')==[]
                    reopened.screenshot(path=str(directory/'reopened-mobile.png'))
                    fresh.close()
                    assert not fatal, fatal
                    assert any(s['host']=='tiles.openfreemap.org' and s['status']==200 for s in statuses)
                    assert not any(s['status']>=400 for s in statuses), statuses
                finally:
                    (directory/'network.json').write_text(json.dumps({'responses':statuses,'failures':failures,'page_errors':fatal,
                                                                      'elapsed_seconds':round(time.monotonic()-start,2)},indent=2))
                    page.screenshot(path=str(directory/'final-state.png'))
                    context.close()
        finally:
            browser.close()
            (root/'acceptance.json').write_text(json.dumps(results,indent=2))
    assert len(results)==4
    print(json.dumps({'status':'pass','cases':results},indent=2))

if __name__=='__main__':main()
