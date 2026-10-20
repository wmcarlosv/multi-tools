"""Grabación de voz desde el micrófono y guardado temporal en WAV."""

from __future__ import annotations

import ctypes.util
import tempfile
import threading
import time
import wave
from pathlib import Path

import numpy as np

from .config import VENDOR

SAMPLERATE = 16000
CHANNELS = 1

_sounddevice = None
_find_library_patched = False


def _patch_find_library() -> None:
    """Hace que ctypes encuentre el PortAudio empaquetado en .vendor."""
    global _find_library_patched
    if _find_library_patched:
        return

    import ctypes.util as ctypes_util

    original = ctypes_util.find_library
    candidates = (
        VENDOR / "usr/lib/x86_64-linux-gnu/libportaudio.so.2",
        VENDOR / "usr/lib/libportaudio.so.2",
    )

    def find_library(name: str):
        if name == "portaudio":
            for candidate in candidates:
                if candidate.exists():
                    return str(candidate)
        return original(name)

    ctypes_util.find_library = find_library
    _find_library_patched = True


def _load_sounddevice():
    global _sounddevice
    if _sounddevice is None:
        _patch_find_library()
        import sounddevice

        _sounddevice = sounddevice
    return _sounddevice


def is_available() -> bool:
    try:
        _load_sounddevice()
    except Exception:  # noqa: BLE001 - sin PortAudio no hay micrófono
        return False
    return True


class Recorder:
    """Graba del micrófono por defecto y genera un WAV temporal."""

    def __init__(self, samplerate: int = SAMPLERATE) -> None:
        self.samplerate = samplerate
        self.level = 0.0
        self._frames: list[np.ndarray] = []
        self._stream = None
        self._started_at = 0.0
        self._samples = 0
        self._paused = False

    @property
    def duration(self) -> float:
        return self._samples / self.samplerate

    def start(self) -> None:
        sounddevice = _load_sounddevice()
        self._frames = []
        self._samples = 0
        self._paused = False
        self.level = 0.0
        self._stream = sounddevice.InputStream(
            samplerate=self.samplerate,
            channels=CHANNELS,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()
        self._started_at = time.monotonic()

    def pause(self) -> None:
        self._paused = True
        self.level = 0.0

    def resume(self) -> None:
        self._paused = False

    @property
    def paused(self) -> bool:
        return self._paused

    def _callback(self, indata, frames, time_info, status) -> None:
        if self._paused:
            return
        self._frames.append(indata.copy())
        self._samples += len(indata)
        if indata.size:
            rms = float(np.sqrt(np.mean(np.square(indata))))
            self.level = min(1.0, rms * 12.0)

    def stop(self) -> Path:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None

        data = (
            np.concatenate(self._frames, axis=0)
            if self._frames
            else np.zeros((0, CHANNELS), dtype="float32")
        )
        self.level = 0.0
        self._paused = False
        return self._write_wav(data)

    def cancel(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None
        self._frames = []
        self._samples = 0
        self.level = 0.0
        self._paused = False

    def _write_wav(self, data: np.ndarray) -> Path:
        pcm = (data * 32767).clip(-32768, 32767).astype("<i2")
        handle = tempfile.NamedTemporaryFile(
            prefix="multi-tools-mic-",
            suffix=".wav",
            delete=False,
        )
        path = Path(handle.name)
        handle.close()

        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.samplerate)
            wav_file.writeframes(pcm.tobytes())

        return path
