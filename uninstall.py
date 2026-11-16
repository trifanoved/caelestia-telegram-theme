#!/usr/bin/env python3
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess

HOME = Path.home()
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config"))
DATA = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share"))
SYSTEMD_UNIT = CONFIG / "systemd/user/caelestia-telegram-theme.service"
CLI_CONFIG = CONFIG / "caelestia/cli.json"
HOOK = str(HOME / ".local/bin/caelestia-telegram-theme") + " trigger"

def main() -> int:
    if CLI_CONFIG.exists():
        try:
            cli = json.loads(CLI_CONFIG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"Warning: {CLI_CONFIG} is invalid JSON; leaving it untouched.")
            cli = None
        if isinstance(cli, dict):
            for section in ("wallpaper", "theme"):
                block = cli.get(section)
                if not isinstance(block, dict):
                    continue
                value = block.get("postHook")
                if not isinstance(value, str):
                    continue
                # Installer appends our command as a final '; command' suffix.
                if value == HOOK:
                    block.pop("postHook", None)
                elif value.endswith("; " + HOOK):
                    block["postHook"] = value[:-(len(HOOK) + 2)].rstrip()
                if not block:
                    cli.pop(section, None)
            if cli:
                temp = CLI_CONFIG.with_suffix(".json.tmp")
                temp.write_text(json.dumps(cli, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
                os.replace(temp, CLI_CONFIG)
            else:
                CLI_CONFIG.unlink(missing_ok=True)

    subprocess.run(
        ["systemctl", "--user", "stop", "caelestia-telegram-theme.service"],
        check=False,
    )
    SYSTEMD_UNIT.unlink(missing_ok=True)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    (HOME / ".local/bin/caelestia-telegram-theme").unlink(missing_ok=True)

    app_dir = DATA / "caelestia-telegram-theme"
    app_file = app_dir / "app.py"
    app_file.unlink(missing_ok=True)
    # Preserve the generated theme: Telegram may still refer to it.
    print("Uninstalled service, launcher and Caelestia hooks.")
    print(
        f"Preserved generated theme, logs, and config.json (if any) under "
        f"{app_dir}, ~/.local/state/caelestia-telegram-theme, and "
        f"{CONFIG / 'caelestia-telegram-theme'}."
    )
    return 0
    
if __name__ == "__main__":
    raise SystemExit(main())
