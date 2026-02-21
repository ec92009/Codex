from __future__ import annotations

import argparse
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from dateutil import parser as date_parser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DEFAULT_QUERY = "from:idealista"
MAX_RESULTS = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List newest emails sent directly by Idealista from Gmail."
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help=f"Gmail search query (default: {DEFAULT_QUERY!r})",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=MAX_RESULTS,
        help=f"Maximum emails to list (default: {MAX_RESULTS})",
    )
    return parser.parse_args()


def load_credentials(base_dir: Path) -> Credentials:
    token_path = base_dir / "token.json"
    creds_path = base_dir / "credentials.json"

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                raise FileNotFoundError(
                    f"Missing {creds_path}. Download OAuth client credentials and place them there."
                )

            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)

        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def get_header(headers: list[dict[str, str]], key: str) -> str:
    key_lower = key.lower()
    for header in headers:
        if header.get("name", "").lower() == key_lower:
            return header.get("value", "")
    return ""


def to_iso_datetime(value: str) -> str:
    if not value:
        return "(no date)"
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().isoformat()
    except Exception:
        try:
            dt2 = date_parser.parse(value)
            if dt2.tzinfo is None:
                dt2 = dt2.replace(tzinfo=timezone.utc)
            return dt2.astimezone().isoformat()
        except Exception:
            return value


def fetch_messages(service: Any, query: str, max_results: int) -> list[dict[str, Any]]:
    response = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    ids = response.get("messages", [])
    results: list[dict[str, Any]] = []

    for msg in ids:
        details = (
            service.users()
            .messages()
            .get(userId="me", id=msg["id"], format="metadata")
            .execute()
        )
        headers = details.get("payload", {}).get("headers", [])
        results.append(
            {
                "id": details.get("id", ""),
                "thread_id": details.get("threadId", ""),
                "from": get_header(headers, "From"),
                "to": get_header(headers, "To"),
                "subject": get_header(headers, "Subject"),
                "date_raw": get_header(headers, "Date"),
                "date": to_iso_datetime(get_header(headers, "Date")),
                "snippet": details.get("snippet", ""),
            }
        )

    return results


def print_messages(messages: list[dict[str, Any]]) -> None:
    if not messages:
        print("No matching emails found.")
        return

    print(f"Found {len(messages)} email(s):\n")
    for idx, msg in enumerate(messages, start=1):
        print(f"{idx}. Date:    {msg['date']}")
        print(f"   From:    {msg['from']}")
        print(f"   To:      {msg['to']}")
        print(f"   Subject: {msg['subject']}")
        print(f"   Snippet: {msg['snippet']}")
        print(f"   ID:      {msg['id']}")
        print()


def main() -> None:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent

    try:
        creds = load_credentials(base_dir)
        service = build("gmail", "v1", credentials=creds)
        messages = fetch_messages(service, args.query, args.max_results)
        print_messages(messages)
    except FileNotFoundError as exc:
        print(str(exc))
    except HttpError as exc:
        print(f"Gmail API error: {exc}")


if __name__ == "__main__":
    main()
