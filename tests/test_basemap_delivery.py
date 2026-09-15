"""Deterministic offline basemap tests; live-provider acceptance is separate."""
from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path

import pytest
from map_builder import build_map, main
from mapcore.basemaps import default_basemaps, migrate_legacy_basemaps, basemap_warnings
from mapcore.spec import validate_spec, SpecError
from test_view_state import _project, _payload

ROOT = Path(__file__).resolve().parents[1]
NETWORK = re.compile(r'^https?://')
STYLES = re.compile(r'^https://tiles\.openfreemap\.org/styles/')
LEGACY = [
 {'name': 'CARTO Positron', 'url': 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png', 'visible': True, 'attribution': 'CARTO'},
 {'name': 'OpenStreetMap Standard', 'url': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', 'visible': False, 'attribution': 'OSM'},
]
STYLE = {'version': 8, 'sources': {'demo': {'type': 'geojson', 'data': {
 'type':'FeatureCollection', 'features':[{'type':'Feature','properties':{},'geometry':{
 'type':'LineString','coordinates':[[116.38,39.89],[116.44,39.92]]}}]}}},
 'layers': [{'id':'background','type':'background','paint':{'background-color':'#eeeeee'}},
 {'id':'street','type':'line','source':'demo','paint':{'line-color':'#777777','line-width':3}}]}


def _build(tmp, template='map-list', maps=None):
 path = _project(tmp/'project',template, 'zh-CN')
 spec=json.loads(path.read_text());spec['basemaps']=default_basemaps() if maps is None else maps
 path.write_text(json.dumps(spec));build_map(path,tmp/'dist')
 return tmp/'dist/map.html'


def test_migration_is_explicit_and_preserves_custom_and_business_data(tmp_path):
 path=_project(tmp_path/'project');spec=json.loads(path.read_text())
 custom={'name':'Authorized', 'url':LEGACY[0]['url']+'?key=owned', 'attribution':'Owner'}
 spec['basemaps']=copy.deepcopy(LEGACY)+[custom];before=copy.deepcopy(spec)
 result,changes=migrate_legacy_basemaps(spec)
 assert spec==before and result['layers']==spec['layers']
 assert len(changes)==2 and result['basemaps'][2]==custom
 assert [x.get('visible',False) for x in result['basemaps']]==[True,False,False]
 assert result['schema_version']=='1.2'
 assert migrate_legacy_basemaps(result)==(result,[])
 assert migrate_legacy_basemaps({'basemaps':[]})==({'basemaps':[]},[])


def test_migration_cli_preserves_input_and_rebases_relative_sources(tmp_path):
 path=_project(tmp_path/'project');spec=json.loads(path.read_text());spec['basemaps']=LEGACY
 path.write_text(json.dumps(spec));before=path.read_bytes();out=tmp_path/'other/new.json'
 assert main(['migrate-basemaps','--spec',str(path),'--out',str(out)])==0
 new=json.loads(out.read_text())
 assert path.read_bytes()==before
 assert (out.parent/new['layers'][0]['source']['path']).resolve()==(path.parent/'places.geojson').resolve()
 assert main(['migrate-basemaps','--spec',str(path),'--out',str(out)])==2


def test_schema_upgrade_and_renderer_is_optional(tmp_path):
 path=_project(tmp_path/'project');spec=json.loads(path.read_text())
 assert validate_spec(spec)['schema_version']=='1.2' and spec['schema_version']=='1.1'
 spec['basemaps']=default_basemaps();spec['basemaps'][0]['kind']='unknown'
 with pytest.raises(SpecError,match='kind'):validate_spec(spec)
 none=_build(tmp_path/'none',maps=[]);vector=_build(tmp_path/'vector')
 assert 'maplibregl=' not in none.read_text()
 assert 'maplibre-gl-js' in vector.read_text() or 'maplibregl=' in vector.read_text()
 assert '<script src=' not in vector.read_text()
 assert _payload(vector)['spec']['basemaps'][0]['kind']=='vector'
 report=json.loads((vector.parent/'build_report.json').read_text())
 assert report['basemap_live_check']=='not_performed'
 assert report['checks']['html_qa']['vector_renderer_embedded'] is True
 assert len(basemap_warnings({'basemaps':LEGACY}))==2


@pytest.fixture
def browser():
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  kwargs={'headless':True, 'args':['--enable-unsafe-swiftshader']}
  if os.environ.get('IMB_CHROMIUM'):kwargs['executable_path']=os.environ['IMB_CHROMIUM']
  b=p.chromium.launch(**kwargs);yield b;b.close()


def _open(page,path):
 if os.environ.get('IMB_INLINE_TEST')=='1':page.set_content(path.read_text(),wait_until='domcontentloaded')
 else:page.goto(path.resolve().as_uri(),wait_until='domcontentloaded')
 page.wait_for_function('window.__interactiveMapBuilderQA && window.__interactiveMapBuilderQA.ready')


@pytest.mark.browser
@pytest.mark.parametrize('template',['map-list','multilayer'])
def test_vector_render_switch_share_and_reopen(tmp_path,browser,template):
 path=_build(tmp_path,template)
 context=browser.new_context(viewport={'width':1360,'height':850})
 unexpected=[];intercepted=[]
 context.route(NETWORK,lambda route:(unexpected.append(route.request.url),route.abort()))
 def style(route):
  intercepted.append(route.request.url)
  route.fulfill(json=STYLE,headers={'Access-Control-Allow-Origin':'*'})
 context.route(STYLES,style)
 page=context.new_page();_open(page,path)
 page.wait_for_function('window.__interactiveMapBuilderQA.basemapStatus === "ready"')
 assert page.locator('.maplibregl-canvas').count()==1
 assert page.evaluate('window.__interactiveMapBuilderQA.basemapSummary().rendered_features')>0
 for index in ['1','-1','0','1']:
  page.evaluate('(x)=>window.__interactiveMapBuilderQA.actions.setBasemap(x)',index)
 page.wait_for_function('window.__interactiveMapBuilderQA.basemapStatus === "ready"')
 assert page.locator('.maplibregl-canvas').count()==1
 state=page.evaluate('window.__interactiveMapBuilderQA.actions.captureViewState()')
 html=page.evaluate('window.__interactiveMapBuilderQA.actions.exportViewHTML()')
 exported=tmp_path/'renamed.html';exported.write_text(html)
 other=context.new_page();_open(other,exported)
 other.wait_for_function('window.__interactiveMapBuilderQA.basemapStatus === "ready"')
 assert other.evaluate('window.__interactiveMapBuilderQA.actions.captureViewState().map.basemap')==1
 assert other.locator('.maplibregl-canvas').count()==1
 assert other.evaluate('window.__interactiveMapBuilderQA.errors')==[]
 assert intercepted and not unexpected
 assert other.locator('#imb-map-attribution a').count()==3
 other.set_viewport_size({'width':390,'height':844})
 other.wait_for_timeout(500)
 assert other.locator('#imb-map-attribution a').evaluate_all('''elements => elements.every(el => {
   const r = el.getClientRects()[0];
   return r && r.width > 0 && r.top >= 0 && r.bottom <= innerHeight &&
     document.elementFromPoint(r.x + r.width/2, r.y + r.height/2) === el;
 })''')
 context.close()


@pytest.mark.browser
@pytest.mark.parametrize('code',['key','local'])
def test_legacy_provider_not_requested_for_local_html(tmp_path,browser,code):
 path=_build(tmp_path,maps=[LEGACY[0 if code=='key' else 1]])
 context=browser.new_context();requests=[]
 context.route(NETWORK,lambda route:(requests.append(route.request.url),route.abort()))
 page=context.new_page();_open(page,path)
 page.wait_for_function('window.__interactiveMapBuilderQA.basemapFallback === true')
 assert requests==[]
 assert page.evaluate('window.__interactiveMapBuilderQA.basemapDiagnostics.code')==code
 assert page.evaluate('window.__interactiveMapBuilderQA.ready')
 context.close()


@pytest.mark.browser
def test_vector_failure_keeps_business_controls_and_can_retry(tmp_path,browser):
 path=_build(tmp_path)
 context=browser.new_context();denied=[]
 def reject(route):
  denied.append(route.request.url)
  route.fulfill(status=403,body='Denied')
 context.route(NETWORK,reject)
 page=context.new_page();_open(page,path)
 page.wait_for_function('window.__interactiveMapBuilderQA.basemapFallback === true')
 assert page.locator('.maplibregl-canvas').count()==0
 assert page.evaluate('window.__interactiveMapBuilderQA.errors')==[]
 assert denied, 'The denied-provider test must actually intercept a request'
 assert page.evaluate('window.__interactiveMapBuilderQA.basemapDiagnostics.code')=='network'
 context.unroute(NETWORK);context.route(NETWORK,lambda r:r.abort())
 context.route(STYLES,lambda r:r.fulfill(json=STYLE))
 page.evaluate('window.__interactiveMapBuilderQA.actions.setBasemap("0")')
 page.wait_for_function('window.__interactiveMapBuilderQA.basemapStatus === "ready"')
 page.locator('#imb-search').fill('Place 01')
 page.wait_for_timeout(400)
 assert page.evaluate('window.__interactiveMapBuilderQA.actions.captureViewState().view.search')=='Place 01'
 page.evaluate('window.__interactiveMapBuilderQA.actions.setBasemap("none")')
 assert page.locator('.maplibregl-canvas').count()==0
 context.close()


@pytest.mark.browser
def test_webgl_unavailable_does_not_break_subsequent_leaflet_events(tmp_path, browser):
    path = _build(tmp_path)
    context = browser.new_context()
    context.add_init_script("""(() => {
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function(kind, ...args) {
        if (String(kind).includes('webgl')) return null;
        return original.call(this, kind, ...args);
      };
    })()""")
    page = context.new_page()
    failures = []
    page.on('pageerror', lambda error: failures.append(str(error)))
    _open(page, path)
    page.wait_for_function('window.__interactiveMapBuilderQA.basemapFallback === true')
    assert page.evaluate('window.__interactiveMapBuilderQA.basemapDiagnostics.code') == 'renderer'
    assert page.locator('.maplibregl-canvas').count() == 0
    state = page.evaluate('window.__interactiveMapBuilderQA.actions.captureViewState()')
    state['map']['zoom'] += 1
    page.evaluate('(state) => window.__interactiveMapBuilderQA.actions.restoreViewState(state)', state)
    page.locator('#imb-search').fill('Place 01')
    page.wait_for_timeout(400)
    assert page.evaluate('window.__interactiveMapBuilderQA.errors') == []
    assert failures == []
    context.close()
