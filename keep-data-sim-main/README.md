# Keep Data Simulator 项目手册

Keep Data Simulator 是一个用于生成运动轨迹数据的 Python 命令行工具。它可以模拟跑步或骑行活动，生成带有 GPS 轨迹、时间戳、速度、心率、海拔和步频/踏频的数据文件，并导出为 GPX 或 FIT 格式。

本项目适合用于测试运动 App、数据导入流程、轨迹展示、运动指标分析，以及需要构造可复现运动记录的场景。

## 功能概览

- 支持运动类型：跑步 `running`、骑行 `cycling`
- 支持输出格式：GPX、FIT
- 支持路线类型：
  - 环形路线 `circular`
  - 往返路线 `out_and_back`
  - 指定途经点路线 `waypoint`
  - 导入 GPX 路线 `gpx_import`
  - 导入 JSON/CSV 坐标文件 `coord_file`
  - 从手绘地图工具导出的 JSON 路线 `hand_drawn`
- 支持配速策略：
  - 匀速 `constant`
  - 后半程加速 `negative_split`
  - 后半程减速 `positive_split`
  - 间歇训练 `interval`
- 支持模拟心率、海拔、步频/踏频、GPS 噪声
- 支持随机种子 `--seed`，便于复现实验结果

## 项目结构

```text
keep_data_sim/
  cli.py                  # 命令行入口和参数解析
  __main__.py             # 支持 python -m keep_data_sim
  config/
    schema.py             # 配置 dataclass 定义
    defaults.py           # 默认配置相关模块
  core/
    simulator.py          # 主模拟流程：路线 -> 指标 -> 导出
    registry.py           # 路线生成器和导出器注册表
    types.py              # TrackPoint 数据结构
  route/
    circular.py           # 环形路线
    out_and_back.py       # 往返路线
    waypoint.py           # 途经点路线
    gpx_import.py         # GPX 导入路线
    coord_file.py         # JSON/CSV 坐标导入路线
    hand_drawn.py         # 手绘地图 JSON 导入路线
    noise.py              # GPS 噪声和平滑
  metrics/
    pace_strategy.py      # 配速/速度策略
    heart_rate.py         # 心率曲线生成
    elevation.py          # 海拔曲线生成
    cadence.py            # 步频/踏频生成
  export/
    gpx_exporter.py       # GPX 导出
    fit_exporter.py       # FIT 导出
tools/
  hand_drawn_map.html     # 手绘路线辅助工具
tests/
  __init__.py             # 测试目录
pyproject.toml            # 项目元数据、依赖和 CLI 注册
```

## 环境要求

- Python 3.10 或更高版本
- 依赖包：
  - `gpxpy`
  - `garmin-fit-sdk`
  - `numpy`

开发测试额外依赖：

- `pytest`
- `pytest-cov`

## 安装与运行

### 可视化控制台

仓库附带一个本地可视化控制台，会将表单转换成 `keep-data-sim` 参数并显示完整命令；点击生成后在项目目录执行。它不自动安装依赖，执行前请先完成下方虚拟环境安装。

```powershell
.\.venv\Scripts\Activate.ps1
.\run_gui.ps1
```

浏览器打开 `http://127.0.0.1:8765`。控制台使用参数数组和 `shell=False`，只绑定本机回环地址。安全审查见 [`SECURITY_REVIEW.md`](SECURITY_REVIEW.md)。

建议在虚拟环境中安装：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

安装开发依赖：

```powershell
python -m pip install -e ".[dev]"
```

安装后可以直接使用命令：

```powershell
keep-data-sim --help
```

也可以使用模块方式运行：

```powershell
python -m keep_data_sim --help
```

## 快速开始

生成一条默认 5 公里跑步记录，输出 GPX 和 FIT 文件到当前目录：

```powershell
keep-data-sim
```

生成 10 公里跑步，配速 5:00/km，输出到 `outputs` 目录：

```powershell
keep-data-sim --distance 10000 --pace 5:00 --output-dir outputs
```

生成骑行记录，平均速度 28 km/h，只导出 GPX：

```powershell
keep-data-sim --sport cycling --distance 30000 --speed 28 --format gpx --output-dir outputs
```

只预览模拟摘要，不写入文件：

```powershell
keep-data-sim --distance 5000 --pace 5:30 --dry-run
```

使用固定随机种子，保证每次生成结果一致：

```powershell
keep-data-sim --distance 5000 --pace 5:30 --seed 42
```

