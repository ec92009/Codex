from __future__ import annotations

import argparse
import base64
import csv
import html as html_lib
import json
import re
import time
from datetime import timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dateutil import parser as date_parser
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DEFAULT_QUERY = "from:idealista"
MAX_RESULTS = 10
DEFAULT_REPORT_MAX_RESULTS = 250
DEFAULT_ENRICH_LIMIT = 25
LISTING_ID_RE = re.compile(r"/inmueble/(\d+)")
PRICE_RE = re.compile(r"(\d[\d., ]*)\s*(€|eur|k|m)\b", re.IGNORECASE)


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = dict(attrs)
        href = attr_map.get("href")
        if href:
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._current_href:
            return
        self.links.append(
            {
                "href": self._current_href,
                "text": normalize_whitespace("".join(self._current_text)),
            }
        )
        self._current_href = None
        self._current_text = []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read Idealista Gmail alerts and build listing reports."
    )
    subparsers = parser.add_subparsers(dest="command")

    emails_parser = subparsers.add_parser(
        "emails",
        help="List the newest matching Idealista emails.",
    )
    emails_parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help=f"Gmail search query (default: {DEFAULT_QUERY!r})",
    )
    emails_parser.add_argument(
        "--max-results",
        type=int,
        default=MAX_RESULTS,
        help=f"Maximum emails to list (default: {MAX_RESULTS})",
    )

    report_parser = subparsers.add_parser(
        "report",
        help="Extract Idealista listings from matching emails and write reports.",
    )
    report_parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help=f"Gmail search query (default: {DEFAULT_QUERY!r})",
    )
    report_parser.add_argument(
        "--max-results",
        type=int,
        default=DEFAULT_REPORT_MAX_RESULTS,
        help=f"Maximum emails to inspect (default: {DEFAULT_REPORT_MAX_RESULTS})",
    )
    report_parser.add_argument(
        "--output-prefix",
        default="listing_report",
        help="Output path prefix without extension (default: listing_report)",
    )

    enrich_parser = subparsers.add_parser(
        "enrich",
        help="Visit email-derived listing URLs and capture public advertiser details.",
    )
    enrich_parser.add_argument(
        "--input-csv",
        default="listing_report.csv",
        help="Input listing report CSV (default: listing_report.csv)",
    )
    enrich_parser.add_argument(
        "--output-prefix",
        default="listing_report_enriched",
        help="Output path prefix without extension (default: listing_report_enriched)",
    )
    enrich_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_ENRICH_LIMIT,
        help=f"Maximum listings to enrich (default: {DEFAULT_ENRICH_LIMIT})",
    )
    enrich_parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless. Omit for interactive debugging/challenge handling.",
    )
    enrich_parser.add_argument(
        "--profile-dir",
        default=".playwright-profile",
        help="Persistent Chromium profile directory (default: .playwright-profile)",
    )
    parser.set_defaults(command="emails")
    return parser.parse_args()


def load_credentials(base_dir: Path) -> Credentials:
    token_path = base_dir / "token.json"
    creds_path = base_dir / "credentials.json"

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                creds = None
        if not creds or not creds.valid:
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


def decode_body_data(data: str) -> str:
    padding = "=" * (-len(data) % 4)
    decoded = base64.urlsafe_b64decode(data + padding)
    return decoded.decode("utf-8", errors="replace")


def iter_parts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    parts = payload.get("parts") or []
    if not parts:
        return [payload]
    flattened: list[dict[str, Any]] = []
    for part in parts:
        flattened.extend(iter_parts(part))
    return flattened


def extract_message_bodies(payload: dict[str, Any]) -> tuple[str, str]:
    html_chunks: list[str] = []
    text_chunks: list[str] = []
    for part in iter_parts(payload):
        mime_type = part.get("mimeType", "")
        body_data = part.get("body", {}).get("data")
        if not body_data:
            continue
        decoded = decode_body_data(body_data)
        if mime_type == "text/html":
            html_chunks.append(decoded)
        elif mime_type == "text/plain":
            text_chunks.append(decoded)
    return "\n".join(html_chunks), "\n".join(text_chunks)


def normalize_whitespace(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}/"


def extract_listing_id(url: str) -> str | None:
    match = LISTING_ID_RE.search(url)
    if not match:
        return None
    return match.group(1)


def parse_price_to_eur(value: str) -> int | None:
    text = normalize_whitespace(value).lower().replace("eur", "€")
    match = PRICE_RE.search(text)
    if not match:
        return None
    number_text = match.group(1).replace(" ", "")
    suffix = match.group(2).lower()
    if "," in number_text and "." in number_text:
        number_text = number_text.replace(".", "").replace(",", ".")
    elif "," in number_text:
        number_text = number_text.replace(",", ".")
    try:
        amount = float(number_text)
    except ValueError:
        return None
    if suffix == "k":
        amount *= 1_000
    elif suffix == "m":
        amount *= 1_000_000
    return int(round(amount))


