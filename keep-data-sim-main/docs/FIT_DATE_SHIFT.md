# 修改已有 FIT 活动日期

`shift-fit` 可以把已有 FIT 活动移动到新的开始时间，同时保留原活动的轨迹、持续时间、心率、配速、功率、圈数及其他消息。

## 使用方法

以下命令把活动开始时间修改为北京时间 `2026-07-24 07:30:00`：

```powershell
keep-data-sim shift-fit .\original.fit `
  --start-time "2026-07-24 07:30:00" `
  --output .\modified.fit
```

也可以使用模块入口：

```powershell
python -m keep_data_sim shift-fit .\original.fit `
  --start-time "2026-07-24 07:30:00" `
  --output .\modified.fit
```

`--timezone` 默认是 `Asia/Shanghai`，因此通常不用额外填写。如果输入的是其他时区的当地时间：

```powershell
keep-data-sim shift-fit .\original.fit `
  --start-time "2026-07-24 07:30:00" `
  --timezone Europe/London
```

未提供 `--output` 时，程序会在原文件旁生成 `original_shifted.fit`。

## 安全与兼容性

- 原文件不会被覆盖；输入和输出不能是同一路径。
- 已存在的输出文件不会被覆盖。
- 输入文件必须通过 FIT CRC 校验。
- 所有由 Garmin FIT SDK 识别的时间字段会按同一时间差移动。
- 输出由 Garmin FIT SDK 重新编码，并在写入后再次进行 CRC 解码验证。

如果原文件包含当前 Garmin FIT SDK 不认识的厂商私有消息，程序会跳过这些无法重编码的消息，并在结果中报告数量；标准轨迹、圈数和会话消息仍会完整保留并验证。

## 保留 Garmin 原始结构

对于包含设备私有消息的 Garmin 原生 FIT，推荐使用原结构模式：

```powershell
keep-data-sim shift-fit .\original.fit `
  --start-time "2026-07-18 05:49:46" `
  --timezone Asia/Shanghai `
  --preserve-structure `
  --output .\modified.fit
```

该模式直接平移原始数据记录中的 UTC 与本地时间值，保持协议版本、消息定义、私有消息、文件长度和记录顺序不变，并重新计算 CRC。