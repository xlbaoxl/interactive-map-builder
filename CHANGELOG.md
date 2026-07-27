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

## [0.4.3] - 2026-07-27

### Added / 新增

- 新增对标准 Skill 安装器所产生“无 `.git`、无 `PACKAGE_MANIFEST.json`”精确副本的安全接管：
  updater 会下载当前本地版本对应的官方 Release，完成发行包 SHA-256、清单和逐文件哈希比对；
  只有本地受管文件与官方版本完全一致时才写入清单并继续更新，用户额外文件保持不变。
  Added verified adoption for exact unmanaged copies created by common Skill installers. The
  updater downloads the official Release matching the local version, validates its checksum and
  manifest, compares every managed file, writes only the verified manifest, and preserves unrelated
  user files before continuing the update.
- 版本预检结果新增安装类型、执行阶段和稳定状态字段，Agent 可以明确区分联网检查、缓存检查、
  自动接管、成功更新、需要人工处理和检查失败。
  Added explicit installation type, operation phase, and stable result states so Agents can
  distinguish network checks, cached checks, adoption, successful updates, manual attention, and
  check failures.

### Changed / 变更

- Skill 每次实际调用均使用 `update --auto --force` 完成一次新鲜的官方 Release 检查；普通用户仍可
  使用不带 `--force` 的 `--check` 享受 24 小时缓存。Agent 必须读取并简要报告 JSON 结果，不能仅
  根据退出码判断版本状态。
  Skill invocations now use `update --auto --force` for a fresh official Release check. Ordinary
  manual checks may still use the 24-hour cache. Agents must read and briefly report the JSON result
  instead of inferring success from the process exit code.
- 包版本更新为 0.4.3；MapSpec、地图模板、运行依赖和制图能力保持不变。
  Updated the package to 0.4.3 without changing MapSpec, map templates, runtime dependencies, or
  cartographic scope.

### Fixed / 修复

- 修复缓存未随本地版本或活动 Skill 根目录变化而失效的问题；缓存中的官方版本低于当前本地版本
  时会被拒绝并重新联网检查，不再产生“本地 0.4.1、最新 0.4.0、状态 current”一类矛盾结果。
  Fixed cache reuse across a changed local version or active Skill root. A cached official version
  older than the running version is rejected and refreshed instead of producing contradictory
  `current` results.
- 修复自动应用更新失败后丢失已确认的 `latest_version`、`release_url`、来源和
  `update_available=true` 的问题；失败结果现在保留检查事实，并标注发生在 adoption 或 apply
  阶段。
  Fixed apply failures discarding the already verified latest-version metadata. Failure results now
  preserve the release, source, and availability facts and identify the adoption or apply phase.
- 修复存在多个标准 Skill 目录时 updater 静默猜测活动副本的问题；此时要求显式 `--skill-dir`，
  避免更新 `.codex/skills` 与 `.agents/skills` 中错误的那一份。
  Fixed silent root guessing when multiple standard Skill directories exist; the updater now asks
  for an explicit `--skill-dir` rather than modifying the wrong copy.
- 发布工作流现在能够识别并修复“标签已存在但 Release 或发行资产不完整”的中断状态，同时拒绝
  将既有标签移动到其他提交。
  The release workflow now repairs an incomplete Release when its tag already exists, while refusing
  to move an existing tag to a different commit.

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

- 静态图改为严格按需生成；包版本更新为 0.4.1，MapSpec、模板和运行依赖保持不变。
  Made static figures strictly opt-in and updated the package to 0.4.1 without changing MapSpec,
  templates, or runtime dependencies.

### Fixed / 修复

- 明确区分完整包级 CLI 与内部构建脚本，并替换 README 中重复平铺的离线截图底纹。
  Clarified the package CLI versus the internal builder and replaced the repeated README mock tile.

## [0.4.0] - 2026-07-27

### Added / 新增

- 新增 Atlas Studio Light 视觉默认值解析器、稳定的点线面绘制层级，以及
  `focus`、`hover`、`selected`、`dimmed` 状态。
  Added the Atlas Studio Light visual resolver, stable point-line-polygon draw order, and explicit
  focus, hover, selected, and dimmed states.

### Changed / 变更

