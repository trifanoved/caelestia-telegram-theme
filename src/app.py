#!/usr/bin/env python3
"""Generate and apply a Caelestia-synchronised Telegram Desktop theme."""

from __future__ import annotations

import argparse
import fcntl
import json
import logging
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import zipfile
import io


HOME = Path.home()
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share"))
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", HOME / ".local/state"))
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config"))
APP_DIR = DATA_DIR / "caelestia-telegram-theme"
APP_STATE = STATE_DIR / "caelestia-telegram-theme"
CONFIG_FILE = CONFIG_DIR / "caelestia-telegram-theme/config.json"
SCHEME_FILE = STATE_DIR / "caelestia/scheme.json"
DEFAULT_OUTPUT = DATA_DIR / "caelestia-telegram-theme/current.tdesktop-theme"
LOG_FILE = APP_STATE / "manager.log"
LOCK_FILE = APP_STATE / "trigger.lock"

# Retains the user's existing colour design while sourcing every value from
# Caelestia's Material 3 scheme. Fallbacks are only used if a role is absent.
COLOR_MAP = {
    "windowBg": ("surfaceContainerLow", "surfaceContainer"),
    "windowFg": ("onSurface", "text"),
    "windowBgOver": ("surfaceContainerHigh", "surfaceVariant"),
    "windowBgActive": ("primaryContainer", "surfaceContainerHigh"),
    "windowFgActive": ("onPrimary", "onSurface"),
    "windowActiveTextFg": ("primary", "surfaceTint"),
    "windowSubTextFg": ("onSurfaceVariant", "onSurface"),
    "topBarBg": ("surfaceContainer", "surface"),
    "titleBg": ("surfaceContainer", "surface"),
    "titleBgActive": ("surfaceContainer", "surface"),
    "dialogsBg": ("surfaceContainer", "surface"),
    "dialogsBgOver": ("surfaceContainerHigh", "surfaceVariant"),
    "dialogsBgActive": ("primaryContainer", "surfaceContainerHigh"),
    "dialogsNameFg": ("onSurface", "text"),
    "dialogsNameFgOver": ("onSurface", "text"),
    "dialogsNameFgActive": ("onPrimaryContainer", "onSurface"),
    "dialogsTextFg": ("onSurfaceVariant", "subtext1"),
    "dialogsTextFgActive": ("onPrimaryContainer", "onSurface"),
    "dialogsTextFgOver": ("onSurfaceVariant", "subtext1"),
    "dialogsTextFgService": ("primary", "windowActiveTextFg"),
    "dialogsTextFgServiceOver": ("primary", "windowActiveTextFg"),
    "dialogsTextFgServiceActive": ("onPrimaryContainer", "primary"),
    "dialogsDateFg": ("onSurfaceVariant", "subtext1"),
    "dialogsDateFgActive": ("onPrimaryContainer", "onSurfaceVariant"),
    "filterInputInactiveBg": ("surfaceContainerHigh", "surfaceVariant"),
    "filterInputActiveBg": ("surfaceContainerHighest", "surfaceContainerHigh"),
    "filterInputBorderFg": ("outline", "outlineVariant"),
    "sideBarBg": ("surfaceContainer", "surfaceContainerLow"),
    "sideBarBgActive": ("primaryContainer", "surfaceContainerHigh"),
    "sideBarTextFg": ("onSurface", "text"),
    "sideBarTextFgActive": ("onPrimaryContainer", "onSurface"),
    "sideBarIconFg": ("onSurfaceVariant", "subtext1"),
    "sideBarIconFgActive": ("primary", "surfaceTint"),

    # Telegram emoji picker surfaces
    "emojiPanBg": ("surfaceContainer", "surfaceContainerLow"),
    "emojiPanCategories": ("surfaceContainerHigh", "surfaceContainer"),
    
    "sideBarBadgeBg": ("primary", "surfaceTint"),
    "sideBarBadgeBgMuted": ("secondary", "primary"),
    "sideBarBadgeFg": ("onPrimary", "onSurface"),

    "historyPeer1NameFg": ("primary", "surfaceTint"),
    "historyPeer2NameFg": ("secondary", "primary"),
    "historyPeer3NameFg": ("tertiary", "secondary"),
    "historyPeer4NameFg": ("primary", "surfaceTint"),
    "historyPeer5NameFg": ("secondary", "primary"),
    "historyPeer6NameFg": ("tertiary", "secondary"),
    "historyPeer7NameFg": ("primary", "surfaceTint"),
    "historyPeer8NameFg": ("secondary", "primary"),
    "historyBg": ("background", "surface"),
    "historyTextInFg": ("onSurface", "text"),
    "historyTextOutFg": ("onSurface", "text"),
    "msgInBg": ("surfaceContainerLow", "surfaceContainer"),
    "msgOutBg": ("primaryContainer", "surfaceContainerHigh"),
    "msgDateFg": ("onSurfaceVariant", "subtext1"),
    "msgServiceFg": ("onSurfaceVariant", "subtext1"),
    "msgServiceBg": ("surfaceContainer", "surface"),
    "msgOutDateFg": ("onPrimaryContainer", "onSurface"),
    "historyComposeAreaBg": ("surfaceContainer", "surface"),
    "historyComposeAreaFg": ("onSurface", "text"),
    "historyComposeIconFg": ("onSurfaceVariant", "subtext1"),
    "historyComposeIconFgOver": ("primary", "surfaceTint"),
    "activeButtonBg": ("primary", "surfaceTint"),
    "activeButtonFg": ("onPrimary", "onSurface"),
    "lightButtonBg": ("surfaceContainerHigh", "surfaceVariant"),
    "lightButtonFg": ("onSurface", "text"),
    "inputBorderFg": ("outline", "outlineVariant"),
        # Window interactions
    "windowBgRipple": ("primaryContainer", "surfaceContainerHighest"),

    # Dialogs: hover and unread counters
    "dialogsTextFgOver": ("onSurface", "text"),
    "dialogsDateFgOver": ("onSurfaceVariant", "subtext1"),

    "dialogsUnreadBg": ("primary", "surfaceTint"),
    "dialogsUnreadBgMuted": ("secondary", "primary"),
    "dialogsUnreadFg": ("onPrimary", "onSurface"),

    "dialogsUnreadBgOver": ("primaryDim", "primary"),
    "dialogsUnreadBgMutedOver": ("secondary", "primary"),
    "dialogsUnreadFgOver": ("onPrimary", "onSurface"),

    "dialogsUnreadBgActive": ("primary", "surfaceTint"),
    "dialogsUnreadBgMutedActive": ("secondary", "primary"),
    "dialogsUnreadFgActive": ("onPrimary", "onSurface"),

    "notificationBg": ("surfaceContainerHigh", "surface"),
    "notificationsBoxMonitorFg": ("onSurface", "text"),
    "notificationsBoxScreenBg": ("surfaceContainer", "surface"),
    "notificationSampleTextFg": ("onSurface", "text"),
    "notificationSampleNameFg": ("primary", "surfaceTint"),
    "notificationSampleUserpicFg": ("primary", "surfaceTint"),
    "notificationSampleCloseFg": ("onSurfaceVariant", "subtext1"),

    # Buttons
    "activeButtonBgOver": ("primaryDim", "primary"),
    "activeButtonBgRipple": ("primaryContainer", "primaryDim"),
    "lightButtonBgOver": ("surfaceContainerHighest", "surfaceContainerHigh"),
    "lightButtonBgRipple": ("secondaryContainer", "surfaceContainerHighest"),

    # Menus
    "menuBg": ("surfaceContainer", "surface"),
    "menuBgOver": ("surfaceContainerHigh", "surfaceVariant"),
    "menuBgRipple": ("primaryContainer", "surfaceContainerHighest"),
    "menuIconFg": ("onSurfaceVariant", "subtext1"),
    "menuIconFgOver": ("primary", "surfaceTint"),

    # Inputs
    "placeholderFg": ("onSurfaceVariant", "subtext1"),
    "placeholderFgActive": ("primary", "surfaceTint"),

    # Message selection
    "msgInBgSelected": ("secondaryContainer", "surfaceContainerHighest"),
    "msgOutBgSelected": ("primaryDim", "primaryContainer"),
    "msgSelectOverlay": ("primaryContainer", "secondaryContainer"),

    # System messages and unread separator
    "historySystemBg": ("surfaceContainerHigh", "surfaceVariant"),
    "historySystemFg": ("onSurface", "text"),
    "historyUnreadBarBg": ("primaryContainer", "surfaceContainerHighest"),
    "historyUnreadBarBorder": ("surface", "background"),
    "historyUnreadBarFg": ("onPrimaryContainer", "onSurface"),

    # History scrollbars
    "historyScrollBarBg": ("primaryDim", "primary"),
    "historyScrollBarBgOver": ("primary", "surfaceTint"),
    "historyScrollBg": ("surfaceContainerHighest", "surfaceVariant"),
    "historyScrollBgOver": ("outline", "outlineVariant"),

        # Sent message checkmarks
    "dialogsSentIconFg": ("primary", "surfaceTint"),
    "dialogsSentIconFgOver": ("primary", "surfaceTint"),
    "dialogsSentIconFgActive": ("primary", "surfaceTint"),

    "historyOutIconFg": ("primary", "surfaceTint"),
    "historyOutIconFgSelected": ("onPrimaryContainer", "primary"),

    "historySendingOutIconFg": ("secondary", "primary"),
    "historySendingInIconFg": ("onSurfaceVariant", "subtext1"),

        # Reply previews inside message bubbles
    "msgInServiceFg": ("secondary", "primary"),
    "msgInServiceFgSelected": ("onSecondaryContainer", "onSurface"),

    "msgOutServiceFg": ("primary", "surfaceTint"),
    "msgOutServiceFgSelected": ("onPrimaryContainer", "primary"),

    "msgInReplyBarColor": ("secondary", "primary"),
    "msgInReplyBarSelColor": ("onSecondaryContainer", "primary"),

    "msgOutReplyBarColor": ("primary", "surfaceTint"),
    "msgOutReplyBarSelColor": ("onPrimaryContainer", "primary"),

    "msgImgReplyBarColor": ("primary", "surfaceTint"),

        # Reply preview above the compose field
    "historyReplyBg": ("surfaceContainerHigh", "surfaceContainer"),
    "historyReplyIconFg": ("primary", "surfaceTint"),
    "historyReplyCancelFg": ("onSurfaceVariant", "subtext1"),
    "historyReplyCancelFgOver": ("primary", "surfaceTint"),
    # File cards and download indicators
    "msgFile1Bg": ("primaryContainer", "surfaceContainerHigh"),
    "msgFile1BgDark": ("primary", "surfaceTint"),
    "msgFile1BgOver": ("primary", "surfaceTint"),
    "msgFile1BgSelected": ("primaryContainer", "surfaceContainerHigh"),
    "msgFile2Bg": ("secondaryContainer", "surfaceContainerHigh"),
    "msgFile2BgDark": ("secondary", "primary"),
    "msgFile2BgOver": ("secondary", "primary"),
    "msgFile2BgSelected": ("secondaryContainer", "surfaceContainerHigh"),
    "msgFile3Bg": ("tertiaryContainer", "surfaceContainerHigh"),
    "msgFile3BgDark": ("tertiary", "secondary"),
    "msgFile3BgOver": ("tertiary", "secondary"),
    "msgFile3BgSelected": ("tertiaryContainer", "surfaceContainerHigh"),
    "msgFile4Bg": ("errorContainer", "surfaceContainerHigh"),
    "msgFile4BgDark": ("error", "primary"),
    "msgFile4BgOver": ("error", "primary"),
    "msgFile4BgSelected": ("errorContainer", "surfaceContainerHigh"),
    "msgFileInBg": ("surfaceContainerHigh", "surfaceVariant"),
    "msgFileInBgOver": ("surfaceContainerHighest", "surfaceContainerHigh"),
    "msgFileInBgSelected": ("primaryContainer", "surfaceContainerHigh"),
    "msgFileOutBg": ("surfaceContainerHigh", "surfaceVariant"),
    "msgFileOutBgOver": ("surfaceContainerHighest", "surfaceContainerHigh"),
    "msgFileOutBgSelected": ("primaryContainer", "surfaceContainerHigh"),
    "msgFileThumbLinkInFg": ("onPrimary", "onSurface"),
    "msgFileThumbLinkInFgSelected": ("onPrimaryContainer", "onSurface"),
    "msgFileThumbLinkOutFg": ("onPrimary", "onSurface"),
    "msgFileThumbLinkOutFgSelected": ("onPrimaryContainer", "onSurface"),
    "msgDateImgBg": ("surfaceContainerHighest", "surfaceContainerHigh"),
    "msgDateImgBgOver": ("surfaceContainerHigh", "surfaceVariant"),
    "msgDateImgBgSelected": ("primaryContainer", "surfaceContainerHigh"),

    # Telegram's actual theme keys for file icons and selection checks
    "historyFileInIconFg": ("onSurface", "text"),
    "historyFileInIconFgSelected": ("onPrimaryContainer", "onSurface"),
    "historyFileOutIconFg": ("onSurface", "text"),
    "historyFileOutIconFgSelected": ("onPrimaryContainer", "onSurface"),
    "mediaviewFileRedCornerFg": ("error", "primary"),
    "mediaviewFileYellowCornerFg": ("tertiary", "secondary"),
    "mediaviewFileGreenCornerFg": ("secondary", "primary"),
    "mediaviewFileBlueCornerFg": ("primary", "surfaceTint"),
    "overviewCheckBgActive": ("primaryContainer", "surfaceContainerHigh"),
    "overviewCheckFgActive": ("onPrimaryContainer", "onSurface"),
    "settingsIconBg1": ("primaryContainer", "surfaceContainerHigh"),
    "settingsIconBg2": ("secondaryContainer", "surfaceContainerHigh"),
    "settingsIconBg3": ("tertiaryContainer", "surfaceContainerHigh"),
    "settingsIconBg4": ("errorContainer", "surfaceContainerHigh"),
    "settingsIconBg5": ("primaryContainer", "surfaceContainerHigh"),
    "settingsIconBg6": ("secondaryContainer", "surfaceContainerHigh"),
    "settingsIconBg8": ("tertiaryContainer", "surfaceContainerHigh"),
    "settingsIconBgArchive": ("surfaceContainerHigh", "surfaceContainer"),


    # Selection indicators in shared media and file lists
    "overviewCheckBg": ("surfaceContainerHigh", "surfaceContainer"),
    "overviewCheckFg": ("onPrimary", "onSurface"),
    "overviewPhotoSelectOverlay": ("primaryContainer", "surfaceContainerHigh"),

    # Popup menus and separators
    "menuFgDisabled": ("onSurfaceVariant", "subtext1"),
    "menuSeparatorFg": ("outlineVariant", "surfaceContainerHighest"),
    "menuSubmenuArrowFg": ("onSurfaceVariant", "subtext1"),

    # Settings dialogs, rows, and controls
    "boxBg": ("surfaceContainer", "surface"),
    "boxTextFg": ("onSurface", "text"),
    "boxTitleFg": ("onSurface", "text"),
    "boxTitleAdditionalFg": ("onSurfaceVariant", "subtext1"),
    "contactsBg": ("surfaceContainer", "surface"),
    "contactsBgOver": ("surfaceContainerHigh", "surfaceVariant"),
    "contactsNameFg": ("onSurface", "text"),
    "contactsStatusFg": ("onSurfaceVariant", "subtext1"),
    "contactsStatusFgOver": ("onSurfaceVariant", "subtext1"),
    "contactsStatusFgOnline": ("primary", "surfaceTint"),
    "membersAboutLimitFg": ("onSurfaceVariant", "subtext1"),
    "checkboxFg": ("outline", "outlineVariant"),
    "sliderBgInactive": ("surfaceContainerHighest", "surfaceVariant"),
    "sliderBgActive": ("primary", "surfaceTint"),
    "tooltipBg": ("surfaceContainerHighest", "surfaceContainerHigh"),
    "tooltipFg": ("onSurface", "text"),
    "tooltipBorderFg": ("outlineVariant", "surfaceContainerHighest"),
    "mainMenuBg": ("surfaceContainer", "surface"),

}

