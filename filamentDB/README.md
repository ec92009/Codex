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
- small desktop GUI
- optional starter sample rows
- direct TD1 capture from macOS serial output

## Usage

Initialize the local database:

```bash
cd /Users/ecohen/Codex/filamentDB
uv run python filament_db.py init
```

Launch the desktop GUI:

```bash
cd /Users/ecohen/Codex/filamentDB
uv run python filament_db_gui.py
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

Capture one filament directly from the connected TD1:

```bash
uv run python filament_db.py scan \
  --brand SUNLU \
  --type "PLA+ 2.0" \
  --name "Coffee"
```

If needed, you can point it at a specific serial device:

```bash
uv run python filament_db.py scan \
  --brand SUNLU \
  --type "PLA+ 2.0" \
  --name "Coffee" \
  --device /dev/cu.usbmodem21101
```

The GUI wraps the same workflow:

- choose or type `brand`
- choose or type `type`
- choose or type `name`
- press `Scan from TD1` while the filament is in the TD1
- the measured `TD` and `HEX` are saved directly to the local DB
- review the color swatch next to the saved `HEX`
- if the TD1 color is off, type a new HEX or double-click the swatch, then press `Save Color`
- each saved row shows a color sample swatch in the table
- double-click a row swatch to change that filament's color with the native macOS picker
- double-click any non-swatch cell in a row to load that filament into the left panel for editing
- use `Save Changes` to commit edits to brand, type, name, and notes
- select a row and press `Delete Selected` to remove it from the DB
- click a table header to sort by that column
- use the search field above the table to quickly filter filaments

## Sample data note

The seeded sample rows are deliberately small and conservative. They are just starter placeholders and are labeled with `source=sample`. Their `td` values are left blank until you measure them or import trustworthy data.

The current starter set includes:

- `SUNLU PLA Matte`: Black, White, Red, Blue, Green
- `SUNLU Transparent PLA`: Blue, Red, Green, Yellow, Clear, Purple

## Suggested next steps

- add TD1 direct ingestion once the device transport is confirmed
- add duplicate detection
- add a tiny GUI for browsing/editing filaments
- add importers for community or vendor datasets with provenance tracking
