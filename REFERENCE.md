# Clar Focus

Terminal-first productivity suite for **Arch Linux + Hyprland + Omarchy Shell**.

It combines:

- a modern **Textual TUI**
- a real **SQLite-backed task manager**
- a configurable **pomodoro engine**
- a real **hosts-file based focus blocker**
- a native **Omarchy bar command widget**

The project is designed to feel like a polished productivity tool, not a shell-script toy.

## Architecture Plan

1. **Core persistence layer**
   SQLite stores tasks, settings, pomodoro history, focus sessions, blocked sites, and runtime state.
2. **Service layer**
   Dedicated Python services handle tasks, pomodoro logic, stats, notifications, and focus-mode orchestration.
3. **Focus enforcement**
   A separate helper safely edits `/etc/hosts` with explicit markers for recovery and cleanup.
4. **CLI + Omarchy bar**
   CLI commands drive automation, while Omarchy Shell consumes a compact JSON status command.
5. **Premium TUI**
   Textual renders a multi-view dashboard with keyboard-first navigation and modal editors.

## Project Structure

```text
clar-focus/
├── examples/
│   ├── systemd/
│   │   └── clar-focus-recover.service
│   ├── omarchy-shell/
│   │   ├── module.json
│   │   └── clar-focus-bar.sh
│   └── waybar/                  # legacy compatibility examples
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
│       ├── bar.py
│       ├── waybar.py            # legacy Python aliases
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

### Omarchy Bar Integration

- native Omarchy Shell `command` widget
- left click opens TUI
- right click toggles pomodoro
- middle click toggles focus mode
- automatic two-second status refresh

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
- installs the Omarchy bar helper
- updates the native Omarchy Shell bar widget if your config exists

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

Desktop integration:

- Omarchy Shell bar
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

### Status / Omarchy Bar

```bash
clar-focus status
clar-focus status --json
clar-focus bar
clar-focus bar --plain
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

- compact live rail for timer, focus guard, and queue state
- action-first `Now` view with the next task, one-click session controls, queue, and daily rhythm
- tasks view with debounced live search, stable selection, empty-state guidance, and a detail sidebar
- focus view with active session state and blocked-sites table
- statistics view with mini sparkline/progress bars
- settings view with human-readable labels, quick boolean toggles, and validated values
- **light/dark theme** — signature "midnight-gold" (dark) and "daylight-gold"
  (light) themes, toggled with `F2`. The choice is persisted in the settings
  table (`theme_variant`) and restored on the next launch.
- responsive compact mode for narrower terminal windows
- split refresh loop: countdowns update every second without rebuilding tables or stealing input focus

## Keyboard Shortcuts

- `q`: quit
- `a`: add task
- `e`: edit selected task or selected setting
- `d`: delete selected task
- `x`: complete selected task
- `/`: open the task view and focus live search
- `f`: filter
- `s`: start/stop pomodoro
- `p`: pause/resume
- `m`: focus mode on/off
- `b`: blocked sites manager
- `t`: tasks
- `g`: dashboard
- `i`: statistics
- `,`: settings
- `F2`: toggle light/dark theme
- `?`: help

## Omarchy Bar

`./install.sh` updates `~/.config/omarchy/shell.json` without replacing the rest
of your layout. It keeps the widget near `omarchy.indicators`, updates an
existing `clarfocus` entry in place, and stores a timestamped backup when it
changes the file.

Native command widget:

```json
{
  "id": "clarfocus",
  "type": "command",
  "exec": "~/.local/bin/clar-focus-bar status",
  "interval": 2,
  "onClick": "~/.local/bin/clar-focus-bar open",
  "onRightClick": "~/.local/bin/clar-focus-bar toggle-pomodoro",
  "onMiddleClick": "~/.local/bin/clar-focus-bar toggle-focus"
}
```

Controls:

- left click: open or raise the Clar Focus TUI
- right click: start/stop the pomodoro
- middle click: enable/disable Focus Guard

Reference files:

- `examples/omarchy-shell/module.json`
- `examples/omarchy-shell/clar-focus-bar.sh`

The old `clar-focus waybar` command and helper names remain aliases for existing
setups, but the installer no longer edits Waybar configuration or CSS.

## Focus Mode Technical Notes

### Chosen approach

Primary enforcement uses **`/etc/hosts` temporary blocks**.

Why:

- predictable on Arch Linux
- easy to audit
- reversible
- does not require a long-running daemon
- integrates cleanly with CLI + Omarchy bar workflows

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
0.0.0.0 reddit.com www.reddit.com
::1 reddit.com www.reddit.com
# <<< OMARCHY_FOCUS END
```

Blocked domains are pointed at `0.0.0.0` (and `::1` for IPv6) rather than
`127.0.0.1`. Routing to `0.0.0.0` fails fast instead of hitting any local web
server the user might be running, and it is more resistant to DNS-rebinding
style bypasses. The original file's permissions and ownership are preserved on
every write so services like `systemd-resolved` keep working.

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

## Reports

Export a Markdown retrospective (great for a daily/weekly review):

```bash
clar-focus stats --md > ~/focus-report.md
clar-focus stats --json   # machine-readable
```

## Development

Install the dev tool-chain and run the quality gates locally:

```bash
pip install -e ".[dev]"
ruff check .          # lint
ruff format --check . # formatting
mypy                  # type check (informational)
pytest                # tests
```

CI runs these on every push and pull request (see `.github/workflows/ci.yml`).

## Testing

Run the included unit tests:

```bash
pytest
# or, without installing dev deps:
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
