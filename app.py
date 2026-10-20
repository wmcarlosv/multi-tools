#!/usr/bin/env python3
"""Punto de entrada de Multi Tools.

Prepara el entorno (Tk/Tesseract empaquetados en .vendor) y lanza la interfaz.
También incluye modos de diagnóstico: --check, --ocr ARCHIVO y --transcribe ARCHIVO.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
ROOT = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent
VENDOR = ROOT / ".vendor"


def _prepend_path(variable: str, values: list[Path]) -> None:
    current = [p for p in os.environ.get(variable, "").split(os.pathsep) if p]
    missing = [str(p) for p in values if p.exists() and str(p) not in current]
    if missing:
        os.environ[variable] = os.pathsep.join(missing + current)


def _prepare_environment() -> None:
    """Deja disponibles Tk y Tesseract sin instalarlos en el sistema."""
    if not VENDOR.exists():
        return

    lib_dir = VENDOR / "usr/lib"
    lib_arch_dir = VENDOR / "usr/lib/x86_64-linux-gnu"
    tessdata = VENDOR / "usr/share/tesseract-ocr/5/tessdata"

    if FROZEN:
        _prepend_path("LD_LIBRARY_PATH", [lib_dir, lib_arch_dir])
        if tessdata.exists():
            os.environ.setdefault("TESSDATA_PREFIX", str(tessdata))
        return

    current_ld = [p for p in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p]
    if str(lib_arch_dir) not in current_ld:
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [str(lib_dir), str(lib_arch_dir), *current_ld]
        )
        os.execve(sys.executable, [sys.executable, str(ROOT / "app.py"), *sys.argv[1:]], env)

    for path in (VENDOR / "usr/lib/python3.12", VENDOR / "usr/lib/python3.12/lib-dynload"):
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))

    tk_data = VENDOR / "usr/share/tcltk/tk8.6"
    if tk_data.exists():
        os.environ.setdefault("TK_LIBRARY", str(tk_data))

    tcl_data = VENDOR / "usr/share/tcltk/tcl8.6"
    if tcl_data.exists():
        os.environ.setdefault("TCL_LIBRARY", str(tcl_data))

    if tessdata.exists():
        os.environ.setdefault("TESSDATA_PREFIX", str(tessdata))


def _run_cli() -> bool:
    """Modos sin interfaz para diagnóstico y uso desde terminal."""
    args = sys.argv[1:]
    if not args:
        return False

    if args[0] == "--check":
        from multi_tools import microphone, ocr, transcribe
        from PIL import Image, ImageDraw

        print(f"ejecutable: {Path(sys.executable).resolve()}")
        print(f"tesseract: {ocr.is_available()} ({ocr.TESSERACT_CMD})")
        print(f"idiomas OCR: {', '.join(ocr.available_languages()) or 'ninguno'}")
        print(f"whisper: {transcribe.is_available()}")
        print(f"micrófono: {microphone.is_available()}")
        if ocr.is_available():
            image = Image.new("RGB", (460, 90), "white")
            ImageDraw.Draw(image).text((16, 30), "Multi Tools OCR 12345", fill="black")
            text = ocr.extract_text(image, "spa+eng")
            print(f"prueba OCR: {text!r}")
        return True

    if args[0] == "--ocr" and len(args) > 1:
        from multi_tools import ocr

        print(ocr.extract_text(args[1], "spa+eng"))
        return True

    if args[0] == "--transcribe" and len(args) > 1:
        from multi_tools import transcribe

        model = args[2] if len(args) > 2 else transcribe.DEFAULT_MODEL
        text = transcribe.transcribe(
            args[1],
            model_size=model,
            on_status=lambda message: print(message, file=sys.stderr),
        )
        print(text)
        return True

    if args[0] == "--record" and len(args) > 1:
        import time

        from multi_tools import microphone, transcribe

        seconds = max(1.0, float(args[1]))
        model = args[2] if len(args) > 2 else transcribe.DEFAULT_MODEL
        recorder = microphone.Recorder()
        recorder.start()
        time.sleep(seconds)
        path = recorder.stop()
        print(f"grabados {recorder.duration:.1f}s en {path}", file=sys.stderr)
        try:
            text = transcribe.transcribe(
                path,
                model_size=model,
                on_status=lambda message: print(message, file=sys.stderr),
            )
            print(text)
        finally:
            try:
                path.unlink()
            except OSError:
                pass
        return True

    return False


def main() -> None:
    _prepare_environment()
    if _run_cli():
        return

    from multi_tools.ui import MultiToolsApp

    MultiToolsApp().run()


if __name__ == "__main__":
    main()
