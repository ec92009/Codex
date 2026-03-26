#!/usr/bin/env python3

from __future__ import annotations

import os
import plistlib
import shutil
import stat
import subprocess
from pathlib import Path

from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


APP_NAME = "filamentDB"
BUNDLE_ID = "com.ecohen.filamentdb"
VERSION = "0.1.1"
PROJECT_DIR = Path(__file__).resolve().parent
ICON_SVG = PROJECT_DIR / "filamentdb_icon.svg"
ENTRY_SCRIPT = PROJECT_DIR / "filament_db_gui.py"
DIST_DIR = PROJECT_DIR / "dist"
BUILD_DIR = PROJECT_DIR / "build"
ICONSET_DIR = BUILD_DIR / f"{APP_NAME}.iconset"
ICNS_PATH = BUILD_DIR / f"{APP_NAME}.icns"
APP_PATH = DIST_DIR / f"{APP_NAME}.app"
DESKTOP_APP_PATH = Path.home() / "Desktop" / f"{APP_NAME}.app"


def render_icon(source_svg: Path, iconset_dir: Path) -> None:
    renderer = QSvgRenderer(str(source_svg))
    if not renderer.isValid():
        raise RuntimeError(f"Could not render SVG icon: {source_svg}")

    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir(parents=True, exist_ok=True)

    sizes = [16, 32, 128, 256, 512]
    for size in sizes:
        for scale in (1, 2):
            actual_size = size * scale
            image = QImage(actual_size, actual_size, QImage.Format_ARGB32)
            image.fill(QColor(0, 0, 0, 0))
            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            renderer.render(painter)
            painter.end()

            suffix = "" if scale == 1 else "@2x"
            target = iconset_dir / f"icon_{size}x{size}{suffix}.png"
            if not image.save(str(target)):
                raise RuntimeError(f"Could not write icon PNG: {target}")


def build_icns(iconset_dir: Path, icns_path: Path) -> None:
    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)],
        check=True,
    )


def write_info_plist(resources_dir: Path) -> None:
    info = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleDisplayName": APP_NAME,
        "CFBundleExecutable": APP_NAME,
        "CFBundleIconFile": ICNS_PATH.name,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": APP_NAME,
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSApplicationCategoryType": "public.app-category.utilities",
        "NSHighResolutionCapable": True,
    }
    info_path = APP_PATH / "Contents" / "Info.plist"
    with info_path.open("wb") as handle:
        plistlib.dump(info, handle)
    shutil.copy2(ICNS_PATH, resources_dir / ICNS_PATH.name)


def write_launcher(macos_dir: Path) -> None:
    launcher = macos_dir / APP_NAME
    script = f"""#!/bin/zsh
set -euo pipefail

APP_NAME={APP_NAME!r}
PROJECT_DIR={str(PROJECT_DIR)!r}
ENTRY_SCRIPT={str(ENTRY_SCRIPT)!r}
PROJECT_PYTHON="$PROJECT_DIR/.venv/bin/python"
LOG_FILE="${{TMPDIR:-/tmp}}/filamentdb_gui.log"

cd "$PROJECT_DIR"

if [[ -x "$PROJECT_PYTHON" ]]; then
  exec -a "$APP_NAME" "$PROJECT_PYTHON" "$ENTRY_SCRIPT" >>"$LOG_FILE" 2>&1
fi

UV_BIN="${{UV_BIN:-$(command -v uv || true)}}"
if [[ -n "$UV_BIN" ]]; then
  exec -a "$APP_NAME" "$UV_BIN" run --project "$PROJECT_DIR" python "$ENTRY_SCRIPT" >>"$LOG_FILE" 2>&1
fi

/usr/bin/osascript -e 'display alert "filamentDB could not start" message "No project Python or uv executable was found." as critical'
exit 1
"""
    launcher.write_text(script, encoding="utf-8")
    current_mode = launcher.stat().st_mode
    launcher.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def build_app() -> None:
    if APP_PATH.exists():
        shutil.rmtree(APP_PATH)
    resources_dir = APP_PATH / "Contents" / "Resources"
    macos_dir = APP_PATH / "Contents" / "MacOS"
    resources_dir.mkdir(parents=True, exist_ok=True)
    macos_dir.mkdir(parents=True, exist_ok=True)
    write_info_plist(resources_dir)
    write_launcher(macos_dir)
    (APP_PATH / "Contents" / "PkgInfo").write_text("APPL????", encoding="ascii")


def install_on_desktop() -> None:
    if DESKTOP_APP_PATH.exists():
        shutil.rmtree(DESKTOP_APP_PATH)
    shutil.copytree(APP_PATH, DESKTOP_APP_PATH, symlinks=True)


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication([])
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    render_icon(ICON_SVG, ICONSET_DIR)
    build_icns(ICONSET_DIR, ICNS_PATH)
    build_app()
    install_on_desktop()

    print(APP_PATH)
    print(DESKTOP_APP_PATH)
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
