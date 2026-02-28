# Olea Tax Co Project

Local project workspace for Olea Tax Co concept pages used to decide final direction before a production CMS build.

## Scope

Use this folder for Olea Tax Co work only:

- Concept board index: `index.html`
- Homepage directions: `concepts/`
- Shared styles/scripts: `assets/`
- Planning notes: `content-workbook.md`

Do not edit Olea Media Co files from this project thread.

## Local Preview

```bash
cd /Users/ecohen/Codex/web/github.io
python3 -m http.server 8000
```

Open `http://localhost:8000/oleataxco/`.

## Concept Files

- `concepts/01-trust-ledger.html`
- `concepts/02-modern-growth.html`
- `concepts/03-neighborhood-advisor.html`

Update copy and structure in the selected concept first, then backport approved shared changes only when requested.

## Founder Photo

All 3 concept pages now render a founder photo in the hero-side panel using:

- `web/github.io/oleataxco/assets/kelly-portrait.jpg`

Add/replace that file to update the image across Concepts 1-3.

## Draft Disclaimer

All versions include the same top banner text:

- `MOCK DRAFT`
- `Internal review only. Content, pricing, and visuals are placeholders for team feedback.`

## Deployment

GitHub Pages deploy is handled by:

- `/Users/ecohen/Codex/.github/workflows/deploy-oleamediaco-site.yml`

This workflow publishes this folder to:

- `https://ec92009.github.io/Codex/oleataxco/`
