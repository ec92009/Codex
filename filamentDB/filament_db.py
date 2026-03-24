#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path
from typing import Iterable, Optional


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = PROJECT_DIR / "data" / "filaments.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS filaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    filament_type TEXT NOT NULL,
    name TEXT NOT NULL,
    color TEXT NOT NULL,
    td REAL,
    source TEXT NOT NULL DEFAULT 'manual',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


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
        "brand": "Generic",
        "type": "Transparent PLA",
        "name": "Transparent Blue",
        "color": "#2D6CDF",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "Generic",
        "type": "Transparent PLA",
        "name": "Transparent Red",
        "color": "#D83A34",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "Generic",
        "type": "Transparent PLA",
        "name": "Transparent Green",
        "color": "#2FAF5A",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "Generic",
        "type": "Transparent PLA",
        "name": "Transparent Yellow",
        "color": "#F2DA3A",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "Generic",
        "type": "Transparent PLA",
        "name": "Transparent Clear",
        "color": "#F4F7F9",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
    {
        "brand": "Generic",
        "type": "Transparent PLA",
        "name": "Transparent Purple",
        "color": "#7A52CC",
        "td": None,
        "source": "sample",
        "notes": "Starter sample row. TD not measured yet.",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local SQLite filament database using HueForge-style brand/type/name/td/color fields."
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help=f"SQLite database path. Default: {DEFAULT_DB_PATH}",
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

    return parser.parse_args()


def ensure_hex_color(value: str) -> str:
    cleaned = value.strip().upper()
    if not cleaned.startswith("#"):
        cleaned = f"#{cleaned}"
    if len(cleaned) != 7 or any(char not in "0123456789ABCDEF#" for char in cleaned):
        raise ValueError(f"Invalid HEX color: {value}")
    return cleaned


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def migrate_schema(connection: sqlite3.Connection) -> None:
    table_exists = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='filaments'"
    ).fetchone()
    if not table_exists:
        connection.executescript(SCHEMA)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_filaments_brand ON filaments(brand)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_filaments_type ON filaments(filament_type)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_filaments_name ON filaments(name)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_filaments_color ON filaments(color)")
        connection.commit()
        return

    existing_columns = [row["name"] for row in connection.execute("PRAGMA table_info(filaments)")]
    target_columns = ["id", "brand", "filament_type", "name", "color", "td", "source", "notes", "created_at", "updated_at"]
    if existing_columns == target_columns:
        connection.execute("CREATE INDEX IF NOT EXISTS idx_filaments_brand ON filaments(brand)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_filaments_type ON filaments(filament_type)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_filaments_name ON filaments(name)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_filaments_color ON filaments(color)")
        connection.commit()
        return

    connection.execute("DROP TABLE IF EXISTS filaments_new")
    connection.execute(
        """
        CREATE TABLE filaments_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            filament_type TEXT NOT NULL,
            name TEXT NOT NULL,
            color TEXT NOT NULL,
            td REAL,
            source TEXT NOT NULL DEFAULT 'manual',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    if "material_type" in existing_columns:
        type_expr = '"material_type"'
    elif "type" in existing_columns:
        type_expr = '"type"'
    else:
        type_expr = "''"

    if "color_name" in existing_columns:
        name_expr = '"color_name"'
    elif "name" in existing_columns:
        name_expr = '"name"'
    else:
        name_expr = "''"

    if "hex_color" in existing_columns:
        color_expr = '"hex_color"'
    elif "color" in existing_columns:
        color_expr = '"color"'
    else:
        color_expr = "''"

    td_expr = '"td"' if "td" in existing_columns else "NULL"
    source_expr = '"source"' if "source" in existing_columns else "'manual'"
    notes_expr = '"notes"' if "notes" in existing_columns else "''"
    created_expr = '"created_at"' if "created_at" in existing_columns else "CURRENT_TIMESTAMP"
    updated_expr = '"updated_at"' if "updated_at" in existing_columns else "CURRENT_TIMESTAMP"

    connection.execute(
        f"""
        INSERT INTO filaments_new (
            id, brand, filament_type, name, color, td, source, notes, created_at, updated_at
        )
        SELECT
            id,
            brand,
            {type_expr},
            {name_expr},
            {color_expr},
            {td_expr},
            {source_expr},
            {notes_expr},
            {created_expr},
            {updated_expr}
        FROM filaments
        """
    )
    connection.execute("DROP TABLE filaments")
    connection.execute("ALTER TABLE filaments_new RENAME TO filaments")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_filaments_brand ON filaments(brand)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_filaments_type ON filaments(filament_type)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_filaments_name ON filaments(name)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_filaments_color ON filaments(color)")
    connection.commit()


def add_filament(
    connection: sqlite3.Connection,
    *,
    brand: str,
    filament_type: str,
    name: str,
    color: str,
    td: Optional[float],
    source: str,
    notes: str,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO filaments (
            brand, filament_type, name, color, td, source, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            brand.strip(),
            filament_type.strip(),
            name.strip(),
            ensure_hex_color(color),
            None if td is None else float(td),
            source.strip() or "manual",
            notes.strip(),
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def seed_samples(connection: sqlite3.Connection, replace: bool) -> int:
    if replace:
        connection.execute("DELETE FROM filaments")
        connection.commit()
    inserted = 0
    for item in SAMPLE_FILAMENTS:
        add_filament(
            connection,
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


def fetch_rows(connection: sqlite3.Connection, sql: str, params: Iterable[object] = ()) -> list[sqlite3.Row]:
    return list(connection.execute(sql, tuple(params)))


def format_td(value: Optional[float]) -> str:
    return "" if value is None else f"{float(value):.2f}"


def print_rows(rows: list[sqlite3.Row]) -> None:
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
                    row["brand"],
                    row["filament_type"],
                    row["name"],
                    row["color"],
                    format_td(row["td"]),
                    row["source"],
                ]
            )
        )


def show_row(row: Optional[sqlite3.Row]) -> None:
    if row is None:
        print("Record not found.")
        return
    for key in row.keys():
        value = row[key]
        if key == "td":
            value = format_td(value)
        print(f"{key}: {value}")


def export_csv(connection: sqlite3.Connection, path: Path) -> int:
    rows = fetch_rows(
        connection,
        """
        SELECT id, brand, type, name, color, td, source, notes, created_at, updated_at
        FROM filaments
        ORDER BY brand, type, name, id
        """,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "brand", "type", "name", "color", "td", "source", "notes", "created_at", "updated_at"])
        for row in rows:
            writer.writerow([row["id"], row["brand"], row["filament_type"], row["name"], row["color"], row["td"], row["source"], row["notes"], row["created_at"], row["updated_at"]])
    return len(rows)


def delete_row(connection: sqlite3.Connection, record_id: int) -> bool:
    cursor = connection.execute("DELETE FROM filaments WHERE id = ?", (record_id,))
    connection.commit()
    return cursor.rowcount > 0


def main() -> int:
    args = parse_args()
    db_path = Path(args.db).expanduser().resolve()
    connection = connect(db_path)
    migrate_schema(connection)

    if args.command == "init":
        print(f"Initialized filament database at {db_path}")
        return 0

    if args.command == "seed-samples":
        inserted = seed_samples(connection, replace=args.replace)
        print(f"Seeded {inserted} sample filaments into {db_path}")
        return 0

    if args.command == "add":
        record_id = add_filament(
            connection,
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
        rows = fetch_rows(
            connection,
            """
            SELECT id, brand, filament_type, name, color, td, source
            FROM filaments
            ORDER BY brand, filament_type, name, id
            LIMIT ?
            """,
            (args.limit,),
        )
        print_rows(rows)
        return 0

    if args.command == "show":
        row = connection.execute("SELECT * FROM filaments WHERE id = ?", (args.id,)).fetchone()
        show_row(row)
        return 0

    if args.command == "delete":
        deleted = delete_row(connection, args.id)
        if deleted:
            print(f"Deleted filament #{args.id}")
            return 0
        print("Record not found.")
        return 1

    if args.command == "search":
        like = f"%{args.query.strip()}%"
        rows = fetch_rows(
            connection,
            """
            SELECT id, brand, filament_type, name, color, td, source
            FROM filaments
            WHERE brand LIKE ?
               OR filament_type LIKE ?
               OR name LIKE ?
               OR color LIKE ?
               OR source LIKE ?
               OR notes LIKE ?
            ORDER BY brand, filament_type, name, id
            LIMIT ?
            """,
            (like, like, like, like, like, like, args.limit),
        )
        print_rows(rows)
        return 0

    if args.command == "export-csv":
        path = Path(args.path).expanduser().resolve()
        row_count = export_csv(connection, path)
        print(f"Exported {row_count} filaments to {path}")
        return 0

    print(f"Unknown command: {args.command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
