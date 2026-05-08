#!/usr/bin/env bash
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$BIN_DIR/tmux-mas"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

need tmux
need python3

python3 - <<'PY'
try:
    import yaml
except Exception:
    raise SystemExit("Missing Python package: PyYAML. Install with: python3 -m pip install PyYAML")
PY

mkdir -p "$BIN_DIR"
ln -sf "$ROOT/tmux-mas" "$TARGET"
chmod +x "$ROOT/tmux-mas" "$ROOT/runtime/run_scenario.py"

echo "Installed: $TARGET"
echo "Try: tmux-mas list"
