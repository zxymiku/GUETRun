# 跑步模拟器（Android 原生）

支持距离、配速、时间三向换算，以及按真实时间发送环形模拟 GPS 轨迹。Java 编写，Android 8.0 及以上。1.4 新增高德官方地图选点、画圈、连线与手绘，地图使用联网加载的高德 JS API。

已生成可安装调试包：`dist/run-simulator-debug.apk`（该目录不入库）；GitHub Release 中提供由 Actions 编译的调试签名 APK。已通过 Android 35 接口编译、DEX 打包、APK v2/v3 签名校验，以及计算与路线自测；未完成真机和 Keep 读取验证。

### 1.1 排查 Keep 为 0 km

1.1 增加系统 `fused` 定位通道（仅在系统已有此通道时），GPS/网络/融合定位回调诊断、成功发送轮次和具体错误信息。系统融合通道不等于 Google Play Services 或厂商私有的融合接口，不能据此保证 Keep 支持。

覆盖安装 `dist/run-simulator-v1.1-debug.apk`，先停止旧模拟再重新开始。保持系统定位开启，Keep 使用户外跑步、精确位置权限，确认已正式开始且未暂停。配速 6:00/km 时，运行 2 分钟应模拟约 0.33 km；不要用跑步机模式验证 GPS。可先将起点设在实际所在位置附近，避免较大的初始位置跳变。

本应用底部的“定位诊断”会显示系统回读坐标和回调时间。若发送轮次增加但回读长期未收到，说明需继续排查系统位置分发；若回读持续变化而 Keep 仍为 0，可能涉及 Keep 使用不同定位接口、定位权限、运动状态或对模拟数据的过滤，单靠此诊断无法确定。点击“复制定位诊断（含坐标）”提供诊断时注意其中包含测试坐标。另请提供手机型号、Android 和 Keep 版本。当前未获得真机验证结果，不能将此版本视为 Keep 兼容性问题已解决。

## 与 Keep 的关系

本应用通过 Android `LocationManager.addTestProvider` / `setTestProviderLocation` 提供系统模拟位置，**不能直接写入 Keep 账户或保证生成有效记录**。Keep 可能通过融合定位、模拟标记、传感器或服务器校验拒绝这些数据；当前没有真机兼容性验证。运动时间由 Keep 自己计时，不能把 30 分钟运动瞬间写入。vivo V2425A / Android 15 / Keep 9.1.8 的一次现场诊断显示 GPS、network 和 fused 三通道持续回读模拟坐标，但 Keep 仍显示 0 km；这表明系统定位链路正常，尚不能证明 Keep 收到或接受了位置。

没有采用隐藏模拟标记、Root、Xposed 或修改 Keep 的方法，也没有声称 Keep 能导入 Health Connect 数据。请仅用于自己的测试，勿作为真实运动、奖励或比赛成绩提交。

## 使用

1. 安装 APK，点击“授权位置与通知”，允许**精确位置**。
2. 手机设置 → 关于手机 → 连续点击版本号开启开发者选项。在开发者选项的“选择模拟位置信息应用”中选择“跑步模拟器”。打开系统定位。
3. 输入距离、配速、时间中的任意两项，点击相应计算按钮。配速支持 `6:00` 或 `6.5`（6 分 30 秒）。开始模拟始终以当前距离和配速为准。
4. 修改起点 WGS84 经纬度与每圈距离；默认坐标仅为示例。路线预览为示意图，不是道路地图。中国地图常见的 GCJ-02 / BD-09 坐标需要自行转换后使用。
5. 点击开始模拟，再手动打开 Keep 的户外跑步，观察是否读取到位置，并手动开始运动。Keep 启动的时间差会影响其最终统计。
6. 返回本应用或通过通知栏停止模拟。到达目标距离也会自动停止；**Keep 需要自行结束运动**。

模拟会影响本机其他位置应用。正常停止会移除测试定位提供者；如果进程被系统强杀后定位异常，取消开发者选项中的模拟应用、开关系统定位，必要时重启手机。部分手机可能需要允许本应用后台运行。应用不申请后台定位权限，需在本应用可见时启动服务。

距离范围 0–100 km（不含 0），配速 2:00–60:00/km，总时长不超过 24 小时，每圈 100–10000 m，纬度限制 ±80°。轨迹采用局部平面近似，不适用于极区；不提供道路贴合、任意路线导入或运动历史导出。

## 编译

使用 Android Studio 打开本目录，安装 Android SDK Platform 35，使用 JDK 17 或 21，等待 Gradle 同步后 Build APK。Windows 命令行：

