# -*- mode: python ; coding: utf-8 -*-
"""
VirtualChemLab PyInstaller spec

This repo has multiple build entrypoints (scripts/CI/tools). Keeping a single,
checked-in spec file ensures CI and developer tools can build reliably.

Notes:
- Uses onedir + windowed build.
- Bundles runtime data directories (assets/, config/) and config.json.
- Excludes optional heavy libs to keep distributable size down; UI modules must
  degrade gracefully when these are absent in packaged builds.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


block_cipher = None

def _spec_path() -> Path:
    # PyInstaller executes spec via `exec()` without guaranteeing `__file__`.
    # Find the .spec argument from argv, otherwise fall back to CWD.
    for arg in reversed(sys.argv):
        if arg.endswith(".spec") and Path(arg).exists():
            return Path(arg).resolve()
    return Path.cwd() / "VirtualChemLab.spec"


PROJECT_ROOT = _spec_path().parent.resolve()
ENTRY_SCRIPT = str(PROJECT_ROOT / "main.py")
MAC_BUNDLE_ID = "com.virtualchemlab.app"


def _datas() -> list[tuple[str, str]]:
    datas: list[tuple[str, str]] = []

    assets_dir = PROJECT_ROOT / "assets"
    if assets_dir.exists():
        datas.append((str(assets_dir), "assets"))

    config_dir = PROJECT_ROOT / "config"
    if config_dir.exists():
        datas.append((str(config_dir), "config"))

    config_json = PROJECT_ROOT / "config.json"
    if config_json.exists():
        datas.append((str(config_json), "."))

    return datas


def _icon_path() -> str | None:
    icons_dir = PROJECT_ROOT / "assets" / "icons"
    if sys.platform == "darwin":
        candidate = icons_dir / "app.icns"
    else:
        candidate = icons_dir / "app.ico"
    return str(candidate) if candidate.exists() else None


ICON_PATH = _icon_path()
ENTITLEMENTS = str(PROJECT_ROOT / "entitlements.plist") if (PROJECT_ROOT / "entitlements.plist").exists() else None

HIDDENIMPORTS = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "pymunk",
    "sqlalchemy",
]

BUILD_FLAVOR = os.environ.get("VCL_BUILD_FLAVOR", "full").strip().lower()
if BUILD_FLAVOR not in {"full", "lite"}:
    raise ValueError(f"Unknown VCL_BUILD_FLAVOR={BUILD_FLAVOR!r}; expected 'full' or 'lite'")

EXCLUDES = ["pytest"]
if BUILD_FLAVOR == "lite":
    # Keep distributable smaller; optional features must guard imports.
    EXCLUDES.extend(
        [
            "matplotlib",
            "pandas",
        ]
    )

if sys.platform == "darwin":
    # Numba is optional and often pulls in `libomp` issues on macOS bundles.
    EXCLUDES.append("numba")
else:
    HIDDENIMPORTS.append("numba")


a = Analysis(
    [ENTRY_SCRIPT],
    pathex=[str(PROJECT_ROOT), str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=_datas(),
    hiddenimports=HIDDENIMPORTS,
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VirtualChemLab",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=ICON_PATH,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=ENTITLEMENTS,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="VirtualChemLab",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="VirtualChemLab.app",
        icon=ICON_PATH,
        bundle_identifier=MAC_BUNDLE_ID,
    )
