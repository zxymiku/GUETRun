# 专用跑步机 FIT 模式设计

## 目标与基准

新增明确的 `--treadmill` 模式，生成 Garmin Connect 可识别的室内跑步活动。该模式不构造室外路线，也不在 FIT Record 中写入经纬度或海拔。参考文件 `612464936_ACTIVITY.fit` 显示 Garmin 的跑步步频使用单脚周期：其 Session 平均值为 86.515625 rpm，对应 Garmin Connect 展示约 173 spm；平均步幅为 998.5 mm。生成器继续接受双脚步频 spm，并在 FIT 中折半写入整数与小数步频。

## 数据流

配置新增 `treadmill: bool`，CLI 通过 `--treadmill` 启用。跑步机模拟不调用路线生成器，而是按一秒采样推进时间和距离；每个采样点根据现有配速策略获取速度，最后一个不足一秒的区间按剩余距离截断。心率和步频仍复用现有模型，海拔固定为起始值，因此总爬升和下降均为零。内部 TrackPoint 保留占位坐标以避免扩大类型改动，但 FIT 导出器在跑步机模式下完全不写位置和高度字段。

FIT 的 Sport、Lap 和 Session 消息统一写入 `sport=running`、`sub_sport=treadmill`。Record 保留 timestamp、distance、speed、heart_rate、cadence、fractional_cadence 和 step_length。步幅使用 `速度 × 60000 ÷ 双脚步频` 得到毫米；Session/Lap 平均步幅使用总距离除以总步数，确保距离、步频和步幅物理一致。跑步机模式只支持 FIT；CLI 未显式指定格式时自动选择 FIT，显式请求 GPX 时由配置校验拒绝。

## 验证

回归测试覆盖 CLI 默认输出选择、非法骑行/GPX 组合、1 Hz 距离与时间推进、绕过路线生成器、FIT 无 GPS/海拔、treadmill 子类型，以及步频和步幅计算。端到端生成 10 km、6:00/km、平均心率 153 的文件，再使用 Garmin FIT SDK 开启 CRC 校验解码，核对距离 10000 m、计时 3600 s、平均心率 153、合理步频/步幅和零 GPS 记录。
