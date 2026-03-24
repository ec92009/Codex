# filamentDB

Small local SQLite database for filament records, aligned to the simple HueForge-style naming:

- `brand`
- `type`
- `name`
- `color`
- `td`

Optional support fields:

- `source`
- `notes`

The initial goal is to keep a clean local library of your own filaments and measured TD1 readings.

Internally, the SQLite column for `type` is named `filament_type` to avoid SQL keyword awkwardness, but the CLI and exported shape are presented as `type`.

## Current scope

- local SQLite database
- simple CLI
- optional starter sample rows
- ready for future TD1 direct-ingest work

The TD1 can clearly send readings to a computer for HueForge workflows, but the Mac-side protocol for direct standalone capture is not wired into this project yet. This project leaves room for that next step once we confirm how the device exposes readings outside HueForge.

## Usage

Initialize the local database:

```bash
cd /Users/ecohen/Codex/filamentDB
uv run python filament_db.py init
```

Seed a small starter sample set:

```bash
uv run python filament_db.py seed-samples --replace
```

Add a filament manually:

```bash
uv run python filament_db.py add \
  --brand SUNLU \
  --type "PLA Matte" \
  --name "Matte Red" \
  --color "#C62828" \
  --td 5.6 \
  --source td1 \
  --notes "Measured on BIQU TD1"
```

List all filaments:

```bash
uv run python filament_db.py list
```

Search by free text:

```bash
uv run python filament_db.py search matte
```

Show one record:

```bash
uv run python filament_db.py show 1
```

Delete one record:

```bash
uv run python filament_db.py delete 1
```

Export to CSV:

```bash
uv run python filament_db.py export-csv out/filaments.csv
```

## Sample data note

The seeded sample rows are deliberately small and conservative. They are just starter placeholders and are labeled with `source=sample`. Their `td` values are left blank until you measure them or import trustworthy data.

## Suggested next steps

- add TD1 direct ingestion once the device transport is confirmed
- add duplicate detection
- add a tiny GUI for browsing/editing filaments
- add importers for community or vendor datasets with provenance tracking
