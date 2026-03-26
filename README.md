# Codex Workspace

Central workspace repository for ongoing projects under `/Users/ecohen/Codex`.

## Projects

- `MacControl`: Local macOS control/verification scripts, including pointer checks and Desktop screen snapshots.
- `web/github.io`: Canonical local website workspace for GitHub Pages.
- `gmail_idealista_app`: Python app for Gmail + Idealista automation.

## Website Structure

- `web/github.io/oleamediaco`: Olea Media Co site, variants, assets, and published PDFs.
- `web/github.io/oleamediaco/source`: Olea Media Co source materials (offer-sheet markdown/html and PDF generation script).
- `web/github.io/oleataxco`: Olea Tax Co concept board and homepage directions.

When working in separate threads, treat `oleamediaco` and `oleataxco` as separate projects and keep edits scoped to the active project only.

## Notable Files

### Olea Media Co PDFs

- [OleaMediaCo-Offer-EN.pdf](./web/github.io/oleamediaco/OleaMediaCo-Offer-EN.pdf)
- [OleaMediaCo-Oferta-ES.pdf](./web/github.io/oleamediaco/OleaMediaCo-Oferta-ES.pdf)
- [OleaMediaCo-Offre-FR.pdf](./web/github.io/oleamediaco/OleaMediaCo-Offre-FR.pdf)

### Website Concept Previews (GitHub Pages)

- Root landing page: [ec92009.github.io/Codex](https://ec92009.github.io/Codex/)
- Olea Media Co concepts: [ec92009.github.io/Codex/oleamediaco/](https://ec92009.github.io/Codex/oleamediaco/)
- Olea Tax Co. CPA concepts: [ec92009.github.io/Codex/oleataxco/](https://ec92009.github.io/Codex/oleataxco/)

GitHub Pages is deployed by `.github/workflows/deploy-oleamediaco-site.yml`, which now publishes both concept sets in a single Pages artifact.

## Local Development

- Top-level local preview: `cd /Users/ecohen/Codex/web/github.io && python3 -m http.server 8000`
- Olea Media Co: `http://localhost:8000/oleamediaco/`
- Olea Tax Co: `http://localhost:8000/oleataxco/`

## Repo Workflow

- Work inside project folders under `/Users/ecohen/Codex`.
- Commit changes from the repo root with clear messages.
- Push to `main` to sync with GitHub: [ec92009/Codex](https://github.com/ec92009/Codex).

## Cross-Computer Workflow

Use GitHub as the source of truth for code and tracked scripts. Local generated artifacts such as `build/` and `dist/` are ignored and should be rebuilt on each machine.

Finish on computer A:

```bash
cd /Users/ecohen/Codex
git status
git add .
git commit -m "short clear message"
git push origin main
```

Start on computer B:

```bash
cd /Users/ecohen/Codex
git pull --ff-only origin main
```

Rebuild local macOS app bundles after pulling when needed:

```bash
/Users/ecohen/Codex/imageTo3MF/build_leadlight_app.sh
/Users/ecohen/Codex/filamentDB/build_filamentdb_app.sh
```

Each build now also refreshes the Desktop launcher copy automatically:

- `/Users/ecohen/Desktop/LeadLight.app`
- `/Users/ecohen/Desktop/filamentDB.app`

Notes:

- Commit source changes, docs, scripts, icons, and launcher changes.
- Do not commit generated `build/` or `dist/` folders.
- If you change both `imageTo3MF` and `filamentDB`, commit them together from the repo root so the two apps stay in sync.
- Before starting work on another computer, always `git pull` first.

## Cleanup Routine

Use this when settling a machine after pulling fresh changes:

1. `git pull --ff-only origin main`
2. Verify `filamentDB/data/filaments.tsv` looks current.
3. If an old local `filaments.db` is still present and the TSV is confirmed good, archive it to `filaments.db.bak` or remove it.
4. Rebuild local app bundles if launcher, icon, or app-wrapper code changed. This also refreshes the Desktop copies.
5. Start work only after the repo and local wrappers are current.
