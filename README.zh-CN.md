<div align="center">

# Interactive Map Builder

**把已有空间数据交给 AI Agent，得到漂亮、可验证、可直接交付的地图产品。**

[![CI](https://github.com/xlbaoxl/interactive-map-builder/actions/workflows/ci.yml/badge.svg)](https://github.com/xlbaoxl/interactive-map-builder/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![MapSpec 1.1](https://img.shields.io/badge/MapSpec-1.1-0f766e)](references/map-spec.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-2ea44f.svg)](LICENSE)

[在线演示](https://xlbaoxl.github.io/interactive-map-builder/zh-CN/) ·
[English](README.md) ·
[更新日志](CHANGELOG.md)

</div>

[![Interactive Map Builder 地块查询与统计地图](assets/screenshots/zh-CN/map-list.png)](https://xlbaoxl.github.io/interactive-map-builder/zh-CN/map-list/)

Interactive Map Builder 是一个 **以 Codex 为主要使用场景、兼容 Agent Skills 工作流**的地图
Skill。把 GeoJSON、GeoPackage、Shapefile、CSV、Excel 或 ArcGIS 数据交给它，它会先检查
数据，只询问数据本身无法回答的选项，再写入可审计的 MapSpec，生成单文件 Leaflet 地图，
检查交互结果，并同步导出适合 PPT 和论文的静态图。

```text
空间数据 → 检查 → 集中确认 → MapSpec → 构建 → 浏览器验证 → HTML + PNG/SVG/PDF
```

不需要前端工程，不需要手写 Folium 页面，也不会隐藏数据清洗过程。

## 核心特点

- **用自然语言配置地图**：用户只需说明想回答什么问题，不必先掌握分级设色、图层控制等
  GIS 术语。
- **确定性构建**：Agent 负责理解需求和编写 MapSpec，Python 引擎统一负责读取、清洗、
  样式、渲染和校验，避免每次临时生成一套不同代码。
- **两种成熟地图产品**：可搜索筛选的“地图＋清单”，以及可独立开关点、线、面数据的
  “多图层地图”。
- **单文件交付**：Leaflet、界面逻辑和业务几何都嵌入 `map.html`；只有在线街道底图需要网络。
- **汇报与论文输出**：同一份配置可生成 16:9 PNG，以及论文用 PNG、SVG 和 PDF。
- **完整构建记录**：自动保存数据检查、几何修复、生成 ID、性能提示、数据来源、文件哈希
  和可移植状态。
- **真实浏览器测试**：搜索、筛选、排序、图层开关、对象选择、键盘操作和窄屏布局均有
  Chromium 测试。
- **中英文地图界面**：内置稳定的 `zh-CN` 和 `en-US` 文案、ARIA 标签、交付说明和公开演示。

## 在线演示

| 搜索、筛选和比较对象 | 联合查看多个空间主题 |
| --- | --- |
| [![地块分类统计地图](assets/screenshots/zh-CN/map-list.png)](https://xlbaoxl.github.io/interactive-map-builder/zh-CN/map-list/) | [![点线面多图层地图](assets/screenshots/zh-CN/multilayer.png)](https://xlbaoxl.github.io/interactive-map-builder/zh-CN/multilayer/) |
| **地图＋清单。** 搜索地址和属性，筛选类别与数值范围，排序记录，观察统计指标变化，并查看选中地块的完整信息。 | **多图层。** 独立开关邻里分区、自行车线路和地铁站，按业务图层搜索，切换底图并查看对象详情。 |
| [打开交互演示 →](https://xlbaoxl.github.io/interactive-map-builder/zh-CN/map-list/) | [打开交互演示 →](https://xlbaoxl.github.io/interactive-map-builder/zh-CN/multilayer/) |

两个演示都由仓库中的确定性引擎根据固定的
[NYC Open Data 数据快照](assets/examples/SOURCES.md)生成，不是另外制作的设计稿。

## 快速开始

### 1. 在 Codex 中安装 Skill

打开一个新的 Codex 任务，发送：

```text
$skill-installer 请从 https://github.com/xlbaoxl/interactive-map-builder 安装这个 Skill，并安装它需要的 Python 依赖。
```

安装完成后新建任务。如果新任务中没有出现该 Skill，再重启一次 Codex。

### 2. 上传数据并描述目标

```text
使用 $interactive-map-builder，把我上传的空间数据做成可以搜索和筛选的中文交互地图，同时导出一张 16:9 汇报图。
```

Skill 会先检查数据，并在仍有不确定项时维护一份简短需求清单：

```markdown
- [x] Confirmed：用户已明确，或数据已经证明
- [~] Inferred：Skill 根据数据提出的建议，可以修改
- [ ] Needs confirmation：构建前必须确认
```

它只会集中询问一次真正影响结果的内容，例如 CRS、模板、主图层、分类含义、展示字段、
输出格式和地图受众语言。

<details>
<summary><strong>Windows 手动安装</strong></summary>

先安装 [Git for Windows](https://git-scm.com/download/win) 和
[Python 3.9 或更高版本](https://www.python.org/downloads/windows/)，然后在 PowerShell 中运行：

```powershell
New-Item -ItemType Directory -Force "$HOME\.agents\skills" | Out-Null
git clone https://github.com/xlbaoxl/interactive-map-builder.git `
  "$HOME\.agents\skills\interactive-map-builder"
Set-Location "$HOME\.agents\skills\interactive-map-builder"
py -m pip install .
interactive-map-builder --help
```

</details>

<details>
<summary><strong>在 Claude Code 或其他 Agent Skills 客户端中使用</strong></summary>

把完整仓库复制到客户端能够读取的 Skill 或规则目录，让它加载 `SKILL.md`，然后安装一次
确定性引擎：

```bash
python -m pip install .
interactive-map-builder --help
```

工作流不依赖特定客户端界面：检查数据、维护需求清单、写入当前 MapSpec、使用仓库内引擎
构建、验证并交付完整 `dist` 目录。

</details>

## 选择哪种地图

| 用户目标 | 底层模板 | 适用数据 | 主要交互 |
| --- | --- | --- | --- |
| 查找、筛选、排序和比较每条记录 | `map-list` | 地块、建筑、设施、门店、项目、事件、候选地点 | 搜索、分类与数值筛选、排序、动态统计、地图清单联动、详情面板 |
| 同时查看多个相互独立的空间主题 | `multilayer` | 边界、道路、线路、设施、环境和规划背景 | 图层开关、分图层搜索、点线面样式、图例、底图切换、对象详情 |

`map-list` 也可以附带行政区或道路等背景图层。存在多个输入时，Skill 不会仅凭几何类型
猜测业务意图，而会要求用户确认模板和主图层。

## 支持的数据

| 输入格式 | 要求 |
| --- | --- |
| GeoJSON / JSON FeatureCollection | 几何和 CRS 可正常读取 |
| GeoPackage | 包含多个候选图层时需要明确选择 |
| Shapefile ZIP | 每个 ZIP 只放一套 Shapefile；保留 `.cpg`/GDAL 编码识别 |
| CSV | 具有经纬度字段或 WKT，并明确源 CRS |
| Excel | 具有经纬度字段或 WKT，并明确源 CRS |
| ArcGIS FeatureServer | 先下载为本地 GeoJSON 快照，再进入地图构建 |

在推荐地图之前，检查阶段会输出要素数量、几何类型、CRS、字段样例、候选 ID/名称/分类
字段、歧义和性能提示。

## 交付内容

| 文件 | 用途 |
| --- | --- |
| `map.html` | 内嵌业务几何和全部界面逻辑的单文件 Leaflet 地图 |
| `map_slide_16x9.png` | 启用汇报 preset 时生成的 1920×1080 图片 |
| `map_paper.png` / `.svg` / `.pdf` | 启用论文 preset 时生成的出版图件 |
| `map_spec.json` | 解析后的可复用构建契约 |
| `inspection.json` | 输入、CRS、字段候选和待确认项 |
| `build_report.json` | 数量、修复、警告、性能、哈希和可移植状态 |
| `README_USAGE.md` | 面向地图接收者的本地化使用说明 |

普通构建不会复制源数据，`map_spec.json` 只作为原项目中的构建记录。需要把整个结果移动到
其他电脑后独立重建时，使用 `--bundle-sources`。

## 工作原理

```text
用户需求 + 空间文件
          │
          ▼
       检查数据
 CRS · 几何 · 字段 · 数据规模
          │
          ▼
  一次性确认无法自动判断的选项
          │
          ▼
       MapSpec 1.1
          │
          ▼
     确定性 Python 引擎
 读取 · 规范化 · 配色 · 渲染
          │
          ▼
 校验数量、文件、QA 接口、
 数据来源、哈希和浏览器交互
          │
          ▼
 可分享 HTML + 汇报与论文图件
```

打包的 [JSON Schema](scripts/mapcore/resources/map-spec.schema.json) 是 MapSpec 唯一的机器契约。
配置只接受规范的 `snake_case` 字段；不支持的字段和 Schema 版本会被直接拒绝，不会静默迁移。

<details>
<summary><strong>命令行工作流</strong></summary>

只有一个且没有歧义的图层时：

```bash
interactive-map-builder run data.geojson --locale zh-CN --output dist
```

需要显式控制和保存配置时：

```bash
interactive-map-builder inspect sites.geojson districts.geojson \
  --output inspection.json

interactive-map-builder init-spec inspection.json \
  --template map-list \
  --primary-layer sites \
  --locale zh-CN \
  --output map_spec.json

interactive-map-builder build --spec map_spec.json --out dist --bundle-sources
interactive-map-builder verify --dist dist
```

独立的点、线、面业务图层使用 `--template multilayer`，不填写 `--primary-layer`。

</details>

## 能力边界

Interactive Map Builder 专注于 **已有空间数据 → 可交付地图成品**，目前不负责：

- 把地址批量转换成坐标；
- 缓冲区、叠加、选址模型和统计推断；
- 矢量瓦片服务和千万级要素 WebGIS；
- 离线底图下载；
- 根据坐标数值猜测 CRS；
- 三维地形、建筑和数字孪生。

对于较大的 GeoJSON，构建报告会建议使用 `light` 或 `medium` 几何简化，但不会在用户不知情
时切换渲染引擎。

## 项目状态

项目当前处于 **v0.3 Beta**。这一阶段稳定维护两套页面框架和一份 MapSpec 契约，不继续盲目
增加页面模板。下一步由真实用户反馈决定，候选方向包括点聚合、比例圆点、按数值变化的线宽、
区域汇总、导出当前筛选结果和更大数据量的渲染。

已经完成的变化见[更新日志](CHANGELOG.md)。

## 开发与测试

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q -m "not browser"
python -m playwright install chromium
python -m pytest -q -m browser
```

构建中英文 GitHub Pages 演示：

```bash
python scripts/build_demo_site.py --output _site
```

CI 覆盖 Python 3.9、3.10、3.12、Chromium 交互测试、wheel 构建，以及在仓库之外安装 wheel 后
重新生成并验证地图。

## 许可证

[MIT](LICENSE)
