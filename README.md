# 运动数据生成器（Android）

本地生成 GPX / FIT 运动轨迹文件的 Android 应用。按距离、配速、路线和可选指标计算轨迹，通过系统“另存为”选择保存位置。

**本项目只保留文件生成功能。** 原实时模拟定位、前台定位服务、模拟位置应用设置及相关权限已全部移除；应用不会向系统注入位置，也不会写入 Keep 或其他账号。

## 功能

- 输出 **GPX 1.1** 或 **FIT** 文件；支持预览后保存。
- 跑步 / 骑行，匀速、后半程加速、后半程减速、间歇四种配速策略。
- 路线：
  - 默认随机圆形路线；
  - 高德地图选点、田径场跑道、逐点连线、手指画线；
  - 闭合路线可按圈数重复，自动计算总里程与时长。
- 可选平均 / 最大心率、总爬升、步频或踏频、GPS 噪声、随机种子。
- 自定义跑步开始日期与时间（北京时间 Asia/Shanghai，1990–2099），自动计算结束时间，支持跨天、跨月、跨年和闰日。
- 系统“另存为”导出任意文件夹；保存后可分享最近文件。
- 不申请定位、前台服务、通知或存储权限；地图功能仅需联网。

## 使用

1. 安装 APK。安装包由本地构建或 GitHub Release 提供，使用 Android 调试签名。
2. 首次打开无需授予权限。地图和地点搜索需要联网，并需填写自己的高德 Web端（JS API）Key。
3. 输入距离和配速，页面实时显示运动总时间与结束时间；也可先选择开始日期 / 时间。
4. 需要路线时，点击“打开地图 · 选点 / 跑道 / 手绘”，绘制并保存后勾选“使用已保存的地图路线”。闭合路线可启用“按圈数生成”。
5. 点击“预览”检查摘要；点击“生成并另存为”，在系统保存窗口选择文件夹和文件名。
6. 保存成功后可用“分享最近文件”发送该 GPX / FIT。

地图的首次配置、绘制方式、圈数和精度说明见 [MAP_GUIDE.md](MAP_GUIDE.md)。

## 构建

要求：JDK 17 或 21、Android SDK Platform 35、Build-Tools 35.0.0。

使用 Android Studio 打开项目，或执行：

```powershell
./gradlew.bat :app:assembleDebug
```

输出：`app/build/outputs/apk/debug/app-debug.apk`。SDK 不在默认位置时，在本地 `local.properties` 设置 `sdk.dir`（该文件不提交）。

版本信息位于 [app/build.gradle](app/build.gradle)：`versionCode 9`、`versionName 2.0`。

## 测试

纯 Java 计算、路线和导出检查：

```powershell
javac -encoding UTF-8 -d build/test-classes app/src/main/java/com/local/runsimulator/RunMath.java app/src/main/java/com/local/runsimulator/MapGeometry.java app/src/main/java/com/local/runsimulator/ActivityGenerator.java app/src/main/java/com/local/runsimulator/FitWriter.java tests/RunMathTest.java tests/MapGeometryTest.java tests/ActivityTimeTest.java
java -cp build/test-classes RunMathTest
java -cp build/test-classes MapGeometryTest
java -cp build/test-classes ActivityTimeTest
```

地图页面交互检查（需要 Playwright 与 Edge，可通过 `MAP_TEST_BROWSER` 指定浏览器）：

```powershell
node tests/MapPageTest.cjs
```

该检查使用本地替代地图接口，不需要密钥，也不验证高德实际服务或 Android WebView 真机表现。截图写入系统临时目录。

## 发布

仓库内的 [.github/workflows/release.yml](.github/workflows/release.yml) 支持在 Actions 页面手动运行 **Build & Release APK**：编译 `assembleDebug`、运行 Java 检查，并按“上一次 Release 之后的提交记录 + 提交人统计”生成发布说明，创建对应 Release。版本默认读取 `app/build.gradle`，也可在触发时覆盖。

参数、排除文件和排障说明见 [GITHUB_RELEASE_GUIDE.md](GITHUB_RELEASE_GUIDE.md)。

## 项目结构

```text
app/
  build.gradle
  src/main/
    AndroidManifest.xml
    assets/route-map.html          # 高德地图路线编辑器
    java/com/local/runsimulator/
      GeneratorActivity.java       # 主界面与系统保存流程
      ActivityGenerator.java       # 轨迹、指标与 GPX/FIT 数据生成
      FitWriter.java               # FIT 编码
      MapActivity.java             # 地图页容器
      MapGeometry.java             # 轨迹几何与坐标转换
      MapRouteStore.java           # 本机路线存储
      RunMath.java                 # 配速、时长与数值校验
    res/values/strings.xml
tests/                             # 纯 Java 与 Playwright 检查
LICENSES/                          # 第三方许可证文本
.github/                           # 手动发布工作流与说明生成脚本
```

## 边界与合规

- 生成的是本地 GPX / FIT 测试文件，**不会**自动上传或写入 Keep。第三方应用是否接受取决于其版本、导入入口和服务端校验，本项目不绕过这些校验。
- 不支持将文件直接伪装成真实运动记录，也不提供账号、排名或奖励相关功能。请仅用于自己的测试。
- 地图展示使用 GCJ-02，导出前转换为 WGS84；转换为近似算法，不承诺实地测量精度，也不自动贴合道路。
- 地图路线按球面距离计算；缩放、底图分辨率、卫星影像偏移和手动选点都会影响实际位置。
- 未在本轮进行 Android 真机地图加载或第三方导入验收。

## 第三方说明

高德地图 JS API、GPX / FIT 格式及相关归属见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
