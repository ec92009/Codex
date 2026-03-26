# Next Steps

Use this file as a quick checkpoint before stopping work.

## Current Task

- Keep LeadLight and filamentDB in sync across machines, with Desktop app bundles refreshing automatically after rebuilds.
- Continue the `glass_interior_growth_lab.py` experiment for detect mode if we want to replace the current direct lead detector.
- Compare the new `glass_hybrid_anchor_lab.py` baseline against the interior-growth lab before deciding whether to bring a hybrid detect/generate mode into LeadLight.

## Last Completed

- Pushed `423c193` - `leadlight: add shared material preset`
- Updated both macOS app builders so rebuilding also refreshes `/Users/ecohen/Desktop/LeadLight.app` and `/Users/ecohen/Desktop/filamentDB.app`
- Built a more promising detect-mode lab around glass-interior growth instead of direct lead detection.
- Built a hybrid anchor-detect + generated-pane lab that looks strong on most of `A.png` through `F.png`.

## Next Command To Run

- `/Users/ecohen/Codex/imageTo3MF/build_leadlight_app.sh`
- `/Users/ecohen/Codex/filamentDB/build_filamentdb_app.sh`
- `uv run --project /Users/ecohen/Codex/imageTo3MF python /Users/ecohen/Codex/imageTo3MF/glass_interior_growth_lab.py /Users/ecohen/Desktop/F.png --analysis-blur-px 1.4 --lead-luma-threshold 30 --hard-lead-chroma-max 26 --neutral-chroma-max 18 --neutral-edge-threshold 14 --output /tmp/glass_interior_growth_F.png`
- `uv run --project /Users/ecohen/Codex/imageTo3MF python /Users/ecohen/Codex/imageTo3MF/glass_hybrid_anchor_lab.py /Users/ecohen/Desktop/F.png --output /tmp/glass_hybrid_F.png`

## Open Questions

- Should the Desktop app refresh also open Finder to the updated app automatically, or is silent replacement better?
- Should the same Desktop-refresh behavior be added to any future local app bundles under `/Users/ecohen/Codex`?
- Is the `glass_interior_growth_lab.py` approach strong enough to replace detect mode, or should it remain a side experiment?
- Is the hybrid lab good enough to become the new direction for detect mode, or should it stay as a separate “detected-anchor” option?

## Blockers

- No technical blockers currently.
- Desktop app copies now refresh on rebuild; main remaining question is whether to extend the same pattern to other local apps.

## Resume Checklist

- Run `git -C /Users/ecohen/Codex status --short --branch`
- Run `git -C /Users/ecohen/Codex log --oneline -5`
- Review this file and update/remove stale items
- Continue with the next command above
