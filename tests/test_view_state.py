from __future__ import annotations

import copy
import base64
import hashlib
import json
import math
import os
import re
from pathlib import Path

import pytest
from map_builder import build_map
from mapcore.render_html import _safe_json_script


def _project(root: Path, template: str = 'map-list', locale: str = 'en-US') -> Path:
    root.mkdir(parents=True, exist_ok=True)
    features = [{
        'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [116.4 + i * .002, 39.9]},
        'properties': {'id': 'p%02d' % i, 'name': 'Place %02d' % i,
                       'kind': 'A' if i % 2 == 0 else 'B', 'score': i, 'group': 'g%02d' % i}
    } for i in range(12)]
    (root / 'places.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'features': features}))
    layer = {'id': 'places', 'name': 'Places', 'source': {'path': 'places.geojson'},
             'id_field': 'id', 'label_field': 'name', 'search_fields': ['name'],
             'filter_fields': ['kind', 'score', 'group'], 'sort_fields': ['name', 'score'],
             'card_fields': ['kind', 'score'], 'source_note': 'Synthetic test data'}
    context = dict(layer, id='context', name='Context')
    context['filter_fields'] = []
    spec = {'schema_version': '1.1', 'template': template, 'locale': locale,
            'title': 'Portable view test', 'layers': [layer, context], 'basemaps': [],
            'static': {'enabled': False}}
    if template == 'map-list':
        spec['primary_layer'] = 'places'
    path = root / 'map_spec.json'
    path.write_text(json.dumps(spec))
    return path


def _payload(path: Path) -> dict:
    match = re.search(r'<script id="imb-data" type="application/json">(.*?)</script>',
                      path.read_text(encoding='utf-8'), re.S)
    assert match
    return json.loads(match[1])


def test_view_identity_binds_full_payload_and_survives_moving_html(tmp_path: Path) -> None:
    spec = _project(tmp_path / 'project')
    dist = tmp_path / 'dist'
    build_map(spec, dist)
    payload = _payload(dist / 'map.html')
    key = payload.pop('view_state_key')
    assert key == hashlib.sha256(_safe_json_script(payload).encode()).hexdigest()
    build_map(spec, tmp_path / 'another-dist')
    assert _payload(tmp_path / 'another-dist/map.html')['view_state_key'] == key
    source = spec.parent / 'places.geojson'
    changed = json.loads(source.read_text())
    changed['features'][0]['properties']['name'] = 'Changed with identical IDs and counts'
    source.write_text(json.dumps(changed))
    build_map(spec, dist)
    assert _payload(dist / 'map.html')['view_state_key'] != key


@pytest.fixture
def browser():
    playwright = pytest.importorskip('playwright.sync_api')
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


def _open(browser, path: Path, width: int = 1360):
    context = browser.new_context(viewport={'width': width, 'height': 900}, accept_downloads=True)
    context.route('https://tiles.example.test/**', lambda route: route.fulfill(
        content_type='image/png', body=base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC')))
    page = context.new_page()
    page.goto(path.resolve().as_uri())
    page.wait_for_function("window.__interactiveMapBuilderQA && window.__interactiveMapBuilderQA.ready")
    page.wait_for_timeout(350)
    assert page.evaluate('window.__interactiveMapBuilderQA.errors') == []
    return page


def _capture(page) -> dict:
    return page.evaluate('window.__interactiveMapBuilderQA.actions.captureViewState()')


def _restore(page, state) -> bool:
    return page.evaluate('(v) => window.__interactiveMapBuilderQA.actions.restoreViewState(v)',
                         json.dumps(state) if isinstance(state, dict) else state)


def _assert_state(actual: dict, expected: dict) -> None:
    actual = copy.deepcopy(actual)
    expected = copy.deepcopy(expected)
    def pixels(center, zoom):
        lat, lon = center
        scale = 256 * 2 ** zoom
        return ((lon + 180) / 360 * scale,
                (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * scale)
    # Leaflet rounds pixel origins during invalidateSize; compare in screen pixels,
    # not a fixed degree tolerance that becomes meaningless at world zoom.
    assert pixels(actual['map'].pop('center'), actual['map']['zoom']) == pytest.approx(
        pixels(expected['map'].pop('center'), expected['map']['zoom']), abs=1.0, rel=0)

    assert actual == expected


@pytest.mark.browser
@pytest.mark.parametrize('template', ['map-list', 'multilayer'])
@pytest.mark.parametrize('locale', ['en-US', 'zh-CN'])
def test_downloaded_view_opens_in_fresh_context_and_can_be_reshared(
    tmp_path: Path, browser, template: str, locale: str,
) -> None:
    spec = _project(tmp_path / 'project', template, locale)
    build_map(spec, tmp_path / 'dist')
    page = _open(browser, tmp_path / 'dist/map.html')
    if template == 'map-list':
        page.locator('.imb-chip[data-value="B"]').click()
        page.locator('#imb-sort').select_option('score')
        page.locator('#imb-sort-direction').click()
        page.evaluate('window.__interactiveMapBuilderQA.actions.setRange("score", 2, 10)')
        page.locator('.imb-filter-select').select_option('g04')
        page.locator('#imb-search').fill('Place')
        page.locator('#imb-list [data-feature-id="p04"]').click()
        assert page.evaluate('window.__interactiveMapBuilderQA.visibleRecordCount') == 1
    else:
        page.locator('#imb-feature-type-select').select_option('places')
        page.locator('input[data-layer-id="context"]').uncheck()
        page.locator('#imb-search').fill('Place 04')
        page.locator('#imb-list [data-feature-id="places::p04"]').click()
        page.locator('#imb-controls-collapse').click()
        assert page.evaluate('window.__interactiveMapBuilderQA.visibleRecordCount') == 1
    page.locator('#imb-collapse').click()
    if template == 'multilayer':
        page.evaluate('window.__interactiveMapBuilderQA.actions.toggleLegend(true)')
    else:
        page.locator('#imb-legend-toggle').click()
    page.wait_for_timeout(300)
    state = _capture(page)
    state['map']['center'] = [39.912, 116.419]
    state['map']['zoom'] = 13
    assert _restore(page, state)
    page.wait_for_timeout(400)
    _assert_state(_capture(page), state)
    # Local named views must not travel in the downloaded map.
    page.evaluate('window.__interactiveMapBuilderQA.actions.saveView("Private bookmark", [39.9,116.4], 12)')
    page.locator('#imb-share-view').click()
    assert page.locator('#imb-share-privacy').is_visible()
    assert ('全部' if locale == 'zh-CN' else 'ALL') in page.locator('#imb-share-privacy').inner_text()
    with page.expect_download() as download:
        page.locator('#imb-download-view-html').click()
    target = tmp_path / 'renamed-map.html'
    download.value.save_as(target)
    assert _payload(target)['layers'][0]['count'] == 12  # Filtering is not redaction.
    assert 'Private bookmark' not in target.read_text(encoding='utf-8')
    page.context.close()
    restored = _open(browser, target)
    assert restored.evaluate('window.__interactiveMapBuilderQA.viewState.restored')
    _assert_state(_capture(restored), state)
    assert restored.evaluate('window.__interactiveMapBuilderQA.visibleRecordCount') == 1
    assert restored.locator('#imb-share-dialog').is_visible() is False
    assert restored.evaluate('window.__interactiveMapBuilderQA.savedViews.count') == 0
    # Export again without accumulating runtime DOM, widgets or state script tags.
    second = tmp_path / 'second-copy.html'
    second.write_text(restored.evaluate('window.__interactiveMapBuilderQA.actions.exportViewHTML()'), encoding='utf-8')
    again = _open(browser, second)
    _assert_state(_capture(again), state)
    assert again.locator('#imb-view-state').count() == 1
    assert again.locator('#imb-share-view').count() == 1
    assert again.locator('.leaflet-map-pane').count() == 1


@pytest.mark.browser
@pytest.mark.parametrize('template', ['map-list', 'multilayer'])
def test_invalid_and_wrong_map_views_leave_state_unchanged(tmp_path: Path, browser, template: str) -> None:
    spec = _project(tmp_path / 'project', template)
    build_map(spec, tmp_path / 'dist')
    page = _open(browser, tmp_path / 'dist/map.html')
    initial = _capture(page)
    bad = []
    for path, value in [
        (('version',), 999), (('map_key',), 'wrong-map'), (('extra',), True),
        (('map', 'zoom'), '13'), (('map', 'zoom'), 999), (('map', 'center'), [91, 0]),
        (('map', 'center'), [0, None]), (('map', 'basemap'), 10),
        (('panels', 'sidebar'), 'false'), (('view', 'selected_id'), 'missing'),
        (('view', 'search'), None), (('__proto__',), {'polluted': True}),
    ]:
        state = copy.deepcopy(initial)
        parent = state
        for part in path[:-1]: parent = parent[part]
        parent[path[-1]] = value
        bad.append(state)
    state = copy.deepcopy(initial)
    if template == 'map-list':
        state['view']['filters'][0]['values'] = ['UNKNOWN']
    else:
        state['view']['active_layer'] = 'places'
        state['view']['layers'][0]['visible'] = False
    bad.append(state)
    bad += ['not json', 'null', '[1,2,3]', ' ' * (1024 * 1024 + 1)]
    for value in bad:
        assert _restore(page, value) is False
        _assert_state(_capture(page), initial)
    assert page.evaluate('Object.prototype.polluted === undefined')
    assert page.evaluate('window.__interactiveMapBuilderQA.errors') == []


@pytest.mark.browser
def test_json_import_zero_matches_and_script_text_are_safe(tmp_path: Path, browser) -> None:
    spec = _project(tmp_path / 'project')
    build_map(spec, tmp_path / 'dist')
    page = _open(browser, tmp_path / 'dist/map.html')
    state = _capture(page)
    state['view']['search'] = '</script><script>window.viewAttack=true</script> 中文'
    state['view']['filters'][0]['values'] = []
    state['map']['zoom'] = 0
    page.locator('#imb-share-view').click()
    page.locator('#imb-import-view-file').set_input_files({
        'name': 'view.json', 'mimeType': 'application/json', 'buffer': json.dumps(state).encode(),
    })
    page.wait_for_function('window.__interactiveMapBuilderQA.viewState.restored')
    _assert_state(_capture(page), state)
    assert page.evaluate('window.__interactiveMapBuilderQA.visibleRecordCount') == 0
    with page.expect_download() as download:
        page.locator('#imb-export-view-json').click()
    target = tmp_path / 'view.json'
    download.value.save_as(target)
    _assert_state(json.loads(target.read_text()), state)
    target_html = tmp_path / 'safe-copy.html'
    target_html.write_text(page.evaluate('window.__interactiveMapBuilderQA.actions.exportViewHTML()'), encoding='utf-8')
    other = _open(browser, target_html)
    assert other.evaluate('window.viewAttack === undefined')
    assert other.evaluate('window.__interactiveMapBuilderQA.visibleRecordCount') == 0
    _assert_state(_capture(other), state)
    other.locator('#imb-share-view').click()
    other.locator('#imb-import-view-file').set_input_files({
        'name': 'huge.json', 'mimeType': 'application/json', 'buffer': b' ' * (1024 * 1024 + 1),
    })
    assert '1 MiB' in other.locator('#imb-share-status').inner_text()
    _assert_state(_capture(other), state)


@pytest.mark.browser
@pytest.mark.parametrize('template', ['map-list', 'multilayer'])
def test_share_dialog_keyboard_and_narrow_layout(tmp_path: Path, browser, template: str) -> None:
    build_map(_project(tmp_path / 'project', template, 'zh-CN'), tmp_path / 'dist')
    page = _open(browser, tmp_path / 'dist/map.html', width=390)
    button = page.locator('#imb-share-view')
    assert button.is_visible()
    button_box = button.bounding_box()
    assert button_box and button_box['x'] >= 0 and button_box['x'] + button_box['width'] <= 390
    button.focus()
    page.keyboard.press('Enter')
    assert page.locator('#imb-share-dialog').is_visible()
    box = page.locator('#imb-share-dialog').bounding_box()
    assert box and box['x'] >= 0 and box['x'] + box['width'] <= 390
    assert page.locator('#imb-download-view-html').is_visible()
    artifacts = os.environ.get('IMB_BROWSER_ARTIFACTS')
    if artifacts:
        destination = Path(artifacts)
        destination.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(destination / (template + '-share-mobile.png')))
    page.keyboard.press('Escape')
    assert page.locator('#imb-share-dialog').is_visible() is False
    assert page.evaluate('document.activeElement.id') == 'imb-share-view'


@pytest.mark.browser
def test_restore_clears_previous_selection_and_keeps_numeric_order(tmp_path: Path, browser) -> None:
    build_map(_project(tmp_path / 'project'), tmp_path / 'dist')
    page = _open(browser, tmp_path / 'dist/map.html')
    initial = _capture(page)
    page.locator('#imb-list [data-feature-id="p04"]').click()
    assert _restore(page, initial)
    assert page.evaluate('window.__interactiveMapBuilderQA.selectedId') == ''
    assert page.locator('#imb-detail').is_visible() is False
    state = copy.deepcopy(initial)
    state['view']['sort_field'] = 'score'
    state['view']['ascending'] = False
    state['view']['filters'][0]['values'] = ['A']
    state['view']['filters'][1].update(low=2, high=10)
    assert _restore(page, state)
    assert page.locator('#imb-list [data-feature-id]').evaluate_all(
        '(nodes) => nodes.map(n => n.dataset.featureId)') == ['p10', 'p08', 'p06', 'p04', 'p02']
    snapshot = tmp_path / 'sorted.html'
    snapshot.write_text(page.evaluate('window.__interactiveMapBuilderQA.actions.exportViewHTML()'), encoding='utf-8')
    other = _open(browser, snapshot)
    assert other.locator('#imb-list [data-feature-id]').evaluate_all(
        '(nodes) => nodes.map(n => n.dataset.featureId)') == ['p10', 'p08', 'p06', 'p04', 'p02']


@pytest.mark.browser
def test_all_layers_hidden_and_invalid_embedded_state(tmp_path: Path, browser) -> None:
    build_map(_project(tmp_path / 'project', 'multilayer'), tmp_path / 'dist')
    page = _open(browser, tmp_path / 'dist/map.html')
    initial = _capture(page)
    hidden = copy.deepcopy(initial)
    for layer in hidden['view']['layers']: layer['visible'] = False
    assert _restore(page, hidden)
    target = tmp_path / 'hidden.html'
    target.write_text(page.evaluate('window.__interactiveMapBuilderQA.actions.exportViewHTML()'), encoding='utf-8')
    other = _open(browser, target)
    _assert_state(_capture(other), hidden)
    assert other.locator('#imb-layer-options input:checked').count() == 0
    bad = tmp_path / 'bad.html'
    # Alter the embedded state only, not the payload or executable application.
    bad.write_text(re.sub(r'(<script id="imb-view-state" type="application/json">).*?(</script>)',
                         r'\g<1>{"version":999}\g<2>', target.read_text(encoding='utf-8'), flags=re.S),
                   encoding='utf-8')
    rejected = _open(browser, bad)
    _assert_state(_capture(rejected), initial)
    assert rejected.locator('#imb-share-dialog').is_visible()
    assert rejected.evaluate('window.__interactiveMapBuilderQA.viewState.restored') is False


@pytest.mark.browser
def test_basemap_index_restores_without_new_urls(tmp_path: Path, browser) -> None:
    spec_path = _project(tmp_path / 'project')
    spec = json.loads(spec_path.read_text())
    tile = 'https://tiles.example.test/{z}/{x}/{y}.png'
    spec['basemaps'] = [
        {'name': 'First', 'url': tile, 'attribution': 'Test tile'},
        {'name': 'Second', 'url': tile, 'attribution': 'Test tile'},
    ]
    spec_path.write_text(json.dumps(spec))
    build_map(spec_path, tmp_path / 'dist')
    page = _open(browser, tmp_path / 'dist/map.html')
    state = _capture(page)
    state['map']['basemap'] = 1
    assert _restore(page, state)
    assert page.locator('.imb-map-tool-select').input_value() == '1'
    target = tmp_path / 'basemap.html'
    target.write_text(page.evaluate('window.__interactiveMapBuilderQA.actions.exportViewHTML()'), encoding='utf-8')
    other = _open(browser, target)
    assert _capture(other)['map']['basemap'] == 1
    assert other.locator('.imb-map-tool-select').input_value() == '1'
