# 更新日志 / Changelog

本文件记录 Interactive Map Builder 面向用户的重要变化。格式参考
[Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循
[语义化版本](https://semver.org/lang/zh-CN/)。

This file records notable user-facing changes to Interactive Map Builder. Its format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

早期版本条目根据项目提交历史回填；0.3.1 是第一版具有自动标签、发行包和 GitHub Release
流程的版本。

Entries for earlier versions were reconstructed from the project history. Version 0.3.1 is the
first release with an automated tag, distribution assets, and GitHub Release workflow.

## 维护规则 / Maintenance

- 面向用户的新变化先加入 `Unreleased`，并归入 `Added`、`Changed` 或 `Fixed`。
  Add new user-facing changes to `Unreleased` first and classify them as `Added`, `Changed`, or
  `Fixed`.
- 发布新版本时，将对应条目移动到带版本号和发布日期的区段。
  When releasing a version, move its entries into a versioned section with the release date.
- 只记录用户可感知的功能、行为、兼容性和文档变化，不逐条复制提交信息。
  Record user-visible features, behavior, compatibility, and documentation changes rather than
  copying commit messages verbatim.

## [Unreleased] / 未发布

## [0.4.2] - 2026-07-27

### Added / 新增

- 多图层地图的右侧底图、图层和图例现在组成一个可整体收起与恢复的控制栈；左侧搜索面板的
  收起按钮改为紧凑方向按钮，两侧均保留键盘操作和 ARIA 状态。
  Added a collapsible right-side control stack for basemaps, visibility switches, and the legend,
  while making the existing left search-panel toggle compact, keyboard reachable, and explicit.
- 浏览器 QA 新增图例—地图颜色一致性、实际填充色、描边色和混合几何代表类型记录，避免视觉
  错误在构建报告中被误判为通过。
  Added browser QA for legend-to-map color consistency, rendered fill/stroke colors, and the
  representative family used by mixed-geometry layers.

### Changed / 变更

- Atlas Studio Light 新增保守的双语语义配色解析：水体使用蓝色系、公园与开放空间使用绿色系、
  停车设施使用暖橙色、商业与服务设施使用玫红色，并提高专题图层与浅色底图之间的对比度。
  Added conservative bilingual semantic color defaults for water, green space, parking,
  commercial/service facilities, pedestrian networks, and boundaries, with stronger contrast on
  light basemaps.
- 初始化器会为已知且不超过八类的水体、步行等图层生成语义调色板；已明确配置的自定义颜色
  继续保留。精确匹配旧版自动 Atlas 调色板的类别色会迁移到对应语义调色板。
  Initialized known bounded categories with semantic palettes, preserved custom colors, and
  migrated only the exact legacy auto-generated Atlas palette when a semantic layer is recognized.
- 包版本更新为 0.4.2；MapSpec 继续保持 1.1，不增加运行依赖或新的地图模板。
  Updated the package to 0.4.2 while retaining MapSpec 1.1, the current runtime dependencies, and
  the existing templates.

### Fixed / 修复

- 修复水体分类被通用八色调色板渲染为蓝、黄、紫等互不相关颜色的问题；河流、溪流和池塘现在
  使用可区分但保持水体语义的蓝色梯度。
  Fixed water categories being rendered with unrelated generic categorical colors; rivers,
  streams, and ponds now use a coherent blue family.
- 修复点面混合停车图层把 `mixed` 当作不存在的几何族、继而在图例中回退到哈希橙色的问题；
  图层控制和图例现在使用真实代表几何类型，并与地图上的停车符号一致。
  Fixed mixed point/polygon layers falling through to a hashed legend color; controls and legends
  now resolve a real representative geometry family and match rendered parking symbols.
- 修复多类图层透明度过低、边界、水体、绿地和设施在浅色底图上几乎融为一色的问题。
  Fixed overly pale defaults that made boundaries, water, green space, and facilities difficult to
  distinguish on light basemaps.

## [0.4.1] - 2026-07-27

### Added / 新增

- 多图层地图新增中性“总览”入口和紧凑图层下拉选择器；页面打开时所有可见图层保持基础
  样式，只有用户选择搜索图层后才进入 `focus` / `dimmed` 状态。
  Added a neutral Overview entry and compact layer selector to multilayer maps. All visible layers
  now open at their base style, and focus/dimmed states begin only after the user chooses a layer.

### Changed / 变更

- 静态图改为严格按需生成：默认构建只交付 HTML 与构建记录，只有明确启用 `slide-16x9` 或
  `paper` preset 时才生成 PNG、SVG 或 PDF。
  Made static figures strictly opt-in: default builds deliver HTML and build records, while PNG,
  SVG, and PDF are generated only when the slide or paper preset is explicitly enabled.
- 包版本更新为 0.4.1；MapSpec 继续保持 1.1，不新增模板、运行依赖或制图分析能力。
  Updated the package to 0.4.1 while retaining MapSpec 1.1, the existing templates, runtime
  dependencies, and cartographic scope.

### Fixed / 修复

- 明确区分完整包级 CLI 与内部构建脚本：安装体检优先运行
  `interactive-map-builder doctor`，源码回退使用 `python scripts/cli.py doctor`，内部
  `map_builder.py` 的帮助信息不再冒充完整 CLI。
  Clarified the package CLI versus the internal builder so installation checks use
  `interactive-map-builder doctor` or the source `scripts/cli.py` fallback without mistaking
  `map_builder.py` help for the full command set.
- README 的离线截图底图改为按瓦片坐标生成的低干扰街区纹理，不再重复平铺同一张斜线瓦片。
  Replaced the repeated diagonal README mock tile with a deterministic, coordinate-aware,
  low-interference street and block backdrop.

## [0.4.0] - 2026-07-27

### Added / 新增

- 新增 Atlas Studio Light 轻量视觉默认值解析器：根据点、线、面几何类型、粗粒度要素与坐标
  密度、模板角色和稳定绘制顺序补齐未明确的视觉参数，并将解析依据写入构建报告。
  Added the Atlas Studio Light resolver, which fills omitted visual values from geometry family,
  coarse feature/coordinate density, template role, and stable draw order while recording the
  resolved plan and reasons in the build report.
- 新增稳定的面—线—点 Leaflet panes，以及 `focus`、`hover`、`selected`、`dimmed` 状态，让多图层
  地图在切换搜索对象和选择要素时形成清晰但克制的视觉重点。
  Added stable polygon-line-point Leaflet panes and focus, hover, selected, and dimmed states for
  controlled hierarchy during layer search and feature selection.
- 新增针对几何、密度、显式覆盖、分类色上限和 HTML/构建报告共享视觉方案的自动测试。
  Added automated coverage for geometry and density defaults, explicit overrides, categorical
  limits, and shared HTML/build-report visual plans.

### Changed / 变更

- HTML、图例、列表卡片以及 PNG、SVG、PDF 静态输出现在消费同一份渲染器中立视觉方案；用户或
  Agent 在 MapSpec 中明确填写的颜色、尺寸和透明度始终优先。
  Unified HTML, legends, list accents, and PNG/SVG/PDF output around one renderer-neutral visual
  plan while preserving explicit MapSpec colors, sizes, and opacities as the highest priority.
- 默认分类调色板改为八个低饱和 Atlas 色；初始化器在类别超过八个或类别值不完整时不再循环
  自动配色，而是保留筛选能力，等待用户与 Agent 继续确定表达方式。
  Replaced the automatic categorical palette with eight restrained Atlas colors and stopped
  cycling colors when more than eight classes or incomplete values are found.
- UI 更新为 Atlas Studio Light 编辑式视觉语言：降低圆角、阴影和面板重量，将清单卡片改为更
  紧凑的记录行，并提高地图在页面中的视觉优先级。
  Refreshed the interface with the Atlas Studio Light editorial language: flatter panels, tighter
  record rows, restrained accents, and greater visual priority for the map.
- 包版本更新为 0.4.0；MapSpec 继续保持 1.1，不新增模板、前端框架或运行依赖。
  Updated the package to 0.4.0 while keeping MapSpec 1.1, the two existing templates, the current
  frontend stack, and the dependency footprint.

### Fixed / 修复

- 修复点、线、面在 HTML 中共用同一套默认尺寸和透明度、静态图另有一套默认值的问题；密集点
  自动缩小，背景面和辅助线自动后退，HTML 与静态图的填充/描边语义保持一致。
  Fixed the split default systems that gave HTML one generic style and static output another;
  dense points now shrink, context polygons and supporting lines recede, and fill/stroke semantics
  match across deliverables.
- 修复多图层绘制顺序依赖 MapSpec 文件顺序、关闭后重新开启可能改变遮挡关系的问题。
  Fixed layer stacking that previously depended on MapSpec order and could change after toggling a
  layer off and on.

## [0.3.2] - 2026-07-27

### Added / 新增

- 新增安全更新预检：Skill 每次调用可按 24 小时缓存检查官方 GitHub Release；只对官方仓库中
  干净的 `main` 分支或清单未被修改的正式 Skill ZIP 自动更新，并校验发行资产 SHA-256 和包内
  文件清单。断网、本地修改、只读目录和非标准安装不会阻塞地图任务。
  Added a cached, non-blocking release preflight that checks the official GitHub Release and
  automatically updates only a clean official `main` checkout or an unmodified managed Skill ZIP
  after validating the release SHA-256 file and package manifest.
- 新增 `interactive-map-builder update --check|--apply|--auto`，并支持通过
  `IMB_DISABLE_AUTO_UPDATE=1` 关闭自动检查。
  Added `interactive-map-builder update --check|--apply|--auto` with an
  `IMB_DISABLE_AUTO_UPDATE=1` opt-out.
- 更新应用后自动重新安装引擎并运行离线 `doctor`；若安装或体检失败，Git 安装恢复原提交，
  Release ZIP 安装恢复原清单管理的全部文件。
  Added transactional post-update installation and offline doctor verification, with rollback to
  the previous Git commit or managed package files on failure.
- v0.3.2 作为自动更新机制的起始版本；安装该版本一次后，后续兼容版本可由 Skill 预检发现并
  应用。
  Established v0.3.2 as the one-time update bootstrap for subsequent compatible releases.
- 新建 MapSpec 默认加入 CARTO Positron 与 OpenStreetMap Standard 两张免凭证在线底图，
  界面同时提供无底图选项；Esri World Imagery 作为需要授权服务配置的可选影像底图。
  Added CARTO Positron and OpenStreetMap Standard as credential-free defaults plus a no-basemap
  view; Esri World Imagery remains an opt-in provider configuration.
- 触发评估集扩展到 40 条，新增复杂 Codex 任务的可选 Plan mode 引导、本地文件与公网网址边界、
  以及用户明确要求部署时的确认规则。
  Expanded the trigger suite to 40 cases covering optional Codex planning, local-file versus
  public-URL behavior, and explicit deployment requests.

### Changed / 变更

- 包版本更新为 0.3.2，构建报告和 CLI 统一从单一版本模块读取版本号；正式 Release 额外发布
  `SHA256SUMS.txt`。
  Updated the package to 0.3.2, centralized CLI and engine version reporting, and added
  `SHA256SUMS.txt` to each Release.
- “可分享”默认统一为可发送、可双击打开的本地 `map.html`。只有用户明确要求部署时才讨论
  公网网址，并在部署前确认托管平台和数据公开权限。
  Defined the normal deliverable as a portable local `map.html`; public hosting is discussed only
  after an explicit deployment request and confirmation of the hosting target and data exposure.
- 对包含多个独立图层、多个阻塞性设计选择或多种协同输出的 Codex 任务，可在第一轮将 Plan
  mode 作为一次性可选建议；用户不切换也继续推进，明确单图层任务不提示。
  Restored Plan mode as a one-time optional Codex suggestion for genuinely complex tasks without
  making it a prerequisite or recommending it for clear single-layer work.

### Fixed / 修复

- 多图层地图的图层开关和图例改为同一垂直控制区：图层开关固定在上方，长图例在下方滚动并
  可折叠，窄屏默认收起，避免图例遮挡图层按钮。
  Stacked multilayer switches above a collapsible, scrolling legend so large legends no longer
  cover the visibility controls, including at narrow widths.
- 底图切换器现在对默认生成的地图始终可见，并可在两张免凭证在线底图和无底图之间切换；
  OSM 默认地址改为官方标准端点，在线瓦片连续失败时自动回退到无底图。
  Made the basemap selector visible for generated defaults, added a no-basemap fallback, and
  updated OpenStreetMap to its standard tile endpoint.

## [0.3.1] - 2026-07-27

### Added / 新增

- 新增按用户意图触发的 Skill 描述和调用规则：即使用户未提及 GIS、Leaflet、Web Map、Skill
  名称或具体格式，也能根据“搜索、筛选、分享、汇报、多图层”等目标识别任务。
  Added intent-based Skill metadata and invocation guidance so matching tasks can activate from
  search, filtering, sharing, reporting, and multilayer goals without requiring GIS, Leaflet,
  Web Map, the Skill name, or a specific file format.
- 新增 `interactive-map-builder doctor`，使用临时坐标数据离线完成加载、构建、打包资源检查和
  输出哈希验证，为安装后的首次使用提供可重复自检。
  Added `interactive-map-builder doctor`, an offline end-to-end installation check that loads
  generated coordinate data, builds a map, verifies packaged resources, and validates output
  hashes.
- 将触发评估集扩展为 36 条中英文案例，覆盖明确触发、隐式触发、模糊需求和不应触发任务；
  同时新增验证与评分脚本，用于记录覆盖率、触发召回率、误触发率、澄清行为和多次运行稳定性。
  Expanded the trigger suite to 36 English and Chinese cases across explicit, implicit,
  ambiguous, and out-of-scope requests, with a validator and scorer for coverage, trigger recall,
  false positives, clarification behavior, and repeated-run stability.
- 新增确定性的精简 Skill ZIP 构建器。发行包保留 Skill 元数据、Agent 配置、参考文档、Python
  引擎和网页资源，排除演示数据、截图、测试和 CI 文件。
  Added a deterministic lean Skill ZIP builder that keeps Skill metadata, Agent configuration,
  references, the Python engine, and web resources while excluding demos, screenshots, tests,
  and CI files.
- 新增发布工作流：`main` 中出现新版本且 CI 通过后，自动创建 Git 标签和 GitHub Release，并
  附带 wheel、源码包和版本化 Skill ZIP。
  Added release automation that creates a Git tag and GitHub Release after a new version on
  `main` passes CI, attaching the wheel, source archive, and versioned Skill ZIP.

### Changed / 变更

- 包版本更新为 0.3.1，CLI 入口增加轻量封装层，在保持原有 `inspect`、`init-spec`、`build`、
  `verify`、`run` 行为不变的基础上提供 `doctor` 和 `--version`。
  Updated the package to 0.3.1 and added a lightweight CLI wrapper that preserves the existing
  commands while providing `doctor` and `--version`.
- `agents/openai.yaml` 的短描述和默认提示词改为以用户成果为中心，并明确优先使用确定性引擎，
  不在适用任务中临时改写 Folium 或 Leaflet 页面。
  Reworked the OpenAI Agent metadata around user outcomes and made the packaged deterministic
  engine the preferred path over ad hoc Folium or Leaflet implementations.
- 英文主 README 与中文 README 增加自然语言触发示例、安装自检、正式发行包和自动发布说明。
  Updated both READMEs with natural-language activation examples, installation verification,
  versioned distribution assets, and automated release behavior.
- 向导继续使用跨 Agent 的统一需求清单，不依赖特定客户端界面状态；MapSpec 版本继续由打包的
  JSON Schema 单点定义，公共演示继续由演示构建器生成。
  Kept the cross-agent requirements checklist, the packaged JSON Schema as the single MapSpec
  source of truth, and the demo builder as the source of public demo configurations.

### Fixed / 修复

- GitHub Pages 在演示项目逻辑变化时重新构建；wheel 隔离测试继续使用独立、可直接构建的 CSV
  示例，并新增安装后 `doctor` 验证。
  Rebuilds GitHub Pages when demo-project logic changes, keeps wheel validation independent from
  generated demo configurations, and adds the installed `doctor` check.
- 默认初始化不再写入与受众语言无关的英文占位副标题。
  Removed the English placeholder subtitle from newly initialized maps.

## [0.3.0] - 2026-07-25

### Added / 新增

- 新增确定性的 `en-US` 与 `zh-CN` locale 资源，统一管理界面文案、ARIA 标签、字段别名、
  缺失值、静态图说明和交付指南。
  Added deterministic `en-US` and `zh-CN` locale resources for interface copy, ARIA labels,
  field aliases, missing values, static-figure notes, and delivery guidance.
- 新增中英文 GitHub Pages 首页及四个本地化地图页面，并提供四张 1600×900 对应截图。
  Added English and Chinese GitHub Pages landing pages, four localized map pages, and four
  matching 1600×900 screenshots.
- 对复杂或含糊的任务持续使用 `[x] Confirmed`、`[~] Inferred` 与
  `[ ] Needs confirmation` 需求清单补齐信息差。
  Added a persistent Confirmed/Inferred/Needs confirmation checklist for complex or ambiguous
  requests.

### Changed / 变更

- MapSpec 直接升级到 1.1，仅接受 `schema_version: "1.1"`；`locale` 仅接受 `en-US`
  或 `zh-CN`，默认值改为 `en-US`。
  Upgraded MapSpec directly to 1.1, accepting only `schema_version: "1.1"`; `locale` now accepts
  only `en-US` or `zh-CN` and defaults to `en-US`.
- `init-spec` 与 `run` 新增 `--locale`；所有模板、示例、测试和文档均升级到 MapSpec 1.1。
  Added `--locale` to `init-spec` and `run`, and upgraded templates, examples, tests, and
  documentation to MapSpec 1.1.
- 构建交付说明统一改名为 `README_USAGE.md`，并按地图 locale 生成内容。
  Renamed the build delivery guide to `README_USAGE.md` and localized its contents according to
  the map locale.
- 真实 NYC 示例改用语言中立分类代码与本地化显示字段；官方地名继续保留原文。
  Refactored the real NYC examples to use language-neutral category codes and localized display
  fields while preserving official place names.
- 包版本更新为 0.3.0，并补充 Homepage、Repository 与 Issues 元数据。
  Updated the package version to 0.3.0 and added Homepage, Repository, and Issues metadata.

### Removed / 移除

- 移除 MapSpec 1.0 支持；旧版本配置由当前 Schema 直接拒绝，不保留迁移或兼容分支。
  Removed MapSpec 1.0 support; the current Schema rejects old specifications without migration
  or compatibility branches.
- 删除已完成蒸馏的中文实施记录和冗余产品调研文件，保留规则已并入英文技术指南。
  Removed the distilled Chinese implementation note and redundant product-research file after
  preserving durable rules in the English technical guidance.

## [0.2.0] - 2026-07-24

### Added / 新增

- 引入 Atlas UI，包括搜索驱动的地图清单、关键指标摘要、分类与数值范围筛选，以及要素详情面板。
  Introduced the Atlas UI with a search-driven map list, KPI summaries, category and numeric range
  filters, and feature details.
- 新增演示项目构建流程，为真实地图示例生成可部署的 GitHub Pages 站点。
  Added a demo-project build workflow that produces a deployable GitHub Pages site from real map
  examples.

### Changed / 变更

- 重新设计共享 HTML、CSS 和 JavaScript 模板，统一清单地图与多图层地图的响应式界面。
  Redesigned the shared HTML, CSS, and JavaScript templates for a consistent responsive map-list
  and multilayer interface.
- 将用地示例升级为可搜索、可分类的 Lower Manhattan 地块地图，并更新演示截图和说明。
  Upgraded the land-use example to a searchable, classified Lower Manhattan parcel map and
  refreshed its screenshots and documentation.

## [0.1.0] - 2026-07-23

### Added / 新增

- 发布 `inspect`、`init-spec`、`build`、`verify` 和 `run` 命令，形成从数据检查到地图交付的
  完整命令行流程。
  Released `inspect`, `init-spec`, `build`, `verify`, and `run` for an end-to-end workflow from
  data inspection to map delivery.
- 支持 GeoJSON、GeoPackage、Shapefile ZIP、CSV、Excel 和 ArcGIS FeatureServer 数据，并对
  CRS、字段和配置进行显式检查。
  Added support for GeoJSON, GeoPackage, Shapefile ZIP, CSV, Excel, and ArcGIS FeatureServer data
  with explicit CRS, field, and configuration checks.
- 提供 `map-list` 与 `multilayer` 模板、MapSpec v1 配置，以及按语义键进行跨图层关联的能力。
  Added `map-list` and `multilayer` templates, the MapSpec v1 configuration, and semantic-key
  linking across layers.
- 支持生成单文件 Leaflet 地图、构建报告、交付说明，以及用于幻灯片和论文的 PNG、SVG 与 PDF
  静态输出。
  Added single-file Leaflet maps, build reports, delivery notes, and PNG, SVG, and PDF static
  outputs for slides and papers.
- 建立示例、浏览器检查、契约测试和多 Python 版本持续集成。
  Added examples, browser checks, contract tests, and continuous integration across multiple
  Python versions.

### Fixed / 修复

- 修复 Windows 和 POSIX 风格绝对路径的跨平台识别。
  Fixed cross-platform recognition of Windows and POSIX absolute paths.
