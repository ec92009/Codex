#!/bin/zsh

set -euo pipefail

PROJECT_DIR="/Users/ecohen/Codex/imageTo3MF"
LOG_FILE="${TMPDIR:-/tmp}/leadlight_gui.log"

cd "$PROJECT_DIR"
exec /opt/homebrew/bin/uv run python image_grade_to_3mf_gui.py >>"$LOG_FILE" 2>&1
