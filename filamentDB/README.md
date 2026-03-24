# filamentDB

Small local SQLite database for filament records, designed to work well with BIQU TD1 measurements.

For now the project stores a simple record shape:

- `brand`
- `material_type`
- `color_name`
- `hex_color`
- `td`
- `source`
- `notes`

The initial goal is to make it easy to:

- add filaments manually
- list/search them locally
- keep a clean canonical library of your own measured materials

The TD1 can clearly send readings to a computer for HueForge workflows, but the Mac-side protocol for direct programmatic capture is not wired into this project yet. This project leaves room for that next step once we confirm how the device exposes readings outside HueForge.

## Usage

Initialize the local database:

```bash
cd /Users/ecohen/Codex/filamentDB
uv run python filament_db.py init
```

Add a filament manually:

```bash
uv run python filament_db.py add \
  --brand Bambu \
  --type PLA \
  --color "Jade Green" \
  --hex "#2FAF5A" \
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
uv run python filament_db.py search green
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

## Suggested next steps

- add TD1 direct ingestion once the device transport is confirmed
- add duplicate detection
- add brand/type/color normalization helpers
- add importers for community or vendor filament datasets
