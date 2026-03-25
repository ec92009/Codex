#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import glob
import os
import select
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_PROJECT_DIR = Path("/Users/ecohen/Codex/filamentDB")
RUNTIME_PROJECT_DIR = SOURCE_PROJECT_DIR if not (PROJECT_DIR / "data").exists() and SOURCE_PROJECT_DIR.exists() else PROJECT_DIR
DEFAULT_DB_PATH = RUNTIME_PROJECT_DIR / "data" / "filaments.tsv"
LEGACY_DB_PATH = RUNTIME_PROJECT_DIR / "data" / "filaments.db"
FIELDNAMES = [
    "id",
    "brand",
    "filament_type",
    "name",
    "color",
    "td",
    "source",
    "notes",
    "created_at",
    "updated_at",
]


SAMPLE_FILAMENTS = [
    {
        "brand": "SUNLU",
        "type": "PLA Matte",
        "name": "Matte Black",
        "color": "#111111",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "SUNLU",
        "type": "PLA Matte",
        "name": "Matte White",
        "color": "#F2F0E9",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "SUNLU",
        "type": "PLA Matte",
        "name": "Matte Red",
        "color": "#C62828",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "SUNLU",
        "type": "PLA Matte",
        "name": "Matte Blue",
        "color": "#1F4AA8",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "SUNLU",
        "type": "PLA Matte",
        "name": "Matte Green",
        "color": "#2E8B57",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "SUNLU",
        "type": "Transparent PLA",
        "name": "Transparent Blue",
        "color": "#2D6CDF",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "SUNLU",
        "type": "Transparent PLA",
        "name": "Transparent Red",
        "color": "#D83A34",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "SUNLU",
        "type": "Transparent PLA",
        "name": "Transparent Green",
        "color": "#2FAF5A",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "SUNLU",
        "type": "Transparent PLA",
        "name": "Transparent Yellow",
        "color": "#F2DA3A",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "SUNLU",
        "type": "Transparent PLA",
        "name": "Transparent Clear",
        "color": "#F4F7F9",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "SUNLU",
        "type": "Transparent PLA",
        "name": "Transparent Purple",
        "color": "#7A52CC",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
]


@dataclass
class FilamentStore:
    path: Path
    records: list[dict[str, object]]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with temp_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, delimiter="\t")
            writer.writeheader()
            for record in sorted(self.records, key=lambda item: int(item["id"])):
                writer.writerow(serialize_record(record))
        temp_path.replace(self.path)

    def close(self) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local TSV filament database using HueForge-style brand/type/name/td/color fields."
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help=f"TSV database path. Default: {DEFAULT_DB_PATH}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Initialize the local filament database.")

    seed_parser = subparsers.add_parser("seed-samples", help="Insert a small starter sample set.")
    seed_parser.add_argument("--replace", action="store_true", help="Clear existing rows before seeding samples.")

    add_parser = subparsers.add_parser("add", help="Add a filament record.")
    add_parser.add_argument("--brand", required=True, help="Brand.")
    add_parser.add_argument("--type", required=True, help="Type, for example PLA Matte.")
    add_parser.add_argument("--name", required=True, help="HueForge-style material name.")
    add_parser.add_argument("--color", required=True, help="Color HEX like #AABBCC.")
    add_parser.add_argument("--td", type=float, default=None, help="Transmission Distance value, if known.")
    add_parser.add_argument("--source", default="manual", help="Source of the record, for example td1, vendor, or sample.")
    add_parser.add_argument("--notes", default="", help="Optional notes.")

    list_parser = subparsers.add_parser("list", help="List filament records.")
    list_parser.add_argument("--limit", type=int, default=100, help="Maximum number of rows to show.")

    show_parser = subparsers.add_parser("show", help="Show one filament record.")
    show_parser.add_argument("id", type=int, help="Filament record id.")

    delete_parser = subparsers.add_parser("delete", help="Delete one filament record.")
    delete_parser.add_argument("id", type=int, help="Filament record id.")

    search_parser = subparsers.add_parser("search", help="Search filament records by text.")
    search_parser.add_argument("query", help="Free-text search query.")
    search_parser.add_argument("--limit", type=int, default=50, help="Maximum number of rows to show.")

    export_parser = subparsers.add_parser("export-csv", help="Export all records to CSV.")
    export_parser.add_argument("path", help="Destination CSV path.")

    scan_parser = subparsers.add_parser("scan", help="Read one TD1 scan from the connected device and save it.")
    scan_parser.add_argument("--brand", required=True, help="Brand.")
    scan_parser.add_argument("--type", required=True, help="Type, for example PLA+ 2.0.")
    scan_parser.add_argument("--name", required=True, help="HueForge-style material name.")
    scan_parser.add_argument("--source", default="td1", help="Source label for the saved record.")
    scan_parser.add_argument("--notes", default="", help="Optional notes.")
    scan_parser.add_argument(
        "--device",
        default=None,
        help="Serial device path for the TD1. If omitted, the script auto-detects /dev/cu.usbmodem*.",
    )
    scan_parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Maximum seconds to wait for a reading from the TD1. Default: 15.",
    )

    return parser.parse_args()


