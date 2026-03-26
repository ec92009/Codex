# Next Steps

Use this file as a quick checkpoint before stopping work.

## Current Task

- Keep LeadLight and filamentDB in sync across machines, with Desktop app bundles refreshing automatically after rebuilds.

## Last Completed

- Pushed `423c193` - `leadlight: add shared material preset`
- Updated both macOS app builders so rebuilding also refreshes `/Users/ecohen/Desktop/LeadLight.app` and `/Users/ecohen/Desktop/filamentDB.app`

## Next Command To Run

- `/Users/ecohen/Codex/imageTo3MF/build_leadlight_app.sh`
- `/Users/ecohen/Codex/filamentDB/build_filamentdb_app.sh`

## Open Questions

- Should the Desktop app refresh also open Finder to the updated app automatically, or is silent replacement better?
- Should the same Desktop-refresh behavior be added to any future local app bundles under `/Users/ecohen/Codex`?

## Blockers

- No technical blockers currently.
- Desktop app copies now refresh on rebuild; main remaining question is whether to extend the same pattern to other local apps.

## Resume Checklist

- Run `git -C /Users/ecohen/Codex status --short --branch`
- Run `git -C /Users/ecohen/Codex log --oneline -5`
- Review this file and update/remove stale items
- Continue with the next command above
