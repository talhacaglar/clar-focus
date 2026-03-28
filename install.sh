#!/bin/bash

# Install a focus mode that blocks distracting websites (X, YouTube, Reddit)
# via /etc/hosts, with a waybar indicator showing when focus mode is active.
#
# Usage after install:
#   focus       - Block sites
#   focus off   - Unblock sites

set -e

WAYBAR_CONFIG="$HOME/.config/waybar/config.jsonc"
WAYBAR_STYLE="$HOME/.config/waybar/style.css"
INDICATOR_DIR="$HOME/.local/bin"
INDICATOR_SCRIPT="$INDICATOR_DIR/focus-indicator"
FOCUS_SCRIPT="$INDICATOR_DIR/focus"

echo "[focus] Setting up focus mode..."

# 1. Create ~/.local/bin if needed
mkdir -p "$INDICATOR_DIR"

# 2. Install focus script
cat > "$FOCUS_SCRIPT" <<'SCRIPT'
#!/bin/bash

BLOCKED_SITES=(
  "twitter.com"
  "www.twitter.com"
  "x.com"
  "www.x.com"
  "youtube.com"
  "www.youtube.com"
  "reddit.com"
  "www.reddit.com"
  "old.reddit.com"
)

MARKER="# focus-block"

case "${1:-on}" in
  on)
    for site in "${BLOCKED_SITES[@]}"; do
      echo "127.0.0.1 $site $MARKER" | sudo tee -a /etc/hosts > /dev/null
    done
    pkill -RTMIN+11 waybar 2>/dev/null || true
    echo "Blocked: X, YouTube, Reddit"
    ;;
  off)
    sudo sed -i "/$MARKER/d" /etc/hosts
    pkill -RTMIN+11 waybar 2>/dev/null || true
    echo "Unblocked all sites"
    ;;
  *)
    echo "Usage: focus [on|off]"
    ;;
esac
SCRIPT
chmod +x "$FOCUS_SCRIPT"
echo "  -> Installed focus script"

# 3. Install waybar indicator script
cat > "$INDICATOR_SCRIPT" <<'INDICATOR'
#!/bin/bash

if grep -q '# focus-block' /etc/hosts 2>/dev/null; then
  echo '{"text": "󰅶", "tooltip": "Focus mode active", "class": "active"}'
else
  echo '{"text": ""}'
fi
INDICATOR
chmod +x "$INDICATOR_SCRIPT"
echo "  -> Installed focus indicator"

# 4. Add waybar module
if [[ -f "$WAYBAR_CONFIG" ]]; then
  if grep -q 'custom/focus-indicator' "$WAYBAR_CONFIG"; then
    echo "  -> Waybar already has focus module, skipping."
  else
    # Add to modules-center (after notification-silencing-indicator, only in the array line)
    sed -i'' -e '/modules-center/s/"custom\/notification-silencing-indicator"/"custom\/notification-silencing-indicator", "custom\/focus-indicator"/' "$WAYBAR_CONFIG"

    # Add the module config (before the tray definition)
    sed -i'' -e '/"tray": {/i\
  "custom/focus-indicator": {\
    "exec": "~/.local/bin/focus-indicator",\
    "return-type": "json",\
    "signal": 11,\
    "on-click": "focus off"\
  },' "$WAYBAR_CONFIG"

    echo "  -> Added focus indicator module to waybar"
  fi
fi

# 5. Add waybar styling
if [[ -f "$WAYBAR_STYLE" ]]; then
  if grep -q '#custom-focus-indicator' "$WAYBAR_STYLE"; then
    echo "  -> Waybar style already has focus rule, skipping."
  else
    cat >> "$WAYBAR_STYLE" <<'CSSEOF'

#custom-focus-indicator {
  min-width: 12px;
  margin-left: 5px;
  margin-right: 0;
  font-size: 10px;
  padding-bottom: 1px;
}

#custom-focus-indicator.active {
  color: #a55555;
}
CSSEOF
    echo "  -> Added focus indicator styling"
  fi
fi

# 6. Restart waybar
omarchy-restart-waybar 2>/dev/null || true

echo "[focus] Done."
echo ""
echo "  focus        Block X, YouTube, Reddit"
echo "  focus off    Unblock all sites"
echo "  Waybar icon turns red when focus mode is active"
