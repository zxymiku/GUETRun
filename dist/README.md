# dist

本目录仅用于存放本地构建产物，**不纳入 Git 版本库**（根 `.gitignore` 中的 `dist/*` 已排除，仅保留本说明文件）。

本地可能生成的典型文件：

- `run-simulator-debug.apk` / `lasted.apk`：`build-native.ps1` 或 Gradle 构建的调试包；
- `run-simulator-debug.apk.idsig`：APK 签名中间文件；
- `run-simulator-source.zip`：本地打包的源码压缩包；
- `map-editor-v1.6-test.png`：`tests/MapPageTest.cjs` 生成的地图页面截图。

正式分发的 APK 由 GitHub Actions 在 Release 中提供，请查看仓库的 Releases 页面。发布流程见 [GITHUB_RELEASE_GUIDE.md](../GITHUB_RELEASE_GUIDE.md)。

调试签名仅适合个人测试；不同机器的调试证书不同，覆盖安装失败时请先卸载旧包。
