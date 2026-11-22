# OSCA550 Kodi E：MiniDLNA 大文件快进修复验证

E 基于已经能正常显示 HEVC Main10/HDR 视频的 D 版，包名仍为 `com.osca550.kodi.diag`，名称改为 `Kodi OSCA550 Diag E`。签名必须与现用 D 版一致，校验脚本会拒绝导出签名不一致的 APK。

## 这次证据

2026-11-22 用户导出的 Range D 日志显示：

| 操作 | 文件偏移（字节） | 结果 |
|---|---:|---|
| 打开视频 | 0 | HTTP 206，总长度 19,577,329,360 |
| 读取 MKV 尾部索引 | 19,577,198,288 | HTTP 206，剩余长度 131,072，计算的总长度正确 |
| 快进约 20 分钟 | 3,424,986,225 | HTTP 206，恢复播放 |
| 再快进约 5 分钟 | 4,294,534,495 | 连接超时，重试后仍超时；缓存没有读到数据，解复用器报告提前 EOF 并退出 |

失败连接没有正常的 `connect_end`，并非收到一个长度错误的 HTTP 206 响应。`sendRange=false` 只是 Kodi 不使用显式的 `CURLOPT_RANGE`，非零偏移仍通过 `CURLOPT_RESUME_FROM_LARGE` 发出 HTTP Range，不能将其解读成禁用了 Range。

电脑对同一 NAS 地址的独立检查：失败偏移、4 GiB、6.97 GB、文件尾等六处均返回正确 Content-Range 和 16 KiB 数据。服务器标识为 `MiniDLNA/1.2.1`。使用开放结尾的 Range 保留两条未读完的连接时，第三条请求在六秒内无响应；关闭旧连接后，同一偏移请求在约 0.016 秒返回 HTTP 206。

这证明服务器在保留未读完的请求时会发生连接阻塞，与电视现象一致。仍需电视实测确认 Kodi 单会话策略能消除本次快进失败；不能由电脑测试直接声称电视已修复。

补充使用电脑 libcurl 8.23.0 的 `multi_remove_handle/easy_reset/multi_add_handle` 机制测试：双会话在第 5 次位置切换（6.97 GB）出现 HTTP 状态 0、零字节和约 6 秒超时；单会话下相同五个位置全部 HTTP 206，每次首次读到至少 128 KiB 仅耗时约 0.015～0.031 秒。这支持会话保留策略是关键因素，但电脑 libcurl 版本、系统和读缓冲不同于电视，不能当作电视端验证。

## E 版改动

只对 HTTP/HTTPS 响应标识包含 `MiniDLNA/1.2.` 的服务器关闭 Kodi CurlFile 的多会话策略。它改用 Kodi 已有的单会话分支：先 Disconnect 旧传输，再创建下一次 Range 请求。

保留 Range 日志，并增加 `OSCA550-HTTP-SEEK v1 mode=single` 和失败连接的 `connect_failed` 日志。与 Range D 比较时，解码器、Java Surface、HDR 配置、FileCache 和设置文件不变。SMB 未改动。

日志中的旧 MediaCodec buffer 在 flush 后释放失败，在第一次成功恢复播放时也出现；此次不处理这一独立线索。

## 安装与测试

1. 退出现用 Kodi，直接覆盖安装 `OSCA550-Diag-E-HTTP-seek-arm64.apk`。无需清除数据或卸载；现有收藏、中文字体和设置应保留。若电视提示签名冲突，保留旧应用并反馈提示。
2. 保持原有播放器和缓存设置。Debug logging 开启。
3. 通过原来收藏的 DLNA 目录播放同一部完整电影，先正常播放约 10 秒。
4. 跳至约 20 分钟，恢复播放后跳至 25～30 分钟，再尝试 40～60 分钟和往回跳转。
5. 每次跳转后观察是否恢复画面及声音，最后退出 Kodi，通过 SMB 导出 `kodi.log` 和 `kodi.old.log`。无需预先删除日志。

判断：日志应出现 `mode=single`，每次实际网络跳转应收到 `206` 且偏移加剩余长度等于总长度；不应再次出现连接超时后提前 EOF。即使表现正常也保留日志，以确认实际命中修复策略。

源码提交固定在 `1c2da8772de76760e63cd4c30f2ea7143c660e80`；构建工作流 `build-osca550-http-seek.yml`。APK 发布前核对包名、E 标签、ARM64、D 解码标记、Range 标记、HTTP seek 标记、源文件 SHA-256 和已安装版本的签名。