def ensure_hex_color(value: str) -> str:
    cleaned = value.strip().upper()
    if not cleaned.startswith("#"):
        cleaned = f"#{cleaned}"
    if len(cleaned) != 7 or any(char not in "0123456789ABCDEF#" for char in cleaned):
        raise ValueError(f"Invalid HEX color: {value}")
    return cleaned


def now_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_td(value: object) -> Optional[float]:
    if value in (None, "", "None"):
        return None
    return float(value)


def normalize_record(raw: dict[str, object]) -> dict[str, object]:
    return {
        "id": int(raw["id"]),
        "brand": str(raw.get("brand", "")).strip(),
        "filament_type": str(raw.get("filament_type", "")).strip(),
        "name": str(raw.get("name", "")).strip(),
        "color": ensure_hex_color(str(raw.get("color", "#000000"))),
        "td": normalize_td(raw.get("td")),
        "source": str(raw.get("source", "manual")).strip() or "manual",
        "notes": str(raw.get("notes", "")).strip(),
        "created_at": str(raw.get("created_at", "")).strip() or now_timestamp(),
        "updated_at": str(raw.get("updated_at", "")).strip() or now_timestamp(),
    }


def serialize_record(record: dict[str, object]) -> dict[str, str]:
    return {
        "id": str(int(record["id"])),
        "brand": str(record["brand"]),
        "filament_type": str(record["filament_type"]),
        "name": str(record["name"]),
        "color": str(record["color"]),
        "td": "" if record["td"] is None else f"{float(record['td']):.2f}",
        "source": str(record["source"]),
        "notes": str(record["notes"]),
        "created_at": str(record["created_at"]),
        "updated_at": str(record["updated_at"]),
    }


def legacy_db_candidates(tsv_path: Path) -> list[Path]:
    candidates = [tsv_path.with_suffix(".db"), tsv_path.with_suffix(".sqlite3"), LEGACY_DB_PATH]
    ordered: list[Path] = []
    for candidate in candidates:
        if candidate not in ordered:
            ordered.append(candidate)
    return ordered


def import_legacy_sqlite(legacy_path: Path) -> list[dict[str, object]]:
    connection = sqlite3.connect(str(legacy_path))
    connection.row_factory = sqlite3.Row
    try:
        rows = list(
            connection.execute(
                """
                SELECT id, brand, filament_type, name, color, td, source, notes, created_at, updated_at
                FROM filaments
                ORDER BY id
                """
            )
        )
    finally:
        connection.close()
    return [normalize_record(dict(row)) for row in rows]


def connect(db_path: Path) -> FilamentStore:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    if db_path.exists():
        with db_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames is None:
                records = []
            else:
                records = [normalize_record(row) for row in reader]
    if not records:
        for legacy_path in legacy_db_candidates(db_path):
            if legacy_path.exists():
                migrated_records = import_legacy_sqlite(legacy_path)
                if migrated_records:
                    records = migrated_records
                    break
    store = FilamentStore(path=db_path, records=records)
    migrate_schema(store)
    return store


def migrate_schema(store: FilamentStore) -> None:
    if not store.path.exists():
        store.save()


def detect_td1_device() -> Optional[Path]:
    candidates = sorted(glob.glob("/dev/cu.usbmodem*"))
    return Path(candidates[0]) if candidates else None


