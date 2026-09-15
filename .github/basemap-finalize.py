from pathlib import Path

def replace(path, old, new, count=1):
    p=Path(path);text=p.read_text(encoding='utf-8')
    if new in text: return
    assert text.count(old)==count,(path,old[:70],text.count(old),count)
    p.write_text(text.replace(old,new),encoding='utf-8')

replace('scripts/mapcore/resources/templates/basemap-layer.js',
    'gl.on("idle", function () { if (!ready && errors === 0) { loaded(); } });',
    'gl.on("idle", function () {\n            if (!ready && errors === 0 && gl.isStyleLoaded() && gl.loaded()) { loaded(); }\n          });')
replace('scripts/mapcore/resources/templates/shared.css',
    '  z-index: 500;\n  max-width: min(70%, 720px);\n  padding: 3px 6px;\n  overflow: hidden;',
    '  z-index: 800;\n  max-width: min(85%, 720px);\n  padding: 3px 6px;\n  overflow: visible;')
replace('scripts/mapcore/resources/templates/shared.css',
    '  line-height: 1.25;\n  text-overflow: ellipsis;\n  white-space: nowrap;\n  pointer-events: none;\n}',
    '  line-height: 1.35;\n  white-space: normal;\n  pointer-events: auto;\n}\n\n.imb-map-attribution a {\n  color: inherit;\n  text-decoration: underline;\n}\n\n.imb-map-attribution a:focus-visible {\n  outline: 2px solid currentColor;\n  outline-offset: 2px;\n}')
replace('scripts/mapcore/resources/templates/shared.css',
    '  .imb-sidebar {\n    position: absolute;\n    right: 12px;\n    bottom: 12px;',
    '  .imb-map-attribution {\n    max-width: calc(100% - 82px);\n  }\n\n  .imb-sidebar {\n    position: absolute;\n    right: 12px;\n    bottom: 44px;')
replace('scripts/mapcore/resources/templates/shared.css',
    '  .imb-detail-panel {\n    position: absolute;\n    top: auto;\n    right: 12px;\n    bottom: 12px;',
    '  .imb-detail-panel {\n    position: absolute;\n    top: auto;\n    right: 12px;\n    bottom: 44px;')
replace('tests/test_basemap_delivery.py',
    " assert other.locator('#imb-map-attribution a').count()==3\n context.close()",
    """ assert other.locator('#imb-map-attribution a').count()==3
 other.set_viewport_size({'width':390,'height':844})
 other.wait_for_timeout(500)
 assert other.locator('#imb-map-attribution a').evaluate_all('''elements => elements.every(el => {
   const r = el.getClientRects()[0];
   return r && r.width > 0 && r.top >= 0 && r.bottom <= innerHeight &&
     document.elementFromPoint(r.x + r.width/2, r.y + r.height/2) === el;
 })''')
 context.close()""")
replace('scripts/check_live_basemaps.py',
    "                    assert reopened.evaluate('window.__interactiveMapBuilderQA.errors')==[]\n",
    """                    assert reopened.evaluate('window.__interactiveMapBuilderQA.errors')==[]
                    assert reopened.locator('#imb-map-attribution a').evaluate_all('''elements =>
                      elements.length === 3 && elements.every(el => {
                        const r = el.getClientRects()[0];
                        return r && r.top >= 0 && r.bottom <= innerHeight &&
                          document.elementFromPoint(r.x+r.width/2, r.y+r.height/2) === el;
                      })''')
""")
replace('.github/workflows/basemap-live.yml',
    "      - 'scripts/mapcore/resources/templates/shared.js'",
    "      - 'scripts/mapcore/resources/templates/shared.js'\n      - 'scripts/mapcore/resources/templates/shared.css'")
replace('pyproject.toml','version = "0.6.0"','version = "0.7.0"')
replace('scripts/mapcore/version.py','__version__ = "0.6.0"','__version__ = "0.7.0"')
replace('CHANGELOG.md','## [Unreleased] / 未发布\n',
    '## [Unreleased] / 未发布\n\n## [0.7.0] - 2026-09-16\n')
replace('README.md',
    'The current stable release is **v0.6.0**. It combines leaner command startup,\nintent-resolved first builds, and portable **Share view** HTML/JSON handoff. Existing local\nSaved Views remain available; v0.6.0 uses MapSpec 1.1. The basemap repair on this branch\nwrites MapSpec 1.2 and accepts existing 1.1 inputs; both template families are unchanged.',
    'The current stable release is **v0.7.0**. OpenFreeMap Positron/Liberty replace the old\nanonymous basemap defaults for local HTML. Existing visual styles, local Saved Views and\nportable Share view remain available. MapSpec 1.2 accepts existing 1.1 inputs; both template\nfamilies are unchanged. Migrate old factory basemaps explicitly before rebuilding.')
replace('README.md','See [release notes](https://github.com/xlbaoxl/interactive-map-builder/releases/tag/v0.6.0).',
    'See [release notes](https://github.com/xlbaoxl/interactive-map-builder/releases/tag/v0.7.0).')
replace('README.zh-CN.md',
    '当前稳定版本为 **v0.6.0**。本版整合命令启动优化、明确意图直接构建和“分享当前视图”\nHTML／JSON 交付。原有本地保存视角继续可用；v0.6.0 使用 MapSpec 1.1。此分支的底图修复\n输出 MapSpec 1.2，同时兼容读取 1.1；两种既有模板不变。',
    '当前稳定版本为 **v0.7.0**。本地 HTML 的默认底图改为 OpenFreeMap Positron／Liberty，\n保留已有视觉系统、本地保存视角和分享功能。MapSpec 1.2 兼容读取 1.1；两种既有模板不变。\n旧地图需要显式迁移原有匿名底图预设，再重新构建。')
replace('README.zh-CN.md','详见[正式发布说明](https://github.com/xlbaoxl/interactive-map-builder/releases/tag/v0.6.0)。',
    '详见[正式发布说明](https://github.com/xlbaoxl/interactive-map-builder/releases/tag/v0.7.0)。')
