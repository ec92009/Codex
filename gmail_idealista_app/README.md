# Gmail Idealista Mailbox Reader

This app connects to Gmail via OAuth and lists the 10 newest emails that match:
- sent directly by `idealista`

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
python app.py
```

On first run, your browser opens for Google login and consent. A `token.json` file is created for future runs.

## Query used

The app uses this Gmail query by default:

```text
from:idealista
```

You can customize it with:

```bash
python app.py --query 'from:(@idealista.com OR idealista) in:anywhere'
```

## Notes

- This app only reads mailbox metadata/snippets (`gmail.readonly` scope).
- To force re-authentication, delete `token.json`.
