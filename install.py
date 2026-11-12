#!/usr/bin/env python3
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share"))
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config"))
SYSTEMD = CONFIG / "systemd/user"
PROJECT = Path(__file__).resolve().parent
APP_DIR = DATA / "caelestia-telegram-theme"
APP_STATE = Path(os.environ.get("XDG_STATE_HOME", HOME / ".local/state")) / "caelestia-telegram-theme"
CLI_CONFIG = CONFIG / "caelestia/cli.json"
HOOK = str(HOME / ".local/bin/caelestia-telegram-theme") + " trigger"

def require(command: str, message: str) -> None:
    if shutil.which(command) is None:
        raise SystemExit(f"Missing dependency: {command}. {message}")

def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)

def main() -> int:
    require("python3", "Install Python 3.")
    require("systemctl", "Install systemd.")
    require("caelestia", "Make sure caelestia-cli is installed and available in PATH.")
    telegram = Path("/usr/bin/Telegram")
    if not telegram.exists():
        raise SystemExit("Could not find /usr/bin/Telegram. Edit config.json after installation if your binary is elsewhere.")

    APP_DIR.mkdir(parents=True, exist_ok=True)
    APP_STATE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT / "src/app.py", APP_DIR / "app.py")
    (APP_DIR / "app.py").chmod(0o755)

    bin_dir = HOME / ".local/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    launcher = bin_dir / "caelestia-telegram-theme"
    launcher.write_text(
        "#!/bin/sh\n"
        f'exec /usr/bin/python3 "{APP_DIR / "app.py"}" "$@"\n',
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    config_path = CONFIG / "caelestia-telegram-theme/config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        write_json_atomic(config_path, {
            "scheme_file": str(Path(os.environ.get("XDG_STATE_HOME", HOME / ".local/state")) / "caelestia/scheme.json"),
            "output_file": str(DATA / "caelestia-telegram-theme/current.tdesktop-theme"),
            "telegram_binary": "/usr/bin/Telegram",
            "restart_timeout_seconds": 20
        })

    unit = SYSTEMD / "caelestia-telegram-theme.service"
    unit.parent.mkdir(parents=True, exist_ok=True)
    unit.write_text(
        "[Unit]\n"
        "Description=Generate and apply the Caelestia Telegram Desktop theme\n"
        "After=graphical-session.target\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        "ExecStart=%h/.local/bin/caelestia-telegram-theme update\n"
        "TimeoutStartSec=60\n"
        "Environment=PYTHONUNBUFFERED=1\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n",
        encoding="utf-8",
    )

    if CLI_CONFIG.exists():
        try:
            cli = json.loads(CLI_CONFIG.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{CLI_CONFIG} contains invalid JSON: {exc}")
        if not isinstance(cli, dict):
            raise SystemExit(f"{CLI_CONFIG} must contain a JSON object.")
    else:
        cli = {}

    for section in ("wallpaper", "theme"):
        block = cli.setdefault(section, {})
        if not isinstance(block, dict):
            raise SystemExit(f"Invalid '{section}' section in {CLI_CONFIG}; expected an object.")
        existing = block.get("postHook", "")
        if existing and not isinstance(existing, str):
            raise SystemExit(f"Invalid {section}.postHook: expected a string.")
        if HOOK not in existing:
            block["postHook"] = f"{existing.rstrip()}; {HOOK}" if existing.strip() else HOOK

    write_json_atomic(CLI_CONFIG, cli)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)

    print("\nInstalled Caelestia Telegram Theme.")
    print(f"Generated theme: {DATA / 'caelestia-telegram-theme/current.tdesktop-theme'}")
    print("\nNext steps:")
    print("  1. Generate the first theme:")
    print("       ~/.local/bin/caelestia-telegram-theme generate")
    print("  2. In Telegram, import the generated current.tdesktop-theme once:")
    print("       Settings -> Chat Settings -> Choose from file")
    print("  3. Keep Telegram open; subsequent Caelestia palette/wallpaper changes")
    print("     will regenerate the same file and restart Telegram automatically.")
    print("\nThe existing hypr-user.lua is not modified.")
    if str(bin_dir) not in os.environ.get("PATH", "").split(":"):
        print(f"\nNote: add {bin_dir} to PATH if you want to run the command by name.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