- HTML、图例、卡片及静态图共用一份视觉方案；自动分类色限制为八类；UI 更新为更克制的编辑式
  视觉语言；包版本更新为 0.4.0。
  Unified HTML and static outputs around one visual plan, capped automatic categories at eight,
  refreshed the editorial UI, and updated the package to 0.4.0.

### Fixed / 修复

- 修复不同几何共用错误默认值以及绘制顺序依赖 MapSpec 文件顺序的问题。
  Fixed split geometry defaults and layer stacking that depended on MapSpec order.

## [0.3.2] - 2026-07-27

### Added / 新增

- 新增校验 Release ZIP、`SHA256SUMS.txt` 和包内清单的安全更新预检、事务式回滚、默认在线底图与
  无底图回退，并扩展跨 Agent 触发评估。
  Added the verified release preflight, transactional rollback, default online basemaps with a
  no-basemap fallback, and broader cross-agent trigger evaluation.

### Changed / 变更

- 统一版本报告、本地 HTML 交付边界和复杂 Codex 任务的可选 Plan mode 建议。
  Centralized version reporting, clarified local HTML delivery, and restored optional Plan mode
  guidance for genuinely complex Codex tasks.

### Fixed / 修复

- 重组多图层控制区与长图例，并修正默认 OSM 端点和瓦片失败回退。
  Reworked multilayer controls and long legends, and fixed the default OSM endpoint and tile-failure
  fallback.

## [0.3.1] - 2026-07-27

### Added / 新增

- 新增按用户意图触发的 Skill 元数据、离线 `doctor`、36 条中英文触发评估、精简 Skill ZIP 和
  自动 GitHub Release 流程。
  Added intent-based activation, the offline doctor, 36 bilingual trigger evaluations, a lean Skill
  ZIP, and automated GitHub Releases.

### Changed / 变更

- CLI 增加 `doctor` 与 `--version`，更新 Agent 元数据和中英文 README，并保留 MapSpec Schema 与
  演示构建器作为单一来源。
  Added `doctor` and `--version` to the CLI, refreshed Agent metadata and documentation, and retained
  the Schema and demo builder as single sources of truth.

### Fixed / 修复

- 修复演示逻辑变化时的 Pages 重建、隔离 wheel 验证和默认英文占位副标题。
  Fixed Pages rebuild coverage, isolated wheel validation, and the default English placeholder
  subtitle.

## [0.3.0] - 2026-07-25

### Added / 新增

- 新增 `en-US` / `zh-CN` locale、双语 GitHub Pages、需求清单和本地化截图。
  Added deterministic locales, bilingual GitHub Pages, the requirements checklist, and localized
  screenshots.

### Changed / 变更

- MapSpec 升级到 1.1，新增 `--locale`，统一 `README_USAGE.md`，重构语言中立示例，并补充项目
  元数据。
  Upgraded MapSpec to 1.1, added `--locale`, standardized `README_USAGE.md`, refactored neutral
  examples, and added project metadata.

### Removed / 移除

- 移除 MapSpec 1.0 兼容分支及已完成蒸馏的冗余实施记录。
  Removed MapSpec 1.0 compatibility and redundant distilled implementation notes.

## [0.2.0] - 2026-07-24

### Added / 新增

- 引入 Atlas UI、搜索驱动地图清单、指标摘要、分类与数值筛选、详情面板和演示站点构建流程。
  Introduced Atlas UI, search-driven map lists, KPI summaries, filters, detail panels, and the demo
  site workflow.

### Changed / 变更

- 统一重构共享 HTML、CSS 与 JavaScript 模板，并升级 Lower Manhattan 用地演示。
  Redesigned the shared templates and upgraded the Lower Manhattan land-use demo.

## [0.1.0] - 2026-07-23

### Added / 新增

- 发布 `inspect`、`init-spec`、`build`、`verify` 和 `run`，支持 GeoJSON、GeoPackage、Shapefile
  ZIP、CSV、Excel、ArcGIS FeatureServer、两种地图模板、构建报告与静态输出。
  Released the end-to-end CLI, supported spatial input formats, two map templates, build reports,
  and report-ready static outputs.

### Fixed / 修复

- 修复 Windows 和 POSIX 风格绝对路径的跨平台识别。
  Fixed cross-platform recognition of Windows and POSIX absolute paths.
