# Olea Media Co Project

Local project workspace for the Olea Media Co website, concept variants, and client-facing PDFs.

## Scope

Use this folder for Olea Media Co work only:

- Main page: `index.html`
- Shared assets/styles/scripts: `assets/`, `styles.css`, `script.js`, `shared-*.js`
- Concept variants: `v1/` through `v5/`
- Published PDFs: `OleaMediaCo-Offer-EN.pdf`, `OleaMediaCo-Oferta-ES.pdf`, `OleaMediaCo-Offre-FR.pdf`
- Source materials: `source/`

Do not edit Olea Tax Co files from this project thread.

## Local Preview

```bash
cd /Users/ecohen/Codex/web/github.io
python3 -m http.server 8000
```

Open `http://localhost:8000/oleamediaco/`.

## PDF Source Workflow

Source files live under `source/`:

- `source/offer-sheet-en.md`
- `source/offer-sheet-es.md`
- `source/offer-sheet-en.html`
- `source/offer-sheet-es.html`
- `source/make_offer_pdfs.py`

If PDF content changes, regenerate PDFs from `source/` and keep the output files in this folder root so links stay valid.

## Deployment

GitHub Pages deploy is handled by:

- `/Users/ecohen/Codex/.github/workflows/deploy-oleamediaco-site.yml`

This workflow publishes this folder to:

- `https://ec92009.github.io/Codex/oleamediaco/`