def format_price_short(value: int | None) -> str:
    if value is None:
        return ""
    if value >= 1_000_000:
        millions = value / 1_000_000
        return f"{millions:.1f}M".replace(".0", "")
    if value >= 1_000:
        thousands = value / 1_000
        return f"{thousands:.0f}K"
    return str(value)


def extract_links_from_html(html_body: str) -> list[dict[str, str]]:
    collector = LinkCollector()
    collector.feed(html_body)
    return collector.links


def extract_context_text(anchor: Any) -> str:
    candidates: list[str] = []
    parent = anchor.parent
    if parent is not None:
        candidates.append(parent.get_text(" ", strip=True))
    row = anchor.find_parent("tr")
    if row is not None:
        candidates.append(row.get_text(" ", strip=True))
    container = anchor.find_parent(["table", "div", "section", "li"])
    if container is not None:
        candidates.append(container.get_text(" ", strip=True))
    candidates.append(anchor.get_text(" ", strip=True))
    return normalize_whitespace(" ".join(candidates))


def extract_listings_from_message(message: dict[str, Any]) -> list[dict[str, Any]]:
    html_body, text_body = extract_message_bodies(message.get("payload", {}))
    headers = message.get("payload", {}).get("headers", [])
    message_date = to_iso_datetime(get_header(headers, "Date"))
    soup = BeautifulSoup(html_body, "html.parser") if html_body else None

    candidates: dict[str, dict[str, Any]] = {}
    for link in extract_links_from_html(html_body):
        href = html_lib.unescape(link["href"])
        listing_id = extract_listing_id(href)
        if not listing_id:
            continue
        url = normalize_url(href)
        title_hint = link["text"]
        price_eur: int | None = None
        if soup:
            anchor = soup.find("a", href=re.compile(re.escape(href)))
            if anchor:
                context = extract_context_text(anchor)
                if not title_hint:
                    title_hint = normalize_whitespace(anchor.get_text(" ", strip=True))
                price_eur = parse_price_to_eur(context)
        if price_eur is None:
            price_eur = parse_price_to_eur(text_body)
        candidates[listing_id] = {
            "listing_id": listing_id,
            "url": url,
            "title_hint": title_hint,
            "price_eur": price_eur,
            "seen_at": message_date,
            "subject": get_header(headers, "Subject"),
            "from": get_header(headers, "From"),
            "to": get_header(headers, "To"),
            "message_id": message.get("id", ""),
        }

    return list(candidates.values())


def fetch_full_messages(service: Any, query: str, max_results: int) -> list[dict[str, Any]]:
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
            .get(userId="me", id=msg["id"], format="full")
            .execute()
        )
        results.append(details)
    return results


