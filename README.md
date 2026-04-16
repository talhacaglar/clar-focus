# Clar Focus

Premium terminal-first productivity suite for **Arch Linux + Wayland + Hyprland + Waybar**.

It combines:

- a modern **Textual TUI**
- a real **SQLite-backed task manager**
- a configurable **pomodoro engine**
- a real **hosts-file based focus blocker**
- a compact **Waybar module**

The project is designed to feel like a polished productivity tool, not a shell-script toy.

## Architecture Plan

1. **Core persistence layer**
   SQLite stores tasks, settings, pomodoro history, focus sessions, blocked sites, and runtime state.
2. **Service layer**
   Dedicated Python services handle tasks, pomodoro logic, stats, notifications, and focus-mode orchestration.
3. **Focus enforcement**
   A separate helper safely edits `/etc/hosts` with explicit markers for recovery and cleanup.
4. **CLI + Waybar**
   CLI commands drive automation, while Waybar consumes a compact JSON status command.
5. **Premium TUI**
   Textual renders a multi-view dashboard with keyboard-first navigation and modal editors.

## Project Structure

```text
clar-focus/
├── examples/
│   ├── systemd/
│   │   └── clar-focus-recover.service
│   └── waybar/
│       ├── module.jsonc
│       ├── clar-focus-waybar.sh
│       └── style.css
├── src/
│   └── omarchy_focus/
│       ├── __init__.py
│       ├── __main__.py
│       ├── bootstrap.py
│       ├── cli.py
│       ├── database.py
│       ├── exceptions.py
│       ├── focus_hosts_helper.py
│       ├── legacy.py
│       ├── models.py
│       ├── notifications.py
│       ├── paths.py
│       ├── settings.py
│       ├── utils.py
│       ├── waybar.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── focus.py
│       │   ├── pomodoro.py
│       │   ├── stats.py
│       │   └── tasks.py
│       └── tui/
│           ├── __init__.py
│           ├── app.py
│           ├── app.tcss
│           └── dialogs.py
├── tests/
│   ├── test_focus_hosts_helper.py
│   └── test_services.py
├── install.sh
└── pyproject.toml
```

## Features

### Task Management

- add, edit, delete, complete, archive tasks
- priorities: `low`, `medium`, `high`
- tags, notes, estimated duration, due date
- task states: `pending`, `in_progress`, `done`, `archived`
- today view, completed view, filtering, sorting, searching
- pomodoro sessions can be linked to a task

### Pomodoro Engine

- default cycle tuned for deep work: `50 / 10 / 25`
- configurable work, short break, long break durations
- long break after N work sessions
- start / stop / pause / resume
- work and break history in SQLite
- daily and weekly stats

### Focus Mode

- real hosts-file blocking via `/etc/hosts`
- safe markers:
  - `# >>> OMARCHY_FOCUS START`
  - `# <<< OMARCHY_FOCUS END`
- strict mode support
- timed sessions with auto-release support
- recovery on next launch if the app crashed but markers remain
- blocked site list stored in SQLite and editable from CLI/TUI

### Waybar Integration

- JSON status output for `custom/*` modules
- left click opens TUI
- right click toggles pomodoro
- middle click toggles focus mode
- signal-based refresh via `RTMIN+12`

## Install

### Quick install

```bash
cd /path/to/clar-focus
./install.sh
```

The installer:

- creates a local venv under `~/.local/share/clar-focus/venv`
- installs the package into that venv
- symlinks commands into `~/.local/bin`
- installs the Waybar wrapper script
- optionally injects a Waybar module and style snippet if your config exists

### Manual install

