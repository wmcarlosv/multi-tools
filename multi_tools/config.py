"""Utilidades compartidas de Multi Tools."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent
else:
    ROOT = Path(__file__).resolve().parent.parent

VENDOR = ROOT / ".vendor"

APP_NAME = "Multi Tools"
APP_VERSION = "1.1.0"

ICON_PATH = ROOT / "assets/multi-tools.png"
if not ICON_PATH.exists():
    ICON_PATH = ROOT / "multi-tools.jpg"


def _first_existing(*paths: Path | str) -> Path | None:
    for path in paths:
        candidate = Path(path)
        if candidate.exists():
            return candidate
    return None


def _find_tesseract() -> str | None:
    local = VENDOR / "usr/bin/tesseract"
    if local.exists():
        return str(local)
    return shutil.which("tesseract")


def _find_tessdata() -> str | None:
    env_value = os.environ.get("TESSDATA_PREFIX")
    if env_value and Path(env_value).is_dir():
        return env_value

    found = _first_existing(
        VENDOR / "usr/share/tesseract-ocr/5/tessdata",
        "/usr/share/tesseract-ocr/5/tessdata",
        "/usr/share/tesseract-ocr/4.00/tessdata",
        "/usr/share/tessdata",
    )
    return str(found) if found else None


TESSERACT_CMD = _find_tesseract()
TESSDATA_DIR = _find_tessdata()
