# OSCA550 Main10 诊断 C / D

A（透明 Surface）与 B（不透明 Surface）均花屏。A 没有发生 flush 或失效 Buffer 释放异常，因此 B 中的 IllegalStateException 不能被视为花屏的已证实根因。B 导出的 old.log 是 A 会话轮转后的日志。

这轮仅验证 MediaCodec 配置假设，尚未证实修复。两版均基于同一 Kodi 源码提交 `1c2da8772de76760e63cd4c30f2ea7143c660e80`，使用透明 Surface、直接 Surface 播放，保持 HEVC 数据转换、csd-0 注入、flush 和 Buffer 释放行为不变。

| 版本 | 对未加密的海思 HEVC Main10 的改变 |
|---|---|
| C：`C-main10-profile` | 保留原配置，增加 Android `profile=HEVCProfileMain10`（值 2） |
| D：`D-minimal-format` | 保留显式 Main10 profile、MIME、尺寸及 csd-0；省略 max-input-size、priority、operating-rate、rotation、tunneled-playback、色彩提示及静态 HDR 元数据 |

其他解码器和加密流保留原配置。没有把 FFmpeg level 150 直接当作 Android 的 level 枚举传入。

## 安装与测试

1. 先覆盖安装 `OSCA550-Diag-C-main10-profile-arm64.apk`，打开 **Kodi OSCA550 Diag C**。
2. 核实设置：MediaCodec 开、MediaCodec (Surface) 开、Hybrid Surface 关；开启调试日志。安装沿用之前诊断包的数据，已有设置可能覆盖安装包默认值。
3. 从头播放与 A/B 相同的本地原始样片 20～30 秒。第一轮不要拖动进度；记录正常、花屏、黑屏或无法播放，以及颜色、亮度是否异常。
4. 停止播放后，使用已验证可行的 SMB 复制方式导出 `special://logpath/kodi.log`，在电脑端命名为 `kodi-C.log`。先导出，再退出和安装下一版。
5. 退出 Kodi，覆盖安装 `OSCA550-Diag-D-minimal-format-arm64.apk`，打开 **Kodi OSCA550 Diag D**，以相同设置及样片重复测试，导出 `kodi-D.log`。
6. 将 C/D 结果及日志发回。若额外导出了 old.log，请一并注明，不必自行判断其归属。

C/D 与之前 A/B 使用同一诊断包名 `com.osca550.kodi.diag`，两版不能同时安装；构建复用 A/B 的签名缓存。原有 Kodi 可以保留。如果系统提示签名不一致，先反馈提示，不要为了安装而直接清除诊断应用数据。

日志目录是 `Android/data/com.osca550.kodi.diag/files/.kodi/temp/`，Kodi 文件管理器中的 `special://logpath/` 会指向它。日志可能带有局域网地址、用户名和片源路径，请勿公开提交完整日志到仓库。

## 判断依据

- C 正常而 A 花屏：显式 Main10 profile 是有效线索，仍需重复验证。
- 只有 D 正常：继续拆分省略的可选配置，恢复必要的色彩/HDR 处理。D 即使消除了马赛克，也需要确认是否偏色、灰暗或 HDR 亮度异常。
- C/D 均花屏：下一步制作 `MediaExtractor + MediaCodec + SurfaceView` 最小对照，与已正常的系统 MediaPlayer 播放路径比较。
- 黑屏、无法启动或回退软件解码：先按日志确认配置是否被接受，不能仅凭画面判断硬件路径已正常。

日志应包含 `OSCA550-DIAG v2`、对应 C/D 标记，以及 `Main10 experiment eligible=true`。若为 false，本轮配置实验没有匹配到目标解码流。

## 构建和校验

在 GitHub Actions 中手动运行 `Build OSCA550 Kodi Main10 Diagnostic C and D (ARM64)`。工作流先构建 C，再从经过 Git blob 校验的源码重建 D 的修改并增量编译。输出包含 APK、哈希、签名验证结果、包名/标签证据、变更补丁和诊断清单。导出前检查 ARM64、包名、C/D 标签、原生库诊断标记及两版签名一致性。
