#!/bin/zsh

set -euo pipefail

PROJECT_DIR="${0:A:h}"
LOG_FILE="${TMPDIR:-/tmp}/leadlight_gui.log"

cd "$PROJECT_DIR"
nohup /opt/homebrew/bin/uv run python image_grade_to_3mf_gui.py >>"$LOG_FILE" 2>&1 &
disown || true
exit 0
