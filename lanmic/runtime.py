"""Windowless-app helpers: log file, single-instance, tray, error dialogs."""

from __future__ import annotations

import ctypes
import logging
import sys
import threading
import webbrowser
from collections.abc import Callable
from pathlib import Path

from lanmic.paths import log_path, user_data_dir

MUTEX_NAME = "Local\\LanMic.SingleInstance"
ERROR_ALREADY_EXISTS = 183

log = logging.getLogger("lanmic.runtime")
_mutex_handle = None


def has_console() -> bool:
    try:
        return sys.stdout is not None and sys.stdout.isatty()
    except Exception:
        return False


def setup_logging() -> Path:
    folder = user_data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = log_path()
    handlers: list[logging.Handler] = [
        logging.FileHandler(path, encoding="utf-8"),
    ]
    if has_console():
        handlers.append(logging.StreamHandler(sys.stderr))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
    return path


def message_box(title: str, text: str, error: bool = False) -> None:
    if sys.platform != "win32":
        stream = sys.stderr if error else sys.stdout
        if stream is not None:
            print(f"{title}: {text}", file=stream)
        return
    flags = 0x00000010 if error else 0x00000040
    flags |= 0x00040000  # topmost
    try:
        ctypes.windll.user32.MessageBoxW(None, str(text), str(title), flags)
    except Exception:
        pass


def acquire_single_instance() -> bool:
    """Return False if another LanMic is already running."""
    global _mutex_handle
    if sys.platform != "win32":
        return True
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        return True
    _mutex_handle = handle
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return False
    return True


def start_tray(host_url: str, on_quit: Callable[[], None]):
    """Background tray: open console / quit. Returns the icon or None."""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        log.info("tray unavailable (pystray/Pillow missing)")
        return None

    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, 60, 60), fill=(17, 17, 17, 255))
    draw.ellipse((16, 16, 48, 48), fill=(143, 219, 122, 255))

    def _open(_icon=None, _item=None) -> None:
        webbrowser.open(host_url)

    def _quit(icon, _item=None) -> None:
        try:
            icon.stop()
        except Exception:
            pass
        on_quit()

    icon = pystray.Icon(
        "LanMic",
        image,
        "LanMic",
        menu=pystray.Menu(
            pystray.MenuItem("打开控制台", _open, default=True),
            pystray.MenuItem("退出", _quit),
        ),
    )
    threading.Thread(target=icon.run, name="lanmic-tray", daemon=True).start()
    return icon
