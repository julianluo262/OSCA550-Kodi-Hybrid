OSCA-550 Kodi Hybrid Surface 云端编译包
请用 UTF-8 打开 README_中文.md 查看完整说明。

内容：
- .github/workflows/build-osca550-kodi.yml：GitHub Actions 云端构建工作流
- patches/enable_hybrid_defaults.py：首次默认启用 Hybrid MediaCodec Surface 的轻量设置补丁

重要：该构建尚未在本用户设备上验证。Hybrid Surface 的源代码来自 vkapartzianis/xbmc 的 Omega 分支（Meta Quest 3 fork），仅作为 OSCA-550 的试验版本，不保证能修复花屏。请保留原版 Kodi 并行安装测试。
