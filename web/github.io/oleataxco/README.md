# Olea Tax Co Project

Local project workspace for the single Olea Tax Co draft website before a production CMS build.

## Scope

Use this folder for Olea Tax Co work only:

- Single draft homepage: `index.html`
- Legacy concept references: `concepts/`
- Shared styles/scripts: `assets/`
- Planning notes: `content-workbook.md`

Do not edit Olea Media Co files from this project thread.

## Local Preview

```bash
cd ~/Codex/web/github.io
python3 -m http.server 8000
```

Open `http://localhost:8000/oleataxco/`.

## Current Build

- Main draft site: `index.html`
- Theme/script assets: `assets/`
- Optional legacy concept files remain under `concepts/` for reference only
- Includes a `Book a Call` placeholder section with local date/time controls
- Includes a `Before / After` slider that auto-animates from left to right until the user interacts

## Founder Photo

The current site uses this founder photo path:

- `web/github.io/oleataxco/assets/kelly-portrait.jpg`

Add/replace that file to update the photo on the live draft homepage.

## Draft Disclaimer

All versions include the same top banner text:

- `MOCK DRAFT`
- `Internal review only. Content, pricing, and visuals are placeholders for team feedback.`

## Deployment

GitHub Pages deploy is handled by:

- `~/Codex/.github/workflows/deploy-oleamediaco-site.yml`

This workflow publishes this folder to:

- `https://ec92009.github.io/Codex/oleataxco/`

## Scheduling Placeholder

The booking section in `index.html` currently provides local placeholder controls:

- Date picker
- Time options from 10:00 AM to 4:00 PM in 30-minute increments

No external service is connected yet. Replace this with the final scheduling provider when ready.
