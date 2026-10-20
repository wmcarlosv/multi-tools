#!/usr/bin/env bash
# Lanza Multi Tools con Tk/Tesseract empaquetados en .vendor/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -x "$ROOT/.venv/bin/python" ]; then
    echo "No se encontró el entorno virtual. Ejecuta primero: ./setup.sh" >&2
    exit 1
fi

export PYTHONPATH="$ROOT/.vendor/usr/lib/python3.12:$ROOT/.vendor/usr/lib/python3.12/lib-dynload${PYTHONPATH:+:$PYTHONPATH}"
export LD_LIBRARY_PATH="$ROOT/.vendor/usr/lib:$ROOT/.vendor/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TK_LIBRARY="$ROOT/.vendor/usr/share/tcltk/tk8.6"
export TCL_LIBRARY="$ROOT/.vendor/usr/share/tcltk/tcl8.6"
export TESSDATA_PREFIX="$ROOT/.vendor/usr/share/tesseract-ocr/5/tessdata"

exec "$ROOT/.venv/bin/python" "$ROOT/app.py" "$@"