```bash
cd /path/to/clar-focus
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Dependencies

Runtime:

- Python 3.12+
- `textual`
- `notify-send` for desktop notifications
- `sudo` for focus-mode `/etc/hosts` changes

Optional integration:

- Waybar
- Hyprland / Omarchy terminal launch helpers

## CLI Usage

### Launch TUI

```bash
clar-focus
clar-focus tui
```

### Tasks

```bash
clar-focus add-task "Write quarterly report" --priority high --tags "work report" --estimate 90 --due "2026-04-19 15:00"
clar-focus tasks list
clar-focus tasks edit 3 --status in_progress
clar-focus tasks done 3
clar-focus tasks delete 3
```

### Pomodoro

```bash
clar-focus start --task-id 7
clar-focus start --minutes 50 --focus
clar-focus pause
clar-focus resume
clar-focus stop
clar-focus toggle
```

### Focus Mode

```bash
clar-focus focus on --minutes 50
clar-focus focus on --minutes 50 --strict
clar-focus focus off
clar-focus focus off --force
clar-focus focus status --json
clar-focus focus add-site reddit.com
clar-focus focus remove-site instagram.com
clar-focus focus recover
```

### Status / Waybar

```bash
clar-focus status
clar-focus status --json
clar-focus waybar
clar-focus waybar --plain
clar-focus stats
clar-focus settings show
clar-focus settings set pomodoro_work_minutes 50
```

## TUI Layout

Views:

- `Dashboard`
- `Tasks`
- `Focus Session`
- `Statistics`
- `Settings`
- `Help`

Layout direction:

- top status rail with premium cards
- dashboard with agenda, task detail, pomodoro, focus, and analytics panels
- tasks view with searchable task table and detail sidebar
- focus view with active session state and blocked-sites table
- statistics view with mini sparkline/progress bars
- settings view with editable settings table

## Keyboard Shortcuts

- `q`: quit
- `a`: add task
- `e`: edit selected task or selected setting
- `d`: delete selected task
- `x`: complete selected task
- `/`: search
- `f`: filter
- `s`: start/stop pomodoro
- `p`: pause/resume
- `m`: focus mode on/off
- `b`: blocked sites manager
- `t`: tasks
- `g`: dashboard
- `i`: statistics
- `,`: settings
- `?`: help

## Waybar Example

Module snippet:

```jsonc
{
  "custom/clar-focus": {
    "exec": "~/.local/bin/clar-focus-waybar status",
    "return-type": "json",
    "interval": 1,
    "signal": 12,
    "on-click": "~/.local/bin/clar-focus-waybar open",
    "on-click-right": "~/.local/bin/clar-focus-waybar toggle-pomodoro",
    "on-click-middle": "~/.local/bin/clar-focus-waybar toggle-focus",
    "tooltip": true
  }
}
```

Starter style:

```css
#custom-clar-focus {
  min-width: 164px;
  padding: 1px 12px;
  margin: 2px 3px;
  border-radius: 13px;
}
```

Reference files:

- `examples/waybar/module.jsonc`
- `examples/waybar/style.css`
- `examples/waybar/clar-focus-waybar.sh`

## Focus Mode Technical Notes

### Chosen approach

Primary enforcement uses **`/etc/hosts` temporary blocks**.

Why:

- predictable on Arch Linux
- easy to audit
- reversible
- does not require a long-running daemon
- integrates cleanly with CLI + Waybar workflows

### Safety model

The helper:

- never rewrites arbitrary lines blindly
- removes only its own managed block
- writes atomically via a temp file + rename
- stores metadata inside the managed block
- supports recovery when markers remain after a crash

Managed block format:

```text
# >>> OMARCHY_FOCUS START
# OMARCHY_FOCUS_META {"owner": "...", "session_id": "...", "started_at": "...", "strict": true}
127.0.0.1 reddit.com
127.0.0.1 www.reddit.com
# <<< OMARCHY_FOCUS END
```

### Recovery flow

On startup:

1. the app checks SQLite runtime state
2. the app inspects `/etc/hosts`
3. if markers exist but SQLite state is missing, the focus session is reconstructed as recovered
4. if SQLite says active but hosts markers are gone, the session is closed cleanly

### Strict mode

- strict mode is only allowed for timed sessions
- if the timer is still running, `focus off` is rejected
- `focus off --force` exists for explicit override paths like administrative recovery

### Root handling

The main app does not edit `/etc/hosts` directly.

It shells out to:

```bash
clar-focus-hosts-helper apply ...
clar-focus-hosts-helper clear
clar-focus-hosts-helper status
```

When needed, the app invokes that helper with `sudo`.

## Testing

Run the included unit tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Example Terminal Experience

The intended feel is:

- dark polished control room
- gold accents for focus/work state
- muted blue-steel surfaces
- clear tables and sidebar details
- keyboard-driven flow with low friction

The result should feel closer to a premium workstation console than a simple todo script.
