# GitHub 上传与手动发布指南

本文说明本仓库哪些文件不应上传到 GitHub，以及如何通过手动触发 GitHub Actions 完成编译并发布 Release。

## 1. 不进入 Git 仓库的内容

根目录 [`.gitignore`](.gitignore) 与 [`keep-data-sim-main/.gitignore`](keep-data-sim-main/.gitignore) 共同生效。`keep-data-sim-main` 的源码本身保留在仓库中（MIT 许可），但其运行环境和生成物不提交。

| 路径 / 类型 | 内容 | 是否上传 | 原因与处理方式 |
| --- | --- | --- | --- |
| `.tools/`（约 727 MB） | 本地 Android SDK、build-tools、platform、`debug.keystore`、测试类、Gradle 压缩包 | 否 | 体积远超 GitHub 单文件与仓库建议上限；CI 使用官方 `setup-android` 安装 SDK 35，调试签名由 runner 临时生成。 |
| `dist/`（除 `README.md`） | `*.apk`、`*.idsig`、源码 zip、地图测试截图 | 否 | 属于构建产物；发布时由 Actions 编译 APK 并作为 Release 附件提供。仅保留 `dist/README.md` 说明目录用途。 |
| `audit-hashes.txt` | 带本机绝对路径的文件哈希清单 | 否 | 属于本机审计产物，会泄露本地目录结构，且无法在 CI 复现。 |
| `reference-readme.txt` | 本地参考资料（当前为空） | 否 | 非项目源码，原 `.gitignore` 已排除。 |
| `.venv/`、`venv/`、`__pycache__/`、`*.py[cod]` | `keep-data-sim-main` 的 Python 虚拟环境与字节码 | 否 | 约 11 MB，且与操作系统、Python 版本绑定；应由开发者本地创建。 |
| `.pytest_cache/`、`.ruff_cache/`、`.mypy_cache/`、`htmlcov/`、`.coverage*` | Python 测试与覆盖率缓存 | 否 | 可随时重新生成。 |
| `keep-data-sim-main/outputs/`、`test_data/`、`*.gpx`、`*.fit`、`*.tcx` | 生成的轨迹与运动数据 | 否 | 体积大、含位置数据，且属于测试输入/输出而非源码。 |
| `app/build/`、`build/`、`.gradle/`、`.kotlin/` | Gradle / Android 编译缓存和 APK 中间产物 | 否 | 每次构建自动生成；CI 会从源码重新编译。 |
| `local.properties` | 本机 Android SDK 路径 | 否 | 与机器绑定，CI 通过 `ANDROID_HOME` 提供 SDK。 |
| `*.jks`、`*.keystore`、`keystore.properties`、`signing.properties`、`.env*` | 签名密钥与本地配置 | 否 | 属于机密；本仓库使用调试签名，不保存发布密钥。 |
| `.idea/`、`*.iml`、`.vscode/`、`.DS_Store`、`Thumbs.db` | IDE / 操作系统文件 | 否 | 个人环境配置，易产生无意义冲突。 |
| `test-results/`、`playwright-report/`、`node_modules/`、`*.log`、`tmp/` | 测试输出、依赖与日志 | 否 | 可重新生成。 |

会正常上传的内容包括：`app/src/`（Java 与 HTML 资源）、`tests/`、`gradle/wrapper/`、`gradlew`、`gradlew.bat`、`build.gradle`、`settings.gradle`、`build-native.ps1`、`README.md`、`MAP_GUIDE.md`、`THIRD_PARTY_NOTICES.md`、`keep-data-sim-main/` 源码与许可证，以及本文和 `.github/` 下的工作流。

> 仓库不应包含任何高德地图 Key / 安全密钥。地图密钥由使用者在应用内填写，保存在本机。

## 2. 手动发布工作流

工作流文件：[`.github/workflows/release.yml`](.github/workflows/release.yml)。它只通过 `workflow_dispatch` 手动触发，不会在每次 push 时自动发布。

执行步骤：

1. 拉取完整 Git 历史与标签（`fetch-depth: 0`），用于计算自上次 Release 以来的提交。
2. 确定版本号、`versionCode` 和标签；默认读取 `app/build.gradle`，也可在触发时覆盖。
3. 查询最近一次已发布的 Release（排除 draft，包含 Pre-release），作为变更范围的起点。
4. 安装 JDK 17、缓存 Gradle、安装 Android SDK Platform 35 与 Build-Tools 35.0.0。
5. 运行纯 Java 检查：`RunMathTest`、`MapGeometryTest`、`ActivityTimeTest`。
6. 执行 `./gradlew :app:assembleDebug`，生成调试签名 APK。
7. 将 APK 重命名为 `run-simulator-v<版本>-debug.apk`，计算 SHA-256，并上传为 Actions artifact（保留 30 天）。
8. 生成 Release 说明，并调用 `gh release create` 创建标签与 Release，附加 APK。

APK 使用 Android 调试签名。不同机器生成的调试证书不同，如果手机上已安装本地构建的调试包，安装 Release 包前可能需要先卸载旧包。

### 触发方式

1. 将代码推送到 GitHub 仓库的默认分支（工作流文件必须存在于默认分支，Actions 页面才会显示该工作流）。
2. 打开仓库的 **Actions** → **Build & Release APK** → **Run workflow**。
3. 选择分支并按需填写参数，点击 **Run workflow**。
4. 运行结束后查看 Job Summary 或仓库 **Releases** 页面。

建议从默认分支（通常是 `main`）触发。若从其他分支触发，Release 标签会指向该分支的提交，提交范围也以该提交为准；未合并的提交会出现在发布说明中。

### 输入参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `version` | `app/build.gradle` 的 `versionName` | APK 版本名，例如 `1.7.1`；CI 会在本次 runner 内改写 `app/build.gradle`，不提交回仓库。 |
| `version_code` | `app/build.gradle` 的 `versionCode` | 必须为整数，且应随版本递增。 |
| `tag` | `v<version>` | Release 标签。标签已存在时发布步骤会失败，避免覆盖历史版本。 |
| `prerelease` | `false` | 勾选后创建 Pre-release。 |
| `publish` | `true` | 取消勾选则只编译并上传 Actions artifact，不创建 Release；适合先验证编译。 |

版本号规则：`1.7`、`1.7.1`、`1.7.0-beta.1` 均可；默认标签分别为 `v1.7`、`v1.7.1`、`v1.7.0-beta.1`。同一版本重复发布时，请提升 `version`/`version_code`，或手动指定新的 `tag`。

推荐在正式发布前先修改 `app/build.gradle`：

```gradle
defaultConfig { applicationId 'com.local.runsimulator'; minSdk 26; targetSdk 35; versionCode 9; versionName '1.7.1' }
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
javac -encoding UTF-8 -d .tools/test-classes app/src/main/java/com/local/runsimulator/RunMath.java app/src/main/java/com/local/runsimulator/MapGeometry.java app/src/main/java/com/local/runsimulator/ActivityGenerator.java app/src/main/java/com/local/runsimulator/FitWriter.java tests/RunMathTest.java tests/MapGeometryTest.java tests/ActivityTimeTest.java
java -cp .tools/test-classes RunMathTest
java -cp .tools/test-classes MapGeometryTest
java -cp .tools/test-classes ActivityTimeTest
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
- 本项目的用途与限制（模拟定位可能被 Keep 拒绝、勿用于真实运动成绩）仍以根目录 [README.md](README.md) 为准。