## 常用参数

### 基础参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--sport` | `running` | 运动类型，可选 `running`、`cycling` |
| `--distance` | `5000.0` | 目标距离，单位米 |
| `--pace` | `5:30` | 跑步配速，格式为 `M:SS` 或分钟小数 |
| `--speed` | `None` | 骑行平均速度，单位 km/h |
| `--start-time` | 当前 UTC 时间 | 开始时间，格式 `YYYY-MM-DD HH:MM:SS` |
| `--timezone` | `Asia/Shanghai` | FIT 本地时间使用的 IANA 时区 |
| `--treadmill` | 关闭 | 生成无 GPS 轨迹的 Garmin 跑步机 FIT；未指定格式时只输出 FIT |
| `--start-lat` | `39.9042` | 起点或中心点纬度 |
| `--start-lon` | `116.4074` | 起点或中心点经度 |
| `--title` | 自动生成 | 活动标题，也是导出文件名基础 |
| `--seed` | `None` | 随机种子 |

注意：`--start-time` 会按 UTC 时间写入轨迹文件。如果希望生成北京时间 `2026-06-16 07:30:00` 对应的 UTC 时间，需要传入 `2026-06-15 23:30:00`。

### 路线参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--route-type` | `circular` | 路线类型 |
| `--route-radius` | `2000.0` | 环形路线半径，单位米 |
| `--out-distance` | `5000.0` | 往返路线单程距离参数，当前主流程按总距离的一半生成往返 |
| `--bearing` | 随机 | 往返路线方向角，单位度 |
| `--waypoints` | `None` | 途经点，格式 `lat1,lon1;lat2,lon2;...` |
| `--point-spacing` | `10.0` | 轨迹点间距，单位米 |
| `--gps-noise` | `3.0` | GPS 噪声标准差，单位米 |
| `--import-file` | `None` | 导入路线文件路径 |

### 配速策略参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--pace-strategy` | `constant` | 可选 `constant`、`negative_split`、`positive_split`、`interval` |
| `--split-ratio` | `0.95` | 分段策略比例 |
| `--interval-fast` | `4:30` | 跑步间歇快段配速 |
| `--interval-slow` | `6:30` | 跑步间歇慢段配速 |
| `--interval-fast-speed` | `30.0` | 骑行间歇快段速度，km/h |
| `--interval-slow-speed` | `18.0` | 骑行间歇慢段速度，km/h |
| `--interval-fast-dur` | `240.0` | 快段持续时间，秒 |
| `--interval-slow-dur` | `120.0` | 慢段持续时间，秒 |
| `--warmup-dur` | `300.0` | 热身持续时间，秒 |
| `--warmup-factor` | `0.8` | 热身速度系数 |

### 心率、海拔和步频参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--hr-resting` | `60` | 静息心率 |
| `--hr-avg` | `145` | 目标平均心率 |
| `--hr-max` | `190` | 最大心率 |
| `--hr-lag` | `30.0` | 心率响应滞后，秒 |
| `--hr-noise` | `3.0` | 心率随机噪声，bpm |
| `--elevation-mode` | `synthetic` | 海拔模式，可选 `synthetic`、`flat` |
| `--elevation-gain` | `50.0` | 总爬升，米 |
| `--hill-count` | `3` | 模拟坡段数量 |
| `--start-elevation` | `50.0` | 起始海拔，米 |
| `--cadence-avg` | 跑步 170 / 骑行 85 | 平均步频或踏频 |

### 输出参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--output-dir` | `.` | 输出目录 |
| `--format` | `gpx fit` | 输出格式，可以传一个或多个 |
| `--dry-run` | 关闭 | 只打印摘要，不生成文件 |

## 路线类型说明

### 环形路线

默认路线类型。从中心点附近生成一条闭合或近似闭合的路线。

```powershell
keep-data-sim --route-type circular --start-lat 39.9042 --start-lon 116.4074 --distance 8000 --route-radius 1200
```

### 往返路线

从起点出发，沿某个方向前进后返回。未指定 `--bearing` 时会随机选择方向。

```powershell
keep-data-sim --route-type out_and_back --distance 10000 --bearing 90
```

### 途经点路线

通过 `--waypoints` 指定多个经纬度点。至少需要两个点。

```powershell
keep-data-sim --route-type waypoint --distance 6000 --waypoints "39.9042,116.4074;39.9142,116.4174;39.9082,116.4274"
```

