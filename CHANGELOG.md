# 更新日志 / Changelog

本文件记录 Interactive Map Builder 面向用户的重要变化。格式参考
[Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循
[语义化版本](https://semver.org/lang/zh-CN/)。

This file records notable user-facing changes to Interactive Map Builder. Its format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

早期版本条目根据项目提交历史回填；这些版本尚未创建 Git 标签或 GitHub Release。

Entries for earlier versions were reconstructed from the project commit history; those versions
do not yet have Git tags or GitHub Releases.

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

### Changed / 变更

- 向导改用跨 Agent 的统一需求清单，不再依赖特定客户端的 Plan mode、快捷键或界面状态。
  Replaced client-specific planning controls with one cross-agent requirements checklist.
- MapSpec 当前版本由打包的 JSON Schema 单点定义，示例、初始化器和 HTML 载荷不再分别硬编码版本号。
  Made the packaged JSON Schema the single source of truth for the current MapSpec version.
- 公共 `map-list` 演示仅保留固定数据快照，展示配置统一由演示构建器生成。
  Made the demo builder the sole source of truth for the public `map-list` configuration.

### Fixed / 修复

- GitHub Pages 在演示项目逻辑变化时会重新构建；wheel 隔离测试改用独立、可直接构建的 CSV 示例。
  Rebuilds GitHub Pages when demo-project logic changes and keeps wheel validation independent
  from generated demo configurations.
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

- 引入 Atlas UI，包括搜索驱动的地图清单、关键指标摘要、分类与数值范围筛选，以及要素
  详情面板。
  Introduced the Atlas UI with a search-driven map list, KPI summaries, category and numeric
  range filters, and feature details.
- 新增演示项目构建流程，为真实地图示例生成可部署的 GitHub Pages 站点。
  Added a demo-project build workflow that produces a deployable GitHub Pages site from real map
  examples.

### Changed / 变更

- 重新设计共享 HTML、CSS 和 JavaScript 模板，统一清单地图与多图层地图的响应式界面。
  Redesigned the shared HTML, CSS, and JavaScript templates for a consistent responsive
  map-list and multilayer interface.
- 将用地示例升级为可搜索、可分类的 Lower Manhattan 地块地图，并更新演示截图和说明。
  Upgraded the land-use example to a searchable, classified Lower Manhattan parcel map and
  refreshed its screenshots and documentation.

## [0.1.0] - 2026-07-23

### Added / 新增

- 发布 `inspect`、`init-spec`、`build`、`verify` 和 `run` 命令，形成从数据检查到地图交付的
  完整命令行流程。
  Released the `inspect`, `init-spec`, `build`, `verify`, and `run` commands for an end-to-end
  workflow from data inspection to map delivery.
- 支持 GeoJSON、GeoPackage、Shapefile ZIP、CSV、Excel 和 ArcGIS FeatureServer 数据，并对
  CRS、字段和配置进行显式检查。
  Added support for GeoJSON, GeoPackage, Shapefile ZIP, CSV, Excel, and ArcGIS FeatureServer
  data with explicit CRS, field, and configuration checks.
- 提供 `map-list` 与 `multilayer` 模板、MapSpec v1 配置，以及按语义键进行跨图层关联的
  能力。
  Added `map-list` and `multilayer` templates, the MapSpec v1 configuration, and semantic-key
  linking across layers.
- 支持生成单文件 Leaflet 地图、构建报告、交付说明，以及用于幻灯片和论文的 PNG、SVG 与
  PDF 静态输出。
  Added single-file Leaflet maps, build reports, delivery notes, and PNG, SVG, and PDF static
  outputs for slides and papers.
- 建立示例、浏览器检查、契约测试和多 Python 版本持续集成。
  Added examples, browser checks, contract tests, and continuous integration across multiple
  Python versions.

### Fixed / 修复

- 修复 Windows 和 POSIX 风格绝对路径的跨平台识别。
  Fixed cross-platform recognition of Windows and POSIX absolute paths.
