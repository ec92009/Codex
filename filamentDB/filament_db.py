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
    material_type TEXT NOT NULL,
    color_name TEXT NOT NULL,
    hex_color TEXT NOT NULL,
    td REAL NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_filaments_brand ON filaments(brand);
CREATE INDEX IF NOT EXISTS idx_filaments_material_type ON filaments(material_type);
CREATE INDEX IF NOT EXISTS idx_filaments_color_name ON filaments(color_name);
CREATE INDEX IF NOT EXISTS idx_filaments_hex_color ON filaments(hex_color);
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local SQLite filament database for TD1 and manual filament records."
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help=f"SQLite database path. Default: {DEFAULT_DB_PATH}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Initialize the local filament database.")

    add_parser = subparsers.add_parser("add", help="Add a filament record.")
    add_parser.add_argument("--brand", required=True, help="Filament brand.")
    add_parser.add_argument("--type", dest="material_type", required=True, help="Material type, for example PLA.")
    add_parser.add_argument("--color", dest="color_name", required=True, help="Human-readable color name.")
    add_parser.add_argument("--hex", dest="hex_color", required=True, help="HEX color like #AABBCC.")
    add_parser.add_argument("--td", type=float, required=True, help="Transmission Distance value.")
    add_parser.add_argument("--source", default="manual", help="Source of the record, for example td1 or vendor.")
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


def init_db(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    connection.commit()


def add_filament(
    connection: sqlite3.Connection,
    *,
    brand: str,
    material_type: str,
    color_name: str,
    hex_color: str,
    td: float,
    source: str,
    notes: str,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO filaments (
            brand, material_type, color_name, hex_color, td, source, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            brand.strip(),
            material_type.strip(),
            color_name.strip(),
            ensure_hex_color(hex_color),
            float(td),
            source.strip() or "manual",
            notes.strip(),
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def fetch_rows(connection: sqlite3.Connection, sql: str, params: Iterable[object] = ()) -> list[sqlite3.Row]:
    return list(connection.execute(sql, tuple(params)))


def print_rows(rows: list[sqlite3.Row]) -> None:
    if not rows:
        print("No filament records found.")
        return

    headers = ["id", "brand", "type", "color", "hex", "td", "source"]
    print(" | ".join(headers))
    print("-" * 78)
    for row in rows:
        print(
            " | ".join(
                [
                    str(row["id"]),
                    row["brand"],
                    row["material_type"],
                    row["color_name"],
                    row["hex_color"],
                    f"{row['td']:.2f}",
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
            value = f"{float(value):.2f}"
        print(f"{key}: {value}")


def export_csv(connection: sqlite3.Connection, path: Path) -> int:
    rows = fetch_rows(
        connection,
        """
        SELECT id, brand, material_type, color_name, hex_color, td, source, notes, created_at, updated_at
        FROM filaments
        ORDER BY brand, material_type, color_name, id
        """,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "brand", "material_type", "color_name", "hex_color", "td", "source", "notes", "created_at", "updated_at"])
        for row in rows:
            writer.writerow([row["id"], row["brand"], row["material_type"], row["color_name"], row["hex_color"], row["td"], row["source"], row["notes"], row["created_at"], row["updated_at"]])
    return len(rows)


def delete_row(connection: sqlite3.Connection, record_id: int) -> bool:
    cursor = connection.execute("DELETE FROM filaments WHERE id = ?", (record_id,))
    connection.commit()
    return cursor.rowcount > 0


def main() -> int:
    args = parse_args()
    db_path = Path(args.db).expanduser().resolve()
    connection = connect(db_path)
    init_db(connection)

    if args.command == "init":
        print(f"Initialized filament database at {db_path}")
        return 0

    if args.command == "add":
        record_id = add_filament(
            connection,
            brand=args.brand,
            material_type=args.material_type,
            color_name=args.color_name,
            hex_color=args.hex_color,
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
            SELECT id, brand, material_type, color_name, hex_color, td, source
            FROM filaments
            ORDER BY brand, material_type, color_name, id
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
            SELECT id, brand, material_type, color_name, hex_color, td, source
            FROM filaments
            WHERE brand LIKE ?
               OR material_type LIKE ?
               OR color_name LIKE ?
               OR hex_color LIKE ?
               OR source LIKE ?
               OR notes LIKE ?
            ORDER BY brand, material_type, color_name, id
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
