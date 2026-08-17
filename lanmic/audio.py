"""Play decoded WebRTC PCM into a Windows playback device.

Virtual-cable design (recommended):
    Python plays to "CABLE Input"  ->  Windows exposes "CABLE Output"
    as a recording device that Win+H / any app can select.

Speaker fallback (`--speaker`):
    Play to the default output so you can verify the phone path
    before installing VB-CABLE.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 48000
CHANNELS = 1
DTYPE = "int16"
BLOCK = 480  # 10 ms at 48 kHz
QUEUE_SECONDS = 0.25


def _norm(name: str) -> str:
    return " ".join(name.lower().replace("(", " ").replace(")", " ").split())


# Substrings matched against WASAPI playback (output) device names.
VIRTUAL_OUTPUT_HINTS = (
    "cable input",          # VB-Audio Virtual Cable
    "vb-audio",
    "voicemeeter input",    # VoiceMeeter
    "voicemeeter aux input",
    "voicemeeter vaio",
    "cable-a input",
    "cable-b input",
)


@dataclass(frozen=True)
class Device:
    index: int
    name: str
    hostapi: str
    max_input: int
    max_output: int
    default_samplerate: float

    @property
    def label(self) -> str:
        return f"{self.name}  [{self.hostapi}]"


def _hostapi_name(index: int) -> str:
    try:
        return str(sd.query_hostapis(index)["name"])
    except Exception:
        return "unknown"


def list_output_devices() -> list[Device]:
    devices: list[Device] = []
    try:
        raw = sd.query_devices()
    except Exception:
        return devices
    for i, info in enumerate(raw):
        if int(info.get("max_output_channels") or 0) <= 0:
            continue
        devices.append(
            Device(
                index=i,
                name=str(info.get("name") or f"#{i}"),
                hostapi=_hostapi_name(int(info.get("hostapi") or 0)),
                max_input=int(info.get("max_input_channels") or 0),
                max_output=int(info.get("max_output_channels") or 0),
                default_samplerate=float(info.get("default_samplerate") or 0),
            )
        )
    return devices


def list_input_devices() -> list[Device]:
    devices: list[Device] = []
    try:
        raw = sd.query_devices()
    except Exception:
        return devices
    for i, info in enumerate(raw):
        if int(info.get("max_input_channels") or 0) <= 0:
            continue
        devices.append(
            Device(
                index=i,
                name=str(info.get("name") or f"#{i}"),
                hostapi=_hostapi_name(int(info.get("hostapi") or 0)),
                max_input=int(info.get("max_input_channels") or 0),
                max_output=int(info.get("max_output_channels") or 0),
                default_samplerate=float(info.get("default_samplerate") or 0),
            )
        )
    return devices


def find_virtual_output() -> Device | None:
    """Prefer a WASAPI virtual cable if one is installed."""
    devices = list_output_devices()
    wasapi = [d for d in devices if "wasapi" in d.hostapi.lower()]
    search = wasapi + [d for d in devices if d not in wasapi]
    for hint in VIRTUAL_OUTPUT_HINTS:
        for d in search:
            if hint in _norm(d.name):
                return d
    return None


def virtual_cable_installed() -> bool:
    return find_virtual_output() is not None


def recording_hint(output: Device | None) -> str:
    """Tell the user which Windows *input* they should pick."""
    if output is None:
        return "当前走喇叭试听，Win+H 不会用到这部手机。"
    n = _norm(output.name)
    if "cable input" in n:
        return "在 Win+H / 录音设置里选择「CABLE Output」。"
    if "voicemeeter input" in n or "voicemeeter vaio" in n:
        return "在 Win+H 里选择 VoiceMeeter 对应的输出（Output）。"
    return f"把 Windows 默认输入指到与「{output.name}」配对的那只虚拟麦克风。"


class AudioSink:
    """Thread-safe PCM player with a small jitter buffer."""

    def __init__(self, device: Device | None, samplerate: int = SAMPLE_RATE):
        self.device = device
        self.samplerate = samplerate
        self._lock = threading.Lock()
        self._buffer = deque()
        self._buffered = 0
        self._max_samples = int(samplerate * QUEUE_SECONDS)
        self._level = 0.0
        self._underruns = 0
        self._frames_in = 0
        self._stream: sd.OutputStream | None = None
        self._started = False

    @property
    def device_index(self) -> int | None:
        return None if self.device is None else self.device.index

    @property
    def device_name(self) -> str:
        if self.device is None:
            return "系统默认播放设备（喇叭试听）"
        return self.device.label

    def start(self) -> None:
        if self._started:
            return
        extra = None
        # WASAPI shared mode is the least painful on consumer PCs.
        try:
            extra = sd.WasapiSettings(exclusive=False)
        except Exception:
            extra = None
        kwargs = dict(
            samplerate=self.samplerate,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCK,
            callback=self._callback,
            device=self.device_index,
        )
        if extra is not None:
            try:
                self._stream = sd.OutputStream(**kwargs, extra_settings=extra)
            except TypeError:
                self._stream = sd.OutputStream(**kwargs)
            except Exception:
                self._stream = sd.OutputStream(**kwargs)
        else:
            self._stream = sd.OutputStream(**kwargs)
        self._stream.start()
        self._started = True

    def stop(self) -> None:
        stream = self._stream
        self._stream = None
        self._started = False
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        with self._lock:
            self._buffer.clear()
            self._buffered = 0

    def write_int16(self, pcm: np.ndarray) -> None:
        if pcm.size == 0:
            return
        samples = np.ascontiguousarray(pcm, dtype=np.int16).reshape(-1)
        with self._lock:
            self._buffer.append(samples)
            self._buffered += samples.size
            self._frames_in += 1
            # drop oldest chunks if the phone outruns the sound card
            while self._buffered > self._max_samples and self._buffer:
                old = self._buffer.popleft()
                self._buffered -= old.size
            peak = float(np.max(np.abs(samples))) / 32768.0
            self._level = max(peak, self._level * 0.85)

    def level(self) -> float:
        with self._lock:
            return float(self._level)

    def stats(self) -> dict:
        with self._lock:
            return {
                "buffered_ms": int(self._buffered * 1000 / self.samplerate),
                "level": round(float(self._level), 3),
                "underruns": self._underruns,
                "frames_in": self._frames_in,
            }

    def _callback(self, outdata, frames, time_info, status) -> None:  # noqa: ARG002
        needed = frames * CHANNELS
        out = np.zeros(needed, dtype=np.int16)
        filled = 0
        with self._lock:
            while filled < needed and self._buffer:
                chunk = self._buffer[0]
                take = min(needed - filled, chunk.size)
                out[filled : filled + take] = chunk[:take]
                if take >= chunk.size:
                    self._buffer.popleft()
                else:
                    self._buffer[0] = chunk[take:]
                self._buffered -= take
                filled += take
            if filled < needed:
                self._underruns += 1
        outdata[:] = out.reshape(frames, CHANNELS)
