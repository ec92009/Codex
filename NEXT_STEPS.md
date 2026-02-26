# Next Steps

Use this file as a quick checkpoint before stopping work.

## Additional Active Task (OleaTaxCo website concepts)

- Draft concept files moved into `/Users/ecohen/Codex/OleaTaxCoSiteConcepts/` for Kelly's CPA/SquareSpace planning.
- Working domain is `OleaTaxCo.com` (already purchased, not published yet).
- Next command: `python3 -m http.server 8000` (run from `/Users/ecohen/Codex/OleaTaxCoSiteConcepts`) to preview concepts locally.

## Current Task

- Verify `MacControl/mac_pointer_check.py` can force the `Centering Pin` window to the foreground and complete a screenshot/pointer test after macOS permissions are granted.

## Last Completed

- Pushed `ecda97a` - `Focus Centering Pin window before capture`
- Verified script failure mode when `Centering Pin` is not found / not accessible through `System Events`

## Next Command To Run

- `uv run python /Users/ecohen/Codex/MacControl/mac_pointer_check.py`
- If only testing capture + focus: `uv run python /Users/ecohen/Codex/MacControl/mac_pointer_check.py --screenshot-only`

## Open Questions

- Is the target window title exactly `Centering Pin` (case/spaces must match)?
- Which app owns the `Centering Pin` window (useful if we need app-specific targeting)?

## Blockers

- macOS `Accessibility` permission may be missing for `Codex` / `Terminal` / Python (required for `System Events` window focusing).
- macOS `Screen Recording` permission may be missing (required for screenshots).
- The `Centering Pin` window must be open before running the script.

## Permission Setup (before rerun)

- Open `Centering Pin` so the window is visible.
- In `System Settings > Privacy & Security`:
- Enable `Accessibility` for the app running the script (`Codex`, `Terminal`, or Python).
- Enable `Screen Recording` for the app running the script.
- Re-run the command above after granting permissions (macOS may require closing/reopening the app).

## Expected Success Output

- Console line like: `Foreground window forced: Centering Pin (app: <AppName>)`
- Screenshot path on Desktop (`~/Desktop/YYYYMMDD.HHMMSS.png`)
- For full flow, pointer dialog appears and script reports result

## Resume Checklist

- Run `git -C /Users/ecohen/Codex status --short --branch`
- Run `git -C /Users/ecohen/Codex log --oneline -5`
- Review this file and update/remove stale items
- Continue with the next command above
