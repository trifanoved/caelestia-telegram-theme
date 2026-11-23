# Caelestia Telegram Theme

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Platform: Arch Linux](https://img.shields.io/badge/platform-Arch%20Linux-1793D1?logo=archlinux&logoColor=white)
![Python 3](https://img.shields.io/badge/python-3-3776AB?logo=python&logoColor=white)

Automatically builds a Telegram Desktop `.tdesktop-theme` archive from the
current Caelestia Material 3 palette and current wallpaper, and keeps
Telegram in sync as the palette or wallpaper changes.

## Features

- Maps Caelestia's Material 3 roles to Telegram Desktop colour keys
  (dialogs, sidebar, messages, menu, notifications, scrollbars, …).
- Bundles the current wallpaper into the theme archive (enabled by
  default), optionally blurred and darkened for readability.
- Validates the archive before atomically replacing the previous one.
- Supports Telegram's automatic theme reload when the generated archive is
  atomically replaced; no Telegram restart is needed for palette or wallpaper
  changes.
- Keeps an explicit `update` command for cases where a full Telegram restart
  is desired, restoring its window to the previous Hyprland workspace.
- Hooks into Caelestia's `wallpaper.postHook` and `theme.postHook` via a
  user systemd oneshot service, with debouncing to collapse bursts of events.
- Provides an interactive `configure` command for wallpaper processing.

## Requirements

- CachyOS / Arch Linux with the Caelestia CLI available as `caelestia`
- Telegram Desktop installed at `/usr/bin/Telegram`
- Python 3
- systemd user session
- **`python-pillow`** — required by the default configuration
  (`background.enabled=true`). The installer offers to install it via
  `pacman`. If you disable wallpaper processing later, Pillow is not needed.
- Current wallpaper must be JPEG or PNG

No other Python third-party packages are required.

## Install

From the extracted project directory:

```bash
chmod +x install.sh uninstall.sh
./install.sh
```

The installer:

- checks for `python3`, `systemctl`, `caelestia` and `/usr/bin/Telegram`;
- checks for Pillow and, if missing, offers to install `python-pillow` via
  `pacman` (needed because wallpaper processing is on by default);
- copies the generator to `~/.local/share/caelestia-telegram-theme/`;
- installs a launcher in `~/.local/bin/`;
- installs a user systemd oneshot service;
- merges hooks into `~/.config/caelestia/cli.json` without replacing
  unrelated settings;
- does **not** create `~/.config/caelestia-telegram-theme/config.json` —
  defaults live in `src/app.py`, and the file only appears when you run
  `caelestia-telegram-theme configure`;
- does not edit `hypr-user.lua`.

If you declined the Pillow installation, `generate` will fail under the
default configuration; either install `python-pillow` later or disable
wallpaper processing with `caelestia-telegram-theme configure`.

## First-time Telegram setup

Generate the theme:

```bash
~/.local/bin/caelestia-telegram-theme generate
```

The output is:

```text
~/.local/share/caelestia-telegram-theme/current.tdesktop-theme
```

In Telegram Desktop, import this file once via **Settings → Chat Settings →
Choose from file**. The generated file is a ZIP archive with the required
`.tdesktop-theme` extension and contains `colors.tdesktop-theme` plus, by
default, the current wallpaper as `background.jpg`.

The existing imported plain-text theme is not automatically converted in
Telegram's settings. Select the new archive once. Future generations replace
the same archive path atomically.

## Wallpaper processing

`background.enabled` is `true` by default: the current Caelestia wallpaper
is bundled into the archive as `background.jpg` and updated whenever the
palette or wallpaper changes.

When enabled:

1. the current wallpaper is auto-oriented from EXIF;
2. `GaussianBlur(background.blur_radius)` is applied (`0`–`100`);
3. `Brightness(background.brightness)` is applied (`0`–`2`, `1.0` =
   unchanged);
4. the result is encoded as JPEG and bundled as `background.jpg`,
   iteratively downscaled and re-encoded until it fits under 4 MiB
   (Telegram's archive limit is 5 MiB).

Set `blur_radius=0` and `brightness=1` to bundle the **current wallpaper
unmodified** — Telegram then shows exactly what Caelestia shows.

If you set `background.enabled=false`, the archive contains only
`colors.tdesktop-theme`, and Telegram keeps whichever background you have
selected in **Settings → Chat Settings** (its built-in default if none).

Wallpaper processing needs Pillow. Interactive helper:

```bash
caelestia-telegram-theme configure
```

The command asks for `enabled`, and when enabled also for `blur_radius` and
`brightness`, and warns if Pillow is missing.

## Automatic updates

The installer adds the same hook to both `wallpaper.postHook` and
`theme.postHook` in `~/.config/caelestia/cli.json`. Caelestia runs the hook,
which imports the graphical session environment into the user systemd
manager and starts `caelestia-telegram-theme.service`.

The service:

1. reads `~/.local/state/caelestia/scheme.json`;
2. gets the wallpaper from `caelestia shell wallpaper get`, falling back to
   `WALLPAPER_PATH` or legacy state files;
3. processes the wallpaper if `background.enabled=true`;
4. builds and validates the archive;
5. if Telegram is already running, sends `SIGTERM`, waits up to
   `restart_timeout_seconds`, then starts `telegram_binary` again and moves
   the new window back to its previous Hyprland workspace.

If Telegram is not running, the theme is generated but Telegram is not
started. It deliberately does not use `SIGKILL` if Telegram does not exit
cleanly.

## Commands

```bash
caelestia-telegram-theme generate   # Build/replace theme; Telegram hot-reloads it
caelestia-telegram-theme update     # Build theme and explicitly restart Telegram if running
caelestia-telegram-theme trigger    # Trigger the user systemd service
caelestia-telegram-theme status     # Show output path and process status
caelestia-telegram-theme configure  # Interactively edit config.json
```

If `~/.local/bin` is not in `PATH`, use the full path.

Logs:

```text
~/.local/state/caelestia-telegram-theme/manager.log
```

Service status:

```bash
systemctl --user status caelestia-telegram-theme.service
journalctl --user -u caelestia-telegram-theme.service -e
```

## Configuration

Optional file, created by `caelestia-telegram-theme configure` when you
change any default (the installer itself does not create it):

```text
~/.config/caelestia-telegram-theme/config.json
```

Example (equals the built-in defaults):

```json
{
  "scheme_file": "~/.local/state/caelestia/scheme.json",
  "output_file": "~/.local/share/caelestia-telegram-theme/current.tdesktop-theme",
  "telegram_binary": "/usr/bin/Telegram",
  "restart_timeout_seconds": 20,
  "background": {
    "enabled": true,
    "blur_radius": 12.0,
    "brightness": 0.72
  }
}
```

- `background.enabled` — bundle the wallpaper into the theme archive.
  `true` (default) means the current wallpaper is included; `false` means
  Telegram keeps its own background.
- `background.blur_radius` — Gaussian blur radius in pixels (`0`–`100`).
  `0` + `brightness=1` bundles the wallpaper unmodified.
- `background.brightness` — brightness multiplier (`0`–`2`, `1.0` =
  unchanged).
- `restart_timeout_seconds` — how long to wait for Telegram to exit before
  aborting (no `SIGKILL`).

Missing keys fall back to internal defaults (defined in `src/app.py`).
Missing Caelestia colour roles use explicit fallback roles; if no fallback
is available, generation fails without replacing the previous working
archive.

## Uninstall

```bash
./uninstall.sh
```

The uninstaller removes the service, launcher and only its own CLI hook
suffix, preserving unrelated CLI configuration. It intentionally preserves:

- the generated theme file (Telegram may still refer to it);
- `~/.config/caelestia-telegram-theme/config.json` (if you created one);
- logs under `~/.local/state/caelestia-telegram-theme/`.

## Notes

- This integration uses Caelestia CLI's documented `wallpaper.postHook` and
  `theme.postHook`; no Lua changes are required.
- `hypr-user.lua` is left untouched.
- If a custom Telegram binary is used, update `telegram_binary` in config.
- Theme import is a one-time operation for the generated archive path. Later
  atomic replacements of that same file are picked up by Telegram automatically.
- Wallpaper processing is on by default; install `python-pillow` or disable
  it with `configure` if you prefer not to use it.

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 trifanovede.