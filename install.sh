#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/clar-focus"
VENV_DIR="$APP_DIR/venv"
WAYBAR_CONFIG="$HOME/.config/waybar/config.jsonc"
WAYBAR_STYLE="$HOME/.config/waybar/style.css"
WAYBAR_WRAPPER="$BIN_DIR/clar-focus-waybar"

echo "[clar-focus] Bootstrapping premium productivity suite..."
mkdir -p "$BIN_DIR" "$APP_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  python -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -e "$PROJECT_DIR"

for cmd in clar-focus clar-focus-hosts-helper omarchy-focus focus focus-indicator omarchy-focus-hosts-helper; do
  ln -sf "$VENV_DIR/bin/$cmd" "$BIN_DIR/$cmd"
done

install -m 755 "$PROJECT_DIR/examples/waybar/clar-focus-waybar.sh" "$WAYBAR_WRAPPER"
ln -sf "$WAYBAR_WRAPPER" "$BIN_DIR/omarchy-focus-waybar"

if [[ -f "$WAYBAR_CONFIG" ]] && ! grep -q '"custom/clar-focus"' "$WAYBAR_CONFIG"; then
  python - "$WAYBAR_CONFIG" <<'PY'
from pathlib import Path
import sys

config = Path(sys.argv[1])
text = config.read_text(encoding="utf-8")
module = '''
  "custom/clar-focus": {
    "exec": "~/.local/bin/clar-focus-waybar status",
    "return-type": "json",
    "interval": 1,
    "signal": 12,
    "on-click": "~/.local/bin/clar-focus-waybar open",
    "on-click-right": "~/.local/bin/clar-focus-waybar toggle-pomodoro",
    "on-click-middle": "~/.local/bin/clar-focus-waybar toggle-focus",
    "tooltip": true
  },
'''
if '"tray": {' in text:
    text = text.replace('  "tray": {', module + '  "tray": {', 1)
if '"modules-right": [' in text and '"custom/clar-focus"' not in text:
    text = text.replace('"modules-right": [', '"modules-right": [\n    "custom/clar-focus",', 1)
config.write_text(text, encoding="utf-8")
PY
  echo "  -> Added Waybar module snippet"
fi

if [[ -f "$WAYBAR_STYLE" ]] && ! grep -q '#custom-clar-focus' "$WAYBAR_STYLE"; then
  {
    printf '\n'
    cat "$PROJECT_DIR/examples/waybar/style.css"
  } >> "$WAYBAR_STYLE"
  echo "  -> Added Waybar styles"
fi

echo ""
echo "[clar-focus] Installed."
echo "  Command: clar-focus"
echo "  Compatibility alias: omarchy-focus"
echo "  Legacy focus aliases: focus / focus-indicator"
echo "  Waybar helper: $WAYBAR_WRAPPER"
echo ""
echo "Optional:"
echo "  systemctl --user enable --now $PROJECT_DIR/examples/systemd/clar-focus-recover.service"
echo ""
echo "Restart Waybar to load the module."
