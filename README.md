# LanMic

用手机浏览器当 Windows 麦克风。电脑跑一个本地服务，手机打开局域网链接、允许麦克风，声音经 **WebRTC（Opus）** 打到电脑，再写入虚拟声卡。任意软件——尤其是 **Win+H 语音输入**——都能把它当成系统麦克风。

默认场景：**口述写 AI 提示词**。打字慢、提示词又长的时候，拿起手机说即可。

> 仅 Windows。手机不装 App。音频只在局域网里走，不经过云。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![tag](https://img.shields.io/badge/tag-v0.2.0-0f6.svg)](CHANGELOG.md)

---

## 双击使用（推荐）

不需要预装 Python。

1. 打开 [Releases](https://github.com/dongyudadiguo/LanMic/releases)，下载 `LanMic-v0.2.0-windows-x64.zip`。
2. 解压整个文件夹（不要只拷贝 exe）。
3. 双击 `LanMic.exe`。  
   **没有黑框**。浏览器会打开控制台页，右下角出现托盘绿点。
4. 手机连同一 Wi-Fi，用 Chrome / Edge 扫码。
5. 证书不受信任：点 **高级 → 继续前往**，再允许麦克风。
6. 要给 Win+H 用：安装免费的 [VB-Audio Virtual Cable](https://vb-audio.com/Cable/)，系统输入选 `CABLE Output`，光标放到文本框按 **Win+H**。
7. 退出：托盘绿点 → 退出，或控制台页「退出 LanMic」。只关网页不会退出。

Windows SmartScreen 可能提示未知发布者：更多信息 → 仍要运行。防火墙请允许专用网络。

`git push` 一个 `v*` tag 后，GitHub Actions 会自动打这个 zip 并挂到 Release 上。

---

## 它解决什么

对着笔记本自带麦口述，键盘声、风扇、家人说话都会进识别；还得凑近电脑。  
LanMic 让你坐在沙发上、走来走去，用手机麦说，字打到电脑当前光标处。

适合：

- 在 ChatGPT / Claude / 本地大模型对话框里，用 Win+H 说一段长提示词
- 给 IDE、笔记、邮件打腹稿
- 会议软件里临时借手机当麦（同一 Wi-Fi）

不适合：

- 当录音棚、唱歌直播
- 跨公网、手机不在同一局域网
- 锁屏 / 切走浏览器标签后还想继续采音

---

## 从源码运行

```powershell
cd LanMic
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m lanmic
```

喇叭试听（没装虚拟线时）：

```powershell
python -m lanmic --speaker
```

或双击 `scripts\run.bat`。

本机打可双击包：

```powershell
scripts\build.bat
```

产物在 `dist\LanMic-0.2.0-windows-x64.zip`。

---

## 手机连接

1. 手机连 **同一 Wi-Fi**（公司网若开了 AP 隔离，改用电脑开热点）。
2. Chrome / Edge 打开控制台里的 `https://192.168.x.x:8443/`，或扫二维码。
3. 证书不受信任：点 **高级 → 继续前往**（自签名；证书在 `%USERPROFILE%\.lanmic\`）。
4. 允许麦克风，点「开始当麦克风」。控制台电平条应跳动。
5. 保持该页在前台，别锁屏。

---

## 常用命令（源码）

| 命令 | 作用 |
|---|---|
| `python -m lanmic` | 默认 HTTPS :8443，自动找 VB-CABLE |
| `python -m lanmic --speaker` | 喇叭试听 |
| `python -m lanmic --device "VoiceMeeter"` | 按名称选播放设备 |
| `python -m lanmic --port 9443` | 换端口 |
| `python -m lanmic --regen-cert` | 换过 Wi-Fi / IP 后重签证书 |
| `python -m lanmic --http` | 仅本机调试，手机一般**不会**给麦权限 |
| `python -m lanmic --no-browser` | 不要自动打开控制台页 |
| `python -m lanmic --no-tray` | 不要托盘 |

---

## 它怎么工作

```
手机 Chrome
  getUserMedia → RTCPeerConnection (Opus)
        │  HTTPS 页面 + POST /api/offer 信令
        │  媒体走主机 ICE（同一局域网，无 STUN）
        ▼
电脑（打包后的 LanMic.exe 或 python -m lanmic）
  解码成 48 kHz / 16-bit / mono PCM
        ▼
PortAudio / WASAPI → "CABLE Input"
        ▼
Windows 录音设备 "CABLE Output"
  Win+H / Zoom / 任意软件选用
```

没有公网、没有账号、没有录音落盘。

---

## 项目结构

```
LanMic/
  lanmic/                 Python 包
  web/                    手机页 + 电脑控制台
  packaging/lanmic.spec   PyInstaller（windowed / onedir）
  .github/workflows/      push v* tag → zip → GitHub Release
  scripts/build.bat       本机打包
  tests/
  LICENSE                 MIT
```

---

## 故障排除

| 现象 | 处理 |
|---|---|
| 双击没反应 | 看 `%USERPROFILE%\.lanmic\lanmic.log`；是否已有一个实例在跑 |
| 手机打不开页面 | 不在同一网段 / 访客隔离 → 电脑开热点 |
| 证书报错 | 「继续前往」。换网络后 `--regen-cert` 或删掉 `%USERPROFILE%\.lanmic\cert.pem` |
| 有声音但 Win+H 不认 | 没装 / 没选 `CABLE Output` |
| 电平不动 | 手机权限拒绝、静音、或切到了别的标签 |
| 说两句就断 | 锁屏或切走浏览器；把手机页留在前台 |
| SmartScreen | 更多信息 → 仍要运行（当前未做代码签名） |
| 关网页还在后台 | 正常。用托盘或控制台「退出 LanMic」 |

---

## 开源与发版

MIT。见 [CONTRIBUTING.md](CONTRIBUTING.md)。

当前发布：**v0.2.0**。维护者：

```powershell
# 改版本号与 CHANGELOG 后
git add -A
git commit -m "Release v0.2.0"
git tag -a v0.2.0 -m "v0.2.0"
git push origin main --tags
```

推送 `v*` tag 后，Actions 会构建 `LanMic-vX.Y.Z-windows-x64.zip` 并挂到 Release。

---

## 隐私与安全

- 音频只在你的局域网里，从手机到这台电脑。
- 使用自签名证书，**不要**在不信任的网络上点「继续前往」。
- 本程序不写录音文件、不上传、不分析语音。识别由 Windows 语音输入或你打开的 App 完成。
- 这是给你自己用的麦克风，不是远控、不是隐藏录音。
