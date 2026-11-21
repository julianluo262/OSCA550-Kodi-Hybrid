**OSCA-550 Kodi 诊断包 v1：下一轮怎么做**

下一轮比较两个 APK：A 保留原来的透明 Surface；B 仅把视频 Surface 格式改为不透明。两版都有相同的异常日志和 Buffer 时序记录。这是诊断构建，尚未在电视验证，不能当作已经解决花屏的版本。

**一、运行诊断工作流**

仓库已包含诊断工作流和两个补丁脚本，原有 Hybrid 构建工作流继续保留。

打开 GitHub 的 Actions，选择 **Build OSCA550 Kodi Diagnostic A and B (ARM64)**，点击 **Run workflow**。只需运行一次：依赖编译和主要 C++ 编译复用同一个构建目录，然后依次打包 A、B。

成功后下载 artifact：`OSCA550-Kodi-Diagnostic-A-B-ARM64`，里面应有：

```text
OSCA550-Diag-A-transparent-arm64.apk
OSCA550-Diag-B-opaque-arm64.apk
manifest-A.json
manifest-B.json
apk-badging-A.txt / apk-badging-B.txt
apk-signature-A.txt / apk-signature-B.txt
source-changes-A.patch / source-changes-B.patch
```

若 Actions 失败，提供报错步骤的文字或日志，先处理构建错误。工作流会尽量保留已完成的 APK；如果只完成 A，则可先取得 A 的诊断日志，不应把 A 文件改名当作 B 使用。

**二、先安装 A，再安装 B**

诊断版包名是 `com.osca550.kodi.diag`。现有 Kodi 的实际包名是 `org.xbmc.kodi`，因此诊断版作为独立应用安装，首次需要重新设置片源和存储访问权限；现有 Kodi 可以保留。

A 和 B 使用同一个诊断包名、同一次构建的同一个签名，依次覆盖安装即可。安装 A 后桌面名称为 `Kodi OSCA550 Diag A`，安装 B 后改为 `Kodi OSCA550 Diag B`，B 会沿用 A 的 Kodi 设置。不要在 A/B 之间卸载诊断版，以免丢失本轮配置。

同一次 Actions 的 A/B 可以直接互相覆盖。后续重新运行工作流时会尝试从缓存恢复签名；若缓存不存在而生成了新签名，可能需要卸载旧诊断版再安装，新签名不会影响另一个包名的现有 Kodi。

**三、A 的测试步骤**

1. 安装 `OSCA550-Diag-A-transparent-arm64.apk`，打开 **Kodi OSCA550 Diag A**。
2. 按需要允许存储访问，添加现有 SMB 共享目录。视频测试优先使用之前那个电视本地 MP4；日志仍可复制到 SMB。
3. 设置等级切到 Expert，核实 MediaCodec 开、MediaCodec (Surface) 开、Hybrid Surface 关。新配置的默认值已这样设置，Debug logging 也默认开启。
4. 正常退出并重新进入诊断版，从头播放同一片源约 20～30 秒。期间不快进或切换解码设置。记录“正常 / 花屏 / 黑屏 / 无法播放”，再停止播放。
5. 用文件管理器进入 `special://logpath/`，把 `kodi.log` 复制到 SMB。在电脑上将这份副本改名为 **A-kodi.log**，保留后再安装 B。

诊断版的实际存储路径由 HarmonyOS 决定，仍以 `special://logpath/` 或左上角 LOG 显示的路径为准，不要再使用旧包名的目录找日志。

**四、B 的测试步骤**

1. 退出 A，覆盖安装 `OSCA550-Diag-B-opaque-arm64.apk`。
2. 打开 **Kodi OSCA550 Diag B**，保持刚才三项开关和同一片源。
3. 同样从头播放 20～30 秒，记录结果，再停止播放。
4. 将本次 `kodi.log` 通过 SMB 导出，在电脑上命名为 **B-kodi.log**。
5. 提供 A/B 的播放结果，以及 **A-kodi.log、B-kodi.log** 两个文件。

日志中应能看到 `OSCA550-DIAG v1 A-transparent` 或 `OSCA550-DIAG v1 B-opaque`。如果标记不存在，需要先检查打开的是否为诊断版。

B 若导致黑屏、视频遮住菜单或其他显示问题，请记录现象，退出后装回同一次构建的 A 即可。这也是 Surface 图层对照的有效结果。

**结果如何判断**

| A | B | 下一步解释 |
|---|---|---|
| 花屏 | 正常 | 强烈支持视频 Surface 格式参与了兼容性问题，再回归测试其他样片和字幕/菜单 |
| 花屏 | 花屏 | 不透明 Surface 未解决；利用新增异常详情继续排查 flush 后旧 Buffer、MediaFormat 和海思输出 |
| 花屏 | 黑屏/菜单异常 | 不透明图层在当前合成方式下存在问题，回到 A 的路径继续排查 |
| 正常 | 正常 | 新配置或日志时序可能影响结果，先解释基线为何改变，不能直接归功于 B |
| 正常 | 花屏 | B 引入了回归，保留 A 并检查两份日志 |

**这次构建具体改了什么**

- 固定源码到日志对应的提交 `1c2da8772de76760e63cd4c30f2ea7143c660e80`，并核验六个关键源文件的 Git blob 哈希，防止补丁误套到其他版本。
- 从根目录 `version.txt` 修改 APP_PACKAGE，修复之前仅替换打包文件却未改变最终包名的问题；保持 APP_NAME 为 Kodi，避免改变依赖目录和原生库名称。
- 将现有 21 处 JNI 异常处理补充为写入 Java 堆栈到 kodi.log，保留原来的异常打印和清除行为。
- 给取出的 Buffer 记录诊断用 flush 序号，在释放、flush 和配置阶段打印索引及状态。前 64 次正常输出/释放有限记录，跨序号释放和异常继续记录。
- A/B 的有效播放设置相同；B 仅将 `PixelFormat.TRANSPARENT` 改为 `PixelFormat.OPAQUE`，另更新日志标识和桌面名称。
- 保留原工作流已用到的 NDK r26d、FFmpeg 下载校验、Samba Bionic 修补、privacy-policy.txt 和 file_paths.xml 打包修复。
- 导出前验证 APK 的包名、名称、ARM64 库、原生诊断标记和签名；校验 A/B 使用相同签名，避免交付错误或陈旧 APK。

本轮不改变 MediaCodec 的输入参数、HEVC 位流转换、flush 调用或 Buffer 释放策略，也不根据 color-format 或 stride 强行转换像素布局。先用可比较的结果确定后续修复点。

**当前验证范围**

本地已完成关键源码哈希、补丁应用、A/B 差异、重复应用和恢复、错误源码拒绝、Python 语法以及 16 段构建 shell 的语法检查。完整 Android C++/Java 编译、APK 打包与电视播放效果，仍需上述 GitHub Actions 和实机测试确认。
