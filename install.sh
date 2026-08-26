#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/clar-focus"
VENV_DIR="$APP_DIR/venv"
OMARCHY_SHELL_CONFIG="$HOME/.config/omarchy/shell.json"
BAR_WRAPPER="$BIN_DIR/clar-focus-bar"
BAR_MODULE="$PROJECT_DIR/examples/omarchy-shell/module.json"

echo "[clar-focus] Installing productivity suite..."
mkdir -p "$BIN_DIR" "$APP_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  python -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -e "$PROJECT_DIR"

for cmd in clar-focus clar-focus-hosts-helper omarchy-focus focus focus-indicator omarchy-focus-hosts-helper; do
  ln -sf "$VENV_DIR/bin/$cmd" "$BIN_DIR/$cmd"
done

install -m 755 "$PROJECT_DIR/examples/omarchy-shell/clar-focus-bar.sh" "$BAR_WRAPPER"

# Keep old command names working without making Waybar the primary integration.
ln -sf "$BAR_WRAPPER" "$BIN_DIR/clar-focus-waybar"
ln -sf "$BAR_WRAPPER" "$BIN_DIR/omarchy-focus-waybar"

bar_result="skipped"
if [[ -f "$OMARCHY_SHELL_CONFIG" ]]; then
  backup_path="$OMARCHY_SHELL_CONFIG.bak.clar-focus-$(date +%Y%m%d-%H%M%S)"
  cp -- "$OMARCHY_SHELL_CONFIG" "$backup_path"
  bar_result="$("$VENV_DIR/bin/python" "$PROJECT_DIR/scripts/install_omarchy_bar.py" \
    "$OMARCHY_SHELL_CONFIG" "$BAR_MODULE")"
  if [[ "$bar_result" == "unchanged" ]]; then
    rm -- "$backup_path"
  else
    echo "  -> Omarchy bar widget updated"
    echo "  -> Backup: $backup_path"
  fi
else
  echo "  -> Omarchy Shell config not found; bar widget skipped"
fi

echo ""
echo "[clar-focus] Installed."
echo "  Command: clar-focus"
echo "  Omarchy bar helper: $BAR_WRAPPER"
echo "  Bar controls: left=open, right=timer, middle=focus guard"
echo "  Compatibility aliases: omarchy-focus / focus / focus-indicator"
echo ""
echo "Optional recovery service:"
echo "  systemctl --user enable --now $PROJECT_DIR/examples/systemd/clar-focus-recover.service"

if [[ "$bar_result" == "skipped" ]]; then
  echo ""
  echo "Add examples/omarchy-shell/module.json to your Omarchy bar layout when available."
else
  echo ""
  echo "Omarchy Shell reloads the bar configuration automatically."
fi
