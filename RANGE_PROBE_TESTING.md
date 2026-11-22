# OSCA550 大文件 Range 诊断 D

这版保持 D 的 HEVC Main10 MediaFormat 和透明 Surface，仅增加 `OSCA550-RANGE v1` 日志，记录 HTTP Resume、响应码、内容长度、FileCache seek/read 非正返回和 premature EOF。

先用现有 D 连续播放；只有需要复现大文件快进问题时安装本版。设置保持 MediaCodec 开、Surface 开、Hybrid 关。播放 DLNA/HTTP 大文件，依次快进到约 20 分钟、25 分钟或复现位置，导出 kodi.log。SMB 也可重复同样操作。

重点日志：`OSCA550-RANGE connect_begin`、`connect_end`、`premature_read`、`FileCache read_nonpositive`。把日志发回后，比较 seek 偏移、HTTP 响应码、contentLength、fileSize 和底层返回值。此版本只观测，不绕过 EOF、不改变读取结果。

