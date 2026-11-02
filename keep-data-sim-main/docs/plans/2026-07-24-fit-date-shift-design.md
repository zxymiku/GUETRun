# FIT 活动日期修改设计

## 目标

为现有 `keep-data-sim` 增加一个命令，用指定的北京时间替换原 FIT 活动的开始时间，同时保留活动持续时间、轨迹、心率、功率、圈数、设备信息和开发者字段，并生成能通过 Garmin FIT SDK CRC 校验的文件。

## 方案

使用 Garmin FIT SDK 完整解码原文件。优先从 `session.start_time` 获取活动开始时间，缺失时依次回退到 `lap.start_time`、首条 `record.timestamp`。把用户输入的 `YYYY-MM-DD HH:MM:SS` 按 `Asia/Shanghai` 解析并转换为 UTC，计算新旧开始时间之差。

解码得到的所有 FIT 消息保持原顺序。所有由 SDK 解码成 `datetime` 的字段（包括列表中的时间字段）统一加上时间差；其他字段不修改。开发者字段描述先收集后交给编码器，随后由 SDK 重新编码全部消息，生成新的文件头和 CRC。

## 命令行

```powershell
keep-data-sim shift-fit original.fit `
  --start-time "2026-07-24 07:30:00" `
  --timezone Asia/Shanghai `
  --output modified.fit
```

`--timezone` 默认是 `Asia/Shanghai`。未指定 `--output` 时，在原文件旁生成 `<stem>_shifted.fit`。程序拒绝输入与输出为同一路径，避免覆盖原文件。

## 错误与验证

输入文件不存在、扩展名错误、CRC 无效、找不到活动开始时间、时区或时间格式无效时返回明确错误。输出写入后再次使用 SDK 开启 CRC 校验解码；若失败则删除不完整输出并报错。

测试使用项目导出器生成一个小型 FIT 样本，再检查新开始时间、所有时间字段的平移量、活动时长及非时间记录值不变，并覆盖 CLI 参数解析与防覆盖逻辑。