def load_config() -> dict:
    defaults = {
        "scheme_file": str(SCHEME_FILE),
        "output_file": str(DEFAULT_OUTPUT),
        "telegram_binary": "/usr/bin/Telegram",
        "restart_timeout_seconds": 20,
        "background": {
            "enabled": True,
            "blur_radius": 12.0,
            "brightness": 0.72,
        },
    }

    try:
        user = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))

        if not isinstance(user, dict):
            raise ValueError("config root must be a JSON object")

        user_background = user.pop("background", {})
        if not isinstance(user_background, dict):
            raise ValueError("'background' must be a JSON object")

        defaults.update(user)
        defaults["background"].update(user_background)

    except FileNotFoundError:
        pass

    return defaults

def setup_logging() -> None:
    APP_STATE.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def normalize_color(value: object, role: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Missing or invalid Caelestia colour: {role}")
    value = value.strip().lstrip("#")
    if len(value) not in (6, 8) or any(c not in "0123456789abcdefABCDEF" for c in value):
        raise ValueError(f"Invalid HEX colour for {role}: {value!r}")
    return "#" + value.lower()


def get_wallpaper() -> Path:
    # Query Caelestia first: systemd's imported environment can retain an older
    # WALLPAPER_PATH between events. The CLI reports the current wallpaper.
    candidates = []
    try:
        result = subprocess.run(
            ["caelestia", "shell", "wallpaper", "get"],
            check=True, capture_output=True, text=True, timeout=10,
        )
        candidates.extend(Path(line.strip()).expanduser()
                          for line in result.stdout.splitlines() if line.strip())
    except (FileNotFoundError, subprocess.SubprocessError):
        pass

    env_path = os.environ.get("WALLPAPER_PATH", "").strip()
    if env_path:
        candidates.append(Path(env_path).expanduser())

    # Legacy state-file fallback, if present in this Caelestia build.
    for state_file in (
        STATE_DIR / "caelestia/wallpaper/path.txt",
        STATE_DIR / "caelestia/wallpaper_path.txt",
    ):
        try:
            value = state_file.read_text(encoding="utf-8").strip()
            if value:
                candidates.append(Path(value).expanduser())
        except OSError:
            continue

    for path in candidates:
        try:
            resolved = path.resolve(strict=True)
            if resolved.is_file():
                return resolved
        except OSError:
            continue
    raise FileNotFoundError(
        "Could not resolve the current Caelestia wallpaper. "
        "Check `caelestia shell wallpaper get` and WALLPAPER_PATH."
    )



def process_wallpaper(
    wallpaper: Path,
    settings: dict,
) -> tuple[str, bytes | None]:
    """
    Process and compress the current wallpaper for Telegram.

    Always exports JPEG to keep the theme archive small.
    If processing is disabled, no wallpaper is added.
    """
    enabled = settings.get("enabled", False)

    if not isinstance(enabled, bool):
        raise ValueError("background.enabled must be a boolean")

    if not enabled:
        return "background.jpg", None

    if wallpaper.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise ValueError(
            f"Telegram theme wallpaper must be JPEG or PNG; got {wallpaper.name}"
        )

    try:
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    except ImportError as exc:
        raise RuntimeError(
            "Wallpaper processing requires Pillow. "
            "Install it with: sudo pacman -S python-pillow"
        ) from exc

    try:
        blur_radius = float(settings.get("blur_radius", 12.0))
        brightness = float(settings.get("brightness", 0.72))
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid background processing settings") from exc

    if not 0 <= blur_radius <= 100:
        raise ValueError("background.blur_radius must be between 0 and 100")

    if not 0 <= brightness <= 2:
        raise ValueError("background.brightness must be between 0 and 2")

    with Image.open(wallpaper) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")

    if blur_radius > 0:
        image = image.filter(
            ImageFilter.GaussianBlur(radius=blur_radius)
        )

    if brightness != 1.0:
        image = ImageEnhance.Brightness(image).enhance(brightness)

    # Keep the wallpaper below 4 MiB to leave room for the color file
    # and ZIP metadata.
    target_size = 4 * 1024 * 1024

    qualities = (90, 85, 80, 75, 70, 65, 60, 55)
    max_dimension = max(image.size)

    for resize_step in range(12):
        if resize_step == 0:
            candidate = image
        else:
            scale = 0.85 ** resize_step
            width = max(1, round(image.width * scale))
            height = max(1, round(image.height * scale))

            candidate = image.resize(
                (width, height),
                Image.Resampling.LANCZOS,
            )

        for quality in qualities:
            buffer = io.BytesIO()

            candidate.save(
                buffer,
                format="JPEG",
                quality=quality,
                optimize=True,
                progressive=True,
            )

            image_data = buffer.getvalue()

            if len(image_data) <= target_size:
                logging.info(
                    "Processed wallpaper: %dx%d, quality=%d, "
                    "size=%.2f MiB, blur=%.1f, brightness=%.2f",
                    candidate.width,
                    candidate.height,
                    quality,
                    len(image_data) / (1024 * 1024),
                    blur_radius,
                    brightness,
                )

                return "background.jpg", image_data

        if max(candidate.size) <= 800:
            break

    raise RuntimeError(
        "Unable to compress wallpaper below 4 MiB. "
        f"Original dimensions: {image.width}x{image.height}"
    )


def make_colors(scheme: dict) -> str:
    colours = scheme.get("colours")
    if not isinstance(colours, dict):
        raise ValueError("scheme.json does not contain a 'colours' object")

    lines = [
        "// Generated by Caelestia Telegram Theme. Do not edit this generated file.",
        f"// Scheme: {scheme.get('name', 'unknown')} / "
        f"{scheme.get('flavour', 'unknown')} / "
        f"{scheme.get('mode', 'unknown')} / "
        f"{scheme.get('variant', 'unknown')}",
        "",
    ]
    for telegram_key, roles in COLOR_MAP.items():
        value = None
        for role in roles:
            if role in colours:
                value = normalize_color(colours[role], role)
                break
        if value is None:
            raise ValueError(
                f"Scheme is missing all fallback roles for {telegram_key}: {roles}"
            )
        lines.append(f"{telegram_key}: {value};")
    return "\n".join(lines) + "\n"


def generate() -> Path:
    config = load_config()
    scheme_path = Path(config["scheme_file"]).expanduser()
    output_path = Path(config["output_file"]).expanduser()

    scheme = json.loads(scheme_path.read_text(encoding="utf-8"))
    if not isinstance(scheme, dict):
        raise ValueError("scheme.json root must be a JSON object")

    wallpaper = get_wallpaper()

    background_settings = config.get("background", {})
    archive_wallpaper, processed_wallpaper = process_wallpaper(
        wallpaper,
        background_settings,
    )

    colors_text = make_colors(scheme)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=output_path.name + ".", suffix=".tmp", dir=output_path.parent
    )
    os.close(fd)
    temp_path = Path(temp_name)
    try:

        with zipfile.ZipFile(
            temp_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr("colors.tdesktop-theme", colors_text)

            if processed_wallpaper is not None:
                archive.writestr(archive_wallpaper, processed_wallpaper)

        # Validate archive before replacing the previously working theme.
        with zipfile.ZipFile(temp_path, "r") as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"Generated archive failed validation: {bad}")

            names = set(archive.namelist())

            if "colors.tdesktop-theme" not in names:
                raise RuntimeError("Generated archive is missing colors.tdesktop-theme")

            if processed_wallpaper is not None and archive_wallpaper not in names:
                raise RuntimeError("Generated archive is missing its wallpaper")

            if processed_wallpaper is None and archive_wallpaper in names:
                raise RuntimeError("Wallpaper should not be present when disabled")

        # Telegram theme archive size limit: 5 MiB.
        max_archive_size = 5 * 1024 * 1024
        archive_size = temp_path.stat().st_size

        if archive_size > max_archive_size:
            raise RuntimeError(
                f"Generated theme is too large: {archive_size / (1024 * 1024):.2f} MiB "
                f"(limit: {max_archive_size / (1024 * 1024):.2f} MiB)"
            )
        os.replace(temp_path, output_path)

    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass

    logging.info(
        "Generated %s from scheme=%s flavour=%s mode=%s variant=%s wallpaper=%s",
        output_path, scheme.get("name"), scheme.get("flavour"),
        scheme.get("mode"), scheme.get("variant"), wallpaper,
    )
    print(output_path)
    return output_path


