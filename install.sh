#!/usr/bin/env bash
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$BIN_DIR/tmux-mas"
VERSION="$(cat "$ROOT/VERSION" 2>/dev/null || printf '0.0.0-dev')"

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
chmod +x "$ROOT/runtime/doctor.py"
chmod +x "$ROOT/runtime/watch_session.py"

echo "Installed tmux-mas $VERSION: $TARGET"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    echo "Warning: $BIN_DIR is not on PATH." >&2
    echo "Add this to your shell profile:" >&2
    echo "  export PATH=\"$BIN_DIR:\$PATH\"" >&2
    ;;
esac

"$TARGET" --version >/dev/null
"$TARGET" list >/dev/null
"$TARGET" doctor >/dev/null

echo "Try: tmux-mas --help"
