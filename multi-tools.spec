# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

for package in (
    "faster_whisper",
    "ctranslate2",
    "onnxruntime",
    "av",
    "tokenizers",
    "huggingface_hub",
    "hf_xet",
):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    except Exception:
        continue
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    hiddenimports=hiddenimports + ["PIL._tkinter_finder", "sounddevice", "_sounddevice"],
    excludes=["pytest", "IPython", "notebook"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MultiTools",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MultiTools",
)
