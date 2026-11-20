# OSCA-550 Kodi Hybrid Surface 云端编译包

目的：不在 Windows 电脑安装 Linux/WSL，在 GitHub Actions 云端编译一个 ARM64、与官方 Kodi 并存的测试 APK。

## 重要说明

- 本工作流从 `https://github.com/vkapartzianis/xbmc` 的 `Omega` 分支取源码。Hybrid MediaCodec Surface 实现已经在该分支中；本包不重新复制整套 C++/Java 渲染实现。
- `patches/enable_hybrid_defaults.py` 只把两个 Kodi 设置的首次默认值改为：关闭普通 MediaCodec Surface、开启 Hybrid MediaCodec Surface。它不是针对 OSCA-550 的底层解码补丁。
- 这个 Hybrid 方案最初是为 Meta Quest 设备开发，Kodi Issue #27862 中描述其渲染路径是 MediaCodec -> SurfaceTexture -> OpenGL shader -> 输出 Surface。尚未在荣耀 OSCA-550 上验证是否修复花屏。第一次构建的目标是实机 A/B 测试，而不是宣称已修复。
- 为避免和官方 Kodi 签名冲突，工作流把包名改为 `com.osca550.kodi`，安装后会成为独立 APP。它有独立 Kodi 用户数据目录，首次启动需要重新添加 NAS SMB 媒体源。
- 请保留原来的 Kodi，不要卸载；先并行安装测试版。
- 工作流基于 Kodi 官方 Android 交叉编译流程编写，固定 NDK r28c。GitHub 云端构建尚未在本项目实际运行过，第一次可能遇到上游依赖/构建差异，需要根据 Actions 日志修正。

## 最简单的使用步骤

### 1. 在 GitHub 建一个自己的公开仓库

1. 登录 GitHub。
2. 打开 `https://github.com/xbmc/xbmc`，或者直接新建一个空仓库，建议名称 `OSCA550-Kodi-Hybrid`。
3. 建议使用公开仓库以便使用 GitHub 公共仓库的 Actions 标准运行器。不要上传 NAS 密码、媒体列表、个人数据或私钥。
4. 在新仓库页面选择 **Add file -> Upload files**，把本 ZIP 解压后的所有文件和文件夹上传。请确保 `.github/workflows/build-osca550-kodi.yml` 的目录结构完整。
5. 点击 **Commit changes**。

### 2. 启用 Actions

1. 进入仓库 **Actions** 标签。
2. 如果出现启用提示，选择 **I understand my workflows, go ahead and enable them**。
3. 左侧应能看到 **Build Kodi OSCA550 Hybrid (Android ARM64)**。

### 3. 触发构建

1. 进入 Actions -> **Build Kodi OSCA550 Hybrid (Android ARM64)**。
2. 点击 **Run workflow**。
3. 保持默认分支，确认运行。
4. 在运行页面展开日志。构建步骤包括安装依赖、拉取源码、验证 Hybrid 实现、改默认设置、编译 depends、编译 Kodi、打包 APK。
5. 成功后在同一运行页面底部的 **Artifacts** 下载 `Kodi-OSCA550-Hybrid-ARM64`。

首次完整构建会花较长时间；如果失败，打开失败步骤，复制从第一个 `error` / `fatal` 附近开始的日志，而不是只发最后一行。

## 安装与第一次测试

1. 解压下载的 artifact ZIP，得到 APK。
2. 复制 APK 到 U 盘，在电视上安装。
3. 保留原版 Kodi；新版本的包名是 `com.osca550.kodi`，应该并存。
4. 打开新 Kodi，进入 **设置 -> 播放器 -> 视频**，确认能看到 `Allow hardware acceleration - MediaCodec (Hybrid Surface)`。工作流已经把它设为默认开启，并关闭普通 `MediaCodec Surface`。
5. 用相同的原始样片 1、2、3 测试，并记录：是否花屏、是否流畅、HDR 色彩是否异常、暂停/拖动/退出是否正常。

## 当前限制

- 目前是“全局启用 Hybrid Surface”的首轮验证版，不是按 HDR10 自动切换。先证明这条渲染路径在 OSCA-550 上有用，再开发按视频流特征自动选择。
- 该分支还包含 Quest 设备专属代码；Hybrid Surface 开关本身在 issue 中被作者描述为非 Quest 专属，但厂商设备适配仍需实机验证。
- 本工作流没有把 vkapartzianis 的改动合并到 Kodi 官方仓库；它只是从该第三方分支编译。
- 公开仓库意味着源码和工作流公开可见。不要把 NAS 账号密码写进 `sources.xml`、workflow 或提交历史。

## 文件说明

- `.github/workflows/build-osca550-kodi.yml`：GitHub Actions 云端 ARM64 构建流程。
- `patches/enable_hybrid_defaults.py`：把 Hybrid Surface 设置设为首次默认开启的轻量补丁。

## 依据

- Kodi Android build guide（21.3 Omega）：https://github.com/xbmc/xbmc/blob/21.3-Omega/docs/README.Android.md
- Hybrid Surface fork issue：https://github.com/xbmc/xbmc/issues/27862
- Hybrid 实现分支：https://github.com/vkapartzianis/xbmc/tree/Omega
