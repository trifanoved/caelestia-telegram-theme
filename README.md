# Caelestia Telegram Theme

Automatically builds a Telegram Desktop `.tdesktop-theme` archive from the
current Caelestia Material 3 palette and current wallpaper.

## Requirements

- CachyOS / Arch Linux with Caelestia CLI available as `caelestia`
- Telegram Desktop installed at `/usr/bin/Telegram`
- Python 3
- systemd user session
- Current wallpaper must be JPEG or PNG

No Python third-party packages are required.

## Install

From the extracted project directory:

```bash
chmod +x install.sh uninstall.sh
./install.sh
```

The installer:
- copies the generator to `~/.local/share/caelestia-telegram-theme/`;
- installs a launcher in `~/.local/bin/`;
- installs a user systemd oneshot service;
- merges hooks into `~/.config/caelestia/cli.json` without replacing unrelated settings;
- does not edit `hypr-user.lua`.

## First-time Telegram setup

Generate the theme:

```bash
~/.local/bin/caelestia-telegram-theme generate
```

The output is:

```text
~/.local/share/caelestia-telegram-theme/current.tdesktop-theme
```

In Telegram Desktop, import this file once using **Settings → Chat Settings →
Choose from file**. The generated file is a ZIP archive with the required
`.tdesktop-theme` extension and contains `colors.tdesktop-theme` plus the
current wallpaper as `background.jpg` or `background.png`.

The existing imported plain-text theme is not automatically converted in
Telegram's settings. Select the new archive once. Future generations replace
the same archive path atomically.

## Automatic updates

The installer adds the same hook to both `wallpaper.postHook` and
`theme.postHook` in `~/.config/caelestia/cli.json`. Caelestia runs the hook,
which imports the graphical session environment into the user systemd manager
and starts `caelestia-telegram-theme.service`.

The service:
1. reads `~/.local/state/caelestia/scheme.json`;
2. gets the wallpaper from `WALLPAPER_PATH`, or falls back to
   `caelestia shell wallpaper get`;
3. builds and validates the archive;
4. if Telegram is already running, sends SIGTERM, waits up to 20 seconds,
   then starts `/usr/bin/Telegram` again.

If Telegram is not running, the theme is generated but Telegram is not started.
It deliberately does not use SIGKILL if Telegram does not exit cleanly.

## Commands

```bash
caelestia-telegram-theme generate  # Build theme without restarting Telegram
caelestia-telegram-theme update    # Build theme and restart Telegram if running
caelestia-telegram-theme trigger   # Trigger the user systemd service
caelestia-telegram-theme status    # Show output path and process status
```

If `~/.local/bin` is not in PATH, use the full path.

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

Optional file:

```text
~/.config/caelestia-telegram-theme/config.json
```

Example:

```json
{
  "scheme_file": "~/.local/state/caelestia/scheme.json",
  "output_file": "~/.local/share/caelestia-telegram-theme/current.tdesktop-theme",
  "telegram_binary": "/usr/bin/Telegram",
  "restart_timeout_seconds": 20
}
```

The current implementation maps the Caelestia roles used by the user's
existing Telegram theme. Missing roles use explicit fallback roles; if no
fallback is available, generation fails without replacing the previous
working archive.

## Uninstall

```bash
./uninstall.sh
```

The uninstaller removes the service, launcher and only its own CLI hook suffix,
preserving unrelated CLI configuration. It intentionally preserves the
generated theme file because Telegram may still refer to it.

## Notes

- This integration uses Caelestia CLI's documented `wallpaper.postHook` and
  `theme.postHook`; no Lua changes are required.
- `hypr-user.lua` is left untouched.
- If a custom Telegram binary is used, update `telegram_binary` in config.
- Theme import is a one-time operation for the new archive path.
