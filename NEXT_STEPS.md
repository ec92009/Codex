# Next Steps

Use this file as a quick checkpoint before stopping work.

## Current Task

- Keep LeadLight and filamentDB in sync across machines, with Desktop app bundles refreshing automatically after rebuilds.
- Validate the integrated hybrid `detect` mode on a wider real-image set and decide whether the old direct-detect helpers can be retired.

## Last Completed

- Pushed `423c193` - `leadlight: add shared material preset`
- Updated both macOS app builders so rebuilding also refreshes `/Users/ecohen/Desktop/LeadLight.app` and `/Users/ecohen/Desktop/filamentDB.app`
- Built a more promising detect-mode lab around glass-interior growth instead of direct lead detection.
- Built a hybrid anchor-detect + generated-pane lab that looks strong on most of `A.png` through `F.png`.
- Added a before/after palette reduction view to the hybrid lab so it can be judged against the real `8..10 color` print constraint.
- Updated the reduced hybrid preview so generated lead between panes of the same reduced color is removed automatically.
- Integrated the hybrid anchor-detect + generated-pane pipeline into LeadLight's `detect` mode while leaving `generate` untouched.

## Next Command To Run

- `/Users/ecohen/Codex/imageTo3MF/build_leadlight_app.sh`
- `/Users/ecohen/Codex/filamentDB/build_filamentdb_app.sh`
- `uv run --project /Users/ecohen/Codex/imageTo3MF python /Users/ecohen/Codex/imageTo3MF/image_grade_to_3mf.py /Users/ecohen/Desktop/F.png --lead-source detect --no-open --preview /tmp/leadlight_detect_preview.png --output /tmp/leadlight_detect_test.3mf`

## Open Questions

- Should the Desktop app refresh also open Finder to the updated app automatically, or is silent replacement better?
- Should the same Desktop-refresh behavior be added to any future local app bundles under `/Users/ecohen/Codex`?
- Should the old direct-detect helper code and tuning lab be cleaned out now that hybrid detect is integrated?
- Do we want a user-facing control for hybrid detect sensitivity, or keep the defaults fixed for now?

## Blockers

- No technical blockers currently.
- Desktop app copies now refresh on rebuild; main remaining question is whether to extend the same pattern to other local apps.

## Resume Checklist

- Run `git -C /Users/ecohen/Codex status --short --branch`
- Run `git -C /Users/ecohen/Codex log --oneline -5`
- Review this file and update/remove stale items
- Continue with the next command above