def read_td1_scan(device_path: Path, timeout: float) -> tuple[float, str]:
    fd = os.open(str(device_path), os.O_RDONLY | os.O_NONBLOCK)
    start = time.time()
    pending = ""
    latest_td: Optional[float] = None
    latest_hex: Optional[str] = None
    try:
        while time.time() - start < timeout:
            readable, _, _ = select.select([fd], [], [], 0.5)
            if fd not in readable:
                continue
            try:
                chunk = os.read(fd, 4096)
            except BlockingIOError:
                continue
            if not chunk:
                continue
            pending += chunk.decode("utf-8", "replace")
            while "\n" in pending:
                line, pending = pending.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                parts = [part.strip() for part in line.split(",")]
                if len(parts) >= 6 and parts[-2] and parts[-1]:
                    try:
                        maybe_td = float(parts[-2])
                    except ValueError:
                        maybe_td = None
                    maybe_hex = parts[-1].upper()
                    if maybe_td is not None and len(maybe_hex) == 6 and all(ch in "0123456789ABCDEF" for ch in maybe_hex):
                        latest_td = maybe_td
                        latest_hex = maybe_hex
                        return latest_td, f"#{latest_hex}"
                if line.startswith("display,"):
                    display_parts = [part.strip() for part in line.split(",")]
                    if len(display_parts) >= 4:
                        maybe_value = display_parts[1]
                        try:
                            latest_td = float(maybe_value)
                        except ValueError:
                            if len(maybe_value) == 6 and all(ch in "0123456789ABCDEFabcdef" for ch in maybe_value):
                                latest_hex = maybe_value.upper()
                    if latest_td is not None and latest_hex is not None:
                        return latest_td, f"#{latest_hex}"
    finally:
        os.close(fd)
    raise TimeoutError(f"No TD1 reading arrived on {device_path} within {timeout:.1f}s")


def next_record_id(store: FilamentStore) -> int:
    return 1 + max((int(record["id"]) for record in store.records), default=0)


def add_filament(
    store: FilamentStore,
    *,
    brand: str,
    filament_type: str,
    name: str,
    color: str,
    td: Optional[float],
    source: str,
    notes: str,
) -> int:
    timestamp = now_timestamp()
    record_id = next_record_id(store)
    store.records.append(
        normalize_record(
            {
                "id": record_id,
                "brand": brand,
                "filament_type": filament_type,
                "name": name,
                "color": color,
                "td": td,
                "source": source,
                "notes": notes,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )
    )
    store.save()
    return record_id


def seed_samples(store: FilamentStore, replace: bool) -> int:
    if replace:
        store.records = []
    inserted = 0
    for item in SAMPLE_FILAMENTS:
        add_filament(
            store,
            brand=item["brand"],
            filament_type=item["type"],
            name=item["name"],
            color=item["color"],
            td=item["td"],
            source=item["source"],
            notes=item["notes"],
        )
        inserted += 1
    return inserted


def format_td(value: Optional[float]) -> str:
    return "" if value is None else f"{float(value):.2f}"


def list_filaments(store: FilamentStore, *, limit: Optional[int] = None, query: Optional[str] = None) -> list[dict[str, object]]:
    rows = list(store.records)
    if query:
        needle = query.strip().lower()
        rows = [
            row
            for row in rows
            if needle in str(row["brand"]).lower()
            or needle in str(row["filament_type"]).lower()
            or needle in str(row["name"]).lower()
            or needle in str(row["color"]).lower()
            or needle in str(row["source"]).lower()
            or needle in str(row["notes"]).lower()
        ]
    rows.sort(key=lambda row: int(row["id"]), reverse=True)
    if limit is not None:
        rows = rows[:limit]
    return rows


def fetch_distinct_values(store: FilamentStore, column: str) -> list[str]:
    values = {str(record.get(column, "")).strip() for record in store.records}
    return sorted(value for value in values if value)


def print_rows(rows: list[dict[str, object]]) -> None:
    if not rows:
        print("No filament records found.")
        return

    headers = ["id", "brand", "type", "name", "color", "td", "source"]
    print(" | ".join(headers))
    print("-" * 96)
    for row in rows:
        print(
            " | ".join(
                [
                    str(row["id"]),
                    str(row["brand"]),
                    str(row["filament_type"]),
                    str(row["name"]),
                    str(row["color"]),
                    format_td(normalize_td(row["td"])),
                    str(row["source"]),
                ]
            )
        )


def show_row(row: Optional[dict[str, object]]) -> None:
    if row is None:
        print("Record not found.")
        return
    for key in FIELDNAMES:
        value = row.get(key)
        if key == "td":
            value = format_td(normalize_td(value))
        print(f"{key}: {value}")


def export_csv(store: FilamentStore, path: Path) -> int:
    rows = sorted(store.records, key=lambda row: (str(row["brand"]), str(row["filament_type"]), str(row["name"]), int(row["id"])))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "brand", "type", "name", "color", "td", "source", "notes", "created_at", "updated_at"])
        for row in rows:
            writer.writerow(
                [
                    row["id"],
                    row["brand"],
                    row["filament_type"],
                    row["name"],
                    row["color"],
                    normalize_td(row["td"]),
                    row["source"],
                    row["notes"],
                    row["created_at"],
                    row["updated_at"],
                ]
            )
    return len(rows)


