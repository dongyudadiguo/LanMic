@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
  echo [LanMic] creating .venv ...
  python -m venv .venv || exit /b 1
)

".venv\Scripts\python.exe" -m pip install -U pip
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt || exit /b 1
".venv\Scripts\python.exe" -m PyInstaller packaging\lanmic.spec --noconfirm --clean || exit /b 1

copy /Y "packaging\使用说明.txt" "dist\LanMic\使用说明.txt" >nul

".venv\Scripts\python.exe" -c "from lanmic import __version__; print(__version__)" > "%TEMP%\lanmic_ver.txt"
set /p VER=<%TEMP%\lanmic_ver.txt
set ZIP=dist\LanMic-%VER%-windows-x64.zip
if exist "%ZIP%" del /f "%ZIP%"
powershell -NoProfile -Command "Compress-Archive -Path 'dist\LanMic' -DestinationPath '%ZIP%' -Force"
echo [LanMic] packed %ZIP%
