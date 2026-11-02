# GitHub 上传与手动发布指南

本文说明本仓库哪些内容不应提交到 GitHub，以及如何通过手动触发 GitHub Actions 完成编译并发布 Release。

## 1. 不进入 Git 仓库的内容

规则位于根目录 [`.gitignore`](.gitignore)。

| 路径 / 类型 | 内容 | 是否上传 | 原因与处理方式 |
| --- | --- | --- | --- |
| `app/build/`、`build/`、`.gradle/`、`.kotlin/`、`captures/` | Gradle / Android 编译缓存、APK 中间产物、测试类 | 否 | 每次构建自动生成；CI 从源码重新编译。 |
| `*.apk`、`*.aab`、`*.idsig`、`*.hprof` | 安装包、签名中间文件、内存转储 | 否 | 二进制构建产物；APK 由 Actions 编译后作为 Release 附件提供。 |
| `local.properties` | 本机 Android SDK 路径 | 否 | 与机器绑定；CI 通过 `ANDROID_HOME` 提供 SDK。 |
| `.tools/` | 本地 Android SDK / 工具链（如果自行创建） | 否 | 体积大且与机器绑定；CI 使用 `setup-android` 安装所需平台。 |
| `dist/`、`test-output/` | 本地发布包、测试截图等 | 否 | 构建或测试产物，可重新生成。 |
| `*.gpx`、`*.fit`、`*.tcx` | 生成的轨迹 / 运动数据 | 否 | 属于导出结果，可能包含位置信息。 |
| `*.jks`、`*.keystore`、`keystore.properties`、`signing.properties`、`.env*` | 签名密钥与本地配置 | 否 | 属于机密；本仓库使用临时调试签名，不保存发布密钥。 |
| `test-results/`、`playwright-report/`、`node_modules/`、`*.log`、`*.tmp`、`tmp/` | 测试输出、依赖与日志 | 否 | 可重新生成。 |
| `.idea/`、`*.iml`、`.vscode/`、`.DS_Store`、`Thumbs.db` | IDE / 操作系统文件 | 否 | 个人环境配置，易产生无意义冲突。 |

会正常提交的内容：`app/src/`（Java、HTML 资源与 `res/values/strings.xml`）、`tests/`、`gradle/wrapper/`、`gradlew`、`gradlew.bat`、根目录 Gradle 配置、`README.md`、`MAP_GUIDE.md`、`THIRD_PARTY_NOTICES.md`、`LICENSES/`、`.gitignore`、`.gitattributes`，以及 `.github/` 下的工作流和说明生成脚本。

> 仓库不应包含任何高德地图 Key / 安全密钥。地图密钥由使用者在应用内填写，只保存在本机。

## 2. 手动发布工作流

工作流文件：[`.github/workflows/release.yml`](.github/workflows/release.yml)。仅通过 `workflow_dispatch` 手动触发，不会在每次 push 时自动发布。

执行步骤：

1. 拉取完整 Git 历史与标签（`fetch-depth: 0`），用于计算自上次 Release 以来的提交。
2. 确定版本号、`versionCode` 和标签；默认读取 `app/build.gradle`，也可在触发时覆盖。
3. 查询最近一次已发布的 Release（排除 draft，包含 Pre-release），作为变更范围的起点。
4. 安装 JDK 17、缓存 Gradle、安装 Android SDK Platform 35 与 Build-Tools 35.0.0。
5. 运行纯 Java 检查：`RunMathTest`、`MapGeometryTest`、`ActivityTimeTest`。
6. 执行 `./gradlew :app:assembleDebug`，生成调试签名 APK。
7. 将 APK 重命名为 `run-data-generator-v<版本>-debug.apk`，计算 SHA-256，并上传为 Actions artifact（保留 30 天）。
8. 生成 Release 说明，并调用 `gh release create` 创建标签与 Release，附加 APK。

APK 使用 Android 调试签名。不同机器生成的调试证书不同；如果手机上已安装其他调试版，安装 Release 包前可能需要先卸载旧包。

### 触发方式

1. 将代码推送到 GitHub 仓库的默认分支（工作流文件必须存在于默认分支，Actions 页面才会显示该工作流）。
2. 打开仓库的 **Actions** → **Build & Release APK** → **Run workflow**。
3. 选择分支并按需填写参数，点击 **Run workflow**。
4. 运行结束后查看 Job Summary 或仓库 **Releases** 页面。

建议从默认分支（通常是 `main`）触发。若从其他分支触发，Release 标签会指向该分支的提交，提交范围也以该提交为准；未合并的提交会出现在发布说明中。