def delete_row(store: FilamentStore, record_id: int) -> bool:
    before = len(store.records)
    store.records = [record for record in store.records if int(record["id"]) != record_id]
    if len(store.records) == before:
        return False
    store.save()
    return True


def delete_filaments(store: FilamentStore, record_ids: Iterable[int]) -> int:
    id_set = {int(record_id) for record_id in record_ids}
    before = len(store.records)
    store.records = [record for record in store.records if int(record["id"]) not in id_set]
    removed = before - len(store.records)
    if removed:
        store.save()
    return removed


def update_filament_color(store: FilamentStore, record_id: int, color: str) -> bool:
    for record in store.records:
        if int(record["id"]) == record_id:
            record["color"] = ensure_hex_color(color)
            record["updated_at"] = now_timestamp()
            store.save()
            return True
    return False


def update_filament(
    store: FilamentStore,
    *,
    record_id: int,
    brand: str,
    filament_type: str,
    name: str,
    notes: str,
) -> bool:
    for record in store.records:
        if int(record["id"]) == record_id:
            record["brand"] = brand.strip()
            record["filament_type"] = filament_type.strip()
            record["name"] = name.strip()
            record["notes"] = notes.strip()
            record["updated_at"] = now_timestamp()
            store.save()
            return True
    return False


def fetch_filament(store: FilamentStore, record_id: int) -> Optional[dict[str, object]]:
    for record in store.records:
        if int(record["id"]) == record_id:
            return dict(record)
    return None


def main() -> int:
    args = parse_args()
    db_path = Path(args.db).expanduser().resolve()
    store = connect(db_path)

    if args.command == "init":
        print(f"Initialized filament database at {db_path}")
        return 0

    if args.command == "seed-samples":
        inserted = seed_samples(store, replace=args.replace)
        print(f"Seeded {inserted} sample filaments into {db_path}")
        return 0

    if args.command == "add":
        record_id = add_filament(
            store,
            brand=args.brand,
            filament_type=args.type,
            name=args.name,
            color=args.color,
            td=args.td,
            source=args.source,
            notes=args.notes,
        )
        print(f"Added filament #{record_id} to {db_path}")
        return 0

    if args.command == "list":
        rows = list_filaments(store, limit=args.limit)
        rows.sort(key=lambda row: (str(row["brand"]), str(row["filament_type"]), str(row["name"]), int(row["id"])))
        print_rows(rows)
        return 0

    if args.command == "show":
        show_row(fetch_filament(store, args.id))
        return 0

    if args.command == "delete":
        deleted = delete_row(store, args.id)
        if deleted:
            print(f"Deleted filament #{args.id}")
            return 0
        print("Record not found.")
        return 1

    if args.command == "search":
        rows = list_filaments(store, limit=args.limit, query=args.query)
        rows.sort(key=lambda row: (str(row["brand"]), str(row["filament_type"]), str(row["name"]), int(row["id"])))
        print_rows(rows)
        return 0

    if args.command == "export-csv":
        path = Path(args.path).expanduser().resolve()
        row_count = export_csv(store, path)
        print(f"Exported {row_count} filaments to {path}")
        return 0

    if args.command == "scan":
        device_path = Path(args.device).expanduser().resolve() if args.device else detect_td1_device()
        if device_path is None:
            print("No TD1 serial device found under /dev/cu.usbmodem*", file=sys.stderr)
            return 1
        print(f"Listening for TD1 scan on {device_path}...")
        td, color = read_td1_scan(device_path, args.timeout)
        record_id = add_filament(
            store,
            brand=args.brand,
            filament_type=args.type,
            name=args.name,
            color=color,
            td=td,
            source=args.source,
            notes=args.notes,
        )
        print(f"Captured TD {td:.2f} and HEX {color}; added filament #{record_id} to {db_path}")
        return 0

    print(f"Unknown command: {args.command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
