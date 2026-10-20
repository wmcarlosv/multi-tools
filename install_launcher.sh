#!/usr/bin/env bash
# Instala Multi Tools en el menú de aplicaciones con su icono.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICON_SOURCE="$ROOT/assets/multi-tools.png"
ICON_DIR="$HOME/.local/share/icons/hicolor/512x512/apps"
ICON_NAME="multi-tools-app"
APPS_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$APPS_DIR/multi-tools.desktop"

if [ ! -f "$ICON_SOURCE" ]; then
    echo "No se encontró el icono: $ICON_SOURCE" >&2
    exit 1
fi

mkdir -p "$ICON_DIR" "$APPS_DIR"
cp "$ICON_SOURCE" "$ICON_DIR/$ICON_NAME.png"
rm -f "$ICON_DIR/multi-tools.png"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Multi Tools
GenericName=OCR y transcripción
Comment=Extrae texto de capturas, imágenes, audio y video
Exec="$ROOT/run.sh"
Path=$ROOT
Icon=$ICON_DIR/$ICON_NAME.png
Terminal=false
Categories=Utility;
StartupWMClass=Multitools
Keywords=OCR;texto;audio;video;transcripción;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"
update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true

echo "Lanzador instalado en: $DESKTOP_FILE"
echo "Busca «Multi Tools» en el menú de aplicaciones."
