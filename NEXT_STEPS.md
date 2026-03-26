# Next Steps

Use this file as a quick checkpoint before stopping work.

## Current Task

- Keep LeadLight and filamentDB in sync across machines, with Desktop app bundles refreshing automatically after rebuilds.
- Validate the integrated hybrid `detect` mode on a wider real-image set and decide whether the old direct-detect helpers can be retired.
- `gmail_idealista_app`: added `report` mode to extract listing URLs from Idealista alert emails and `enrich` mode to visit only those email-derived property URLs for public advertiser details.

## Last Completed

- Pushed `423c193` - `leadlight: add shared material preset`
- Updated both macOS app builders so rebuilding also refreshes `/Users/ecohen/Desktop/LeadLight.app` and `/Users/ecohen/Desktop/filamentDB.app`
- Built a more promising detect-mode lab around glass-interior growth instead of direct lead detection.
- Built a hybrid anchor-detect + generated-pane lab that looks strong on most of `A.png` through `F.png`.
- Added a before/after palette reduction view to the hybrid lab so it can be judged against the real `8..10 color` print constraint.
- Updated the reduced hybrid preview so generated lead between panes of the same reduced color is removed automatically.
- Integrated the hybrid anchor-detect + generated-pane pipeline into LeadLight's `detect` mode while leaving `generate` untouched.
- Added Gmail token refresh fallback in [`/Users/rookcohen/Codex/gmail_idealista_app/app.py`](/Users/rookcohen/Codex/gmail_idealista_app/app.py) so expired OAuth tokens re-enter browser auth instead of crashing.
- Added `report` and `enrich` flows plus docs in [`/Users/rookcohen/Codex/gmail_idealista_app/README.md`](/Users/rookcohen/Codex/gmail_idealista_app/README.md).
- Verified `enrich` writes outputs against the email-derived listing URLs and currently reports `challenge_or_unparsed` when Idealista serves a challenge page.

## Next Command To Run

- `/Users/ecohen/Codex/imageTo3MF/build_leadlight_app.sh`
- `/Users/ecohen/Codex/filamentDB/build_filamentdb_app.sh`
- `uv run --project /Users/ecohen/Codex/imageTo3MF python /Users/ecohen/Codex/imageTo3MF/image_grade_to_3mf.py /Users/ecohen/Desktop/F.png --lead-source detect --no-open --preview /tmp/leadlight_detect_preview.png --output /tmp/leadlight_detect_test.3mf`
- `cd /Users/rookcohen/Codex/gmail_idealista_app && uv run app.py report --max-results 100`
- `cd /Users/rookcohen/Codex/gmail_idealista_app && uv run app.py enrich --input-csv listing_report.csv --limit 25 --output-prefix listing_report_enriched`

## Open Questions

- Should the Desktop app refresh also open Finder to the updated app automatically, or is silent replacement better?
- Should the same Desktop-refresh behavior be added to any future local app bundles under `/Users/ecohen/Codex`?
- Should the old direct-detect helper code and tuning lab be cleaned out now that hybrid detect is integrated?
- Do we want a user-facing control for hybrid detect sensitivity, or keep the defaults fixed for now?
- Does the existing `.playwright-profile` already contain a trusted Idealista session, or does it need one manual browser pass to clear DataDome?
- Which advertiser fields matter most after enrichment: phone only, agency name, owner-vs-agent classification, or profile URL as well?

## Blockers

- No technical blockers currently for LeadLight / filamentDB.
- Desktop app copies now refresh on rebuild; main remaining question is whether to extend the same pattern to other local apps.
- Idealista currently returns a challenge page in headless enrichment runs, so advertiser data is not yet being extracted until the browser profile clears that challenge.
- Gmail `report` mode requires one fresh Google OAuth browser login because the previous token was revoked.

## Resume Checklist

- Run `git -C /Users/rookcohen/Codex status --short --branch`
- Re-auth Gmail if needed with `cd /Users/rookcohen/Codex/gmail_idealista_app && uv run app.py report --max-results 100`
- Run the constrained enrichment command and inspect `listing_report_enriched.csv`
- If the challenge persists, rerun `enrich` without `--headless` so the browser session can clear it interactively`
