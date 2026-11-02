# Garmin Connect 兼容 FIT 导出设计

## 目标

让模拟器直接生成符合 Garmin Activity 文件结构、可供 Garmin Connect 导入的 FIT 文件，同时保持现有轨迹、心率、步频、海拔、圈和会话统计。

## 设计

导出顺序采用 Garmin 推荐的 summary-last 模式：`file_id`、创建者 `device_info`、`sport`、Timer Start、所有 `record`、Timer Stop、`lap`、`session`、`activity`。Timer Start 与首个记录使用相同 UTC 时间，Timer Stop 与最后一个记录使用相同 UTC 时间。

`activity.local_timestamp` 根据配置时区生成。配置新增 `timezone_name`，CLI 新增 `--timezone`，默认 `Asia/Shanghai`。UTC 时间仍按原有 `--start-time` 规则输入；本地时间只用于 FIT 的时区偏移字段。

文件创建者不再冒用 Garmin 厂商和产品。`file_id` 与 `device_info` 使用 FIT 的 `development` 厂商 ID、稳定产品号和 `Keep Data Simulator` 产品名；`device_info.device_index` 设为 Creator。

步频统一采用运动语义正确的口径：模拟器中的跑步步频是双脚总步数/分钟，FIT `cadence` 按单脚周期/分钟写入，并用 `fractional_cadence` 保留半步精度；骑行踏频保持原 rpm。跑步 record 的 `step_length` 由速度和双脚步频计算，lap/session 的 `avg_step_length` 由总距离和总步数计算，`total_cycles` 对跑步按总步幅数积分。

## 验证

测试解码生成文件并检查 CRC、消息顺序、两个 Timer 事件、本地时间偏移、创建者身份、跑步步频/步幅、骑行踏频，以及 Lap/Session 的必需字段。随后实际生成跑步和骑行样本，验证 Garmin SDK 解码无错误。
