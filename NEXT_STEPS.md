# Next Steps

Use this file as a quick checkpoint before stopping work.

## Session Handoff - 2026-03-27

- Shared path convention: use `~/Codex` in cross-machine notes so the same instructions work on `David`, `Max`, and `Par_Rook6`.
- `David` is this Mac under `ecohen`.
- `Max` is the MacBook Pro under `ecohen`.
- `Par_Rook6` is the VM hosted on `David`, where you operate as `Rook` / `Openclaw`.
- Olea Tax work is active and the latest visible design target is the `v25.2` direction under `~/Codex/web/github.io/oleataxco/`.
- The two planning PDFs now exist on GitHub on both `main` and `codex/oleataxco-new-look`:
  `web/github.io/oleataxco/assets/Scalable-Tax-Planning-Pod-Model.pdf`
  `web/github.io/oleataxco/assets/Workload-and-Task-Justification-Model.pdf`
- Before editing Olea Tax again, decide whether to continue on `main` or on `codex/oleataxco-new-look`.
- On `David`, treat `~/Codex/filamentDB/data/filaments.tsv` as the source of truth. Legacy SQLite state is no longer relevant for `filamentDB`.

### Olea Tax Resume Commands

- `git -C ~/Codex fetch origin --prune`
- `git -C ~/Codex branch -vv`
- `git -C ~/Codex switch main && git -C ~/Codex pull --ff-only origin main`
- If you want the Olea Tax branch instead: `git -C ~/Codex switch codex/oleataxco-new-look && git -C ~/Codex pull --ff-only origin codex/oleataxco-new-look`
- `cd ~/Codex/web/github.io && python3 -m http.server 8000`
- Open `http://localhost:8000/oleataxco/`

### Olea Tax Open Questions

- Is `v25.2` close enough to the PDF-inspired advisory-deck direction, or should it move even closer?
- Should the placeholder scheduler area be replaced with a real inquiry CTA?
- Should future Olea Tax changes land directly on `main`, or stay on `codex/oleataxco-new-look` until merged?

## Current Task

- Keep LeadLight and filamentDB in sync across machines via their canonical `dist/` app bundles.
- Keep `~/Codex/filamentDB/data/filaments.tsv` on `David` as the canonical filament dataset and sync changes outward through Git.
- Validate the integrated hybrid `detect` mode on a wider real-image set and decide whether the old direct-detect helpers can be retired.
- `gmail_idealista_app`: added `report` mode to extract listing URLs from Idealista alert emails and `enrich` mode to visit only those email-derived property URLs for public advertiser details.

## Last Completed

- Pushed a portability pass so instructions now use `~/Codex` and the LeadLight / filamentDB launcher-build scripts resolve paths from the current home directory instead of `/Users/ecohen`
- Verified both documented rebuild commands succeed on `Par_Rook6`:
  `~/Codex/imageTo3MF/build_leadlight_app.sh`
  `~/Codex/filamentDB/build_filamentdb_app.sh`
- Pushed `423c193` - `leadlight: add shared material preset`
- Updated both macOS app builders to refresh only the canonical `dist/` app bundles
- Built a more promising detect-mode lab around glass-interior growth instead of direct lead detection.
- Built a hybrid anchor-detect + generated-pane lab that looks strong on most of `A.png` through `F.png`.
- Added a before/after palette reduction view to the hybrid lab so it can be judged against the real `8..10 color` print constraint.
- Updated the reduced hybrid preview so generated lead between panes of the same reduced color is removed automatically.
- Integrated the hybrid anchor-detect + generated-pane pipeline into LeadLight's `detect` mode while leaving `generate` untouched.
- Added Gmail token refresh fallback in `~/Codex/gmail_idealista_app/app.py` so expired OAuth tokens re-enter browser auth instead of crashing.
- Added `report` and `enrich` flows plus docs in `~/Codex/gmail_idealista_app/README.md`.
- Verified `enrich` writes outputs against the email-derived listing URLs and currently reports `challenge_or_unparsed` when Idealista serves a challenge page.

## Next Command To Run

- `~/Codex/imageTo3MF/build_leadlight_app.sh`
- `~/Codex/filamentDB/build_filamentdb_app.sh`
- `uv run --project ~/Codex/imageTo3MF python ~/Codex/imageTo3MF/image_grade_to_3mf.py ~/Desktop/F.png --lead-source detect --no-open --preview /tmp/leadlight_detect_preview.png --output /tmp/leadlight_detect_test.3mf`
- `cd ~/Codex/gmail_idealista_app && uv run app.py report --max-results 100`
- `cd ~/Codex/gmail_idealista_app && uv run app.py enrich --input-csv listing_report.csv --limit 25 --output-prefix listing_report_enriched`

## Open Questions

- Should future local app bundles under `~/Codex` follow the same `dist/`-only pattern?
- Should the old direct-detect helper code and tuning lab be cleaned out now that hybrid detect is integrated?
- Do we want a user-facing control for hybrid detect sensitivity, or keep the defaults fixed for now?
- Does the existing `.playwright-profile` already contain a trusted Idealista session, or does it need one manual browser pass to clear DataDome?
- Which advertiser fields matter most after enrichment: phone only, agency name, owner-vs-agent classification, or profile URL as well?

## Blockers

- No technical blockers currently for LeadLight / filamentDB.
- App rebuilds now target only the canonical `dist/` bundles.
- Idealista currently returns a challenge page in headless enrichment runs, so advertiser data is not yet being extracted until the browser profile clears that challenge.
- Gmail `report` mode requires one fresh Google OAuth browser login because the previous token was revoked.

## Resume Checklist

- Run `git -C ~/Codex status --short --branch`
- Re-auth Gmail if needed with `cd ~/Codex/gmail_idealista_app && uv run app.py report --max-results 100`
- Run the constrained enrichment command and inspect `listing_report_enriched.csv`
- If the challenge persists, rerun `enrich` without `--headless` so the browser session can clear it interactively`
