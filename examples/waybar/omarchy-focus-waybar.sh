#!/usr/bin/env bash

set -euo pipefail

case "${1:-status}" in
  status)
    exec omarchy-focus waybar
    ;;
  open)
    if omarchy-focus raise >/dev/null 2>&1; then
      exit 0
    fi
    exec omarchy-launch-or-focus-tui omarchy-focus tui
    ;;
  toggle-pomodoro)
    exec omarchy-focus toggle
    ;;
  toggle-focus)
    if omarchy-focus focus status | grep -q "Focus ON"; then
      if sudo -n true 2>/dev/null; then
        exec omarchy-focus focus off
      fi
      if command -v omarchy-launch-floating-terminal-with-presentation >/dev/null 2>&1; then
        exec omarchy-launch-floating-terminal-with-presentation "omarchy-focus focus off; printf '\n'; read -r -p 'Enter ile kapat...' _"
      fi
      exec xdg-terminal-exec -e bash -lc "omarchy-focus focus off; printf '\n'; read -r -p 'Enter ile kapat...' _"
    else
      if sudo -n true 2>/dev/null; then
        exec omarchy-focus focus on --minutes 50
      fi
      if command -v omarchy-launch-floating-terminal-with-presentation >/dev/null 2>&1; then
        exec omarchy-launch-floating-terminal-with-presentation "omarchy-focus focus on --minutes 50; printf '\n'; read -r -p 'Enter ile kapat...' _"
      fi
      exec xdg-terminal-exec -e bash -lc "omarchy-focus focus on --minutes 50; printf '\n'; read -r -p 'Enter ile kapat...' _"
    fi
    ;;
  *)
    echo "Usage: $0 {status|open|toggle-pomodoro|toggle-focus}" >&2
    exit 1
    ;;
esac
