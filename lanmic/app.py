"""LanMic HTTP/HTTPS server + WebRTC signaling."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import ssl
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any

from aiohttp import web

from lanmic import __version__
from lanmic.audio import (
    AudioSink,
    Device,
    find_virtual_output,
    list_output_devices,
    recording_hint,
    virtual_cable_installed,
)
from lanmic.certs import ensure_certificate
from lanmic.net import lan_ips, phone_urls
from lanmic.paths import web_dir
from lanmic.runtime import (
    acquire_single_instance,
    has_console,
    message_box,
    setup_logging,
    start_tray,
)
from lanmic.webrtc import PhoneSession

log = logging.getLogger("lanmic")

WEB_DIR = web_dir()
HOST_PAGE = WEB_DIR / "host.html"
PHONE_PAGE = WEB_DIR / "phone.html"


def _qr_data_uri(url: str) -> str:
    try:
        import base64
        import io

        import qrcode
    except ImportError:
        return ""
    img = qrcode.make(url, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


class Hub:
    def __init__(self, sink: AudioSink, port: int, scheme: str):
        self.sink = sink
        self.port = port
        self.scheme = scheme
        self.session: PhoneSession | None = None
        self.started_at = time.time()
        self._lock = asyncio.Lock()

    def urls(self) -> list[str]:
        return phone_urls(self.port, self.scheme)

    def status(self) -> dict[str, Any]:
        session = None
        if self.session is not None:
            session = self.session.snapshot()
        return {
            "version": __version__,
            "urls": self.urls(),
            "ips": lan_ips(),
            "port": self.port,
            "scheme": self.scheme,
            "device": self.sink.device_name,
            "virtual_cable": virtual_cable_installed(),
            "recording_hint": recording_hint(self.sink.device),
            "audio": self.sink.stats(),
            "session": session,
            "uptime_s": int(time.time() - self.started_at),
        }

    async def replace_session(self, ua: str) -> PhoneSession:
        async with self._lock:
            old = self.session
            self.session = PhoneSession(self.sink, on_change=lambda: None)
            self.session.remote_ua = ua
        if old is not None:
            await old.close()
        return self.session

    async def hangup(self) -> None:
        async with self._lock:
            old = self.session
            self.session = None
        if old is not None:
            await old.close()


def _html(path: Path) -> web.Response:
    if not path.is_file():
        raise web.HTTPNotFound(text=f"missing {path.name}")
    return web.FileResponse(path)


def build_app(hub: Hub) -> web.Application:
    app = web.Application()

    async def index(_request: web.Request) -> web.StreamResponse:
        return _html(PHONE_PAGE)

    async def host(_request: web.Request) -> web.StreamResponse:
        return _html(HOST_PAGE)

    async def status(_request: web.Request) -> web.Response:
        return web.json_response(hub.status())

    async def qr(_request: web.Request) -> web.Response:
        urls = hub.urls()
        url = urls[0] if urls else f"{hub.scheme}://127.0.0.1:{hub.port}/"
        return web.json_response({"url": url, "png": _qr_data_uri(url), "all": urls})

    async def offer(request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            raise web.HTTPBadRequest(text="invalid json")
        sdp = body.get("sdp")
        if not isinstance(sdp, str) or "v=0" not in sdp:
            raise web.HTTPBadRequest(text="missing sdp")
        ua = request.headers.get("User-Agent", "")
        session = await hub.replace_session(ua)
        try:
            answer = await session.apply_offer(sdp)
        except Exception as exc:
            log.exception("failed to apply offer")
            await session.close()
            raise web.HTTPInternalServerError(text=f"webrtc: {exc}") from exc
        return web.json_response({"sdp": answer, "type": "answer"})

    async def hangup(_request: web.Request) -> web.Response:
        await hub.hangup()
        return web.json_response({"ok": True})

    async def shutdown(_request: web.Request) -> web.Response:
        asyncio.get_running_loop().call_later(0.15, _request.app["stop"].set)
        return web.json_response({"ok": True})

    async def devices(_request: web.Request) -> web.Response:
        outs = [
            {
                "index": d.index,
                "name": d.name,
                "hostapi": d.hostapi,
                "label": d.label,
            }
            for d in list_output_devices()
        ]
        return web.json_response({"outputs": outs, "current": hub.sink.device_name})

    app.router.add_get("/", index)
    app.router.add_get("/phone", index)
    app.router.add_get("/host", host)
    app.router.add_get("/api/status", status)
    app.router.add_get("/api/qr", qr)
    app.router.add_get("/api/devices", devices)
    app.router.add_post("/api/offer", offer)
    app.router.add_post("/api/hangup", hangup)
    app.router.add_post("/api/shutdown", shutdown)
    app.router.add_static("/static", WEB_DIR, show_index=False)
    return app


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="lanmic",
        description="用手机浏览器当 Windows 麦克风（局域网 WebRTC）。",
    )
    p.add_argument("--host", default="0.0.0.0", help="绑定地址，默认 0.0.0.0")
    p.add_argument("--port", type=int, default=8443, help="HTTPS 端口，默认 8443")
    p.add_argument(
        "--http",
        action="store_true",
        help="仅用 HTTP（手机浏览器几乎一定不给麦克风权限，只留给本机调试）",
    )
    p.add_argument(
        "--speaker",
        action="store_true",
        help="不走虚拟声卡，直接从电脑喇叭播放，用来确认链路",
    )
    p.add_argument(
        "--device",
        default="",
        help="按名称子串选择播放设备（覆盖自动检测）",
    )
    p.add_argument(
        "--regen-cert",
        action="store_true",
        help="强制重签证书（换过 Wi-Fi / IP 时用）",
    )
    p.add_argument(
        "--no-browser",
        action="store_true",
        help="启动时不要打开电脑上的控制台页",
    )
    p.add_argument(
        "--no-tray",
        action="store_true",
        help="不要系统托盘（无控制台时仍可从控制台页点退出）",
    )
    p.add_argument("--version", action="version", version=f"lanmic {__version__}")
    return p.parse_args(argv)


def pick_device(args: argparse.Namespace) -> Device | None:
    if args.speaker:
        return None
    if args.device:
        needle = args.device.lower()
        for d in list_output_devices():
            if needle in d.name.lower() or needle in d.label.lower():
                return d
        raise SystemExit(f"找不到名称包含 {args.device!r} 的播放设备")
    found = find_virtual_output()
    if found is None:
        log.warning(
            "没有检测到 Wave Link / VoiceMeeter / CABLE。先用喇叭试听；"
            "要给 Win+H 用，请安装 Elgato Wave Link（winget install Elgato.WaveLink）后再启动。"
        )
        return None
    return found


def print_banner(hub: Hub) -> None:
    if not has_console():
        return
    urls = hub.urls()
    print()
    print(f"  LanMic v{__version__}   口述写提示词用的局域网麦克风")
    print("  " + "-" * 52)
    print(f"  输出设备 : {hub.sink.device_name}")
    print(f"  {recording_hint(hub.sink.device)}")
    print()
    if urls:
        print("  手机用 Chrome / Edge 打开（同一 Wi-Fi）：")
        for u in urls:
            print(f"    {u}")
        print()
        try:
            import qrcode

            qr = qrcode.QRCode(border=1)
            qr.add_data(urls[0])
            qr.make(fit=True)
            qr.print_ascii(invert=True)
        except Exception:
            pass
    else:
        print("  没找到局域网 IP。可开电脑热点，或检查网线 / Wi-Fi。")
    print()
    print("  电脑控制台: "
          f"{hub.scheme}://127.0.0.1:{hub.port}/host")
    print("  第一次手机会提示证书不受信任：点「高级 → 继续前往」。")
    print()


def fail(message: str, code: int = 1) -> None:
    log.error(message)
    message_box("LanMic 无法启动", message, error=True)
    raise SystemExit(code)


def main(argv: list[str] | None = None) -> None:
    setup_logging()
    args = parse_args(argv)

    if not acquire_single_instance():
        host_url = f"https://127.0.0.1:{args.port}/host"
        try:
            webbrowser.open(host_url)
        except Exception:
            pass
        message_box("LanMic 已在运行", "已打开控制台页。若要退出，点托盘图标或控制台里的「退出」。")
        return

    if os.name != "nt":
        log.warning("当前按 Windows 场景维护；其他系统仅能喇叭试听。")

    try:
        device = pick_device(args)
    except SystemExit as exc:
        fail(str(exc) or "选不到播放设备")

    sink = AudioSink(device)
    try:
        sink.start()
    except Exception as exc:
        fail(f"打不开播放设备：{exc}")

    scheme = "http" if args.http else "https"
    ssl_ctx = None
    if not args.http:
        try:
            cert, key = ensure_certificate(force=args.regen_cert)
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_ctx.load_cert_chain(str(cert), str(key))
        except Exception as exc:
            sink.stop()
            fail(f"证书失败：{exc}")

    hub = Hub(sink, port=args.port, scheme=scheme)
    app = build_app(hub)
    print_banner(hub)

    host_url = f"{scheme}://127.0.0.1:{args.port}/host"
    if not args.no_browser:
        try:
            webbrowser.open(host_url)
        except Exception:
            log.exception("failed to open browser")

    async def _run() -> None:
        stop = asyncio.Event()
        app["stop"] = stop
        loop = asyncio.get_running_loop()

        tray = None
        if not args.no_tray:
            tray = start_tray(host_url, on_quit=lambda: loop.call_soon_threadsafe(stop.set))

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=args.host, port=args.port, ssl_context=ssl_ctx)
        try:
            await site.start()
        except OSError as exc:
            if tray is not None:
                try:
                    tray.stop()
                except Exception:
                    pass
            raise SystemExit(f"端口 {args.port} 无法监听：{exc}") from exc

        log.info("listening on %s://%s:%s", scheme, args.host, args.port)
        try:
            await stop.wait()
        finally:
            if tray is not None:
                try:
                    tray.stop()
                except Exception:
                    pass
            await hub.hangup()
            await runner.cleanup()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass
    except SystemExit as exc:
        if exc.code not in (0, None):
            fail(str(exc) if exc.code is not None else "启动失败")
        raise
    except Exception as exc:
        log.exception("fatal")
        fail(f"运行出错：{exc}")
    finally:
        sink.stop()


if __name__ == "__main__":
    main()
