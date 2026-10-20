"""Preferencias persistentes (último directorio usado)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

APP_DIR_NAME = "multi-tools"
CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
CONFIG_FILE = CONFIG_HOME / APP_DIR_NAME / "settings.json"


def _download_dir_from_xdg() -> Path | None:
    config_file = CONFIG_HOME / "user-dirs.dirs"
    try:
        content = config_file.read_text(encoding="utf-8")
    except OSError:
        return None

    match = re.search(r'^XDG_DOWNLOAD_DIR="(.+)"$', content, re.MULTILINE)
    if not match:
        return None

    value = match.group(1).replace("$HOME", str(Path.home()))
    return Path(value)


def downloads_directory() -> Path:
    """Carpeta de descargas del usuario, con alternativas para español."""
    candidates = []

    env_dir = os.environ.get("XDG_DOWNLOAD_DIR")
    if env_dir:
        candidates.append(Path(env_dir))

    xdg_dir = _download_dir_from_xdg()
    if xdg_dir is not None:
        candidates.append(xdg_dir)

    candidates.extend(
        [
            Path.home() / "Downloads",
            Path.home() / "Descargas",
            Path.home() / "descargas",
        ]
    )

    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    return Path.home()


def _read_settings() -> dict:
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_settings(data: dict) -> None:
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def get_last_directory() -> str | None:
    value = _read_settings().get("last_directory")
    if isinstance(value, str) and Path(value).is_dir():
        return value
    return None


def set_last_directory(directory: str | Path) -> None:
    path = Path(directory)
    if not path.is_dir():
        return
    data = _read_settings()
    data["last_directory"] = str(path)
    _write_settings(data)


def initial_directory() -> str:
    """Último directorio usado o, la primera vez, la carpeta de descargas."""
    return get_last_directory() or str(downloads_directory())