如果最后一个点与第一个点距离超过 50 米，程序会自动补一段回到起点附近。

### 导入 GPX 路线

读取已有 GPX 文件中的 track 或 route 点，并按目标距离缩放、重采样和加噪声。

```powershell
keep-data-sim --route-type gpx_import --import-file route.gpx --distance 10000
```

### 导入 JSON/CSV 坐标文件

JSON 支持两种格式：

```json
[
  {"lat": 39.9042, "lon": 116.4074},
  {"lat": 39.9142, "lon": 116.4174}
]
```

或：

```json
[
  [39.9042, 116.4074],
  [39.9142, 116.4174]
]
```

CSV 支持带表头或不带表头：

```csv
lat,lon
39.9042,116.4074
39.9142,116.4174
```

运行示例：

```powershell
keep-data-sim --route-type coord_file --import-file route.csv --distance 5000
```

### 手绘路线

打开 `tools/hand_drawn_map.html`，在地图上点击绘制路线并导出 JSON。导出的文件可通过 `hand_drawn` 路线类型导入。

```powershell
keep-data-sim --route-type hand_drawn --import-file hand_route.json --distance 5000
```

手绘工具导出的典型结构：

```json
{
  "points": [
    {"lat": 39.9042, "lng": 116.4074},
    {"lat": 39.9142, "lng": 116.4174}
  ]
}
```

## 输出文件

程序会用活动标题生成文件名。若未指定 `--title`，默认标题为：

- 跑步：`Run YYYY-MM-DD`
- 骑行：`Ride YYYY-MM-DD`

例如：

```powershell
keep-data-sim --title "Morning Run" --format gpx fit --output-dir outputs
```

会生成：

```text
outputs/Morning_Run.gpx
outputs/Morning_Run.fit
```

GPX 文件包含 Garmin TrackPointExtension，用于记录心率和步频/踏频。FIT 文件按 Garmin Activity 的 summary-last 结构写入创建者设备信息、Timer Start/Stop、record、lap、session 和 activity，并包含本地时间。跑步输入步频使用双脚步数/分钟（例如 170 spm），导出时会转换为 FIT 单脚周期并写入步幅；骑行踏频保持 rpm，不做折半。

### 跑步机模式

跑步机模式按一秒间隔生成距离、速度、心率、步频和步幅，不生成室外路线，也不会在 FIT Record 中写入经纬度或海拔。Sport、Lap 和 Session 会标记为 Garmin `treadmill` 子类型。速度和步频使用平滑相关波动，心率包含热身上升和后程漂移，步幅由实时速度与步频联动计算；指定的总距离、总时间、平均心率和平均步频保持不变。该模式只支持 FIT 输出。

```powershell
keep-data-sim --treadmill --distance 10000 --pace 6:00 `
  --warmup-dur 0 --hr-avg 153 --cadence-avg 170 `
  --format fit --output-dir generated
```

## 模拟流程

主流程位于 `keep_data_sim/core/simulator.py`：

1. 校验配置：`validate_config(config)`
2. 根据 `route.type` 从注册表选择路线生成器
3. 生成经纬度坐标序列
4. 根据路线点计算累计距离
5. 根据配速策略计算每个点的速度和时间戳
6. 生成海拔曲线
7. 生成与速度相关的心率曲线
8. 生成与速度相关的步频/踏频
9. 组装为 `TrackPoint`
10. 按指定格式导出文件

## 配置校验规则

当前校验规则包括：

- 距离必须大于 0
- 运动类型只能是 `running` 或 `cycling`
- `waypoint` 路线至少需要两个途经点
- `gpx_import`、`coord_file`、`hand_drawn` 必须提供 `--import-file`
- 导入文件必须存在
- 配速策略只能是已注册策略
- 跑步平均配速必须在 2 到 12 分钟/公里之间
- 骑行平均速度必须在 5 到 60 km/h 之间
- 静息心率必须小于最大心率
- 平均心率必须介于静息心率和最大心率之间
- 输出格式只能是 `gpx` 或 `fit`
- 环形路线半径必须大于 0
- 往返路线距离参数必须大于 0

## 开发指南

### 运行测试

```powershell
pytest
```

如需覆盖率：

```powershell
pytest --cov=keep_data_sim
```

### 新增路线类型