```powershell
./gradlew.bat :app:assembleDebug
```

SDK 不在默认位置时在本地 `local.properties` 设置 `sdk.dir`。输出：`app/build/outputs/apk/debug/app-debug.apk`。调试包适合个人安装测试。

### GitHub Actions 手动发布

仓库内的 [.github/workflows/release.yml](.github/workflows/release.yml) 支持在 Actions 页面手动运行 **Build & Release APK**：自动编译 `assembleDebug`、运行 Java 检查，并按“上一次 Release 之后的提交记录 + 提交人统计”生成发布说明，创建对应 Release。版本默认读取 `app/build.gradle`，也可在触发时覆盖。排除文件清单、参数说明和故障排查见 [GITHUB_RELEASE_GUIDE.md](GITHUB_RELEASE_GUIDE.md)。

也可使用随附的 `build-native.ps1 -SdkRoot <SDK目录>`，通过官方 SDK 的 javac / d8 / aapt / zipalign / apksigner 直接构建到 `dist/run-simulator-debug.apk`。本次交付 APK 使用此方式构建（Gradle 下载遇到网络与本机 Java 证书问题）。需安装 platform 35 和 build-tools 35.0.0。调试签名只适合个人测试。

纯 Java 计算与路线检查：

```powershell
javac -encoding UTF-8 -d .tools/test-classes app/src/main/java/com/local/runsimulator/RunMath.java tests/RunMathTest.java
java -cp .tools/test-classes RunMathTest
```

## 参考与实现边界

