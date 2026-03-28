# Omarchy Focus

Block distracting websites on [Omarchy](https://omarchy.org/) with a single command. Includes a Waybar indicator that shows when focus mode is active.

![Focus mode active on Omarchy](screenshots/desktop.png)

![Waybar detail showing the focus indicator](screenshots/waybar-detail.png)

## Install

```bash
git clone https://github.com/janhesters/omarchy-focus.git
cd omarchy-focus
./install.sh
```

The install script places two scripts in `~/.local/bin/`, adds a custom module to your Waybar config, and restarts Waybar.

## Usage

```bash
focus         # Block sites
focus off     # Unblock sites
```

Clicking the Waybar indicator also runs `focus off`.

## Configure blocked sites

Edit `~/.local/bin/focus` and modify the `BLOCKED_SITES` array:

```bash
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
```

## How it works

`focus` adds entries to `/etc/hosts` that redirect blocked domains to `127.0.0.1`. It signals Waybar to update the indicator via `RTMIN+11`. Running `focus off` removes the entries and updates the indicator.

## Requirements

- [Omarchy](https://omarchy.org/) (Arch Linux + Hyprland + Waybar)
