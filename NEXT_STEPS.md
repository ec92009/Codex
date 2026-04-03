# Next Steps

Use this file as a quick checkpoint before stopping work.

## Session Handoff - 2026-03-27

- Shared path convention: use `~/Codex` in cross-machine notes so the same instructions work on `David`, `Max`, and `Par_Rook6`.
- `David` is this Mac under `ecohen`.
- `Max` is the MacBook Pro under `ecohen`.
- `Par_Rook6` is the VM hosted on `David`, where you operate as `Rook` / `Openclaw`.
- As of `2026-04-03`, `LeadLight` and `FilamentDB` have moved to standalone repos and their old `~/Codex` remnants were removed locally.
- `codex/oleataxco-new-look` is no longer the default resume branch.
- Olea Tax work is active and the latest visible design target is the `v25.2` direction under `~/Codex/web/github.io/oleataxco/`.
- The two planning PDFs now exist on GitHub on both `main` and `codex/oleataxco-new-look`:
  `web/github.io/oleataxco/assets/Scalable-Tax-Planning-Pod-Model.pdf`
  `web/github.io/oleataxco/assets/Workload-and-Task-Justification-Model.pdf`
- Before editing Olea Tax again, decide whether to continue on `main` or on `codex/oleataxco-new-look`.
- On `David`, treat `~/Dev/FilamentDB/data/filaments.tsv` in the standalone `FilamentDB` repo as the source of truth. Legacy SQLite state is no longer relevant for `FilamentDB`.

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

- On any machine switch, start with `git -C ~/Codex pull --ff-only origin main`.
- For LeadLight or FilamentDB work, switch to their standalone repos before editing.
- Olea Tax work remains active under `~/Codex/web/github.io/oleataxco/`.
- `gmail_idealista_app`: added `report` mode to extract listing URLs from Idealista alert emails and `enrich` mode to visit only those email-derived property URLs for public advertiser details.

## Last Completed

- Removed the old `~/Codex/imageTo3MF` tree and stale LeadLight/FilamentDB temp build artifacts after both projects moved to standalone repos.
- Updated `~/Codex` docs so this repo no longer claims ownership of LeadLight or FilamentDB.
- Added Gmail token refresh fallback in `~/Codex/gmail_idealista_app/app.py` so expired OAuth tokens re-enter browser auth instead of crashing.
- Added `report` and `enrich` flows plus docs in `~/Codex/gmail_idealista_app/README.md`.
- Verified `enrich` writes outputs against the email-derived listing URLs and currently reports `challenge_or_unparsed` when Idealista serves a challenge page.

## Next Command To Run

- `git -C ~/Codex pull --ff-only origin main`
- `cd ~/Codex/gmail_idealista_app && uv run app.py report --max-results 100`
- `cd ~/Codex/gmail_idealista_app && uv run app.py enrich --input-csv listing_report.csv --limit 25 --output-prefix listing_report_enriched`

## Open Questions

- Do we want a user-facing control for hybrid detect sensitivity, or keep the defaults fixed for now?
- Does the existing `.playwright-profile` already contain a trusted Idealista session, or does it need one manual browser pass to clear DataDome?
- Which advertiser fields matter most after enrichment: phone only, agency name, owner-vs-agent classification, or profile URL as well?

## Blockers

- No technical blockers currently inside `~/Codex`.
- Idealista currently returns a challenge page in headless enrichment runs, so advertiser data is not yet being extracted until the browser profile clears that challenge.
- Gmail `report` mode requires one fresh Google OAuth browser login because the previous token was revoked.

## Resume Checklist

- Run `git -C ~/Codex status --short --branch`
- Re-auth Gmail if needed with `cd ~/Codex/gmail_idealista_app && uv run app.py report --max-results 100`
- Run the constrained enrichment command and inspect `listing_report_enriched.csv`
- If the challenge persists, rerun `enrich` without `--headless` so the browser session can clear it interactively`
