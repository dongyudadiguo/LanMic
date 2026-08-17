@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
  echo [LanMic] creating .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo [LanMic] python -m venv failed. Install Python 3.10+ and retry.
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install -U pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [LanMic] pip install failed.
    pause
    exit /b 1
  )
)

echo [LanMic] starting...
".venv\Scripts\python.exe" -m lanmic %*
