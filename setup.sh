#!/usr/bin/env bash
# Instala las dependencias del proyecto sin permisos de administrador.
# Descarga Tk y Tesseract como paquetes .deb y los extrae en .vendor/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR="$ROOT/.vendor"
DEBS="$ROOT/.cache/debs"

cd "$ROOT"
mkdir -p "$VENDOR" "$DEBS"

need_vendor=0
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    need_vendor=1
fi
if ! command -v tesseract >/dev/null 2>&1; then
    need_vendor=1
fi
if ! ldconfig -p 2>/dev/null | grep -q "libportaudio.so.2"; then
    need_vendor=1
fi

if [ "$need_vendor" -eq 1 ]; then
    packages=()

    if ! python3 -c "import tkinter" >/dev/null 2>&1; then
        packages+=(python3-tk libtk8.6 libtcl8.6 tcl8.6 tk8.6 tk8.6-blt2.5 blt)
    fi

    if ! command -v tesseract >/dev/null 2>&1; then
        packages+=(
            tesseract-ocr libtesseract5 liblept5
            tesseract-ocr-eng tesseract-ocr-osd tesseract-ocr-spa
        )
    fi

    if ! ldconfig -p 2>/dev/null | grep -q "libportaudio.so.2"; then
        packages+=(libportaudio2)
    fi

    if [ ${#packages[@]} -gt 0 ]; then
        echo "Descargando componentes del sistema en .vendor/…"
        (cd "$DEBS" && apt-get download "${packages[@]}")
        for deb in "$DEBS"/*.deb; do
            dpkg-deb -x "$deb" "$VENDOR"
        done
    fi
fi

echo "Creando entorno virtual…"
python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/pip" install --quiet --upgrade pip
"$ROOT/.venv/bin/pip" install --quiet -r "$ROOT/requirements.txt"

echo
echo "Instalación completada. Inicia la aplicación con:"
echo "  ./run.sh"
