# 参与贡献

谢谢你愿意给 LanMic 提改进。本项目场景很窄：  
**Windows 上用手机浏览器当麦克风，方便口述写 AI 提示词。**

## 开发环境

```powershell
cd LanMic
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m lanmic --speaker
```

`--speaker` 可不装虚拟声卡，先从电脑喇叭听链路是否通。

本机打可双击包：

```powershell
scripts\build.bat
```

需要 `requirements-build.txt` 里的 PyInstaller。产物不要提交进 git。

## 分支与提交

- `main` 保持可运行
- 提交说明用现在时、说清楚为什么
- 用户可见的行为变化请改 `CHANGELOG.md`

## 发版打 tag

维护者发版：

```powershell
# 先改 lanmic/__init__.py 与 pyproject.toml 的 version，并更新 CHANGELOG
git add -A
git commit -m "Release v0.2.1"
git tag -a v0.2.1 -m "v0.2.1"
git push origin main --tags
```

推送 `v*` tag 后，`.github/workflows/release.yml` 在 `windows-latest` 上打包 zip，并创建 GitHub Release。

仓库需要默认 `GITHUB_TOKEN` 写 `contents`（workflow 已声明 `permissions: contents: write`）。若 Release 没出来，看 Actions 日志，并确认 tag 推到了 GitHub 而不是只在本地。

## 范围（请先讨论再做大改）

欢迎：延迟、稳定性、证书体验、虚拟设备检测、无障碍、文档、打包体积。

请先开 issue 再动手：公网穿透、iOS App、自研内核声卡驱动、云端识别。

不要提交：录音文件样本、证书私钥、`.venv`、`dist/`、`build/`、真实内网 IP 截图（可打码）。