### 输入参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `version` | `app/build.gradle` 的 `versionName` | APK 版本名，例如 `2.0.1`；CI 会在本次 runner 内改写 `app/build.gradle`，不提交回仓库。 |
| `version_code` | `app/build.gradle` 的 `versionCode` | 必须为整数，且应随版本递增。 |
| `tag` | `v<version>` | Release 标签。标签已存在时发布会失败，避免覆盖历史版本。 |
| `prerelease` | `false` | 勾选后创建 Pre-release。 |
| `publish` | `true` | 取消勾选则只编译并上传 Actions artifact，不创建 Release；适合先验证编译。 |

版本号规则：`2.0`、`2.0.1`、`2.1.0-beta.1` 均可；默认标签分别为 `v2.0`、`v2.0.1`、`v2.1.0-beta.1`。同一版本重复发布时，请提升 `version` / `version_code`，或手动指定新的 `tag`。

推荐在正式发布前先修改 `app/build.gradle`：

```gradle
defaultConfig {
    applicationId 'com.local.runsimulator'
    minSdk 26
    targetSdk 35
    versionCode 10
    versionName '2.0.1'
}
```

## 3. Release 说明如何生成

生成脚本：[`.github/scripts/generate-release-notes.sh`](.github/scripts/generate-release-notes.sh)。

- 起点：GitHub API 返回的最近一个非 draft Release 标签；如果该标签不存在于当前历史中，会给出警告并按首次发布处理。
- 范围：`<上次标签>..HEAD`。首次发布时使用全部历史。
- 内容：
  - 版本、变更范围、提交数量、提交人数；
  - 按提交人分组的提交记录（短哈希链接、日期、提交标题）；
  - `Co-authored-by` 尾注中的协作提交人；
  - 提交人统计表；
  - 代码变更统计（`git diff --shortstat`）；
  - 与上次发布的 GitHub compare 链接；
  - APK 附件大小与 SHA-256（由工作流追加）。
- 合并提交不计入“提交”数量。

如果上次 Release 之后没有新提交，说明中会明确显示“没有新的提交”，但仍会创建 Release。

## 4. 本地检查

不依赖 Actions 的验证方式：

```powershell
# 编译调试 APK（需要 Android SDK Platform 35、JDK 17+）
./gradlew.bat :app:assembleDebug

# 纯 Java 计算与时间检查
javac -encoding UTF-8 -d build/test-classes app/src/main/java/com/local/runsimulator/RunMath.java app/src/main/java/com/local/runsimulator/MapGeometry.java app/src/main/java/com/local/runsimulator/ActivityGenerator.java app/src/main/java/com/local/runsimulator/FitWriter.java tests/RunMathTest.java tests/MapGeometryTest.java tests/ActivityTimeTest.java
java -cp build/test-classes RunMathTest
java -cp build/test-classes MapGeometryTest
java -cp build/test-classes ActivityTimeTest
```

地图页面检查（需要 Playwright 与 Edge）：

```powershell
node tests/MapPageTest.cjs
```

检查忽略规则：

```powershell
git status --ignored --short
```

## 5. 常见问题

| 现象 | 处理 |
| --- | --- |
| 提示“标签已存在” | 提升 `version` 与 `version_code`，或指定新的 `tag`。不要删除已发布标签来覆盖版本。 |
| `Resource not accessible by integration` | 确认工作流包含 `permissions: contents: write`，且仓库 Settings → Actions → General 允许工作流创建 Release。 |
| 首次发布说明包含全部历史 | 正常行为：仓库还没有可比较的 Release。 |
| 上次发布标签不在当前历史 | 说明中会警告并按首次发布处理；检查标签是否被删除或分支被重写。 |
| Android SDK / license 安装失败 | 重跑工作流；确认 `platforms;android-35` 与 `build-tools;35.0.0` 可下载。 |
| Gradle 下载超时 | 重跑；wrapper 使用 Gradle 8.9，Gradle 缓存由 `gradle/actions/setup-gradle` 管理。 |
| 手机上安装失败（签名冲突） | 先卸载本地调试版；CI 的调试证书与本地不同。 |

## 6. 安全边界

- 发布不需要在仓库中配置签名密钥；`GITHUB_TOKEN` 由 Actions 临时提供，仅用于当前运行。
- 工作流不会上传 `.tools/`、`local.properties`、密钥库或用户填写的高德地图 Key。
- 产物是调试签名 APK，只适合个人测试，不应作为正式分发或应用商店包。
- 本应用只生成本地 GPX / FIT 文件，不模拟系统位置，也不写入 Keep 或其他账号。第三方是否接受文件由对方校验决定，相关限制见 [README.md](README.md)。
