# -*- mode: python ; coding: utf-8 -*-
"""Windowless onedir build. Run from repo root:

    pyinstaller packaging/lanmic.spec --noconfirm --clean
"""

from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import collect_all

SPECDIR = Path(SPEC).resolve().parent
ROOT = SPECDIR.parent

datas = [(str(ROOT / "web"), "web")]
binaries = []
hiddenimports = [
    "PIL",
    "PIL._tkinter_finder",
    "qrcode.image.pil",
    "numpy",
    "cffi",
    "pystray._win32",
]

for pkg in ("aiortc", "av", "aiohttp", "sounddevice", "cryptography", "pystray", "aioice"):
    try:
        collected = collect_all(pkg)
    except Exception:
        continue
    datas += collected[0]
    binaries += collected[1]
    hiddenimports += collected[2]

a = Analysis(
    [str(ROOT / "lanmic" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "unittest"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LanMic",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="LanMic",
)
