<div align="center">

# Interactive Map Builder

**把已有空间数据交给 AI Agent，得到可搜索、可汇报、可验证、可直接交付的地图产品。**

[![CI](https://github.com/xlbaoxl/interactive-map-builder/actions/workflows/ci.yml/badge.svg)](https://github.com/xlbaoxl/interactive-map-builder/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/xlbaoxl/interactive-map-builder)](https://github.com/xlbaoxl/interactive-map-builder/releases)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![MapSpec 1.1](https://img.shields.io/badge/MapSpec-1.1-0f766e)](references/map-spec.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-2ea44f.svg)](LICENSE)

[产品主页](https://xlbaoxl.github.io/interactive-map-builder/zh-CN/) ·
[English](README.md) ·
[版本发布](https://github.com/xlbaoxl/interactive-map-builder/releases) ·
[更新日志](CHANGELOG.md)

</div>

Interactive Map Builder 是一个**以 Codex 为主要使用场景、兼容 Agent Skills 工作流**的地图
Skill。用户只需要描述想得到什么成果，并提供 GeoJSON、GeoPackage、Shapefile、CSV、Excel 或
ArcGIS 数据；Agent 会检查输入、只补齐真正阻塞构建的信息差、写入可审计的 MapSpec，再由确定性
引擎生成并验证最终地图成果。

```text
已有空间数据 → 检查 → 集中确认 → MapSpec → 构建 → 验证 → 可发送 HTML + 可选静态图件
```

产品始终以地图为主界面：帮助用户**找到空间对象、理解空间上下文、保存重点视角，并把结果直接
交付**，而不是把页面继续扩张成通用 BI Dashboard。

## 核心产品能力

- **搜索与筛选。** 按名称或属性查找对象，筛选类别和数值范围，排序结果，并查看要素详情；不必
  为了每个问题重新打开桌面 GIS。
- **图层控制。** 在中性总览和重点图层之间切换，同时独立控制图层显隐、图例和底图，避免把
  “当前重点浏览谁”和“哪些上下文可见”混成一件事。
- **保存视角。** 在当前浏览器中保存最多 8 个命名的 Center + Zoom 位置，在探索和汇报时快速
  返回“总览”或重点场地。保存视角不修改 MapSpec，也不会回写交付的 HTML 文件。
- **成果交付。** 默认交付自包含的 `map.html`；只有用户明确需要时，才生成 16:9 汇报图或论文用
  PNG/SVG/PDF。

## 两种地图产品

| 地图＋清单 | 多图层地图 |
| --- | --- |
| [![地块分类统计地图](assets/screenshots/zh-CN/map-list.png)](https://xlbaoxl.github.io/interactive-map-builder/zh-CN/map-list/) | [![点线面多图层地图](assets/screenshots/zh-CN/multilayer.png)](https://xlbaoxl.github.io/interactive-map-builder/zh-CN/multilayer/) |
| **地图＋清单。** 通过清单—地图联动完成搜索、筛选、排序、动态统计和对象详情查看，适合地块、建筑、设施、门店、项目、事件与候选地点。 | **多图层。** 从总览进入图层聚焦，独立控制多个空间主题的显隐和上下文，查看对象详情，并保存汇报中需要反复返回的视角；适合边界、道路、线路、设施、环境与规划背景。 |
| [打开交互地图 →](https://xlbaoxl.github.io/interactive-map-builder/zh-CN/map-list/) | [打开交互地图 →](https://xlbaoxl.github.io/interactive-map-builder/zh-CN/multilayer/) |

两个在线地图都由仓库中的确定性引擎根据固定的
[NYC Open Data 数据快照](assets/examples/SOURCES.md)生成，是实际产品输出，不是另外绘制的设计稿。

## 探索 → 聚焦 → 汇报

```mermaid
flowchart LR
    A["探索<br/>搜索 · 筛选 · 切换图层"] --> B["聚焦<br/>查看一个地点的空间上下文"]
    B --> C["汇报<br/>保存并快速返回重点视角"]
```

一个常见工作流是：先看完整地图，再逐步聚焦到一个或多个值得讲的地点，最后在会议或汇报中
需要准确回到这些位置。**保存视角**补上了最后一步：它只记录浏览器本地的 Center + Zoom，保留
固定“总览”，支持重命名和删除，并与地图数据及 MapSpec 构建契约保持分离。

## 直接描述成果，不必记住工具名称

下面这些表达都属于 Skill 应当识别的任务：

```text
这张 Excel 已经有经纬度，请做成一个能按设施名称搜索、按类型筛选、点击查看详情并分享给
同事的浏览器页面。
```

```text
把地块、道路、水系、绿地和停车位放到一张规划汇报地图里，可以独立开关图层、查看对象信息，
并保存几个汇报时需要反复返回的重点视角。
```

```text
同事电脑没有 ArcGIS，请把这些现有图层做成一个 HTML 文件，同时导出一张 16:9 汇报图。
```

用户仍然可以显式调用 `$interactive-map-builder`，但在任务匹配时不需要知道 Skill 名称。

## 快速开始

### 1. 在 Codex 中安装 Skill

打开一个新的 Codex 任务，发送：

```text
$skill-installer 请从 https://github.com/xlbaoxl/interactive-map-builder 安装这个 Skill，并安装它需要的 Python 依赖。安装后运行 interactive-map-builder doctor 和 interactive-map-builder update --preflight。
```

安装完成后新建任务。如果新任务中没有出现该 Skill，再重启一次 Codex。从 v0.4.3 开始，
`$skill-installer` 产生的仓库复制件只有在所有 Release 管理文件与官方校验包完全一致时，才会
自动转为可更新安装。

### 2. 上传数据并描述目标

```text
把我上传的空间数据做成可以搜索和筛选的中文交互地图，同时导出一张 16:9 汇报图。
```

Skill 会先检查数据，并在仍有不确定项时维护一份简短需求清单：

```markdown
- [x] Confirmed：用户已明确，或数据已经证明
- [~] Inferred：Skill 根据数据提出的建议，可以修改
- [ ] Needs confirmation：构建前必须确认
```

它只会集中询问一次真正影响结果的内容，例如 CRS、模板、主图层、分类含义、展示字段、输出
格式和地图受众语言。

### 3. 验证安装结果

```bash
interactive-map-builder doctor
interactive-map-builder update --preflight
```

`doctor` 会在临时目录中生成一张坐标表，离线完成数据读取、地图构建、Leaflet 资源检查和输出
哈希验证，返回 JSON 结果后删除临时文件。该命令不会下载底图，也不会发送使用统计。更新命令
返回结构化 JSON，明确给出本地版本、可确认的官方版本、结果来源、安装类型和状态。仅需缓存状态
查询时，运行 `interactive-map-builder update --check`。

安装后优先运行 `interactive-map-builder doctor`。若在源码目录中尚未生成该命令，可使用
`python scripts/cli.py doctor`；`python scripts/map_builder.py --help` 只列出内部构建命令，
不能据此判断正式安装包缺少 `doctor`。

<details>
<summary><strong>适合持续自动更新的 Git 手动安装</strong></summary>

Codex 只保留一个活动 Skill 目录，避免 `.codex` 与 `.agents` 同时存在重复副本。
旧版 Windows 安装位置可能是 `$HOME\.agents\skills`；使用下方活动目录前先将其归档。

**Windows PowerShell**

```powershell
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { "$HOME\.codex" }
New-Item -ItemType Directory -Force "$CodexHome\skills" | Out-Null
git clone https://github.com/xlbaoxl/interactive-map-builder.git `
  "$CodexHome\skills\interactive-map-builder"
Set-Location "$CodexHome\skills\interactive-map-builder"
py -m pip install .
interactive-map-builder doctor
interactive-map-builder update --preflight
```

**macOS 或 Linux**

```bash
CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$CODEX_ROOT/skills"
git clone https://github.com/xlbaoxl/interactive-map-builder.git \
  "$CODEX_ROOT/skills/interactive-map-builder"
cd "$CODEX_ROOT/skills/interactive-map-builder"
python3 -m pip install .
interactive-map-builder doctor
interactive-map-builder update --preflight
```

</details>

<details>
<summary><strong>从正式版本安装</strong></summary>

从 v0.3.1 开始，每个 GitHub Release 会同时发布：

- `interactive-map-builder-skill-vX.Y.Z.zip`：包含 `SKILL.md`、Agent 元数据、参考文档、确定性
  引擎和网页资源的精简 Skill 包；
- Python wheel 与源码包：用于常规 Python 安装；
- `SHA256SUMS.txt`：用于发行资产校验和受管 Skill 安全更新。

精简 Skill 包不包含演示数据、截图、测试和 CI 文件。将它解压到 Agent Skills 目录后，运行
`python -m pip install .`，再运行 `interactive-map-builder doctor`。

</details>

<details>
<summary><strong>在 Claude Code 或其他 Agent Skills 客户端中使用</strong></summary>

把完整仓库或正式版本中的 Skill ZIP 放到客户端能够读取的 Skill 或规则目录，让它加载
`SKILL.md`，然后安装一次确定性引擎：

```bash
python -m pip install .
interactive-map-builder doctor
```

工作流不依赖特定客户端界面：检查数据、维护需求清单、写入当前 MapSpec、使用打包引擎构建、
验证并交付完整 `dist` 目录。

</details>

## 为可靠交付而构建

面向用户的交互建立在同一条确定性构建路径之上，而不是每次临时拼一个不同的网页：

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
 Atlas Studio Light 解析器
  几何 · 密度 · 角色 · 层级
          │
          ▼
     确定性 Python 引擎
      读取 · 规范化 · 渲染
          │
          ▼
 校验数量、文件、QA 接口、
 数据来源、哈希和浏览器交互
          │
          ▼
 可发送 HTML + 汇报与论文图件
```

打包的 [JSON Schema](scripts/mapcore/resources/map-spec.schema.json) 是 MapSpec 唯一的机器契约。
配置只接受规范的 `snake_case` 字段；不支持的字段和 Schema 版本会被直接拒绝，不会静默迁移。

## 版本更新、计划模式与公网发布

每次 Skill 任务开始时，Agent 会从 Skill 根目录运行
`interactive-map-builder update --preflight`。该命令只检查版本：有效结果最多缓存 24 小时，
不会修改当前安装；版本已是最新时保持静默，只有发现新版本或检查失败时才提示。断网不会阻塞
地图制作。设置 `IMB_DISABLE_AUTO_UPDATE=1` 可以关闭更新检查。

安装更新属于独立维护动作。`update --apply` 与兼容保留的 `update --auto --force` 继续执行 Release
校验、Manifest 校验、精确复制安装接管、本地修改保护、重复目录拒绝、安装后 doctor 和失败回滚，
普通地图任务不再修改正在运行的 Skill。

v0.3.2—v0.4.2 本身尚未包含复制安装接管逻辑。已经安装的无 `.git`、无 Manifest 旧副本需要
通过官方 v0.4.3 做一次重新安装；此后的兼容版本即可自动更新。

更新采用事务式处理：替换经过校验的版本后会重新安装引擎并运行离线 `doctor`；安装或体检失败
时，自动恢复此前的 Git 提交或原清单管理的全部文件。应用失败时仍保留已经确认的官方版本、
Release 地址和 `update_available=true`，不会再把“存在新版本”静默改写为“没有更新”。完整规则
见[安全更新策略](references/update-policy.md)。

当 Codex 任务确实复杂，例如包含多个独立图层、多个待确认设计选项，或需要协调 HTML、汇报图和
论文图时，Agent 可以在第一轮用一句话将 Plan mode 作为可选建议。用户不切换也会立即继续检查
数据；明确的单图层任务不会收到这项提示。

正常交付物是可移动、可发送的本地 `map.html`。“发给同事”表示发送文件，不等于把内嵌空间数据
发布到互联网。只有用户明确提出公开网址时，才会在确认托管平台和数据公开权限后进入独立部署
流程；公网托管不属于地图构建的默认输出。

## Atlas Studio Light 视觉系统

v0.4 引入的是轻量视觉默认值解析器，不是一套全包式自动设计系统。当 MapSpec 没有明确填写
底层视觉参数时，引擎根据几何类型、粗粒度要素/坐标密度、模板角色和稳定绘制顺序生成一版
克制的初始图面：

- 密集点图层自动使用更小的点和更低的填充强度；
- 点、线、面分别使用适合自身的尺寸、填充和描边；
- `map-list` 主图层保持突出，背景图层自动后退；
- 多图层地图打开时保持所有可见图层的基础样式，用户选择图层后才进入聚焦状态；
- HTML、图例、卡片、PNG、SVG 和 PDF 共用同一份解析结果；
- 自动分类配色最多使用八个明确颜色，不再循环形成彩虹图。

用户或 Agent 明确写入的 MapSpec 参数始终优先。系统只负责提供达到总体协调、可以继续汇报和
修改的起点，不替代规划师或设计师完成项目专属表达。用户仍可通过自然语言或直接编辑 MapSpec
继续调整颜色、尺寸、透明度、字段和层级。所有推断结果都会记录在 `build_report.json` 的
`visual` 与 `visual_system` 中。

## 产品行为与地图控件

`map-list` 可以在主搜索图层之外附带行政区、道路等背景图层。`multilayer` 则明确区分**搜索焦点**
和**图层显隐**：选择当前重点浏览的图层不会自动隐藏其他空间上下文。两种产品都支持保存视角，
并使用同一份解析后的视觉方案生成地图与图例。

新建 MapSpec 默认包含两张不需要用户凭证的在线底图：以浅色、低干扰的 **CARTO Positron**
为默认底图，**OpenStreetMap Standard** 用于查看详细道路与地名。底图选择器还提供**无底图**，
在线瓦片连续失败时会自动回退，因此业务图层、搜索和图层控制仍然可用。**Esri World Imagery**
仅在用户提供经过授权的服务地址或令牌，并接受浏览器端凭证可能出现在 HTML 中时加入。

多图层产品将图层开关固定在控制区上方，图例排列在下方；图例内容过长时内部滚动，窄屏默认
收起，因此大量分类不会再遮挡图层关闭按钮。

## 支持的数据

| 输入格式 | 要求 |
| --- | --- |
| GeoJSON / JSON FeatureCollection | 几何和 CRS 可正常读取 |
| GeoPackage | 包含多个候选图层时需要明确选择 |
| Shapefile ZIP | 每个 ZIP 只放一套 Shapefile；保留 `.cpg`/GDAL 编码识别 |
| CSV | 具有经纬度字段或 WKT，并明确源 CRS |
| Excel | 具有经纬度字段或 WKT，并明确源 CRS |
| ArcGIS FeatureServer | 先下载为本地 GeoJSON 快照，再进入地图构建 |

在推荐地图之前，检查阶段会输出要素数量、几何类型、CRS、字段样例、候选 ID、名称、分类字段、
歧义和性能提示。

## 交付内容

| 文件 | 用途 |
| --- | --- |
| `map.html` | 内嵌业务几何和全部界面逻辑的本地单文件 Leaflet 地图 |
| `map_slide_16x9.png` | 启用汇报 preset 时生成的 1920×1080 图片 |
| `map_paper.png` / `.svg` / `.pdf` | 启用论文 preset 时生成的出版图件 |
| `map_spec.json` | 解析后的可复用构建契约 |
| `inspection.json` | 输入、CRS、字段候选和待确认项 |
| `build_report.json` | 数量、修复、警告、性能、哈希和可移植状态 |
| `DELIVERY_MANIFEST.json` | 事务性交付管理的文件归属、大小和 SHA-256 清单 |
| `README_USAGE.md` | 面向地图接收者的本地化使用说明 |

普通构建不会复制源数据，`map_spec.json` 只作为原项目中的构建记录。需要把整个结果移动到其他
电脑后独立重建时，使用 `--bundle-sources`。

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

Interactive Map Builder 专注于**已有空间数据 → 可交付地图成品**，目前不负责：

- 把地址批量转换成坐标；
- 缓冲区、叠加、路径规划、选址模型和统计推断；
- 矢量瓦片服务和千万级要素 WebGIS；
- 离线底图下载；
- 根据坐标数值猜测 CRS；
- 三维地形、建筑和数字孪生；
- 维护已有的定制 Leaflet 或 React 应用；
- 在用户没有明确提出部署且未确认数据公开权限时自动发布公网网址。

对于较大的 GeoJSON，构建报告会建议使用 `light` 或 `medium` 几何简化，但不会在用户不知情时
切换渲染引擎。

## 项目状态

当前稳定版本为 **v0.5.1**。v0.5 为两种现有地图产品加入浏览器本地持久化的保存视角；v0.5.1
进一步保证命名视角较多、需要横向滚动时，“总览”、保存和管理入口仍保持可见。MapSpec 继续
保持 1.1，两种既有模板不变。

已经完成的变化见[更新日志](CHANGELOG.md)。

## 开发与测试

```bash
python -m pip install -r requirements-dev.txt
python scripts/evaluate_triggers.py validate
python -m pytest -q -m "not browser"
python -m playwright install chromium
python -m pytest -q -m browser
```

构建中英文 GitHub Pages 演示和精简 Skill 发行包：

```bash
python scripts/build_demo_site.py --output _site
python scripts/build_skill_package.py
```

CI 覆盖 Python 3.9–3.12、触发评估集验证、Chromium 交互测试、wheel 构建、离线安装体检、Windows
smoke、仓库外构建验证和 Skill ZIP。新包版本通过 `main` CI 后，Release 工作流会创建版本与资产；
若同一版本的 Release 已存在但资产不完整，则补齐资产而不会移动已有标签。

## 许可证

[MIT](LICENSE)
