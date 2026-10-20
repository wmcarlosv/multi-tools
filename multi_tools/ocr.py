"""Extracción de texto (OCR) con Tesseract."""

from __future__ import annotations

import os
from pathlib import Path

import pytesseract
from PIL import Image

from .config import TESSDATA_DIR, TESSERACT_CMD, VENDOR

LANGUAGES = ("spa+eng", "spa", "eng")
DEFAULT_LANGUAGE = "spa+eng"

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

if TESSDATA_DIR:
    os.environ.setdefault("TESSDATA_PREFIX", TESSDATA_DIR)

if VENDOR.exists():
    lib_paths = [
        VENDOR / "usr/lib",
        VENDOR / "usr/lib/x86_64-linux-gnu",
    ]
    current = [p for p in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p]
    missing = [str(p) for p in lib_paths if p.exists() and str(p) not in current]
    if missing:
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(missing + current)


def is_available() -> bool:
    return bool(TESSERACT_CMD) and Path(TESSERACT_CMD).exists()


def available_languages() -> list[str]:
    if not is_available():
        return []
    try:
        return sorted(pytesseract.get_languages(config=""))
    except Exception:
        return []


def extract_text(image: Image.Image | str | Path, language: str = DEFAULT_LANGUAGE) -> str:
    """Devuelve el texto detectado en una imagen o en la ruta de una imagen."""
    if isinstance(image, (str, Path)):
        with Image.open(image) as source:
            return _extract(source, language)
    return _extract(image, language)


def _extract(image: Image.Image, language: str) -> str:
    prepared = image.convert("RGB")
    text = pytesseract.image_to_string(
        prepared,
        lang=language,
        config="--oem 3 --psm 3",
    )
    return text.strip()
