# keep-data-sim-main 安全审查

审查范围：仓库内 Python 源码、`pyproject.toml`、测试、工具 HTML、README、许可证和本地文件列表。审查日期：2026-10-26。

说明：当前目录没有 `.git` 元数据，因此无法从本地确认提交历史、远程来源或文件是否被改写；以下是对当前工作区内容的静态审查，不等同于作者身份或供应链证明。

## 结论

未发现明显恶意代码。项目是一个本地 GPX/FIT 生成器，主要进行数学计算、读取用户指定的 GPX/JSON/CSV 文件和写入用户指定的输出目录。

## 检查到的行为

- `keep_data_sim` 使用 `numpy` 生成路线、配速、心率、海拔和步频，并使用 `gpxpy` / `garmin-fit-sdk` 导出文件。
- `fit_shift.py` 和 `fit_binary_shift.py` 读取 FIT、调整时间戳并写入新文件；它们要求输出路径与输入不同，使用独占创建，避免覆盖原文件。
- 路线导入器只读取 GPX、JSON、CSV；JSON/CSV 被解析为坐标，不执行其中内容。
- `core/simulator.py` 创建输出目录并写入 GPX/FIT；文件名经过安全字符过滤。
- 原项目核心未发现 `subprocess`、`Popen`、`os.system`、shell 调用、socket、动态 `eval`/`exec`、`pickle`/`marshal`、凭据/环境秘密读取、注册表持久化、删除文件或混淆载荷。
- `tools/hand_drawn_map.html` 明确从 `https://unpkg.com/leaflet@1.9.4` 加载 Leaflet，并从 `https://{s}.tile.openstreetmap.org` 加载地图瓦片；这属于外部联网行为，应在严格离线环境禁用或替换为本地资源。它不参与本 GUI 的执行路径。

## 依赖风险

依赖为 `gpxpy`、`garmin-fit-sdk`、`numpy`，Windows 额外使用 `tzdata`；开发依赖为 `pytest`、`pytest-cov`。依赖安装前仍应从 PyPI/锁定版本来源核对包名、版本和哈希。仓库没有 lockfile，依赖可能随时间变化。

## 本 GUI 的执行边界

`gui.py` 仅绑定 `127.0.0.1`，不接受远程连接；表单参数经过允许选项过滤，调用使用 Python 参数数组和 `shell=False`，没有拼接 shell 命令。执行目录固定为项目根目录，超时 180 秒，输出截断到 12000 字符。它不会自动安装依赖，也不会上传文件或调用 Keep。GUI 自身使用本地回环 HTTP 供浏览器展示，不代表原项目需要联网。

## 限制

本审查是静态审查，不能证明第三方依赖没有漏洞，也没有审计 Python 解释器、操作系统或浏览器。安装依赖、导入不可信路线文件或运行生成的文件前，应先在隔离环境中测试。GPX/FIT 是否被 Keep 接受取决于 Keep 的导入支持和校验。
