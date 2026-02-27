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

- Olea Media Co preview: `cd /Users/ecohen/Codex/web/github.io/oleamediaco && python3 -m http.server 8000`
- Olea Tax Co preview: `cd /Users/ecohen/Codex/web/github.io/oleataxco && python3 -m http.server 8001`

## Repo Workflow

- Work inside project folders under `/Users/ecohen/Codex`.
- Commit changes from the repo root with clear messages.
- Push to `main` to sync with GitHub: [ec92009/Codex](https://github.com/ec92009/Codex).
