from __future__ import annotations

import ctypes
import ctypes.util
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


def _load_core_graphics() -> ctypes.CDLL:
    path = ctypes.util.find_library("ApplicationServices")
    if not path:
        raise RuntimeError("Could not find ApplicationServices framework")
    return ctypes.CDLL(path)


cg = _load_core_graphics()

cg.CGMainDisplayID.restype = ctypes.c_uint32
cg.CGDisplayPixelsWide.argtypes = [ctypes.c_uint32]
cg.CGDisplayPixelsWide.restype = ctypes.c_size_t
cg.CGDisplayPixelsHigh.argtypes = [ctypes.c_uint32]
cg.CGDisplayPixelsHigh.restype = ctypes.c_size_t
cg.CGWarpMouseCursorPosition.argtypes = [CGPoint]
cg.CGWarpMouseCursorPosition.restype = ctypes.c_int32
cg.CGAssociateMouseAndMouseCursorPosition.argtypes = [ctypes.c_bool]
cg.CGAssociateMouseAndMouseCursorPosition.restype = ctypes.c_int32
cg.CGEventCreate.argtypes = [ctypes.c_void_p]
cg.CGEventCreate.restype = ctypes.c_void_p
cg.CGEventGetLocation.argtypes = [ctypes.c_void_p]
cg.CGEventGetLocation.restype = CGPoint

core_foundation = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
core_foundation.CFRelease.restype = None


def get_main_display_center() -> CGPoint:
    display_id = cg.CGMainDisplayID()
    width = float(cg.CGDisplayPixelsWide(display_id))
    height = float(cg.CGDisplayPixelsHigh(display_id))
    return CGPoint(width / 2.0, height / 2.0)


def get_pointer_position() -> CGPoint:
    event = cg.CGEventCreate(None)
    if not event:
        raise RuntimeError("Could not read current pointer position")
    try:
        return cg.CGEventGetLocation(event)
    finally:
        core_foundation.CFRelease(event)


def move_pointer(point: CGPoint) -> None:
    result = cg.CGWarpMouseCursorPosition(point)
    cg.CGAssociateMouseAndMouseCursorPosition(True)
    if result != 0:
        raise RuntimeError(
            "Failed to move pointer. macOS Accessibility permission may be required."
        )


def ask_worked() -> bool:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        return messagebox.askyesno(
            "Pointer Test",
            "Did the pointer move to the center of the screen?",
            parent=root,
        )
    finally:
        root.destroy()


def take_screenshot_to_desktop() -> Path:
    desktop = Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d.%H%M%S')}.png"
    target = desktop / filename
    subprocess.run(["screencapture", "-x", str(target)], check=True)
    return target


def main() -> int:
    try:
        center = get_main_display_center()
        move_pointer(center)
        worked = ask_worked()
        current = get_pointer_position()
        move_pointer(CGPoint(current.x + 50.0, current.y + 100.0))
        screenshot_path = take_screenshot_to_desktop()
        print(f"User selected: {'Yes' if worked else 'No'}")
        print("Pointer moved 50px right and 100px down from the selection position.")
        print(f"Screenshot saved: {screenshot_path}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        print(
            "If this is a permission issue, enable Accessibility and Screen Recording access for Terminal/Codex/Python in System Settings > Privacy & Security.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