def telegram_pids() -> list[int]:
    pids = []
    proc = Path("/proc")
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            comm = (entry / "comm").read_text(encoding="utf-8").strip().lower()
            if comm in {"telegram", "telegram-desktop", "telegram-desktop-bin"}:
                pids.append(int(entry.name))
                continue
            raw = (entry / "cmdline").read_bytes().split(b"\0")
            first = raw[0].decode(errors="ignore") if raw and raw[0] else ""
            if Path(first).name.lower() in {"telegram", "telegram-desktop"}:
                pids.append(int(entry.name))
        except (OSError, ProcessLookupError):
            continue
    return sorted(set(pids))

def get_telegram_workspace(pids: list[int]) -> dict | None:
    """Find the Hyprland workspace occupied by Telegram."""
    try:
        result = subprocess.run(
            ["hyprctl", "-j", "clients"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        clients = json.loads(result.stdout)

        for client in clients:
            if client.get("pid") not in pids:
                continue

            window_class = (
                client.get("class", "") + " " +
                client.get("initialClass", "")
            ).lower()

            if "telegram" not in window_class:
                continue

            workspace = client.get("workspace", {})
            name = workspace.get("name")

            if name:
                logging.info(
                    "Telegram workspace detected: %s (window=%s)",
                    name,
                    client.get("address"),
                )
                return {
                    "name": name,
                    "address": client.get("address"),
                }

    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        logging.exception("Failed to detect Telegram workspace: %s", exc)

    logging.warning("Could not detect Telegram workspace.")
    return None


def restore_telegram_workspace(workspace: dict | None, timeout: int) -> bool:
    """Wait for the new Telegram window and move it to its previous workspace."""
    if not workspace:
        logging.warning("Workspace restoration skipped: no saved workspace.")
        return False

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            result = subprocess.run(
                ["hyprctl", "-j", "clients"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            clients = json.loads(result.stdout)

            pids = telegram_pids()

            for client in clients:
                if client.get("pid") not in pids:
                    continue

                window_class = (
                    client.get("class", "") + " " +
                    client.get("initialClass", "")
                ).lower()

                if "telegram" not in window_class:
                    continue

                address = client.get("address")
                if not address:
                    continue

                lua_command = (
                    "hl.dsp.window.move({ "
                    f"workspace = {json.dumps(workspace['name'])}, "
                    f"window = {json.dumps(f'address:{address}')}, "
                    "follow = false "
                    "})"
                )

                result = subprocess.run(
                    ["hyprctl", "dispatch", lua_command],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode != 0:
                    logging.error(
                        "Failed to restore Telegram workspace: %s",
                        result.stderr.strip() or result.stdout.strip(),
                    )
                    return False

                logging.info(
                    "Telegram window %s moved to workspace %s.",
                    address,
                    workspace["name"],
                )
                return True

        except (
            OSError,
            subprocess.SubprocessError,
            json.JSONDecodeError,
        ) as exc:
            logging.warning("Workspace restoration attempt failed: %s", exc)

        time.sleep(0.25)

    logging.error(
        "Telegram window did not appear on time; workspace %s was not restored.",
        workspace["name"],
    )
    return False


def restart_telegram() -> bool:
    config = load_config()
    binary = Path(config["telegram_binary"]).expanduser()
    timeout = int(config.get("restart_timeout_seconds", 20))

    pids = telegram_pids()

    if not pids:
        logging.info("Telegram is not running; generated theme only, no launch.")
        print("Telegram is not running; theme generated, application not launched.")
        return False

    if not binary.exists():
        raise FileNotFoundError(f"Telegram executable not found: {binary}")

    if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
        raise RuntimeError(
            "No WAYLAND_DISPLAY or DISPLAY in the user service environment. "
            "Import the graphical session environment and retry."
        )

    # Remember Telegram's current workspace before stopping it.
    previous_workspace = get_telegram_workspace(pids)

    logging.info("Stopping Telegram processes: %s", pids)

    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if not telegram_pids():
            break
        time.sleep(0.25)
    else:
        raise TimeoutError(
            f"Telegram did not exit within {timeout}s; refusing to SIGKILL it."
        )

    # Launch Telegram in an independent systemd user service.
    subprocess.run(
        [
            "systemd-run",
            "--user",
            "--no-block",
            "--collect",
            "--unit=caelestia-telegram-desktop",
            str(binary),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    logging.info("Telegram relaunched using %s", binary)

    # Wait for its new window and restore the previous workspace.
    restored = restore_telegram_workspace(previous_workspace, timeout)

    if restored:
        print("Telegram restarted and returned to its previous workspace.")
    else:
        print("Telegram restarted, but workspace restoration failed. Check manager.log.")

    return True


def trigger() -> None:
    # Import the compositor/session environment into the user systemd manager,
    # because services do not automatically inherit the hook's environment.
    names = (
        "WAYLAND_DISPLAY", "DISPLAY", "XAUTHORITY", "XDG_RUNTIME_DIR",
        "DBUS_SESSION_BUS_ADDRESS", "XDG_CURRENT_DESKTOP", "XDG_SESSION_TYPE",
        "WALLPAPER_PATH",
    )
    present = [name for name in names if os.environ.get(name)]
    if present:
        subprocess.run(
            ["systemctl", "--user", "import-environment", *present],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    APP_STATE.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        now = time.time()
        lock.seek(0)
        previous_text = lock.read().strip()
        try:
            previous = float(previous_text) if previous_text else 0.0
        except ValueError:
            previous = 0.0
        if now - previous < 3.0:
            logging.info("Duplicate Caelestia hook suppressed (debounce).")
            return
        lock.seek(0)
        lock.truncate()
        lock.write(str(now))
        lock.flush()

    subprocess.run(
        ["systemctl", "--user", "start", "--no-block",
         "caelestia-telegram-theme.service"],
        check=True,
    )


def configure() -> None:
    config = load_config()
    background = config["background"]

    def ask_bool(prompt: str, current: bool) -> bool:
        default = "Y/n" if current else "y/N"

        while True:
            answer = input(f"{prompt} [{default}]: ").strip().lower()

            if not answer:
                return current
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False

            print("Enter y or n.")

    def ask_float(
        prompt: str,
        current: float,
        minimum: float,
        maximum: float,
    ) -> float:
        while True:
            answer = input(f"{prompt} [{current}]: ").strip()

            if not answer:
                return current

            try:
                value = float(answer)
            except ValueError:
                print("Enter a valid number.")
                continue

            if minimum <= value <= maximum:
                return value

            print(f"Value must be between {minimum} and {maximum}.")

    print("\nCaelestia Telegram Theme configuration")
    print("--------------------------------------")
    print("Wallpaper processing")
    print("  Enabled: bundle the current Caelestia wallpaper into the theme")
    print("           archive and keep it in sync with wallpaper changes.")
    print("  Disabled: theme contains colours only; Telegram keeps whatever")
    print("            background you selected in its settings.")
    print("  Tip: to bundle the wallpaper unmodified, enable processing and set")
    print("       blur_radius=0, brightness=1.")
    background["enabled"] = ask_bool(
        "Enable wallpaper blur and darkening?",
        background["enabled"],
    )

    if background["enabled"]:
        background["blur_radius"] = ask_float(
            "Blur radius (0-100)",
            float(background["blur_radius"]),
            0,
            100,
        )

        background["brightness"] = ask_float(
            "Brightness multiplier (0-2; 1 = original)",
            float(background["brightness"]),
            0,
            2,
        )

    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        prefix=CONFIG_FILE.name + ".",
        suffix=".tmp",
        dir=CONFIG_FILE.parent,
    )

    temp_path = Path(temp_name)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=4, ensure_ascii=False)
            file.write("\n")

        os.replace(temp_path, CONFIG_FILE)

    finally:
        temp_path.unlink(missing_ok=True)

    print(f"\nConfiguration saved to: {CONFIG_FILE}")

    if background["enabled"]:
        try:
            import PIL  # noqa: F401
        except ImportError:
            print(
                "\nWarning: Pillow is not installed. "
                "Install it with: sudo pacman -S python-pillow"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
    "action",
    choices=("generate", "update", "trigger", "status", "configure"),
    )
    args = parser.parse_args()
    setup_logging()
    try:
        if args.action == "generate":
            generate()
        elif args.action == "update":
            generate()
            restart_telegram()
        elif args.action == "trigger":
            trigger()
        elif args.action == "status":
            cfg = load_config()
            bg = cfg.get("background", {})
            if bg.get("enabled"):
                wallpaper_mode = (
                    f"bundled (blur={bg.get('blur_radius')}, "
                    f"brightness={bg.get('brightness')})"
                )
            else:
                wallpaper_mode = "not bundled (Telegram keeps its own)"
            print(f"Output: {cfg['output_file']}")
            print(f"Telegram running: {'yes' if telegram_pids() else 'no'}")
            print(f"Log: {LOG_FILE}")
            print(f"Wallpaper: {wallpaper_mode}")
        elif args.action == "configure":
            configure()
        return 0
    except Exception as exc:
        logging.exception("Action %s failed: %s", args.action, exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())