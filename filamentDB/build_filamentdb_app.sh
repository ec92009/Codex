#!/bin/zsh

set -euo pipefail

cd "/Users/ecohen/Codex/filamentDB"
UV_BIN="${UV_BIN:-$(command -v uv || true)}"
if [[ -z "$UV_BIN" ]]; then
  echo "uv was not found on PATH." >&2
  exit 1
fi
exec "$UV_BIN" run python build_macos_app.py