- 公开实现检索：[EnderWolf006/auto_runner](https://github.com/EnderWolf006/auto_runner)。其 README 提及按路线模拟 GPS，同时要求 Android 11、Root/Xposed。这里只调研其公开思路，未复制其代码。
- Android 原生 API：[LocationManager](https://developer.android.com/reference/android/location/LocationManager#addTestProvider(java.lang.String,boolean,boolean,boolean,boolean,boolean,boolean,boolean,int,int))、[模拟位置的标记](https://developer.android.com/reference/android/location/Location#isMock())、[位置前台服务要求](https://developer.android.com/develop/background-work/services/fgs/service-types#location)。
- 当前应用自行生成圆形路线，使用前台位置服务、单调时钟和部分唤醒锁每秒发送位置；模拟标记由 Android 自动设置。
- Gradle Wrapper 来自 Gradle 官方仓库，受其 Apache-2.0 许可约束。

## 真机验收

用较短距离先测试：授权和开发者设置完成 → 启动模拟 → 检查通知栏距离递增 → 检查位置应用/Keep 的响应 → 手动停止 → 检查真实定位恢复。另需验证拒绝权限、未选择模拟应用、切入后台、目标结束、通知停止和手机厂商后台限制。仅计算与路线测试通过不能代表 Keep 接入成功。

## keep-data-sim 可视化控制台

项目中还包含 keep-data-sim-main 的本地可视化控制台，可按距离、配速、路线、心率和输出目录生成命令并执行，生成 GPX/FIT 测试文件。入口和安全审查见 [keep-data-sim-main/README.md](C:/Users/miku/Documents/keep/keep-data-sim-main/README.md) 与 [SECURITY_REVIEW.md](C:/Users/miku/Documents/keep/keep-data-sim-main/SECURITY_REVIEW.md)。该工具只生成文件，不能绕过 Keep 对模拟数据的校验。

## 手机版文件生成

1.2 版 APK 启动后进入“手机运动数据生成器”，按原项目的路线、配速策略、心率、海拔和步频流程在本地生成 GPX/FIT；支持预览、保存和分享，并可从按钮进入旧版实时模拟定位页面。实现说明和许可证见 [THIRD_PARTY_NOTICES.md](C:/Users/miku/Documents/keep/THIRD_PARTY_NOTICES.md)。

1.3 版增加跑步总时间实时计算：修改里程或配速后立即更新，无需点击预览。例如 5 公里 × 6:00/公里 = 00:30:00，10 公里 × 5:30/公里 = 00:55:00；配速也支持小数分钟（6.5 等于 6:30）。输入为空或格式错误时显示提示。实时计算按匀速计算，变速/间歇策略的实际生成时长仍以预览结果为准；骑行模式请使用预览查看时长。

1.4 版增加高德地图路线编辑：地点搜索、标准 / 卫星图、地图选点、点圆心和圆边或输入半径画圈、逐点连线、手指画线、闭合选择、撤销和本机保存。首次需自行申请高德 **Web端（JS API）Key 与安全密钥**，在地图页配置。完整步骤见 [MAP_GUIDE.md](MAP_GUIDE.md)。地图功能仅用于本机 GPX / FIT 文件生成，旧版实时定位页面的路线设置独立。

1.5 版将文件导出改为系统“另存为”：点击 **生成并另存为**，在手机系统保存窗口选择文件夹（例如 Download / 下载），可修改文件名，然后点“保存”。GPX 和 FIT 均支持，不再将最终文件固定放在应用私有目录；也不需要“所有文件访问权限”。完成后显示文件名，系统能提供时会显示保存路径；可用“分享最近文件”分享该文件。取消会删除本次临时数据，保存失败可重新选择位置。生成内容会先暂存到应用缓存，以便切换到系统保存窗口后仍可导出，完成或取消后删除暂存。系统文件服务支持持久授权时，重启应用后也可分享最近保存的文件。

1.6 版优化地图编辑：可连续重新选点；各绘制方式保留独立草稿，支持撤销 / 重做；连线可拖动拐点，手绘支持多笔续接和单独的移动地图模式。原“画圈”升级为两直道、两半圆的田径场跑道，支持 400 / 800 米预设、手输单圈长度、拖动缩放与旋转、调整直道占比。闭合路线支持设置圈数，在地图页和首页均可修改，自动计算总里程和配速时长，并将完整轨迹按圈数重复到 GPX / FIT。例：400 米 × 5 圈 = 2 公里，6:00 配速为 12 分钟。系统“另存为”仍保留，可自行选择文件夹。安装包：`dist/run-simulator-v1.6-debug.apk`。详细操作见 [MAP_GUIDE.md](MAP_GUIDE.md)。

1.7 版新增自定义跑步开始日期 / 时间和自动结束时间。首页点击“选择日期”“选择时间”，或“设为当前时间”；均按北京时间（Asia/Shanghai）处理。日期支持 1990–2099 年，时间选择器为 24 小时制，选择到分钟（秒置 0）；默认及“当前时间”保留当前秒。开始时间固定为页面中显示的值，不会在点击预览或生成时偷偷改为当前时刻。结束时间由同一套轨迹生成逻辑自动计算，随里程、配速、圈数、配速策略及相关参数更新，支持跨天、跨月、跨年和闰日。例：2026-10-26 23:50 开始，5 公里、6:00 配速，结束为 2026-10-27 00:20。匀速、变速、间歇与骑行均使用实际生成时长；输入不完整或超出生成范围时显示错误，不显示过期的结束时间。时间计算在停止输入约 0.3 秒后在后台进行。

生成的 GPX / FIT 使用选定的开始时间和计算出的各采样点时间；预览及保存结果同时显示开始 / 结束。页面重建时保留开始时间和表单配置。界面时长和结束时间显示到秒（四舍五入），FIT 时间戳精度为秒，GPX 保留毫秒；文件中的 UTC 表示与界面的北京时间代表同一时刻。此设置用于文件生成；安装包：`dist/run-simulator-v1.7-debug.apk`。

地图采用 GCJ-02，保存和导出前转换到 WGS84；已画路线保持地理位置和大小，闭合绕圈或开放往返至目标里程。保留拐点，地图路线关闭随机 GPS 噪声。球面距离与实际道路距离可能不同，不承诺实测定位精度或自动贴路。

新增数值检查（坐标转换、绕圈、往返、拐点、时长和 GPX）：

```powershell
javac -encoding UTF-8 -d .tools/test-classes app/src/main/java/com/local/runsimulator/RunMath.java app/src/main/java/com/local/runsimulator/MapGeometry.java app/src/main/java/com/local/runsimulator/ActivityGenerator.java tests/RunMathTest.java tests/MapGeometryTest.java
java -cp .tools/test-classes RunMathTest
java -cp .tools/test-classes MapGeometryTest
```

地图页面交互检查（需要 Playwright 和 Edge，可通过 MAP_TEST_BROWSER 指定浏览器）：

```powershell
node tests/MapPageTest.cjs
```

此检查使用本地替代地图接口，不需要密钥，也不验证实际高德服务或 Android WebView 真机表现。

开始 / 结束时间与导出检查（包括跨天、跨年、闰日、多圈和变速策略）：

```powershell
javac -encoding UTF-8 -d .tools/test-classes app/src/main/java/com/local/runsimulator/RunMath.java app/src/main/java/com/local/runsimulator/MapGeometry.java app/src/main/java/com/local/runsimulator/ActivityGenerator.java app/src/main/java/com/local/runsimulator/FitWriter.java tests/ActivityTimeTest.java
java -cp .tools/test-classes ActivityTimeTest
```
