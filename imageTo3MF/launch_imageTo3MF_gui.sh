#!/bin/zsh

set -euo pipefail

PROJECT_DIR="${0:A:h}"

cd "$PROJECT_DIR"
exec uv run --project "$PROJECT_DIR" python "$PROJECT_DIR/image_grade_to_3mf_gui.py"
