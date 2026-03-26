# Gmail Idealista Mailbox Reader

This app connects to Gmail via OAuth and can:
- list the newest emails sent directly by `idealista`
- extract Idealista listing links from those emails into `csv`, `tsv`, `json`, and `html` reports

## 1) Create Google Cloud credentials

1. Go to Google Cloud Console.
2. Create/select a project.
3. Enable **Gmail API**.
4. Configure OAuth consent screen (External is fine for personal use).
5. Create OAuth client ID of type **Desktop app**.
6. Download the JSON and save it as:

`credentials.json`

inside this folder (`/Users/rookcohen/Codex/gmail_idealista_app`).

## 2) Install dependencies

```bash
cd /Users/rookcohen/Codex/gmail_idealista_app
uv python install 3.12
uv venv --python 3.12 --clear .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## 3) Run

```bash
uv run app.py emails
```

On first run, your browser opens for Google login and consent. A `token.json` file is created for future runs.

## 4) Build a listing report

```bash
cd /Users/rookcohen/Codex/gmail_idealista_app
uv run app.py report --max-results 250
```

This writes:

- `listing_report.csv`
- `listing_report.tsv`
- `listing_report.json`
- `listing_report.html`

Use `--output-prefix` to change the base filename:

```bash
uv run app.py report --output-prefix reports/my_search
```

## 5) Enrich listings with public advertiser details

This step reads the email-derived listings and visits only those property URLs. It does not crawl broader search pages.

```bash
cd /Users/rookcohen/Codex/gmail_idealista_app
uv run app.py enrich --input-csv listing_report.csv --limit 25
```

This writes:

- `listing_report_enriched.csv`
- `listing_report_enriched.json`

Notes:

- The browser step uses the local Chromium profile in `.playwright-profile`.
- Omit `--headless` if you want to watch the browser and manually clear any Idealista challenge.
- Captured fields are limited to publicly visible advertiser details on each listing page, such as advertiser name, office name, phone text if shown, and advertiser profile URL.

## Query used

Both commands use this Gmail query by default:

```text
from:idealista
```

You can customize it with:

```bash
uv run app.py emails --query 'from:(@idealista.com OR idealista) in:anywhere'
uv run app.py report --query 'from:(@idealista.com OR idealista) in:anywhere'
```

## Notes

- This app only reads mailbox metadata/snippets (`gmail.readonly` scope).
- Direct anonymous scraping of `idealista.com` is currently blocked by DataDome, so the implemented scrape path is based on the Idealista alert emails already reaching Gmail.
- The `enrich` command stays constrained to the listing URLs extracted from those emails.
- To force re-authentication, delete `token.json`.
