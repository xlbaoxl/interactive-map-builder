# Interactive Map Builder

[中文](#中文) · [English](#english)

Build lightweight, searchable Leaflet maps and report-ready figures from existing spatial
data—without a frontend build system.

---

## 中文

Interactive Map Builder 是一个面向 Codex 与其他 AI Agent 的轻量地图 Skill。它先检查
数据与配置歧义，再由确定性的 Python CLI 生成单文件交互 HTML、汇报图片和论文矢量图。

### 效果预览

#### Map + List

![带搜索、筛选和可收起清单的 map-list 地图](assets/screenshots/map-list.png)

#### Multilayer

![带图层开关、跨图层搜索和底图切换的 multilayer 地图](assets/screenshots/multilayer.png)

### 三分钟开始

```powershell
git clone https://github.com/xlbaoxl/interactive-map-builder.git
cd interactive-map-builder
python -m pip install .

interactive-map-builder inspect assets/examples/map-list/neighborhoods.geojson `
  --output inspection.json
interactive-map-builder init-spec inspection.json `
  --template map-list `
  --primary-layer neighborhoods `
  --output map_spec.json
interactive-map-builder build --spec map_spec.json --out dist
interactive-map-builder verify --dist dist
```

只有一个且无歧义的图层时，也可以使用快捷命令：

```powershell
interactive-map-builder run data.geojson --output dist
```

### 安装为 Codex Skill

把仓库放入个人 Skill 目录，并安装确定性执行引擎：

```powershell
git clone https://github.com/xlbaoxl/interactive-map-builder.git `
  "$env:CODEX_HOME\skills\interactive-map-builder"
cd "$env:CODEX_HOME\skills\interactive-map-builder"
python -m pip install .
```

如果没有设置 `CODEX_HOME`，使用 `~/.codex/skills/interactive-map-builder`。随后可在提示中
写：

```text
Use $interactive-map-builder to inspect these spatial files and build a searchable map.
```

### 安装到其他 Agent

将整个仓库复制到 Agent 可读取的 Skill/规则目录，让它加载 `SKILL.md`，再运行
`python -m pip install .`。其他 Agent 必须遵守同一 MapSpec 和 CLI 流程；不要让模型临时
重写一套 Folium 或前端实现。

### 支持的输入

- GeoJSON / JSON FeatureCollection
- GeoPackage（可指定图层）
- 单数据集 Shapefile ZIP
- CSV 经纬度或 WKT（必须显式 CRS）
- Excel 经纬度或 WKT（必须显式 CRS）
- ArcGIS FeatureServer（先下载为本地 GeoJSON）

不支持：

- 地址地理编码
- 缓冲区、叠加、选址或统计推断
- 矢量瓦片服务
- 离线底图下载
- 根据数值范围猜测 CRS

### 固定输出

每次构建都会生成：

- `map.html`：内嵌 Leaflet、样式、脚本与业务 GeoJSON 的单文件地图
- `map_spec.json`：解析默认值后的构建记录
- `inspection.json`：输入、字段候选、CRS 与模板确认状态
- `build_report.json`：校验、修复、警告、性能指标、哈希与可移植状态
- `README_使用说明.md`：交付给最终使用者的简短说明

静态 preset 另外生成：

- `slide-16x9` → `map_slide_16x9.png`
- `paper` → `map_paper.png`、`map_paper.svg`、`map_paper.pdf`

普通 `build` 不复制源数据，输出的 `map_spec.json` 只是构建记录。需要独立重建包时使用：

```powershell
interactive-map-builder build --spec map_spec.json --out dist --bundle-sources
```

### 完整示例一：主图层 + 上下文图层

检查多个输入后，显式选择主要清单图层：

```powershell
interactive-map-builder inspect sites.geojson districts.geojson `
  --output inspection.json
interactive-map-builder init-spec inspection.json `
  --template map-list `
  --primary-layer sites `
  --output map_spec.json
interactive-map-builder build --spec map_spec.json --out dist --bundle-sources
interactive-map-builder verify --dist dist
```

### 完整示例二：点线面多图层

```powershell
interactive-map-builder inspect districts.geojson routes.geojson places.geojson `
  --output inspection.json
interactive-map-builder init-spec inspection.json `
  --template multilayer `
  --output map_spec.json
interactive-map-builder build --spec map_spec.json --out dist
interactive-map-builder verify --dist dist
```

多图层中的相同要素 ID 默认互不关联。只有各图层显式配置相同语义的 `link_key` 时才会
跨图层高亮。

### 当前限制

- HTML 会一次性创建全部 Leaflet 要素；报告会给出 `light`/`medium` 简化建议，但不会
  自动切换到矢量瓦片。
- 在线底图仍需要网络；业务几何与界面代码可离线使用。
- 系统没有 CJK 字体时静态图继续生成，但报告会提示中文字体回退。
- `linked_view` 是 experimental，只做已有 x/y 变量的 ID 联动，不解释象限或因果关系。
- 多图层任务必须由用户确认 `map-list` 或 `multilayer`；工具不会从几何类型猜测业务意图。

### 路线图

- 用更多真实但可公开的数据包扩充行为 eval
- 改进超大 GeoJSON 的搜索和渐进加载
- 增加可选的视觉回归测试
- 在保持 MapSpec v1 稳定的前提下评估更多静态输出 preset

---

## English

Interactive Map Builder is a lightweight map Skill for Codex and other AI agents. The agent
inspects data and resolves ambiguity; a deterministic Python CLI then produces a single-file
interactive map plus presentation- and publication-ready figures.

### Preview

#### Map + List

![Map-list template with search, filters, and a collapsible catalog](assets/screenshots/map-list.png)

#### Multilayer

![Multilayer template with layer toggles, cross-layer search, and basemap switching](assets/screenshots/multilayer.png)

### Three-minute quick start

```bash
git clone https://github.com/xlbaoxl/interactive-map-builder.git
cd interactive-map-builder
python -m pip install .

interactive-map-builder inspect assets/examples/map-list/neighborhoods.geojson \
  --output inspection.json
interactive-map-builder init-spec inspection.json \
  --template map-list \
  --primary-layer neighborhoods \
  --output map_spec.json
interactive-map-builder build --spec map_spec.json --out dist
interactive-map-builder verify --dist dist
```

For one unambiguous layer:

```bash
interactive-map-builder run data.geojson --output dist
```

### Install as a Codex Skill

Clone the repository into your personal Skill directory and install its deterministic engine:

```bash
git clone https://github.com/xlbaoxl/interactive-map-builder.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/interactive-map-builder"
cd "${CODEX_HOME:-$HOME/.codex}/skills/interactive-map-builder"
python -m pip install .
```

Then invoke it with a prompt such as:

```text
Use $interactive-map-builder to inspect these spatial files and build a searchable map.
```

### Install for another agent

Copy the complete repository into a Skill or rules directory that the agent can read, instruct
it to load `SKILL.md`, and run `python -m pip install .`. Keep the MapSpec and CLI as the source
of truth instead of asking the model to generate an unrelated Folium or frontend implementation.

### Supported inputs

- GeoJSON / JSON FeatureCollection
- GeoPackage, with explicit layer selection when needed
- A single-dataset Shapefile ZIP
- CSV longitude/latitude or WKT with an explicit CRS
- Excel longitude/latitude or WKT with an explicit CRS
- ArcGIS FeatureServer downloaded to local GeoJSON first

Out of scope:

- Address geocoding
- Buffers, overlays, site selection, or statistical inference
- Vector-tile services
- Offline basemap acquisition
- Guessing a CRS from coordinate ranges

### Fixed outputs

Every build writes:

- `map.html`: single-file Leaflet map with embedded UI and business GeoJSON
- `map_spec.json`: resolved build record
- `inspection.json`: inputs, field candidates, CRS, and template-confirmation state
- `build_report.json`: validation, repairs, warnings, performance, hashes, and portability
- `README_使用说明.md`: short delivery note for the end user

Static presets add:

- `slide-16x9` → `map_slide_16x9.png`
- `paper` → `map_paper.png`, `map_paper.svg`, and `map_paper.pdf`

A normal `build` does not copy source data. Create a portable rebuild bundle explicitly:

```bash
interactive-map-builder build --spec map_spec.json --out dist --bundle-sources
```

### Complete example 1: primary layer plus context

```bash
interactive-map-builder inspect sites.geojson districts.geojson \
  --output inspection.json
interactive-map-builder init-spec inspection.json \
  --template map-list \
  --primary-layer sites \
  --output map_spec.json
interactive-map-builder build --spec map_spec.json --out dist --bundle-sources
interactive-map-builder verify --dist dist
```

### Complete example 2: mixed multilayer explorer

```bash
interactive-map-builder inspect districts.geojson routes.geojson places.geojson \
  --output inspection.json
interactive-map-builder init-spec inspection.json \
  --template multilayer \
  --output map_spec.json
interactive-map-builder build --spec map_spec.json --out dist
interactive-map-builder verify --dist dist
```

Equal feature IDs in different layers remain isolated. Cross-layer highlighting is enabled only
when layers explicitly declare a semantically shared `link_key`.

### Current limitations

- Leaflet objects are still created eagerly. The report recommends `light` or `medium`
  simplification but does not introduce vector tiles.
- Online basemap tiles require a network connection; business geometry and UI remain embedded.
- Static figures continue with a fallback when no CJK font is installed and record a warning.
- `linked_view` is experimental and links existing x/y variables by ID without inventing
  quadrant, causal, or statistical meaning.
- Multi-layer tasks always require explicit confirmation of `map-list` versus `multilayer`.

### Roadmap

- Expand behavioral evals with additional redistributable real-world datasets
- Improve search and progressive rendering for larger GeoJSON payloads
- Add optional visual-regression coverage
- Evaluate more static presets without expanding or fragmenting MapSpec v1

## License

MIT
