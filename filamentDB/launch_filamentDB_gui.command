#!/bin/zsh

cd /Users/ecohen/Codex/filamentDB || exit 1
exec /opt/homebrew/bin/uv run python filament_db_gui.py
