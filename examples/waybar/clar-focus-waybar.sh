#!/usr/bin/env bash

set -euo pipefail

case "${1:-status}" in
  status)
    exec clar-focus waybar
    ;;
  open)
    if clar-focus raise >/dev/null 2>&1; then
      exit 0
    fi
    exec omarchy-launch-or-focus-tui clar-focus tui
    ;;
  toggle-pomodoro)
    exec clar-focus toggle
    ;;
  toggle-focus)
    if clar-focus focus status | grep -q "Focus ON"; then
      if sudo -n true 2>/dev/null; then
        exec clar-focus focus off
      fi
      if command -v omarchy-launch-floating-terminal-with-presentation >/dev/null 2>&1; then
        exec omarchy-launch-floating-terminal-with-presentation "clar-focus focus off; printf '\n'; read -r -p 'Enter ile kapat...' _"
      fi
      exec xdg-terminal-exec -e bash -lc "clar-focus focus off; printf '\n'; read -r -p 'Enter ile kapat...' _"
    else
      if sudo -n true 2>/dev/null; then
        exec clar-focus focus on --minutes 50
      fi
      if command -v omarchy-launch-floating-terminal-with-presentation >/dev/null 2>&1; then
        exec omarchy-launch-floating-terminal-with-presentation "clar-focus focus on --minutes 50; printf '\n'; read -r -p 'Enter ile kapat...' _"
      fi
      exec xdg-terminal-exec -e bash -lc "clar-focus focus on --minutes 50; printf '\n'; read -r -p 'Enter ile kapat...' _"
    fi
    ;;
  *)
    echo "Usage: $0 {status|open|toggle-pomodoro|toggle-focus}" >&2
    exit 1
    ;;
esac
