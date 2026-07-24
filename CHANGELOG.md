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

- 优化清单地图和多图层示例的交互、示例数据与说明，使搜索、图层切换和地图浏览更聚焦。
  Refined the map-list and multilayer demos, sample data, and guidance for more focused search,
  layer switching, and map exploration.
- 补充交互地图设计经验和下一版本体验要求。
  Documented interactive-map design lessons and user-experience requirements for the next
  version.

### Fixed / 修复

- 稳定数值范围筛选器的打开、切换和关闭行为，同步 `aria-expanded` 状态，并在关闭后恢复
  键盘焦点。
  Stabilized range-filter opening, switching, and closing, kept `aria-expanded` in sync, and
  restored keyboard focus after closing.

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
