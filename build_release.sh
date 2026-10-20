#!/usr/bin/env bash
# Compila Multi Tools y genera los artefactos de producción en release/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="1.1.0"
ARCH="amd64"
APP="MultiTools"

DIST="$ROOT/dist"
BUILD="$ROOT/.build"
RELEASE="$ROOT/release"
STAGE="$BUILD/deb"

cd "$ROOT"

if [ ! -x "$ROOT/.venv/bin/python" ] || [ ! -d "$ROOT/.vendor" ]; then
    echo "Faltan dependencias de desarrollo. Ejecuta primero: ./setup.sh" >&2
    exit 1
fi

if ! "$ROOT/.venv/bin/python" -c "import PyInstaller" >/dev/null 2>&1; then
    echo "Instalando PyInstaller…"
    "$ROOT/.venv/bin/pip" install --quiet -r "$ROOT/requirements-build.txt"
fi

export PYTHONPATH="$ROOT/.vendor/usr/lib/python3.12:$ROOT/.vendor/usr/lib/python3.12/lib-dynload${PYTHONPATH:+:$PYTHONPATH}"
export LD_LIBRARY_PATH="$ROOT/.vendor/usr/lib:$ROOT/.vendor/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TK_LIBRARY="$ROOT/.vendor/usr/share/tcltk/tk8.6"
export TCL_LIBRARY="$ROOT/.vendor/usr/share/tcltk/tcl8.6"
export TESSDATA_PREFIX="$ROOT/.vendor/usr/share/tesseract-ocr/5/tessdata"

echo "Compilando con PyInstaller…"
"$ROOT/.venv/bin/pyinstaller" \
    --noconfirm \
    --clean \
    --workpath "$BUILD/pyinstaller" \
    --distpath "$DIST" \
    "$ROOT/multi-tools.spec" >/dev/null

echo "Añadiendo Tesseract, icono y documentación…"
cp -a "$ROOT/.vendor" "$DIST/$APP/.vendor"
mkdir -p "$DIST/$APP/assets"
cp "$ROOT/assets/multi-tools.png" "$DIST/$APP/assets/"
cp "$ROOT/README.md" "$DIST/$APP/"

mkdir -p "$RELEASE"
rm -f "$RELEASE"/*.deb "$RELEASE"/*.tar.gz

echo "Creando paquete .deb…"
rm -rf "$STAGE"
mkdir -p \
    "$STAGE/DEBIAN" \
    "$STAGE/opt/multi-tools" \
    "$STAGE/usr/share/applications" \
    "$STAGE/usr/share/icons/hicolor/512x512/apps"

cp -a "$DIST/$APP/." "$STAGE/opt/multi-tools/"
cp "$ROOT/assets/multi-tools.png" \
    "$STAGE/usr/share/icons/hicolor/512x512/apps/multi-tools.png"

cat > "$STAGE/usr/share/applications/multi-tools.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Multi Tools
GenericName=OCR y transcripción
Comment=Extrae texto de capturas, imágenes, audio y video
Exec=/opt/multi-tools/$APP
Icon=/usr/share/icons/hicolor/512x512/apps/multi-tools.png
Terminal=false
Categories=Utility;
StartupWMClass=Multitools
Keywords=OCR;texto;audio;video;transcripción;
StartupNotify=true
EOF

cat > "$STAGE/DEBIAN/control" <<EOF
Package: multi-tools
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: Multi Tools <local@localhost>
Installed-Size: $(du -sk "$STAGE/opt" | cut -f1)
Depends: libc6, libx11-6, libxext6, libxrender1, libxft2, libfontconfig1, libxss1, libgomp1
Description: OCR y transcripción de audio y video
 Extrae texto de capturas de pantalla e imágenes con Tesseract
 y transcribe audio o video con faster-whisper.
EOF

cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
exit 0
EOF
chmod 0755 "$STAGE/DEBIAN/postinst"

dpkg-deb --build --root-owner-group "$STAGE" \
    "$RELEASE/multi-tools_${VERSION}_${ARCH}.deb" >/dev/null

echo "Creando archivo portable .tar.gz…"
tar -C "$DIST" -czf "$RELEASE/MultiTools-${VERSION}-linux-x86_64.tar.gz" "$APP"

echo
echo "Producción lista en: $RELEASE"
ls -lh "$RELEASE"
echo
echo "Instalar:   sudo apt install $RELEASE/multi-tools_${VERSION}_${ARCH}.deb"
echo "Portable:   tar -xzf $RELEASE/MultiTools-${VERSION}-linux-x86_64.tar.gz && ./$APP/$APP"
