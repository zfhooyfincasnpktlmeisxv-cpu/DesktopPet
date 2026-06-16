# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — run: pyinstaller DesktopPet.spec"""
from pathlib import Path

ROOT = Path(SPECPATH)


def _collect_tree(rel: str) -> list:
    base = ROOT / rel
    if not base.is_dir():
        return []
    return [(str(p), str(p.parent.relative_to(ROOT)).replace("\\", "/")) for p in base.rglob("*") if p.is_file()]


def _collect_assets() -> list:
    out = []
    assets = ROOT / "assets"
    if not assets.is_dir():
        return out
    for p in assets.rglob("*"):
        if not p.is_file():
            continue
        if "_src" in p.parts or p.suffix.lower() == ".bmp":
            continue
        rel = p.relative_to(ROOT)
        out.append((str(p), str(rel.parent).replace("\\", "/")))
    return out


datas = []
datas += _collect_tree("src/config")
datas += _collect_tree("src/i18n/locales")
datas += _collect_tree("skins")
datas += _collect_assets()

hiddenimports = [
    "chess",
    "chess.engine",
    "chess.pgn",
    "PyQt6.QtMultimedia",
    "PyQt6.QtMultimediaWidgets",
]

a = Analysis(
    ["src/main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "pandas"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DesktopPet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "icon.ico") if (ROOT / "assets" / "icon.ico").is_file() else None,
)
