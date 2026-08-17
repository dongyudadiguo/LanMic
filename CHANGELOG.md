# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [0.2.0] - 2026-03-25

### Added

- Windows 可双击包：PyInstaller onedir，**无黑框**，系统托盘退出
- 控制台页增加「退出 LanMic」（关网页不会停进程）
- 单实例：重复双击会打开已有控制台页
- 启动失败用系统对话框提示；日志写到 `%USERPROFILE%\.lanmic\lanmic.log`
- `scripts/build.bat` 本机出 zip
- GitHub Actions：push `v*` tag 自动构建并发布 `LanMic-vX.Y.Z-windows-x64.zip`

### Changed

- 默认使用方式改为「下载 Release zip」，源码安装仍保留

## [0.1.0] - 2026-03-25

### Added

- 电脑端 Python HTTPS 服务：手机浏览器打开局域网链接即可当麦克风
- WebRTC（Opus）音频传输，同网低延迟
- 自签名证书（含局域网 IP 的 SAN），满足 `getUserMedia` 安全上下文
- 自动检测 VB-CABLE / VoiceMeeter 等虚拟声卡，并写入系统输入
- 无虚拟线时可用 `--speaker` 先从喇叭试听
- 主机控制台页：二维码、连接状态、电平
- 手机页：连接 / 静音 / 屏幕常亮（Wake Lock）
- 面向「口述写提示词」场景的使用说明（Win+H 语音输入）
- MIT 开源许可

[0.2.0]: https://github.com/dongyudadiguo/LanMic/releases/tag/v0.2.0
[0.1.0]: https://github.com/dongyudadiguo/LanMic/releases/tag/v0.1.0
