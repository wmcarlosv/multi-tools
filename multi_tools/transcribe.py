"""Transcripción de audio y video con faster-whisper."""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Callable

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")

logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

MODEL_SIZES = ("tiny", "base", "small", "medium", "large-v3")
DEFAULT_MODEL = "base"

LANGUAGES: dict[str, str | None] = {
    "Automático": None,
    "Español": "es",
    "Inglés": "en",
    "Portugués": "pt",
    "Francés": "fr",
    "Alemán": "de",
    "Italiano": "it",
}

LANGUAGE_NAMES = {
    "es": "español",
    "en": "inglés",
    "pt": "portugués",
    "fr": "francés",
    "de": "alemán",
    "it": "italiano",
}

ProgressCallback = Callable[[float], None]
StatusCallback = Callable[[str], None]

_models: dict[str, object] = {}
_models_lock = threading.Lock()


def is_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except Exception:
        return False
    return True


def _load_model(model_size: str):
    with _models_lock:
        if model_size not in _models:
            from faster_whisper import WhisperModel

            logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
            _models[model_size] = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
                cpu_threads=max(1, os.cpu_count() or 1),
            )
        return _models[model_size]


def preload_model(model_size: str = DEFAULT_MODEL) -> None:
    """Carga (o descarga) el modelo en segundo plano para la próxima transcripción."""
    try:
        _load_model(model_size)
    except Exception:  # noqa: BLE001 - el error real se mostrará al transcribir
        pass


def _notify(callback, value) -> None:
    if callback is not None:
        callback(value)


def transcribe(
    path: str | Path,
    model_size: str = DEFAULT_MODEL,
    language: str | None = None,
    on_status: StatusCallback | None = None,
    on_progress: ProgressCallback | None = None,
) -> str:
    """Transcribe un archivo de audio o video y devuelve el texto completo."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"No existe el archivo: {source}")

    _notify(
        on_status,
        f"Cargando modelo «{model_size}»… la primera vez puede tardar en descargarse.",
    )
    model = _load_model(model_size)

    segments, info = model.transcribe(
        str(source),
        language=language,
        beam_size=1,
        temperature=0.0,
        vad_filter=True,
        condition_on_previous_text=False,
    )

    detected = getattr(info, "language", None)
    if language is None and detected:
        probability = float(getattr(info, "language_probability", 0) or 0)
        language_name = LANGUAGE_NAMES.get(detected, detected)
        _notify(
            on_status,
            f"Idioma detectado: {language_name} ({probability:.0%}). Transcribiendo…",
        )
    else:
        _notify(on_status, "Transcribiendo audio…")

    duration = float(getattr(info, "duration", 0) or 0)
    parts: list[str] = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            parts.append(text)
        if duration > 0:
            _notify(on_progress, min(0.99, max(0.0, segment.end / duration)))

    _notify(on_progress, 1.0)
    _notify(on_status, "Transcripción finalizada.")
    return " ".join(parts).strip()
