#!/bin/zsh

set -euo pipefail

PROJECT_DIR="${0:A:h}"
LOG_FILE="${TMPDIR:-/tmp}/imageTo3MF_gui.log"

cd "$PROJECT_DIR"
nohup uv run --project "$PROJECT_DIR" python "$PROJECT_DIR/image_grade_to_3mf_gui.py" >>"$LOG_FILE" 2>&1 &
disown
exit 0
