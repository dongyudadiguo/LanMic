# LanMic

用手机浏览器当 Windows 麦克风。电脑跑一个 Python 服务，手机打开局域网链接、允许麦克风，声音经 **WebRTC（Opus）** 打到电脑，再写入虚拟声卡。任意软件——尤其是 **Win+H 语音输入**——都能把它当成系统麦克风。

本仓库的默认场景是：**口述写 AI 提示词**。打字慢、提示词又长的时候，拿起手机说即可。

> 仅 Windows。手机不装 App。音频只在局域网里走，不经过云。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![tag](https://img.shields.io/badge/tag-v0.1.0-0f6.svg)](CHANGELOG.md)

---

## 它解决什么

对着笔记本自带麦口述，键盘声、风扇、家人说话都会进识别；还得凑近电脑。  
LanMic 让你坐在沙发上、走来走去，用手机麦说，字打到电脑当前光标处。

适合：

- 在 ChatGPT / Claude / 本地大模型对话框里，用 Win+H 说一段长提示词
- 给 IDE、笔记、邮件打腹稿
- 会议软件里临时借手机当麦（同一 Wi-Fi）

不适合：

- 当录音棚、唱歌直播（抖动缓冲和浏览器 AEC 不是这个量级）
- 跨公网、手机不在同一局域网
- 锁屏 / 切走浏览器标签后还想继续采音（浏览器会停）

---

## 10 分钟上手

### 0. 电脑准备

- Windows 10 / 11
- Python 3.10+（3.14 可用）
- 强烈建议安装免费虚拟声卡 **[VB-Audio Virtual Cable](https://vb-audio.com/Cable/)**  
  不装也能先用 `--speaker` 从喇叭听链路是否通，但 Win+H **选不到** 这部手机。

### 1. 安装

```powershell
cd $env:USERPROFILE\Desktop\LanMic
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

或双击 `scripts\run.bat`（会自建 `.venv` 并启动）。

### 2. 启动

```powershell
python -m lanmic
```

只想先听声音、还没装虚拟线：

```powershell
python -m lanmic --speaker
```

电脑会弹出控制台页，并在终端里打印二维码。

### 3. 手机连接

1. 手机连 **同一 Wi-Fi**（公司网若开了 AP 隔离，改用电脑热点）。
2. Chrome / Edge 打开终端里的 `https://192.168.x.x:8443/`，或扫控制台二维码。
3. 证书不受信任：点 **高级 → 继续前往**（自签名，只为给你的麦克风权限；证书在 `%USERPROFILE%\.lanmic\`）。
4. 允许麦克风，点「开始当麦克风」。控制台电平条应跳动。

### 4. 口述写提示词

1. Windows 设置 → 系统 → 声音 → **输入** → 选 `CABLE Output`。
2. 也可：设置 → 时间和语言 → 语音 → 麦克风，选同一只。
3. 把光标点到要写提示词的文本框。
4. 按 **Win + H**，对着手机说话。
5. 保持手机页在前台，别锁屏。

说的时候可以带标点口令（中文语音输入常见）：「句号」「逗号」「换行」「问号」。

---

## 常用命令

| 命令 | 作用 |
|---|---|
| `python -m lanmic` | 默认 HTTPS :8443，自动找 VB-CABLE |
| `python -m lanmic --speaker` | 喇叭试听 |
| `python -m lanmic --device "VoiceMeeter"` | 按名称选播放设备 |
| `python -m lanmic --port 9443` | 换端口 |
| `python -m lanmic --regen-cert` | 换过 Wi-Fi / IP 后重签证书 |
| `python -m lanmic --http` | 仅本机调试，手机一般**不会**给麦权限 |
| `python -m lanmic --no-browser` | 不要自动打开控制台页 |

---

## 它怎么工作

```
手机 Chrome
  getUserMedia → RTCPeerConnection (Opus)
        │  HTTPS 页面 + POST /api/offer 信令
        │  媒体走主机 ICE（同一局域网，无 STUN）
        ▼
电脑 Python (aiohttp + aiortc)
  解码成 48 kHz / 16-bit / mono PCM
        ▼
PortAudio / WASAPI
  播放到 "CABLE Input"
        ▼
Windows 录音设备 "CABLE Output"
  Win+H / Zoom / 任意软件选用
```

没有公网、没有账号、没有录音落盘。关掉窗口即断开。

---

## 项目结构

```
LanMic/
  lanmic/          Python 包（证书、网卡、声卡、WebRTC、HTTP）
  web/             手机页 + 电脑控制台（零构建）
  scripts/         Windows 一键启动
  tests/           不依赖声卡的单元测试
  CHANGELOG.md
  LICENSE          MIT
```

---

## 故障排除

| 现象 | 处理 |
|---|---|
| 手机打不开页面 | 不在同一网段 / 路由器开了访客隔离 → 电脑开热点让手机连 |
| 打开是 HTTP 明文、没权限 | 必须用 `https://`；别手改成 http |
| 证书报错 | 点「继续前往」。换网络后执行 `--regen-cert` |
| 有声音但 Win+H 不认 | 没装 / 没选 `CABLE Output`；确认不是 `--speaker` |
| 电平不动 | 手机权限拒绝、静音、或切到了别的标签 |
| 说两句就断 | 锁屏、省电限制后台；把 LanMic 页留在前台，关掉电池优化对浏览器的限制 |
| 换过 Wi-Fi 连不上 | `--regen-cert`，证书 SAN 要覆盖当前 IP |
| 公司防火墙拦 8443 | `--port` 换成 443 或 9443（443 可能要管理员） |

---

## 开源与版本

MIT。欢迎提 issue / PR，见 [CONTRIBUTING.md](CONTRIBUTING.md)。

当前发布：**v0.1.0**（见 [CHANGELOG.md](CHANGELOG.md)）。  
仓库用 annotated tag 标记发布，例如 `v0.1.0`。

---

## 隐私与安全

- 音频只在你的局域网里，从手机到这台电脑。
- 使用自签名证书，**不要**在不信任的网络上点「继续前往」。
- 本程序不写录音文件、不上传、不分析语音。识别由 Windows 语音输入或你打开的 App 完成。
- 这是给你自己用的麦克风，不是远控、不是隐藏录音。