def build_listing_report(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    listings: dict[str, dict[str, Any]] = {}
    for message in messages:
        for listing in extract_listings_from_message(message):
            listing_id = listing["listing_id"]
            existing = listings.get(listing_id)
            if existing is None:
                listings[listing_id] = {
                    "listing_id": listing_id,
                    "url": listing["url"],
                    "title_hint": listing["title_hint"],
                    "price_eur": listing["price_eur"],
                    "first_seen": listing["seen_at"],
                    "last_seen": listing["seen_at"],
                    "days_since_first_seen": 0,
                    "email_hits": 1,
                    "latest_subject": listing["subject"],
                    "latest_from": listing["from"],
                    "latest_to": listing["to"],
                    "latest_message_id": listing["message_id"],
                }
                continue
            existing["email_hits"] += 1
            if listing["title_hint"] and not existing["title_hint"]:
                existing["title_hint"] = listing["title_hint"]
            if listing["price_eur"] is not None:
                existing["price_eur"] = listing["price_eur"]
            if listing["seen_at"] < existing["first_seen"]:
                existing["first_seen"] = listing["seen_at"]
            if listing["seen_at"] >= existing["last_seen"]:
                existing["last_seen"] = listing["seen_at"]
                existing["latest_subject"] = listing["subject"]
                existing["latest_from"] = listing["from"]
                existing["latest_to"] = listing["to"]
                existing["latest_message_id"] = listing["message_id"]

    rows = sorted(
        listings.values(),
        key=lambda item: (item["last_seen"], item["listing_id"]),
        reverse=True,
    )
    for row in rows:
        first_seen = date_parser.isoparse(row["first_seen"])
        last_seen = date_parser.isoparse(row["last_seen"])
        row["days_since_first_seen"] = (last_seen.date() - first_seen.date()).days
        row["price_short"] = format_price_short(row["price_eur"])
    return rows


def write_listing_report(rows: list[dict[str, Any]], output_prefix: str) -> list[Path]:
    prefix_path = Path(output_prefix)
    if not prefix_path.is_absolute():
        prefix_path = Path(__file__).resolve().parent / prefix_path
    prefix_path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "listing_id",
        "url",
        "title_hint",
        "price_eur",
        "first_seen",
        "last_seen",
        "days_since_first_seen",
        "email_hits",
        "latest_subject",
        "latest_from",
        "latest_to",
        "latest_message_id",
    ]

    csv_path = prefix_path.with_suffix(".csv")
    tsv_path = prefix_path.with_suffix(".tsv")
    json_path = prefix_path.with_suffix(".json")
    html_path = prefix_path.with_suffix(".html")

    for path, delimiter in ((csv_path, ","), (tsv_path, "\t")):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter=delimiter)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fields})

    json_path.write_text(
        json.dumps([{field: row.get(field, "") for field in fields} for row in rows], indent=2),
        encoding="utf-8",
    )

    generated_at = date_parser.parse(rows[0]["last_seen"]).astimezone().isoformat() if rows else ""
    html_rows = []
    for row in rows:
        html_rows.append(
            "<tr>"
            f"<td>{row['listing_id']}</td>"
            f"<td><a href=\"{html_lib.escape(row['url'])}\" target=\"_blank\" rel=\"noopener noreferrer\">Open</a></td>"
            f"<td>{html_lib.escape(row['title_hint'])}</td>"
            f"<td>{html_lib.escape(row['price_short'])}</td>"
            f"<td>{html_lib.escape(row['first_seen'][:10])}</td>"
            f"<td>{html_lib.escape(row['last_seen'][:10])}</td>"
            f"<td>{row['days_since_first_seen']}</td>"
            f"<td>{row['email_hits']}</td>"
            "</tr>"
        )
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Idealista Listing Links</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 24px; }}
    h1 {{ margin: 0 0 6px 0; }}
    .meta {{ color: #555; margin-bottom: 16px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f4f4f4; position: sticky; top: 0; }}
    tr:nth-child(even) {{ background: #fafafa; }}
  </style>
</head>
<body>
  <h1>Idealista Listing Links</h1>
  <div class="meta">Generated: {html_lib.escape(generated_at)} | Total listings: {len(rows)}</div>
  <table>
    <thead>
      <tr>
        <th>Listing ID</th>
        <th>Link</th>
        <th>Title Hint</th>
        <th>Price</th>
        <th>First Seen</th>
        <th>Last Seen</th>
        <th>Days Since First Seen</th>
        <th>Email Hits</th>
      </tr>
    </thead>
    <tbody>
      {''.join(html_rows)}
    </tbody>
  </table>
</body>
</html>
"""
    html_path.write_text(html_doc, encoding="utf-8")
    return [csv_path, tsv_path, json_path, html_path]


def resolve_output_prefix(output_prefix: str) -> Path:
    prefix_path = Path(output_prefix)
    if not prefix_path.is_absolute():
        prefix_path = Path(__file__).resolve().parent / prefix_path
    prefix_path.parent.mkdir(parents=True, exist_ok=True)
    return prefix_path


def load_csv_rows(input_csv: str) -> list[dict[str, str]]:
    input_path = Path(input_csv)
    if not input_path.is_absolute():
        input_path = Path(__file__).resolve().parent / input_path
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def first_text(page: Any, selectors: list[str]) -> str:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.count() == 0:
                continue
            text = normalize_whitespace(locator.inner_text(timeout=2_000))
            if text:
                return text
        except Exception:
            continue
    return ""


def first_attr(page: Any, selectors: list[str], attr: str) -> str:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.count() == 0:
                continue
            value = locator.get_attribute(attr, timeout=2_000)
            if value:
                return value
        except Exception:
            continue
    return ""


def extract_phone_from_text(text: str) -> str:
    match = re.search(r"(\+?\d[\d\s().-]{7,}\d)", text)
    return normalize_whitespace(match.group(1)) if match else ""


def parse_json_ld_contacts(page: Any) -> dict[str, str]:
    result = {
        "contact_name": "",
        "contact_phone": "",
        "contact_url": "",
        "agency_name": "",
    }
    scripts = page.locator("script[type='application/ld+json']")
    count = min(scripts.count(), 10)
    for index in range(count):
        try:
            raw = scripts.nth(index).inner_text(timeout=2_000)
            data = json.loads(raw)
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            seller = item.get("seller") or item.get("provider") or item.get("author")
            if isinstance(seller, dict):
                result["agency_name"] = result["agency_name"] or seller.get("name", "")
                result["contact_phone"] = result["contact_phone"] or seller.get("telephone", "")
                result["contact_url"] = result["contact_url"] or seller.get("url", "")
            result["contact_name"] = result["contact_name"] or item.get("name", "")
    return result


def extract_contact_details(page: Any, url: str) -> dict[str, str]:
    body_text = ""
    try:
        body_text = page.locator("body").inner_text(timeout=5_000)
    except Exception:
        pass

    json_ld = parse_json_ld_contacts(page)
    advertiser_name = first_text(
        page,
        [
            "[data-testid='professional-name']",
            ".advertiser-name-container",
            ".about-advertiser-name",
            ".offer-advertiser-name",
            ".professional-name",
            "a[href*='/pro/']",
        ],
    )
    advertiser_type = first_text(
        page,
        [
            "[data-testid='advertiser-type']",
            ".professional-name + p",
            ".about-advertiser-subtitle",
            ".offer-advertiser-type",
        ],
    )
    office_name = first_text(
        page,
        [
            "[data-testid='office-name']",
            ".about-advertiser-office",
            ".offer-advertiser-office",
        ],
    )
    contact_phone = first_text(
        page,
        [
            "a[href^='tel:']",
            "[data-testid='phone-number']",
            ".contact-phones",
            ".phone-number",
        ],
    )
    if not contact_phone:
        contact_phone = extract_phone_from_text(body_text)

    advertiser_profile_url = first_attr(
        page,
        [
            "a[href*='/pro/']",
            "a[href*='/inmobiliaria/']",
            "a[href*='/particular/']",
        ],
        "href",
    )
    if advertiser_profile_url and advertiser_profile_url.startswith("/"):
        advertiser_profile_url = f"https://www.idealista.com{advertiser_profile_url}"

    return {
        "listing_url": url,
        "page_title": page.title(),
        "final_url": page.url,
        "scrape_status": "ok" if "idealista.com" in page.url else "unexpected_url",
        "advertiser_name": advertiser_name or json_ld["agency_name"] or json_ld["contact_name"],
        "advertiser_type": advertiser_type,
        "office_name": office_name,
        "contact_phone": contact_phone or json_ld["contact_phone"],
        "advertiser_profile_url": advertiser_profile_url or json_ld["contact_url"],
        "body_contact_hint": extract_phone_from_text(body_text),
    }


def enrich_listing_rows(
    rows: list[dict[str, str]],
    profile_dir: str,
    headless: bool,
    limit: int,
) -> list[dict[str, str]]:
    if limit > 0:
        rows = rows[:limit]
    profile_path = Path(profile_dir)
    if not profile_path.is_absolute():
        profile_path = Path(__file__).resolve().parent / profile_path

    enriched: list[dict[str, str]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_path),
            headless=headless,
        )
        page = browser.new_page()
        for row in rows:
            url = row.get("url", "").strip()
            if not url:
                enriched.append({**row, "scrape_status": "missing_url"})
                continue
            record = {**row}
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_timeout(3_000)
                record.update(extract_contact_details(page, url))
                if page.title().strip() == "idealista.com" and "inmueble" in page.url:
                    record["scrape_status"] = "challenge_or_unparsed"
            except PlaywrightTimeoutError:
                record.update(
                    {
                        "listing_url": url,
                        "final_url": page.url,
                        "page_title": page.title() if page else "",
                        "scrape_status": "timeout",
                    }
                )
            except Exception as exc:
                record.update(
                    {
                        "listing_url": url,
                        "scrape_status": f"error:{type(exc).__name__}",
                    }
                )
            enriched.append(record)
            time.sleep(1.0)
        browser.close()
    return enriched


def write_enriched_report(rows: list[dict[str, str]], output_prefix: str) -> list[Path]:
    prefix_path = resolve_output_prefix(output_prefix)
    csv_path = prefix_path.with_suffix(".csv")
    json_path = prefix_path.with_suffix(".json")

    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return [csv_path, json_path]


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
        if args.command == "enrich":
            rows = load_csv_rows(args.input_csv)
            enriched_rows = enrich_listing_rows(
                rows=rows,
                profile_dir=args.profile_dir,
                headless=args.headless,
                limit=args.limit,
            )
            output_paths = write_enriched_report(enriched_rows, args.output_prefix)
            print(f"Enriched {len(enriched_rows)} listing(s):")
            for path in output_paths:
                print(f"- {path}")
            return

        creds = load_credentials(base_dir)
        service = build("gmail", "v1", credentials=creds)
        if args.command == "report":
            messages = fetch_full_messages(service, args.query, args.max_results)
            rows = build_listing_report(messages)
            output_paths = write_listing_report(rows, args.output_prefix)
            print(f"Generated {len(rows)} listing(s):")
            for path in output_paths:
                print(f"- {path}")
        else:
            messages = fetch_messages(service, args.query, args.max_results)
            print_messages(messages)
    except FileNotFoundError as exc:
        print(str(exc))
    except HttpError as exc:
        print(f"Gmail API error: {exc}")


if __name__ == "__main__":
    main()
