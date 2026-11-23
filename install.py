#!/usr/bin/env python3
"""Install the Caelestia Telegram Theme integration for the current user."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

HOME = Path.home()
DATA = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share"))
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config"))
SYSTEMD = CONFIG / "systemd/user"
PROJECT = Path(__file__).resolve().parent
APP_DIR = DATA / "caelestia-telegram-theme"
CLI_CONFIG = CONFIG / "caelestia/cli.json"
LAUNCHER = HOME / ".local/bin/caelestia-telegram-theme"
HOOK = str(LAUNCHER) + " trigger"
TELEGRAM_BINARY = Path("/usr/bin/Telegram")
PILLOW_PACKAGE = "python-pillow"


def require(command: str, message: str) -> None:
    if shutil.which(command) is None:
        raise SystemExit(f"Missing dependency: {command}. {message}")


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def pillow_available() -> bool:
    """Check Pillow in a fresh interpreter (avoids import cache after pacman)."""
    try:
        result = subprocess.run(
            ["/usr/bin/python3", "-c", "import PIL"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def ensure_pillow() -> bool:
    """
    Pillow is needed by the default configuration (background.enabled=true).
    Offer to install it via pacman; return whether it is available afterwards.
    """
    if pillow_available():
        return True

    print("\nOptional dependency missing: python-pillow (Pillow)")
    print("  Required for wallpaper processing, which is enabled by default")
    print("  (background.enabled=true in config.json).")

    if shutil.which("pacman") is None:
        print("  pacman not found. Install 'python-pillow' manually, or disable")
        print("  wallpaper processing later with `caelestia-telegram-theme configure`.")
        return False

    try:
        answer = input("  Install it now with pacman? [Y/n]: ").strip().lower()
    except EOFError:
        answer = ""

    if answer in ("n", "no"):
        print("  Skipped. You can install it later with:")
        print("    sudo pacman -S python-pillow")
        return False

    cmd = ["pacman", "-S", "--noconfirm", PILLOW_PACKAGE]
    if os.geteuid() != 0:
        if shutil.which("sudo") is None:
            print("  Cannot install: sudo is not available.")
            return False
        cmd.insert(0, "sudo")

    try:
        subprocess.run(cmd, check=False)
    except OSError as exc:
        print(f"  Failed to run pacman: {exc}")
        return False

    if pillow_available():
        print("  Installed python-pillow.")
        return True

    print("  python-pillow is still missing.")
    return False


def install_app() -> None:
    source = PROJECT / "src/app.py"
    if not source.is_file():
        raise SystemExit(
            f"Could not find {source}. Run install.py from the project root."
        )

    APP_DIR.mkdir(parents=True, exist_ok=True)
    target = APP_DIR / "app.py"
    shutil.copy2(source, target)
    target.chmod(0o755)


def install_launcher() -> None:
    LAUNCHER.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHER.write_text(
        "#!/bin/sh\n"
        f'exec /usr/bin/python3 "{APP_DIR / "app.py"}" "$@"\n',
        encoding="utf-8",
    )
    LAUNCHER.chmod(0o755)


def install_unit() -> None:
    unit = SYSTEMD / "caelestia-telegram-theme.service"
    unit.parent.mkdir(parents=True, exist_ok=True)
    unit.write_text(
        "[Unit]\n"
        "Description=Generate the Caelestia Telegram Desktop theme\n"
        "After=graphical-session.target\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        "ExecStart=%h/.local/bin/caelestia-telegram-theme generate\n"
        "TimeoutStartSec=60\n"
        "Environment=PYTHONUNBUFFERED=1\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n",
        encoding="utf-8",
    )


def merge_hooks() -> None:
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
            raise SystemExit(
                f"Invalid '{section}' section in {CLI_CONFIG}; expected an object."
            )
        existing = block.get("postHook", "")
        if existing and not isinstance(existing, str):
            raise SystemExit(f"Invalid {section}.postHook: expected a string.")
        if HOOK not in existing:
            block["postHook"] = f"{existing.rstrip()}; {HOOK}" if existing.strip() else HOOK

    write_json_atomic(CLI_CONFIG, cli)


def main() -> int:
    require("python3", "Install Python 3.")
    require("systemctl", "Install systemd.")
    require("caelestia", "Make sure caelestia-cli is installed and available in PATH.")

    if not TELEGRAM_BINARY.exists():
        raise SystemExit(
            "Could not find /usr/bin/Telegram. "
            "Edit config.json after installation if your binary is elsewhere."
        )

    pillow_ok = ensure_pillow()

    install_app()
    install_launcher()
    install_unit()
    merge_hooks()

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)

    print("\nInstalled Caelestia Telegram Theme.")
    print(f"Generated theme: {DATA / 'caelestia-telegram-theme/current.tdesktop-theme'}")
    print("\nNext steps:")
    print("  1. Generate the first theme:")
    print("       ~/.local/bin/caelestia-telegram-theme generate")
    print("  2. In Telegram, import the generated current.tdesktop-theme once:")
    print("       Settings -> Chat Settings -> Choose from file")
    print("  3. Keep Telegram open; subsequent Caelestia palette/wallpaper changes")
    print("     will regenerate the same file; Telegram reloads the theme automatically.")

    if not pillow_ok:
        print("\nWarning: Pillow is missing. The default configuration enables")
        print("wallpaper processing (background.enabled=true), so `generate` will")
        print("fail until you either install python-pillow or disable processing:")
        print("  sudo pacman -S python-pillow")
        print("    -- or --")
        print("  ~/.local/bin/caelestia-telegram-theme configure")

    print("\nCustomize wallpaper blur/brightness with:")
    print("  ~/.local/bin/caelestia-telegram-theme configure")

    print("\nThe existing hypr-user.lua is not modified.")
    if str(LAUNCHER.parent) not in os.environ.get("PATH", "").split(":"):
        print(f"\nNote: add {LAUNCHER.parent} to PATH if you want to run the command by name.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())