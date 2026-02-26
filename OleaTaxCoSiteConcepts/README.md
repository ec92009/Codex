# Olea Tax Co. Website Concepts (for SquareSpace planning)

This folder contains a small static preview site with **3 homepage concepts** for Kelly Olea's CPA business.

Current domain already secured (not published yet): **OleaTaxCo.com**

## Files

- `index.html` - comparison page linking to all concepts
- `concepts/01-trust-ledger.html` - traditional / premium concept
- `concepts/02-modern-growth.html` - modern / growth-focused concept
- `concepts/03-neighborhood-advisor.html` - warm / local concept
- `content-workbook.md` - questions and content checklist for Kelly

## How to preview locally

Open `index.html` in a browser, or run a simple local server:

```bash
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

## Recommended workflow (GitHub + SquareSpace)

1. Review the 3 concepts with Kelly and pick one direction (or mix pieces).
2. Mark edits directly in the HTML text (headlines, services, tone, CTA).
3. Finalize content using `content-workbook.md`.
4. Recreate the chosen layout in SquareSpace using a template that matches the style.
5. Paste finalized content into SquareSpace pages (Home, Services, About, Contact, FAQ).
6. Connect `OleaTaxCo.com` and publish from SquareSpace.

## GitHub Pages preview (for sharing options)

After pushing to `main` in the `Codex` repo and waiting for the Pages workflow:

- Concept board URL: `https://ec92009.github.io/Codex/oleataxco/`
- Repo Pages landing page: `https://ec92009.github.io/Codex/`

## Why use this before SquareSpace

- Fast experimentation without fighting template settings
- Easy to compare multiple brand directions side-by-side
- Lets Kelly react to real wording, not just colors/fonts

## SquareSpace build mapping (practical)

- Hero section -> SquareSpace banner/intro section
- Services cards -> Summary/List blocks
- Process steps -> Accordion or stacked text sections
- Testimonials -> Quote blocks
- CTA buttons -> Button blocks + Contact Form block

## Content notes

All copy is draft placeholder content for planning. Replace with Kelly's actual:

- legal business name
- website/domain reference (`OleaTaxCo.com`)
- service offerings
- service area (local/remote)
- contact details
- credentials/bio
- testimonials (when available)
