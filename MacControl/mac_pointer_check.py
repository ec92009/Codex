from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import json
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from typing import Any


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
TARGET_WINDOW_TITLE = "Centering Pin"
MAX_SPACES_TO_SCAN = 10
WINDOW_DESC_PROBE_LIMIT = 20
WINDOW_DESC_TIMEOUT_SECONDS = 3.0


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


def list_open_windows() -> list[str]:
    script = """
tell application "System Events"
    set linesList to {}
    repeat with p in (application processes whose background only is false)
        try
            set procName to (name of p as text)
            repeat with w in windows of p
                try
                    set windowName to (name of w as text)
                    copy (procName & " | " & windowName) to end of linesList
                end try
            end repeat
        end try
    end repeat
    set AppleScript's text item delimiters to linefeed
    return linesList as text
end tell
""".strip()
    result = subprocess.run(
        ["osascript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    text = result.stdout.strip()
    return [line for line in text.splitlines() if line.strip()]


def print_open_windows() -> None:
    windows = list_open_windows()
    print("Open windows visible to System Events:", flush=True)
    if not windows:
        print("- (none)", flush=True)
        return
    for line in windows:
        print(f"- {line}", flush=True)


def switch_space(direction: str) -> None:
    if direction not in {"left", "right"}:
        raise ValueError("direction must be 'left' or 'right'")
    key_code = "123" if direction == "left" else "124"
    script = f"""
tell application "System Events"
    key code {key_code} using control down
end tell
""".strip()
    subprocess.run(["osascript", "-e", script], check=True)


def sleep_short(seconds: float) -> None:
    subprocess.run(["/bin/sleep", f"{seconds}"], check=True)


def bring_window_to_foreground(window_title: str) -> str:
    escaped_title = window_title.replace("\\", "\\\\").replace('"', '\\"')
    script = f"""
on run
    set targetTitle to "{escaped_title}"
    tell application "System Events"
        repeat with p in (application processes whose background only is false)
            repeat with w in windows of p
                try
                    if name of w is targetTitle then
                        set frontmost of p to true
                        try
                            perform action "AXRaise" of w
                        end try
                        return name of p as text
                    end if
                end try
            end repeat
        end repeat
    end tell
    error "Window not found: " & targetTitle
end run
""".strip()
    result = subprocess.run(
        ["osascript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "Unknown app"


def try_focus_window(window_title: str) -> str | None:
    try:
        return bring_window_to_foreground(window_title)
    except subprocess.CalledProcessError:
        return None


def scan_spaces_and_focus_window(window_title: str) -> str:
    print("Scanning Spaces for target window...", flush=True)
    print("Space 1 (current):", flush=True)
    print_open_windows()
    app_name = try_focus_window(window_title)
    if app_name:
        return app_name

    moves_right = 0
    for index in range(2, MAX_SPACES_TO_SCAN + 1):
        switch_space("right")
        moves_right += 1
        sleep_short(0.35)
        print(f"Space {index}:", flush=True)
        print_open_windows()
        app_name = try_focus_window(window_title)
        if app_name:
            return app_name

    for _ in range(moves_right):
        switch_space("left")
        sleep_short(0.2)

    raise RuntimeError(
        f"Window not found across up to {MAX_SPACES_TO_SCAN} Spaces: {window_title}"
    )


def _osascript_json(script: str) -> dict[str, Any]:
    result = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        timeout=WINDOW_DESC_TIMEOUT_SECONDS,
    )
    return json.loads(result.stdout)


def get_window_accessibility_summary(app_name: str, window_title: str) -> dict[str, Any]:
    js = f"""
ObjC.import('stdlib');
function safe(fn, fallback) {{ try {{ return fn(); }} catch (e) {{ return fallback; }} }}
function run() {{
  const se = Application('System Events');
  const proc = se.applicationProcesses.byName({json.dumps(app_name)});
  const win = proc.windows.byName({json.dumps(window_title)});
  const attrs = {{}};
  attrs.app = {json.dumps(app_name)};
  attrs.window = {json.dumps(window_title)};
  attrs.frontmost = safe(() => proc.frontmost(), false);
  attrs.position = safe(() => win.position(), null);
  attrs.size = safe(() => win.size(), null);
  attrs.role = safe(() => win.role(), '');
  attrs.subrole = safe(() => win.subrole(), '');
  let elements = [];
  let top = safe(() => win.uiElements(), []);
  let count = 0;
  for (const e of top) {{
    if (count >= {WINDOW_DESC_PROBE_LIMIT}) break;
    const row = {{
      role: safe(() => e.role(), ''),
      subrole: safe(() => e.subrole(), ''),
      name: safe(() => e.name(), ''),
      description: safe(() => e.description(), ''),
      position: safe(() => e.position(), null),
      size: safe(() => e.size(), null),
    }};
    elements.push(row);
    count += 1;
  }}
  attrs.topLevelElements = elements;
  return JSON.stringify(attrs);
}}
run();
""".strip()
    try:
        return _osascript_json(js)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError):
        return {
            "app": app_name,
            "window": window_title,
            "frontmost": True,
            "probeError": "Accessibility probe timed out or failed",
            "topLevelElements": [],
        }


def _element_area(element: dict[str, Any]) -> int:
    size = element.get("size")
    if not isinstance(size, list) or len(size) != 2:
        return -1
    try:
        return int(size[0]) * int(size[1])
    except Exception:  # noqa: BLE001
        return -1


def _best_main_pane_element(summary: dict[str, Any]) -> dict[str, Any] | None:
    ignored_roles = {
        "AXToolbar",
        "AXTitleBar",
        "AXButton",
        "AXMenuButton",
        "AXScrollBar",
        "AXGrowArea",
    }
    candidates = [
        e
        for e in summary.get("topLevelElements", [])
        if e.get("role") not in ignored_roles and _element_area(e) > 0
    ]
    if not candidates:
        return None
    return max(candidates, key=_element_area)


def build_window_description_text(
    *,
    app_name: str,
    window_title: str,
    screenshot_path: Path,
    summary: dict,
) -> str:
    lines = [
        "Window Description (Accessibility-based, best effort)",
        f"App: {app_name}",
        f"Window: {window_title}",
        f"Screenshot: {screenshot_path}",
    ]
    if summary.get("size"):
        lines.append(f"Window size: {summary['size']}")
    if summary.get("position"):
        lines.append(f"Window position: {summary['position']}")
    if summary.get("probeError"):
        lines.append(f"Probe note: {summary['probeError']}")

    main_pane = _best_main_pane_element(summary)
    lines.append("")
    lines.append("Main Pane (inferred)")
    if main_pane is None:
        lines.append(
            "- Could not infer a main pane from accessible top-level elements."
        )
        if app_name == "BambuStudio":
            lines.append(
                "- Likely content is a BambuStudio 3D model/canvas view, but the viewport is not exposed with a detailed Accessibility description."
            )
    else:
        lines.append(
            f"- Role: {main_pane.get('role') or '(unknown)'}"
        )
        if main_pane.get("subrole"):
            lines.append(f"- Subrole: {main_pane['subrole']}")
        if main_pane.get("name"):
            lines.append(f"- Name: {main_pane['name']}")
        if main_pane.get("description"):
            lines.append(f"- Description: {main_pane['description']}")
        if main_pane.get("size"):
            lines.append(f"- Size: {main_pane['size']}")
        if main_pane.get("position"):
            lines.append(f"- Position: {main_pane['position']}")
        lines.append(
            "- Note: This is inferred from macOS Accessibility and may not describe the actual 3D image pixels."
        )

    lines.append("")
    lines.append("Visible Top-Level Elements")
    elements = summary.get("topLevelElements", [])
    if not elements:
        lines.append("- (none)")
    else:
        for element in elements:
            role = element.get("role") or "?"
            name = element.get("name") or ""
            desc = element.get("description") or ""
            size = element.get("size") or ""
            parts = [role]
            if name:
                parts.append(f"name={name}")
            if desc:
                parts.append(f"desc={desc}")
            if size:
                parts.append(f"size={size}")
            lines.append("- " + " | ".join(parts))

    return "\n".join(lines) + "\n"


def write_window_description_to_desktop(
    screenshot_path: Path, app_name: str, window_title: str
) -> Path:
    summary = get_window_accessibility_summary(app_name, window_title)
    text = build_window_description_text(
        app_name=app_name,
        window_title=window_title,
        screenshot_path=screenshot_path,
        summary=summary,
    )
    description_path = screenshot_path.with_suffix(".txt")
    description_path.write_text(text, encoding="utf-8")
    return description_path


def run_pointer_check() -> int:
    try:
        app_name = scan_spaces_and_focus_window(TARGET_WINDOW_TITLE)
        center = get_main_display_center()
        move_pointer(center)
        worked = ask_worked()
        current = get_pointer_position()
        move_pointer(CGPoint(current.x + 50.0, current.y + 100.0))
        screenshot_path = take_screenshot_to_desktop()
        description_path = write_window_description_to_desktop(
            screenshot_path, app_name, TARGET_WINDOW_TITLE
        )
        print(f"Foreground window forced: {TARGET_WINDOW_TITLE} (app: {app_name})")
        print(f"User selected: {'Yes' if worked else 'No'}")
        print("Pointer moved 50px right and 100px down from the selection position.")
        print(f"Screenshot saved: {screenshot_path}")
        print(f"Description saved: {description_path}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        print(
            "If this is a permission issue, enable Accessibility and Screen Recording access for Terminal/Codex/Python in System Settings > Privacy & Security.",
            file=sys.stderr,
        )
        return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pointer movement check and/or full-screen screenshot on macOS."
    )
    parser.add_argument(
        "--screenshot-only",
        action="store_true",
        help="Skip pointer movement checks and only save a full-screen screenshot to the Desktop.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.screenshot_only:
        try:
            app_name = scan_spaces_and_focus_window(TARGET_WINDOW_TITLE)
            screenshot_path = take_screenshot_to_desktop()
            description_path = write_window_description_to_desktop(
                screenshot_path, app_name, TARGET_WINDOW_TITLE
            )
            print(f"Foreground window forced: {TARGET_WINDOW_TITLE} (app: {app_name})")
            print(f"Screenshot saved: {screenshot_path}")
            print(f"Description saved: {description_path}")
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}", file=sys.stderr)
            print(
                "If this is a permission issue, enable Accessibility and Screen Recording access for Terminal/Codex/Python in System Settings > Privacy & Security.",
                file=sys.stderr,
            )
            return 1

    return run_pointer_check()


if __name__ == "__main__":
    raise SystemExit(main())
