"""WebRTC peer that pulls the phone microphone and dumps PCM into AudioSink."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable

import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamError
from av.audio.resampler import AudioResampler

from lanmic.audio import CHANNELS, SAMPLE_RATE, AudioSink

log = logging.getLogger("lanmic.webrtc")


class PhoneSession:
    def __init__(
        self,
        sink: AudioSink,
        on_change: Callable[[], None] | None = None,
    ):
        self.sink = sink
        self.on_change = on_change
        self.pc = RTCPeerConnection()
        self.connected = False
        self.remote_ua = ""
        self.started_at = time.time()
        self._track_task: asyncio.Task | None = None
        self._closed = False
        self.pc.on("connectionstatechange", self._on_state)
        self.pc.on("track", self._on_track)

    @property
    def state(self) -> str:
        return self.pc.connectionState

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "connected": self.connected,
            "ua": self.remote_ua,
            "uptime_s": int(time.time() - self.started_at),
            "audio": self.sink.stats(),
        }

    async def apply_offer(self, sdp: str) -> str:
        offer = RTCSessionDescription(sdp=sdp, type="offer")
        await self.pc.setRemoteDescription(offer)
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)
        # Wait until ICE candidates are gathered so the SDP is complete
        # (no trickle — keeps the phone page tiny).
        while self.pc.iceGatheringState != "complete":
            await asyncio.sleep(0.02)
        assert self.pc.localDescription is not None
        return self.pc.localDescription.sdp

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.connected = False
        if self._track_task is not None:
            self._track_task.cancel()
            self._track_task = None
        try:
            await self.pc.close()
        except Exception:
            log.debug("pc.close failed", exc_info=True)
        if self.on_change:
            self.on_change()

    async def _on_state(self) -> None:
        state = self.pc.connectionState
        log.info("peer connection %s", state)
        self.connected = state == "connected"
        if state in {"failed", "closed", "disconnected"}:
            self.connected = False
        if self.on_change:
            self.on_change()
        if state in {"failed", "closed"}:
            await self.close()

    def _on_track(self, track) -> None:  # noqa: ANN001
        log.info("got remote track %s", track.kind)
        if track.kind != "audio":
            return
        if self._track_task is not None:
            self._track_task.cancel()
        self._track_task = asyncio.create_task(self._pump(track), name="lanmic-audio")

    async def _pump(self, track) -> None:  # noqa: ANN001
        resampler = AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
        try:
            while True:
                try:
                    frame = await track.recv()
                except MediaStreamError:
                    break
                for converted in resampler.resample(frame):
                    pcm = converted.to_ndarray()
                    # shape is (channels, samples) or (samples,)
                    if pcm.ndim == 2:
                        pcm = pcm[0] if pcm.shape[0] <= CHANNELS else pcm.mean(axis=0)
                    self.sink.write_int16(np.asarray(pcm, dtype=np.int16))
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("audio pump died")
        finally:
            self.connected = False
            if self.on_change:
                self.on_change()