1. 在 `keep_data_sim/route/` 下新增一个实现 `RouteGenerator` 的类。
2. 实现 `generate(config, distance_m, rng)`，返回 `list[tuple[float, float]]`。
3. 在 `keep_data_sim/core/registry.py` 的 `_ROUTE_GENERATORS` 中注册新类型。
4. 在 `keep_data_sim/cli.py` 的 `--route-type` choices 中加入新类型。
5. 如果需要额外参数，在 `RouteConfig` 和 CLI 参数中补充。
6. 增加测试或至少使用 `--dry-run` 验证。

### 新增导出格式

1. 在 `keep_data_sim/export/` 下新增一个实现 `Exporter` 的类。
2. 实现 `export(points, config, output_dir, title)`。
3. 在模块末尾调用 `register_exporter("format_name", ExporterClass)`。
4. 在 `Simulator._export()` 中确保该导出器模块会被导入。
5. 在 `validate_config()` 和 CLI `--format` choices 中加入新格式。

### 新增指标模拟

推荐做法：

1. 在 `keep_data_sim/metrics/` 下新增生成函数。
2. 在 `config/schema.py` 中新增对应配置 dataclass 或字段。
3. 在 `Simulator._apply_metrics()` 中调用并写入 `TrackPoint` 或新的数据结构。
4. 更新 GPX/FIT 导出器，让新指标真正写入文件。

## 常见问题

### 为什么生成距离与传入距离略有差异？

路线生成会经过插值、缩放、GPS 噪声和平滑，最终会尽量裁剪到目标距离附近。不同路线类型有 3% 到 5% 左右的容差。

### 为什么 GPX/FIT 的时间与本地时间不同？

程序内部使用 UTC 时间写入轨迹文件。许多运动平台导入后会按本地时区展示，这是正常现象。

### 可以导入 Keep 吗？

本项目生成的是通用 GPX/FIT 运动数据文件。是否能导入 Keep，取决于 Keep 当前版本是否支持外部文件导入，以及平台对 GPX/FIT 字段的兼容性。

### 如何让数据更真实？

可以组合调整：

- 增加 `--gps-noise` 让轨迹更像真实 GPS
- 使用 `--elevation-mode synthetic` 和合适的 `--elevation-gain`
- 调整 `--hr-avg`、`--hr-noise`、`--hr-lag`
- 使用 `--pace-strategy interval` 模拟间歇训练
- 使用真实 GPX 或手绘路线作为基础路线

## 示例命令集合

5 公里晨跑：

```powershell
keep-data-sim --distance 5000 --pace 5:20 --title "Morning Run" --output-dir outputs
```

10 公里后半程变化跑：

```powershell
keep-data-sim --distance 10000 --pace 5:10 --pace-strategy negative_split --split-ratio 0.95 --output-dir outputs
```

骑行 40 公里：

```powershell
keep-data-sim --sport cycling --distance 40000 --speed 30 --cadence-avg 88 --title "Weekend Ride" --output-dir outputs
```

平路跑，不模拟爬升：

```powershell
keep-data-sim --distance 5000 --elevation-mode flat --start-elevation 35 --output-dir outputs
```

使用导入路线，只导出 FIT：

```powershell
keep-data-sim --route-type gpx_import --import-file route.gpx --distance 12000 --format fit --output-dir outputs
```

## 当前限制

- 主要通过 CLI 使用，暂未提供配置文件入口。
- 当前测试覆盖的是核心入口、配速策略和基础模拟流程，路线导入和导出兼容性仍可继续扩展测试。
- FIT 导出字段覆盖基础运动记录，复杂设备字段、训练效果、卡路里等尚未模拟。
- GPX 导出包含心率和步频/踏频扩展，但不同平台解析扩展字段的表现可能不同。

## 许可证

本项目采用 MIT License。完整许可证也已放在仓库根目录的 `LICENSE` 文件中。

```text
MIT License

Copyright (c) 2026 Keep Data Simulator contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 修改已有 FIT 活动日期

可以把原 FIT 活动整体移动到指定的北京时间，并由 Garmin FIT SDK 重建 CRC：

```powershell
keep-data-sim shift-fit .\original.fit `
  --start-time "2026-07-24 07:30:00" `
  --output .\modified.fit
```

默认时区是 `Asia/Shanghai`，不指定输出路径时生成 `<原文件名>_shifted.fit`。原文件及已存在的输出文件不会被覆盖。详细说明见 [`docs/FIT_DATE_SHIFT.md`](docs/FIT_DATE_SHIFT.md)。
