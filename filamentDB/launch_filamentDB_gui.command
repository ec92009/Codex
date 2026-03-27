#!/bin/zsh

SCRIPT_DIR="${0:A:h}"

cd "$SCRIPT_DIR" || exit 1
exec /opt/homebrew/bin/uv run python filament_db_gui.py
