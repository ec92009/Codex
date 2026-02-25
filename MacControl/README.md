# MacControl

Small macOS helper scripts for local control and verification.

## `mac_pointer_check.py`

Moves the pointer for a manual check and can save a full-screen screenshot to your Desktop.

### Usage

- Pointer check flow (includes screenshot at the end):
  - `uv run python /Users/ecohen/Codex/MacControl/mac_pointer_check.py`
- Screenshot only (full screen, saved to Desktop):
  - `uv run python /Users/ecohen/Codex/MacControl/mac_pointer_check.py --screenshot-only`

### Output

- Screenshot files are saved to `~/Desktop` with a timestamp filename like `YYYYMMDD.HHMMSS.png`.

### macOS Permissions

- `Screen Recording` is required for screenshots.
- `Accessibility` may be required for pointer movement.
- Enable permissions for the app you are using (`Codex`, `Terminal`, or Python) in:
  - `System Settings > Privacy & Security`
