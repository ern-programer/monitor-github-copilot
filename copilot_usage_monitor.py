#!/usr/bin/env python3
"""Monitor de uso mensual de GitHub Copilot (Premium requests).

Incluye:
- Modo visual flotante (barra angosta movible, siempre visible)
- Modo consola para depuracion
"""

from __future__ import annotations

import argparse
import calendar
import configparser
import datetime as dt
import os
import re
import socket
import sys
import time
import tkinter as tk
import ctypes
import json
import traceback
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, simpledialog

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

try:
    import pystray
    from PIL import Image, ImageDraw

    TRAY_SUPPORTED = True
except Exception:
    pystray = None
    Image = None
    ImageDraw = None
    TRAY_SUPPORTED = False

GITHUB_FEATURES_URL = "https://github.com/settings/copilot/features"
DEFAULT_STATE_PATH = Path(".auth") / "github_storage_state.json"
DEFAULT_CONFIG_PATH = Path("monitor_config.ini")
SINGLE_INSTANCE_HOST = "127.0.0.1"
SINGLE_INSTANCE_PORT = 49371
SINGLE_INSTANCE_LOG_FILE = Path("single_instance_events.txt")
SINGLE_INSTANCE_LOG_MAX_BYTES = 200 * 1024
SINGLE_INSTANCE_LOG_KEEP_LINES = 250
RUNTIME_LOG_FILE = Path("monitor_runtime.log")
RUNTIME_LOG_MAX_BYTES = 300 * 1024
RUNTIME_LOG_KEEP_LINES = 350
AUTOSTART_REG_NAME = "CopilotUsageBar"
APP_VERSION = "v1.3.1"
LANG_EN = "en"
LANG_ES = "es"

THEME_DARK = "dark"
THEME_LIGHT = "light"
THEME_PALETTES = {
    THEME_DARK: {
        "bg": "#101113",
        "border": "#2b2f36",
        "text_primary": "#e9ecef",
        "text_secondary": "#9fb3c8",
        "text_muted": "#8ea0b5",
        "text_clock": "#dfe7ef",
        "refresh": "#8bd3ff",
        "taskbar_dot": "#66d9ff",
        "tray_dot": "#ff922b",
        "close_dot": "#ff5d5d",
        "track": "#2b2f36",
        "bar_text": "#dfe7ef",
        "error": "#e03131",
        "tooltip_bg": "#1f2430",
        "tooltip_fg": "#dfe7ef",
        "tooltip_border": "#3a4654",
        "tray_bg": "#101113",
        "tray_card": "#1f2933",
        "tray_card_border": "#3a4654",
    },
    THEME_LIGHT: {
        "bg": "#f7f9fc",
        "border": "#c9d5e2",
        "text_primary": "#1f2a36",
        "text_secondary": "#3d5369",
        "text_muted": "#657b91",
        "text_clock": "#2d3f51",
        "refresh": "#1f8bd4",
        "taskbar_dot": "#0aa6c2",
        "tray_dot": "#c17c00",
        "close_dot": "#c23b3b",
        "track": "#d9e2ec",
        "bar_text": "#1f2a36",
        "error": "#b83232",
        "tooltip_bg": "#ffffff",
        "tooltip_fg": "#1f2a36",
        "tooltip_border": "#b8c6d6",
        "tray_bg": "#edf3f9",
        "tray_card": "#ffffff",
        "tray_card_border": "#b8c6d6",
    },
}

UI_TEXTS = {
    "loading": {LANG_EN: "Loading...", LANG_ES: "Cargando..."},
    "update_now": {LANG_EN: "Refresh now", LANG_ES: "Actualizar ahora"},
    "notif_area": {LANG_EN: "Notification area", LANG_ES: "Area de notificacion"},
    "minimize": {LANG_EN: "Minimize", LANG_ES: "Minimizar"},
    "always_visible": {LANG_EN: "Always on top: {state}", LANG_ES: "Siempre visible: {state}"},
    "toggle_dock_top": {LANG_EN: "Toggle top dock", LANG_ES: "Alternar dock superior"},
    "settings": {LANG_EN: "Settings", LANG_ES: "Configuracion"},
    "logout": {LANG_EN: "Re-login", LANG_ES: "Log out"},
    "exit": {LANG_EN: "Exit", LANG_ES: "Salir"},
    "restore": {LANG_EN: "Restore", LANG_ES: "Restaurar"},
    "switch_70": {LANG_EN: "Switch to 70px", LANG_ES: "Cambiar a 70px"},
    "switch_100": {LANG_EN: "Switch to 100px", LANG_ES: "Cambiar a 100px"},
    "switch_150": {LANG_EN: "Switch to 150px", LANG_ES: "Cambiar a 150px"},
    "tooltip_tray": {LANG_EN: "Minimize to notification area", LANG_ES: "Minimizar al area de notificacion"},
    "tooltip_taskbar": {LANG_EN: "Minimize to taskbar mode", LANG_ES: "Minimizar a modo taskbar"},
    "tooltip_refresh": {LANG_EN: "Refresh now", LANG_ES: "Actualizar ahora"},
    "tooltip_exit": {LANG_EN: "Exit", LANG_ES: "Salir"},
    "tooltip_menu": {LANG_EN: "Open menu", LANG_ES: "Abrir menu"},
    "tooltip_usage": {LANG_EN: "Monthly Premium requests usage", LANG_ES: "Uso mensual del cupo de Premium requests"},
    "tooltip_metrics": {
        LANG_EN: "User: active GitHub account\nPace: current usage vs linear pace\nMonth: elapsed month percentage\nProj: projected month-end usage",
        LANG_ES: "Usuario: cuenta GitHub activa\nRitmo: uso actual vs ritmo lineal\nMes: porcentaje de mes transcurrido\nProy: proyeccion al cierre",
    },
    "theme": {LANG_EN: "Theme", LANG_ES: "Tema"},
    "theme_dark": {LANG_EN: "Dark", LANG_ES: "Oscuro"},
    "theme_light": {LANG_EN: "Light", LANG_ES: "Claro"},
    "language": {LANG_EN: "Language", LANG_ES: "Idioma"},
    "language_en": {LANG_EN: "English", LANG_ES: "Ingles"},
    "language_es": {LANG_EN: "Spanish", LANG_ES: "Espanol"},
    "interval": {LANG_EN: "Interval", LANG_ES: "Intervalo"},
    "opacity": {LANG_EN: "Opacity", LANG_ES: "Opacidad"},
    "autowidth_toggle": {LANG_EN: "Auto-width: {state} (toggle)", LANG_ES: "Auto-width: {state} (alternar)"},
    "set_fixed_width": {LANG_EN: "Set fixed width...", LANG_ES: "Definir ancho fijo..."},
    "autostart_toggle": {LANG_EN: "Windows autostart: {state} (toggle)", LANG_ES: "Autoarranque Windows: {state} (alternar)"},
    "accounts": {LANG_EN: "Accounts", LANG_ES: "Cuentas"},
    "list_accounts": {LANG_EN: "List accounts", LANG_ES: "Listar cuentas"},
    "add_account": {LANG_EN: "Add account...", LANG_ES: "Agregar cuenta..."},
    "remove_account": {LANG_EN: "Remove account...", LANG_ES: "Quitar cuenta..."},
    "restart_now": {LANG_EN: "Restart bar now", LANG_ES: "Reiniciar barra ahora"},
    "updating": {LANG_EN: "Updating data...", LANG_ES: "Actualizando datos..."},
    "error_prefix": {LANG_EN: "Error", LANG_ES: "Error"},
    "error_internal_ui": {LANG_EN: "Internal UI error (see monitor_runtime.log)", LANG_ES: "Error interno UI (ver monitor_runtime.log)"},
    "no_data": {LANG_EN: "no data", LANG_ES: "sin datos"},
    "account_default": {LANG_EN: "Account {n}", LANG_ES: "Cuenta {n}"},
    "accounts_ok": {LANG_EN: "{ok}/{total} accounts OK", LANG_ES: "{ok}/{total} cuentas OK"},
    "metrics_mini": {LANG_EN: " | {account} | P:{pace:.2f}x | Month:{elapsed:.1f}%", LANG_ES: " | {account} | R:{pace:.2f}x | Mes:{elapsed:.1f}%"},
    "metrics_full": {LANG_EN: " | {account} | Pace:{pace:.2f}x | Month:{elapsed:.1f}% | Proj:{proj:.1f}%", LANG_ES: " | {account} | Ritmo:{pace:.2f}x | Mes:{elapsed:.1f}% | Proy:{proj:.1f}%"},
    "restart_bar_title": {LANG_EN: "Restart bar", LANG_ES: "Reiniciar barra"},
    "restart_bar_confirm": {LANG_EN: "The bar will restart to apply changes. Continue?", LANG_ES: "Se reiniciara la barra para aplicar cambios. Continuar?"},
    "interval_prompt": {LANG_EN: "Seconds between updates (minimum 5):", LANG_ES: "Segundos entre actualizaciones (minimo 5):"},
    "interval_updated": {LANG_EN: "Interval updated to {value}s", LANG_ES: "Intervalo actualizado a {value}s"},
    "opacity_prompt": {LANG_EN: "Bar opacity (0.35 to 1.0):", LANG_ES: "Opacidad de la barra (0.35 a 1.0):"},
    "fixed_width": {LANG_EN: "Fixed width", LANG_ES: "Ancho fijo"},
    "fixed_width_prompt": {LANG_EN: "Window width in pixels (minimum 380):", LANG_ES: "Ancho de ventana en pixeles (minimo 380):"},
    "autostart": {LANG_EN: "Autostart", LANG_ES: "Autoarranque"},
    "autostart_update_error": {LANG_EN: "Could not update: {error}", LANG_ES: "No se pudo actualizar: {error}"},
    "autostart_enabled": {LANG_EN: "enabled", LANG_ES: "activado"},
    "autostart_disabled": {LANG_EN: "disabled", LANG_ES: "desactivado"},
    "autostart_status": {LANG_EN: "Autostart {state}.", LANG_ES: "Autoarranque {state}."},
    "accounts_configured": {LANG_EN: "Configured accounts", LANG_ES: "Cuentas configuradas"},
    "main_account": {LANG_EN: "Main: {path}", LANG_ES: "Principal: {path}"},
    "extra_none": {LANG_EN: "Extras: (none)", LANG_ES: "Extras: (ninguna)"},
    "extras": {LANG_EN: "Extras:", LANG_ES: "Extras:"},
    "add_account_title": {LANG_EN: "Add account", LANG_ES: "Agregar cuenta"},
    "add_account_prompt": {LANG_EN: "Account alias (e.g., account2):", LANG_ES: "Alias de la cuenta (ej: cuenta2):"},
    "account_added": {LANG_EN: "Account added", LANG_ES: "Cuenta agregada"},
    "account_added_msg": {LANG_EN: "Account added to config. Restart the bar to see it in multi-account mode.", LANG_ES: "Cuenta agregada en configuracion. Reinicia la barra para verla en modo multi-cuenta."},
    "add_account_error": {LANG_EN: "Could not add account: {error}", LANG_ES: "No se pudo agregar la cuenta: {error}"},
    "remove_account_title": {LANG_EN: "Remove account", LANG_ES: "Quitar cuenta"},
    "remove_no_extra": {LANG_EN: "No extra accounts configured.", LANG_ES: "No hay cuentas extra configuradas."},
    "remove_account_prompt": {LANG_EN: "Alias or path of extra account to remove:", LANG_ES: "Alias o ruta de la cuenta extra a quitar:"},
    "remove_not_found": {LANG_EN: "That extra account was not found.", LANG_ES: "No se encontro esa cuenta extra."},
    "remove_delete_file": {LANG_EN: "Also delete the .json session file?", LANG_ES: "Tambien borrar el archivo de sesion .json?"},
    "remove_failed": {LANG_EN: "Could not remove account.", LANG_ES: "No se pudo quitar la cuenta."},
    "remove_delete_failed": {LANG_EN: "Removed from config, but could not delete .json: {error}", LANG_ES: "Se quito de config, pero no se pudo borrar .json: {error}"},
    "remove_success": {LANG_EN: "Account removed from config. Restart the bar to apply in the view.", LANG_ES: "Cuenta quitada de configuracion. Reinicia la barra para aplicar el cambio en la vista."},
}

try:
    import winreg
except Exception:
    winreg = None


@dataclass
class UsageSnapshot:
    usage_percent: float
    usage_label: str
    plan_status: str
    reset_note: str
    account_label: str
    fetched_at: dt.datetime


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GitHub Copilot usage monitor (Premium requests)."
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Start floating visual UI (recommended).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Seconds between updates.",
    )
    parser.add_argument(
        "--opacity",
        type=float,
        default=None,
        help="Bar opacity between 0.35 and 1.0.",
    )
    parser.add_argument(
        "--mini",
        action="store_true",
        help="Enable mini mode (narrow bar).",
    )
    parser.add_argument(
        "--normal",
        action="store_true",
        help="Force normal mode (disable mini).",
    )
    parser.add_argument(
        "--dock-top",
        action="store_true",
        help="Dock the bar to the top edge.",
    )
    parser.add_argument(
        "--free-dock",
        action="store_true",
        help="Disable top docking.",
    )
    parser.add_argument(
        "--auto-width",
        action="store_true",
        help="Auto-adjust width based on content.",
    )
    parser.add_argument(
        "--fixed-width",
        action="store_true",
        help="Disable auto width.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Base bar width in pixels.",
    )
    parser.add_argument(
        "--always-on-top",
        action="store_true",
        help="Keep bar always on top.",
    )
    parser.add_argument(
        "--not-always-on-top",
        action="store_true",
        help="Disable always-on-top mode.",
    )
    parser.add_argument(
        "--taskbar-compact",
        action="store_true",
        help="Start in compact taskbar mode 150x30 (bar + percentage only).",
    )
    parser.add_argument(
        "--no-taskbar-compact",
        action="store_true",
        help="Disable compact taskbar mode.",
    )
    parser.add_argument(
        "--taskbar-compact-70",
        action="store_true",
        help="Use compact mini taskbar variant (70px width).",
    )
    parser.add_argument(
        "--taskbar-compact-150",
        action="store_true",
        help="Use compact normal taskbar variant (150px width).",
    )
    parser.add_argument(
        "--taskbar-compact-100",
        action="store_true",
        help="Use compact medium taskbar variant (100px width).",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help="Session file to avoid logging in every run.",
    )
    parser.add_argument(
        "--extra-state-files",
        type=str,
        default=None,
        help="Semicolon-separated list of extra session files for multi-account.",
    )
    parser.add_argument(
        "--add-account",
        type=str,
        default=None,
        help="Add extra account (alias) and save session to .auth/<alias>.json.",
    )
    parser.add_argument(
        "--list-accounts",
        action="store_true",
        help="List configured accounts/sessions.",
    )
    parser.add_argument(
        "--remove-account",
        type=str,
        default=None,
        help="Remove an extra account (alias or path) from config.",
    )
    parser.add_argument(
        "--delete-state-file",
        action="store_true",
        help="With --remove-account, also delete the .json session file.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="INI configuration file.",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Force interactive login and save a new session.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run monitoring without a visible browser window.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit.",
    )
    return parser.parse_args()


def str_to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "si", "on"}


def ensure_config_file(config_path: Path) -> None:
    if config_path.exists():
        return

    default_content = """[app]
interval_seconds = 60
mini_mode = false
opacity = 0.92
auto_width = true
dock_top = false
window_width = 520
always_on_top = true
taskbar_compact_mode = false
taskbar_compact_width = 150
theme = dark
language = en
extra_state_files =

[windows]
auto_start_enabled = false
"""
    config_path.write_text(default_content, encoding="utf-8")


def load_config(config_path: Path) -> dict[str, str]:
    ensure_config_file(config_path)
    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")

    app = parser["app"] if "app" in parser else {}
    windows = parser["windows"] if "windows" in parser else {}

    return {
        "interval_seconds": str(app.get("interval_seconds", "60")),
        "mini_mode": str(app.get("mini_mode", "false")),
        "opacity": str(app.get("opacity", "0.92")),
        "auto_width": str(app.get("auto_width", "true")),
        "dock_top": str(app.get("dock_top", "false")),
        "window_width": str(app.get("window_width", "520")),
        "always_on_top": str(app.get("always_on_top", "true")),
        "taskbar_compact_mode": str(app.get("taskbar_compact_mode", "false")),
        "taskbar_compact_width": str(app.get("taskbar_compact_width", "150")),
        "theme": str(app.get("theme", THEME_DARK)),
        "language": str(app.get("language", LANG_EN)),
        "extra_state_files": str(app.get("extra_state_files", "")),
        "auto_start_enabled": str(windows.get("auto_start_enabled", "false")),
    }


def update_config_values(
    config_path: Path,
    app_updates: dict[str, str] | None = None,
    windows_updates: dict[str, str] | None = None,
) -> None:
    ensure_config_file(config_path)
    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")

    if "app" not in parser:
        parser["app"] = {}
    if "windows" not in parser:
        parser["windows"] = {}

    if app_updates:
        for key, value in app_updates.items():
            parser["app"][key] = value

    if windows_updates:
        for key, value in windows_updates.items():
            parser["windows"][key] = value

    with config_path.open("w", encoding="utf-8") as fh:
        parser.write(fh)


def build_autostart_command() -> str:
    launcher_bat = Path("iniciar_monitor_github.bat").resolve()
    if launcher_bat.exists():
        return f'"{launcher_bat}"'

    script_path = Path(__file__).resolve()
    return f'"{sys.executable}" "{script_path}" --gui --headless'


def is_windows_autostart_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ) as key:
            _value, _value_type = winreg.QueryValueEx(key, AUTOSTART_REG_NAME)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_windows_autostart(enabled: bool) -> tuple[bool, str]:
    if winreg is None:
        return False, "Autostart is not available on this system."

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(key, AUTOSTART_REG_NAME, 0, winreg.REG_SZ, build_autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, AUTOSTART_REG_NAME)
                except FileNotFoundError:
                    pass
        return True, "OK"
    except OSError as exc:
        return False, str(exc)


def normalize_taskbar_width(value: int) -> int:
    if value <= 85:
        return 70
    if value <= 125:
        return 100
    return 150


def normalize_theme(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if raw in THEME_PALETTES:
        return raw
    return THEME_DARK


def normalize_language(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if raw in {LANG_EN, LANG_ES}:
        return raw
    return LANG_EN


def parse_state_file_list(raw_value: str | None) -> list[Path]:
    if not raw_value:
        return []
    parts = [part.strip() for part in raw_value.split(";") if part.strip()]
    return [Path(part) for part in parts]


def stringify_state_file_list(paths: list[Path]) -> str:
    return ";".join(str(path).replace("/", "\\") for path in paths)


def sanitize_account_alias(alias: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", alias.strip())
    return sanitized or "account"


def upsert_extra_state_file(config_path: Path, new_state_file: Path) -> None:
    ensure_config_file(config_path)
    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")
    if "app" not in parser:
        parser["app"] = {}

    existing = parse_state_file_list(parser["app"].get("extra_state_files", ""))
    existing_keys = {str(path).lower() for path in existing}
    key = str(new_state_file).lower()
    if key not in existing_keys:
        existing.append(new_state_file)
    parser["app"]["extra_state_files"] = stringify_state_file_list(existing)

    with config_path.open("w", encoding="utf-8") as fh:
        parser.write(fh)


def remove_extra_state_file(config_path: Path, target_state_file: Path) -> bool:
    ensure_config_file(config_path)
    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")
    if "app" not in parser:
        parser["app"] = {}

    existing = parse_state_file_list(parser["app"].get("extra_state_files", ""))
    target_key = str(target_state_file).replace("/", "\\").lower()
    filtered = [
        path
        for path in existing
        if str(path).replace("/", "\\").lower() != target_key
    ]

    if len(filtered) == len(existing):
        return False

    parser["app"]["extra_state_files"] = stringify_state_file_list(filtered)
    with config_path.open("w", encoding="utf-8") as fh:
        parser.write(fh)
    return True


def resolve_remove_target(extra_state_files: list[Path], alias_or_path: str) -> Path | None:
    raw_value = alias_or_path.strip()
    if not raw_value:
        return None

    raw_lower = raw_value.lower()
    sanitized = sanitize_account_alias(raw_value).lower()
    path_like_lower = str(Path(raw_value)).replace("/", "\\").lower()
    alias_path = str((Path(".auth") / f"{sanitize_account_alias(raw_value)}.json")).replace("/", "\\").lower()

    candidates = {
        raw_lower,
        sanitized,
        f"{sanitized}.json",
        path_like_lower,
        alias_path,
    }

    for item in extra_state_files:
        item_path = str(item).replace("/", "\\").lower()
        if item_path in candidates:
            return item

        item_name = item.name.lower()
        item_stem = item.stem.lower()
        if item_name in candidates or item_stem in candidates:
            return item

    return None


def try_get_account_from_state(state_path: Path) -> str:
    if not state_path.exists():
        return ""
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        origins = data.get("origins", [])
        for origin in origins:
            local_storage = origin.get("localStorage", [])
            for item in local_storage:
                if item.get("name") == "user-login":
                    return item.get("value", "")
    except Exception:
        return ""
    return ""


def run_account_assistant(args: argparse.Namespace) -> int | None:
    if args.delete_state_file and not args.remove_account:
        print("\n--delete-state-file requires --remove-account.")
        return 1

    if args.add_account:
        alias = sanitize_account_alias(args.add_account)
        target_state = Path(".auth") / f"{alias}.json"
        print(f"\nMulti-account assistant: {alias}")
        ensure_login_state(target_state)
        upsert_extra_state_file(args.config, target_state)
        account_login = try_get_account_from_state(target_state)
        if account_login:
            print(f"Account added: @{account_login}")
        print(f"Session saved to: {target_state}")
        print("Configuration updated in monitor_config.ini")
        return 0

    if args.remove_account:
        config = load_config(args.config)
        extra = parse_state_file_list(config.get("extra_state_files", ""))
        if not extra:
            print("\nNo extra accounts configured to remove.")
            return 1

        target = resolve_remove_target(extra, args.remove_account)
        if target is None:
            print(f"\nExtra account not found: {args.remove_account}")
            print("Current extras:")
            for item in extra:
                print(f"- {item}")
            return 1

        removed = remove_extra_state_file(args.config, target)
        if not removed:
            print(f"\nCould not remove account: {target}")
            return 1

        login = try_get_account_from_state(target)
        suffix = f" (@{login})" if login else ""
        print(f"\nExtra account removed: {target}{suffix}")

        if args.delete_state_file:
            try:
                if target.exists():
                    target.unlink()
                    print("Session file deleted as well.")
                else:
                    print("Session file no longer existed on disk.")
            except OSError as exc:
                print(f"Could not delete session file: {exc}")
                return 1
        else:
            print("Removed from config only. Session file was not deleted.")
        return 0

    if args.list_accounts:
        config = load_config(args.config)
        extra = parse_state_file_list(config.get("extra_state_files", ""))
        print("\nConfigured accounts:")
        print(f"- Main: {args.state_file}")
        if not extra:
            print("- Extras: (none)")
        else:
            for item in extra:
                login = try_get_account_from_state(item)
                suffix = f" (@{login})" if login else ""
                print(f"- Extra: {item}{suffix}")
        return 0

    return None


def resolve_settings(args: argparse.Namespace) -> tuple[int, bool, float, bool, bool, int, bool, bool, int, str, str, list[Path]]:
    config = load_config(args.config)

    interval = args.interval
    if interval is None:
        interval = int(config["interval_seconds"])

    mini_mode = str_to_bool(config["mini_mode"], default=False)
    if args.mini:
        mini_mode = True
    if args.normal:
        mini_mode = False

    opacity = args.opacity
    if opacity is None:
        opacity = float(config["opacity"])
    opacity = max(0.35, min(1.0, opacity))

    auto_width = str_to_bool(config["auto_width"], default=True)
    if args.auto_width:
        auto_width = True
    if args.fixed_width:
        auto_width = False

    dock_top = str_to_bool(config["dock_top"], default=False)
    if args.dock_top:
        dock_top = True
    if args.free_dock:
        dock_top = False

    window_width = args.width
    if window_width is None:
        window_width = int(config["window_width"])

    always_on_top = str_to_bool(config["always_on_top"], default=True)
    if args.always_on_top:
        always_on_top = True
    if args.not_always_on_top:
        always_on_top = False

    taskbar_compact_mode = str_to_bool(config["taskbar_compact_mode"], default=False)
    if args.taskbar_compact:
        taskbar_compact_mode = True
    if args.no_taskbar_compact:
        taskbar_compact_mode = False

    taskbar_compact_width = normalize_taskbar_width(int(config["taskbar_compact_width"]))
    if args.taskbar_compact_70:
        taskbar_compact_width = 70
    if args.taskbar_compact_100:
        taskbar_compact_width = 100
    if args.taskbar_compact_150:
        taskbar_compact_width = 150

    theme = normalize_theme(config.get("theme", THEME_DARK))
    language = normalize_language(config.get("language", LANG_EN))

    extra_state_files = parse_state_file_list(config["extra_state_files"])
    if args.extra_state_files is not None:
        extra_state_files = parse_state_file_list(args.extra_state_files)

    return (
        max(5, int(interval)),
        mini_mode,
        opacity,
        auto_width,
        dock_top,
        max(380, int(window_width)),
        always_on_top,
        taskbar_compact_mode,
        taskbar_compact_width,
        theme,
        language,
        extra_state_files,
    )


def normalize_decimal(value: str) -> float:
    cleaned = value.strip().replace(",", ".")
    return float(cleaned)


def log_single_instance_event(message: str) -> None:
    try:
        if SINGLE_INSTANCE_LOG_FILE.exists() and SINGLE_INSTANCE_LOG_FILE.stat().st_size > SINGLE_INSTANCE_LOG_MAX_BYTES:
            lines = SINGLE_INSTANCE_LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
            tail = lines[-SINGLE_INSTANCE_LOG_KEEP_LINES:]
            SINGLE_INSTANCE_LOG_FILE.write_text("\n".join(tail) + "\n", encoding="utf-8")

        timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with SINGLE_INSTANCE_LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"[{timestamp}] {message}\n")
    except Exception:
        # El log nunca debe romper la app.
        pass


def log_runtime_event(message: str) -> None:
    try:
        if RUNTIME_LOG_FILE.exists() and RUNTIME_LOG_FILE.stat().st_size > RUNTIME_LOG_MAX_BYTES:
            lines = RUNTIME_LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
            tail = lines[-RUNTIME_LOG_KEEP_LINES:]
            RUNTIME_LOG_FILE.write_text("\n".join(tail) + "\n", encoding="utf-8")

        timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with RUNTIME_LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"[{timestamp}] {message}\n")
    except Exception:
        # El log nunca debe romper la app.
        pass


def try_signal_existing_instance() -> bool:
    try:
        with socket.create_connection((SINGLE_INSTANCE_HOST, SINGLE_INSTANCE_PORT), timeout=0.4) as conn:
            conn.sendall(b"SHOW")
        log_single_instance_event("SHOW enviado a instancia existente")
        return True
    except OSError:
        log_single_instance_event("Could not send SHOW (no listening instance)")
        return False


def create_single_instance_server() -> socket.socket | None:
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((SINGLE_INSTANCE_HOST, SINGLE_INSTANCE_PORT))
        server.listen(5)
        server.setblocking(False)
        log_single_instance_event("Servidor de instancia unica iniciado")
        return server
    except OSError:
        log_single_instance_event("Could not start single-instance server")
        return None


def extract_usage_percent(main_text: str) -> tuple[float, str]:
    lines = [line.strip() for line in main_text.splitlines() if line.strip()]

    keyword_patterns = (
        "premium requests",
        "solicitudes premium",
        "solicitudes prem",
    )

    for index, line in enumerate(lines):
        lowered = line.lower()
        if any(keyword in lowered for keyword in keyword_patterns):
            window = " ".join(lines[index : index + 6])
            match = re.search(r"(\d+(?:[\.,]\d+)?)\s*%", window)
            if match:
                value = normalize_decimal(match.group(1))
                return value, f"{value:.1f}%"

    fallback = re.search(r"(\d+(?:[\.,]\d+)?)\s*%", main_text)
    if fallback:
        value = normalize_decimal(fallback.group(1))
        return value, f"{value:.1f}%"

    raise ValueError("Could not find usage percentage in the page.")


def extract_plan_status(main_text: str) -> str:
    patterns = (
        r"(Copilot\s+Pro\+?\s+is\s+active\s+for\s+your\s+account)",
        r"(Copilot\s+Pro\+?\s+is\s+inactive[\w\s,.!-]*)",
        r"(Copilot\s+Pro\+?.{0,60}activo.{0,40}cuenta)",
    )
    for pattern in patterns:
        match = re.search(pattern, main_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "Estado del plan no detectado"


def extract_reset_note(main_text: str) -> str:
    patterns = (
        r"(premium request entitlement for your plan will reset at the start of next month\.)",
        r"(la asignacion de solicitudes premium de tu plan se restablecera al comienzo del proximo mes\.)",
    )
    for pattern in patterns:
        match = re.search(pattern, main_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "Monthly reset note not detected"


def extract_account_label(main_text: str, page_html: str) -> str:
    # Meta presente en paginas autenticadas de GitHub.
    meta_match = re.search(
        r'<meta\s+name="octolytics-actor-login"\s+content="([^"]+)"',
        page_html,
        flags=re.IGNORECASE,
    )
    if meta_match:
        return "@" + meta_match.group(1).strip()

    # Fallback simple sobre texto visible.
    text_match = re.search(r"\b([a-zA-Z0-9-]{2,39})\s*\(([a-zA-Z0-9-]{2,39})\)", main_text)
    if text_match:
        return "@" + text_match.group(1).strip()

    return "@unknown-account"


def progress_bar(percent: float, width: int = 32) -> str:
    clipped = max(0.0, min(100.0, percent))
    filled = int(round((clipped / 100.0) * width))
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def month_metrics(current_usage_percent: float) -> tuple[float, float, float]:
    now = dt.datetime.now()
    total_days = calendar.monthrange(now.year, now.month)[1]
    elapsed_percent = (now.day / total_days) * 100.0
    pace_ratio = current_usage_percent / elapsed_percent if elapsed_percent else 0.0
    projected_end_month = min(999.0, pace_ratio * 100.0)
    return elapsed_percent, pace_ratio, projected_end_month


def quality_color(percent: float) -> str:
    if percent < 40:
        return "#12b886"
    if percent < 75:
        return "#f08c00"
    return "#e03131"


def read_snapshot(page) -> UsageSnapshot:
    page.goto(GITHUB_FEATURES_URL, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(1200)

    text = page.locator("main").inner_text()
    html = page.content()
    if not text.strip():
        text = html

    login_markers = (
        "Sign in to GitHub",
        "Inicia sesion en GitHub",
    )
    if any(marker.lower() in text.lower() for marker in login_markers):
        raise PermissionError("Invalid session. Run with --login to authenticate.")

    usage_percent, usage_label = extract_usage_percent(text)

    return UsageSnapshot(
        usage_percent=usage_percent,
        usage_label=usage_label,
        plan_status=extract_plan_status(text),
        reset_note=extract_reset_note(text),
        account_label=extract_account_label(text, html),
        fetched_at=dt.datetime.now(),
    )


def print_snapshot(snapshot: UsageSnapshot) -> None:
    elapsed_percent, pace_ratio, projected_end_month = month_metrics(snapshot.usage_percent)

    print("\n" + "=" * 72)
    print(f"Updated: {snapshot.fetched_at:%Y-%m-%d %H:%M:%S}")
    print(f"Premium monthly usage: {snapshot.usage_label}")
    print(progress_bar(snapshot.usage_percent), snapshot.usage_label)
    print(f"Month pace: {pace_ratio:.2f}x of linear pace")
    print(f"Month elapsed: {elapsed_percent:.1f}%")
    print(f"Projected month-end (if pace holds): {projected_end_month:.1f}%")
    print(f"Plan: {snapshot.plan_status}")
    print(f"Note: {snapshot.reset_note}")
    print("=" * 72)


def ensure_login_state(state_file: Path) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(GITHUB_FEATURES_URL, wait_until="domcontentloaded", timeout=45000)

        print("\nInteractive login required.")
        print("1) Complete login/2FA in the browser window.")
        print("2) Once Copilot Features opens, session state is saved automatically.")
        print("3) Keep this window open until you see the saved-session message.")

        deadline = dt.datetime.now() + dt.timedelta(minutes=10)
        while dt.datetime.now() < deadline:
            page.wait_for_timeout(1200)
            try:
                text = page.locator("main").inner_text().lower()
            except Exception:
                text = page.content().lower()

            if "premium requests" in text or "solicitudes premium" in text:
                context.storage_state(path=str(state_file))
                print("Session saved successfully.")
                browser.close()
                return

        browser.close()
        raise TimeoutError(
            "Copilot Features page was not detected within the expected time."
        )


class CopilotUsageClient:
    def __init__(self, state_file: Path, headless: bool = True) -> None:
        self.state_file = state_file
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    def start(self) -> None:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(storage_state=str(self.state_file))
        self._page = self._context.new_page()

    def fetch_snapshot(self) -> UsageSnapshot:
        if self._page is None:
            raise RuntimeError("Client not initialized.")
        return read_snapshot(self._page)

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None


class Tooltip:
    def __init__(
        self,
        widget,
        text: str,
        delay_ms: int = 350,
        bg: str = "#1f2430",
        fg: str = "#dfe7ef",
        border: str = "#3a4654",
    ) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.bg = bg
        self.fg = fg
        self.border = border
        self.tip_window = None
        self.after_id = None
        widget.bind("<Enter>", self.on_enter, add="+")
        widget.bind("<Leave>", self.on_leave, add="+")

    def set_colors(self, bg: str, fg: str, border: str) -> None:
        self.bg = bg
        self.fg = fg
        self.border = border

    def set_text(self, text: str) -> None:
        self.text = text

    def on_enter(self, _event) -> None:
        self.after_id = self.widget.after(self.delay_ms, self.show)

    def on_leave(self, _event) -> None:
        if self.after_id is not None:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        self.hide()

    def show(self) -> None:
        if self.tip_window is not None:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-topmost", True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            bg=self.bg,
            fg=self.fg,
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=self.border,
            padx=6,
            pady=4,
            font=("Segoe UI", 8),
        )
        label.pack()

    def hide(self) -> None:
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


class FloatingBarApp:
    def __init__(
        self,
        state_files: list[Path],
        interval_s: int,
        mini_mode: bool,
        opacity: float,
        auto_width: bool,
        dock_top: bool,
        window_width: int,
        always_on_top: bool,
        taskbar_compact_mode: bool,
        taskbar_compact_width: int,
        theme: str,
        language: str,
        single_instance_server: socket.socket | None,
        config_path: Path,
    ) -> None:
        self.state_files = state_files
        self.primary_state_file = state_files[0]
        self.multi_mode = len(state_files) > 1
        self.interval_s = max(5, interval_s)
        self.mini_mode = mini_mode
        self.opacity = max(0.35, min(1.0, opacity))
        self.auto_width = auto_width
        self.dock_top = dock_top
        self.window_width = max(380, window_width)
        self.normal_window_width = self.window_width
        self.always_on_top = always_on_top
        self.taskbar_compact_mode = taskbar_compact_mode
        self.taskbar_compact_width = normalize_taskbar_width(taskbar_compact_width)
        self.theme = normalize_theme(theme)
        self.language = normalize_language(language)
        self.theme_colors = THEME_PALETTES[self.theme]
        self.single_instance_server = single_instance_server
        self.config_path = config_path
        self.closed = False
        self.is_hidden_to_tray = False
        self.tray_icon = None
        self.current_percent = 0.0
        self.current_bar_label = "--.-%"
        self.current_fill_color = "#12b886"
        self.current_metrics_label = self.tr("loading")
        self.last_non_compact_geometry = None
        self.restore_geometry: tuple[int, int, int] | None = None
        self.last_normal_x = 60
        self.last_normal_y = 60
        self.compact_refresh_visible = False
        self.compact_active_index = 0
        self.multi_rows: list[dict] = []
        self.tooltips: list[Tooltip] = []

        self.clients = [CopilotUsageClient(state_file=sf, headless=True) for sf in state_files]

        self.root = tk.Tk()
        self.theme_var = tk.StringVar(value=self.theme)
        self.language_var = tk.StringVar(value=self.language)
        self.root.title("Copilot Usage Bar")
        self.window_height = 60
        self.root.geometry(f"{self.window_width}x{self.window_height}+60+60")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", self.always_on_top)
        self.root.attributes("-alpha", self.opacity)
        self.root.configure(bg="#101113")

        self._drag_origin_x = 0
        self._drag_origin_y = 0

        container = tk.Frame(self.root, bg="#101113", highlightthickness=1, highlightbackground="#2b2f36")
        container.pack(fill="both", expand=True, padx=2, pady=(0, 2))
        self.container_frame = container

        header = tk.Frame(container, bg="#101113")
        header.pack(fill="x", padx=8, pady=(0, 0))
        self.header_frame = header
        header.grid_columnconfigure(1, weight=1)

        self.menu_button = tk.Label(
            header,
            text="≡",
            fg="#9fb3c8",
            bg="#101113",
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            padx=2,
            pady=0,
        )
        self.menu_button.place(x=0, y=0, anchor="nw")
        self.menu_button.lift()
        self.menu_button.bind("<Button-1>", self.open_menu_button)

        self.title_container = tk.Frame(header, bg="#101113")
        self.title_container.grid(row=0, column=0, sticky="w", pady=(12, 0))

        self.title_label = tk.Label(
            self.title_container,
            text="GitHub Copilot Monitor",
            fg="#e9ecef",
            bg="#101113",
            font=("Segoe UI", 8 if self.mini_mode else 9, "bold"),
        )
        self.title_label.pack(side="left")

        self.title_version_label = tk.Label(
            self.title_container,
            text=APP_VERSION,
            fg="#8ea0b5",
            bg="#101113",
            font=("Segoe UI", 6 if self.mini_mode else 7),
        )
        self.title_version_label.pack(side="left", padx=(6, 0), pady=(1, 0))

        self.metrics_label = tk.Label(
            header,
            text=f" | {self.tr('loading')}",
            fg="#9fb3c8",
            bg="#101113",
            font=("Segoe UI", 7 if self.mini_mode else 8),
            anchor="w",
        )
        self.metrics_label.grid(row=0, column=1, sticky="we", padx=(6, 0), pady=(12, 0))

        self.time_label = tk.Label(
            header,
            text="--:--:--",
            fg="#dfe7ef",
            bg="#101113",
            font=("Segoe UI", 7 if self.mini_mode else 8, "bold"),
            anchor="e",
        )
        self.time_label.grid(row=0, column=2, sticky="e", padx=(6, 8), pady=(12, 0))

        right_header = tk.Frame(header, bg="#101113")
        right_header.grid(row=0, column=3, sticky="ne", padx=(0, 0), pady=(12, 0))
        self.right_header = right_header

        dot_row = tk.Frame(header, bg="#101113")
        dot_row.place(relx=1.0, x=2, y=0, anchor="ne")
        dot_row.lift()
        self.dot_row = dot_row

        lower_row = tk.Frame(right_header, bg="#101113")
        lower_row.pack(side="top", anchor="e", pady=(0, 0))
        self.lower_row = lower_row

        self.percent_label = tk.Label(
            lower_row,
            text="--.-%",
            fg="#e9ecef",
            bg="#101113",
            font=("Segoe UI Black", 11 if self.mini_mode else 13),
        )
        self.percent_label.pack(side="left", padx=(0, 1), pady=(0, 0))

        self.tray_button = tk.Label(
            dot_row,
            text="●",
            fg="#ff922b",
            bg="#101113",
            font=("Segoe UI", 8, "bold"),
            pady=0,
            cursor="hand2",
        )
        self.tray_button.pack(side="left", padx=(0, 2))
        self.tray_button.bind("<Button-1>", lambda _event: self.minimize_to_tray())

        self.taskbar_button = tk.Label(
            dot_row,
            text="●",
            fg="#66d9ff",
            bg="#101113",
            font=("Segoe UI", 8, "bold"),
            pady=0,
            cursor="hand2",
        )
        self.taskbar_button.pack(side="left", padx=(0, 2))
        self.taskbar_button.bind(
            "<Button-1>",
            lambda _event: self.set_taskbar_compact_mode(True) if not self.taskbar_compact_mode else None,
        )

        self.close_button = tk.Label(
            dot_row,
            text="●",
            fg="#ff5d5d",
            bg="#101113",
            font=("Segoe UI", 8, "bold"),
            pady=0,
            cursor="hand2",
        )
        self.close_button.pack(side="left", padx=(0, 0))
        self.close_button.bind("<Button-1>", lambda _event: self.close(reason="close_button"))

        self.refresh_button = tk.Label(
            lower_row,
            text="↻",
            fg="#8bd3ff",
            bg="#101113",
            font=("Segoe UI", 8, "bold"),
            pady=0,
            cursor="hand2",
        )
        self.refresh_button.pack(side="left", padx=(1, 0), pady=(0, 0))
        self.refresh_button.bind("<Button-1>", lambda _event: self.refresh_now())

        self.canvas = tk.Canvas(container, height=14 if self.mini_mode else 16, bg="#101113", highlightthickness=0)
        self.canvas.pack(fill="x", padx=8, pady=(0, 2))
        self.track = self.canvas.create_rectangle(0, 0, 0, 0, fill="#2b2f36", outline="")
        self.fill = self.canvas.create_rectangle(0, 0, 0, 0, fill="#12b886", outline="")
        self.bar_text = self.canvas.create_text(
            0,
            0,
            text="--.-%",
            fill="#dfe7ef",
            font=("Segoe UI", 7 if self.mini_mode else 8, "bold"),
        )
        self.compact_refresh_icon = self.canvas.create_text(
            0,
            0,
            text="↻",
            fill="#8bd3ff",
            font=("Segoe UI", 8, "bold"),
            state="hidden",
        )

        self.rows_container = tk.Frame(container, bg="#101113")
        if self.multi_mode:
            self.canvas.pack_forget()
            self.rows_container.pack(fill="x", padx=8, pady=(2, 4))
            self.build_multi_rows()
            self.window_height = 34 + (len(self.multi_rows) * 26)

        for widget in (
            self.root,
            container,
            header,
            self.title_container,
            self.title_label,
            self.title_version_label,
            self.metrics_label,
            self.percent_label,
            self.canvas,
        ):
            widget.bind("<ButtonPress-1>", self.on_drag_start)
            widget.bind("<B1-Motion>", self.on_drag_move)
            widget.bind("<Double-Button-1>", self.on_double_click)

        self.root.bind("<Escape>", self.on_escape_key)
        self.root.report_callback_exception = self.on_tk_callback_exception
        self.root.bind("<Button-3>", self.show_menu)
        self.root.bind("<Configure>", self.on_resize)
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.close(reason="wm_delete"))

        self.build_menus()
        self.build_tooltips()

        self.apply_theme()

        self.on_resize(None)
        if self.taskbar_compact_mode:
            self.set_taskbar_compact_mode(True, persist_config=False)
        self.apply_window_geometry(self.window_width)
        self.refresh_menu_state_labels()
        self.rebuild_settings_menu()
        self.root.bind("<Map>", self.on_map_restore)
        self.canvas.bind("<Button-1>", self.on_canvas_click, add="+")
        if self.single_instance_server is not None:
            self.root.after(250, self.poll_single_instance_signal)

    def refresh_menu_state_labels(self) -> None:
        state = "ON" if self.always_on_top else "OFF"
        self.menu_full.entryconfig(self.menu_always_on_top_index, label=self.tr("always_visible", state=state))

    def tr(self, key: str, **kwargs) -> str:
        translations = UI_TEXTS.get(key, {})
        text = translations.get(self.language) or translations.get(LANG_EN) or key
        if kwargs:
            return text.format(**kwargs)
        return text

    def build_menus(self) -> None:
        self.menu_full = tk.Menu(self.root, tearoff=0)
        self.menu_full.add_command(label=self.tr("update_now"), command=self.refresh_now)

        self.menu_minimize = tk.Menu(self.menu_full, tearoff=0)
        self.menu_minimize.add_command(label=self.tr("notif_area"), command=self.minimize_to_tray)
        self.menu_minimize.add_separator()
        self.menu_minimize.add_command(label="Taskbar 70px", command=lambda: self.activate_taskbar_compact_width(70))
        self.menu_minimize.add_command(label="Taskbar 100px", command=lambda: self.activate_taskbar_compact_width(100))
        self.menu_minimize.add_command(label="Taskbar 150px", command=lambda: self.activate_taskbar_compact_width(150))
        self.menu_full.add_cascade(label=self.tr("minimize"), menu=self.menu_minimize)

        self.menu_always_on_top_index = self.menu_full.index("end") + 1
        self.menu_full.add_command(label=self.tr("always_visible", state="ON"), command=self.toggle_always_on_top)
        self.menu_full.add_command(label=self.tr("toggle_dock_top"), command=self.toggle_dock_top)
        self.menu_settings = tk.Menu(self.menu_full, tearoff=0)
        self.menu_full.add_cascade(label=self.tr("settings"), menu=self.menu_settings)
        self.menu_full.add_command(label=self.tr("logout"), command=self.relogin)
        self.menu_full.add_separator()
        self.menu_full.add_command(label=self.tr("exit"), command=lambda: self.close(reason="full_menu"))

        self.menu_taskbar = tk.Menu(self.root, tearoff=0)
        self.menu_taskbar.add_command(label=self.tr("restore"), command=self.restore_from_taskbar_compact)
        self.menu_taskbar.add_command(label=self.tr("switch_70"), command=lambda: self.activate_taskbar_compact_width(70))
        self.menu_taskbar.add_command(label=self.tr("switch_100"), command=lambda: self.activate_taskbar_compact_width(100))
        self.menu_taskbar.add_command(label=self.tr("switch_150"), command=lambda: self.activate_taskbar_compact_width(150))
        self.menu_taskbar.add_command(label=self.tr("exit"), command=lambda: self.close(reason="taskbar_menu"))

    def build_tooltips(self) -> None:
        self.tooltips = [
            Tooltip(self.tray_button, self.tr("tooltip_tray")),
            Tooltip(self.taskbar_button, self.tr("tooltip_taskbar")),
            Tooltip(self.refresh_button, self.tr("tooltip_refresh")),
            Tooltip(self.close_button, self.tr("tooltip_exit")),
            Tooltip(self.menu_button, self.tr("tooltip_menu")),
            Tooltip(self.percent_label, self.tr("tooltip_usage")),
            Tooltip(self.metrics_label, self.tr("tooltip_metrics")),
        ]

    def set_language(self, language: str) -> None:
        normalized = normalize_language(language)
        if normalized == self.language:
            return
        self.language = normalized
        self.language_var.set(self.language)
        self.build_menus()
        self.rebuild_settings_menu()
        self.refresh_menu_state_labels()

        tooltips = [
            self.tr("tooltip_tray"),
            self.tr("tooltip_taskbar"),
            self.tr("tooltip_refresh"),
            self.tr("tooltip_exit"),
            self.tr("tooltip_menu"),
            self.tr("tooltip_usage"),
            self.tr("tooltip_metrics"),
        ]
        for tip, text in zip(self.tooltips, tooltips):
            tip.set_text(text)

        self.persist_runtime_config()

    def apply_theme(self) -> None:
        self.theme_colors = THEME_PALETTES[self.theme]
        c = self.theme_colors

        self.root.configure(bg=c["bg"])
        self.container_frame.configure(bg=c["bg"], highlightbackground=c["border"])
        self.header_frame.configure(bg=c["bg"])
        self.title_container.configure(bg=c["bg"])
        self.right_header.configure(bg=c["bg"])
        self.dot_row.configure(bg=c["bg"])
        self.lower_row.configure(bg=c["bg"])
        self.rows_container.configure(bg=c["bg"])

        self.menu_button.configure(bg=c["bg"], fg=c["text_secondary"])
        self.title_label.configure(bg=c["bg"], fg=c["text_primary"])
        self.title_version_label.configure(bg=c["bg"], fg=c["text_muted"])
        self.metrics_label.configure(bg=c["bg"], fg=c["text_secondary"])
        self.time_label.configure(bg=c["bg"], fg=c["text_clock"])
        self.percent_label.configure(bg=c["bg"], fg=c["text_primary"])

        self.tray_button.configure(bg=c["bg"], fg=c["tray_dot"])
        self.taskbar_button.configure(bg=c["bg"], fg=c["taskbar_dot"])
        self.close_button.configure(bg=c["bg"], fg=c["close_dot"])
        self.refresh_button.configure(bg=c["bg"], fg=c["refresh"])

        self.canvas.configure(bg=c["bg"])
        self.canvas.itemconfig(self.track, fill=c["track"])
        self.canvas.itemconfig(self.bar_text, fill=c["bar_text"])
        self.canvas.itemconfig(self.compact_refresh_icon, fill=c["refresh"])

        if self.current_percent <= 0.0 and self.current_bar_label == self.tr("no_data"):
            self.current_fill_color = c["track"]

        for row in self.multi_rows:
            row["frame"].configure(bg=c["bg"])
            row["account_label"].configure(bg=c["bg"], fg=c["text_secondary"])
            if row.get("label") == "ERR":
                row["pct_label"].configure(bg=c["bg"], fg=c["error"])
            else:
                row["pct_label"].configure(bg=c["bg"])
            row["canvas"].configure(bg=c["bg"])
            row["canvas"].itemconfig(row["track"], fill=c["track"])
            row["canvas"].itemconfig(row["text"], fill=c["bar_text"])

        for tip in self.tooltips:
            tip.set_colors(c["tooltip_bg"], c["tooltip_fg"], c["tooltip_border"])

        if self.tray_icon is not None:
            try:
                self.tray_icon.icon = self.create_tray_image()
            except Exception:
                pass

        self.on_resize(None)

    def set_theme(self, theme: str) -> None:
        normalized = normalize_theme(theme)
        if normalized == self.theme:
            return
        self.theme = normalized
        self.apply_theme()
        self.persist_runtime_config()
        self.rebuild_settings_menu()

    def persist_runtime_config(self) -> None:
        config_snapshot = load_config(self.config_path)
        extra_files = parse_state_file_list(config_snapshot.get("extra_state_files", ""))
        update_config_values(
            self.config_path,
            app_updates={
                "interval_seconds": str(self.interval_s),
                "mini_mode": "true" if self.mini_mode else "false",
                "opacity": f"{self.opacity:.2f}",
                "auto_width": "true" if self.auto_width else "false",
                "dock_top": "true" if self.dock_top else "false",
                "window_width": str(self.normal_window_width),
                "always_on_top": "true" if self.always_on_top else "false",
                "taskbar_compact_mode": "true" if self.taskbar_compact_mode else "false",
                "taskbar_compact_width": str(self.taskbar_compact_width),
                "theme": self.theme,
                "language": self.language,
                "extra_state_files": stringify_state_file_list(extra_files),
            },
        )

    def rebuild_settings_menu(self) -> None:
        self.menu_settings.delete(0, "end")
        self.menu_settings.add_command(label=f"{self.tr('interval')} ({self.interval_s}s)...", command=self.configure_interval)
        self.menu_settings.add_command(label=f"{self.tr('opacity')} ({self.opacity:.2f})...", command=self.configure_opacity)

        language_menu = tk.Menu(self.menu_settings, tearoff=0)
        self.language_var.set(self.language)
        language_menu.add_radiobutton(
            label=self.tr("language_en"),
            value=LANG_EN,
            variable=self.language_var,
            command=lambda: self.set_language(LANG_EN),
        )
        language_menu.add_radiobutton(
            label=self.tr("language_es"),
            value=LANG_ES,
            variable=self.language_var,
            command=lambda: self.set_language(LANG_ES),
        )
        current_lang_label = self.tr("language_en") if self.language == LANG_EN else self.tr("language_es")
        self.menu_settings.add_cascade(label=f"{self.tr('language')}: {current_lang_label}", menu=language_menu)

        theme_menu = tk.Menu(self.menu_settings, tearoff=0)
        self.theme_var.set(self.theme)
        theme_menu.add_radiobutton(
            label=self.tr("theme_dark"),
            value=THEME_DARK,
            variable=self.theme_var,
            command=lambda: self.set_theme(THEME_DARK),
        )
        theme_menu.add_radiobutton(
            label=self.tr("theme_light"),
            value=THEME_LIGHT,
            variable=self.theme_var,
            command=lambda: self.set_theme(THEME_LIGHT),
        )
        self.menu_settings.add_cascade(
            label=f"{self.tr('theme')}: {self.tr('theme_light') if self.theme == THEME_LIGHT else self.tr('theme_dark')}",
            menu=theme_menu,
        )
        self.menu_settings.add_command(
            label=self.tr("autowidth_toggle", state=("ON" if self.auto_width else "OFF")),
            command=self.toggle_auto_width,
        )
        self.menu_settings.add_command(label=self.tr("set_fixed_width"), command=self.configure_fixed_width)
        self.menu_settings.add_separator()

        autostart_enabled = is_windows_autostart_enabled()
        self.menu_settings.add_command(
            label=self.tr("autostart_toggle", state=("ON" if autostart_enabled else "OFF")),
            command=self.toggle_windows_autostart,
        )
        self.menu_settings.add_separator()

        accounts_menu = tk.Menu(self.menu_settings, tearoff=0)
        accounts_menu.add_command(label=self.tr("list_accounts"), command=self.show_accounts_dialog)
        accounts_menu.add_command(label=self.tr("add_account"), command=self.add_account_dialog)
        accounts_menu.add_command(label=self.tr("remove_account"), command=self.remove_account_dialog)
        self.menu_settings.add_cascade(label=self.tr("accounts"), menu=accounts_menu)
        self.menu_settings.add_separator()
        self.menu_settings.add_command(label=self.tr("restart_now"), command=self.restart_bar_now)

    def restart_bar_now(self) -> None:
        if not messagebox.askyesno(
            self.tr("restart_bar_title"),
            self.tr("restart_bar_confirm"),
            parent=self.root,
        ):
            return

        script_path = Path(__file__).resolve()
        argv = [
            sys.executable,
            str(script_path),
            "--gui",
            "--headless",
            "--state-file",
            str(self.primary_state_file),
            "--config",
            str(self.config_path),
        ]

        self._stop_tray()
        if self.single_instance_server is not None:
            try:
                self.single_instance_server.close()
            except Exception:
                pass
            self.single_instance_server = None
        for client in self.clients:
            try:
                client.close()
            except Exception:
                pass

        self.closed = True
        try:
            self.root.destroy()
        except Exception:
            pass

        os.execv(sys.executable, argv)

    def configure_interval(self) -> None:
        value = simpledialog.askinteger(
            self.tr("interval"),
            self.tr("interval_prompt"),
            initialvalue=self.interval_s,
            minvalue=5,
            parent=self.root,
        )
        if value is None:
            return
        self.interval_s = max(5, int(value))
        self.persist_runtime_config()
        self.rebuild_settings_menu()
        self.metrics_label.config(text=f" | {self.tr('interval_updated', value=self.interval_s)}")

    def configure_opacity(self) -> None:
        value = simpledialog.askfloat(
            self.tr("opacity"),
            self.tr("opacity_prompt"),
            initialvalue=self.opacity,
            minvalue=0.35,
            maxvalue=1.0,
            parent=self.root,
        )
        if value is None:
            return
        self.opacity = max(0.35, min(1.0, float(value)))
        self.root.attributes("-alpha", self.opacity)
        self.persist_runtime_config()
        self.rebuild_settings_menu()

    def toggle_auto_width(self) -> None:
        self.auto_width = not self.auto_width
        if self.auto_width:
            self.update_width_for_content()
        self.persist_runtime_config()
        self.rebuild_settings_menu()

    def configure_fixed_width(self) -> None:
        value = simpledialog.askinteger(
            self.tr("fixed_width"),
            self.tr("fixed_width_prompt"),
            initialvalue=self.normal_window_width,
            minvalue=380,
            parent=self.root,
        )
        if value is None:
            return
        self.auto_width = False
        self.apply_window_geometry(max(380, int(value)))
        self.persist_runtime_config()
        self.rebuild_settings_menu()

    def toggle_windows_autostart(self) -> None:
        target = not is_windows_autostart_enabled()
        ok, error_message = set_windows_autostart(target)
        if not ok:
            messagebox.showerror(self.tr("autostart"), self.tr("autostart_update_error", error=error_message), parent=self.root)
            return

        update_config_values(
            self.config_path,
            windows_updates={"auto_start_enabled": "true" if target else "false"},
        )
        self.rebuild_settings_menu()
        state_label = self.tr("autostart_enabled") if target else self.tr("autostart_disabled")
        messagebox.showinfo(self.tr("autostart"), self.tr("autostart_status", state=state_label), parent=self.root)

    def show_accounts_dialog(self) -> None:
        config = load_config(self.config_path)
        extra = parse_state_file_list(config.get("extra_state_files", ""))
        lines = [self.tr("main_account", path=self.primary_state_file)]
        if not extra:
            lines.append(self.tr("extra_none"))
        else:
            lines.append(self.tr("extras"))
            for item in extra:
                login = try_get_account_from_state(item)
                suffix = f" (@{login})" if login else ""
                lines.append(f"- {item}{suffix}")
        messagebox.showinfo(self.tr("accounts_configured"), "\n".join(lines), parent=self.root)

    def add_account_dialog(self) -> None:
        alias_raw = simpledialog.askstring(
            self.tr("add_account_title"),
            self.tr("add_account_prompt"),
            parent=self.root,
        )
        if not alias_raw:
            return

        alias = sanitize_account_alias(alias_raw)
        target_state = Path(".auth") / f"{alias}.json"
        try:
            ensure_login_state(target_state)
            upsert_extra_state_file(self.config_path, target_state)
            messagebox.showinfo(
                self.tr("account_added"),
                self.tr("account_added_msg"),
                parent=self.root,
            )
        except Exception as exc:  # pylint: disable=broad-except
            messagebox.showerror(self.tr("add_account_title"), self.tr("add_account_error", error=exc), parent=self.root)

    def remove_account_dialog(self) -> None:
        config = load_config(self.config_path)
        extra = parse_state_file_list(config.get("extra_state_files", ""))
        if not extra:
            messagebox.showinfo(self.tr("remove_account_title"), self.tr("remove_no_extra"), parent=self.root)
            return

        alias_raw = simpledialog.askstring(
            self.tr("remove_account_title"),
            self.tr("remove_account_prompt"),
            parent=self.root,
        )
        if not alias_raw:
            return

        target = resolve_remove_target(extra, alias_raw)
        if target is None:
            messagebox.showerror(self.tr("remove_account_title"), self.tr("remove_not_found"), parent=self.root)
            return

        delete_file = messagebox.askyesno(
            self.tr("remove_account_title"),
            self.tr("remove_delete_file"),
            parent=self.root,
        )

        removed = remove_extra_state_file(self.config_path, target)
        if not removed:
            messagebox.showerror(self.tr("remove_account_title"), self.tr("remove_failed"), parent=self.root)
            return

        if delete_file and target.exists():
            try:
                target.unlink()
            except OSError as exc:
                messagebox.showerror(self.tr("remove_account_title"), self.tr("remove_delete_failed", error=exc), parent=self.root)
                return

        messagebox.showinfo(
            self.tr("remove_account_title"),
            self.tr("remove_success"),
            parent=self.root,
        )

    def on_drag_start(self, event: tk.Event) -> None:
        self._drag_origin_x = event.x_root - self.root.winfo_x()
        self._drag_origin_y = event.y_root - self.root.winfo_y()

    def build_multi_rows(self) -> None:
        self.multi_rows.clear()
        for index, _state_file in enumerate(self.state_files):
            row = tk.Frame(self.rows_container, bg="#101113")
            row.pack(fill="x", pady=(0, 3))

            account_label = tk.Label(
                row,
                text=self.tr("account_default", n=index + 1),
                fg="#9fb3c8",
                bg="#101113",
                font=("Segoe UI", 8),
                anchor="w",
            )
            account_label.pack(side="left")

            pct_label = tk.Label(
                row,
                text="--.-%",
                fg="#e9ecef",
                bg="#101113",
                font=("Segoe UI", 8, "bold"),
                anchor="e",
            )
            pct_label.pack(side="right")

            bar_canvas = tk.Canvas(row, height=10, bg="#101113", highlightthickness=0)
            bar_canvas.pack(fill="x", padx=(6, 6), pady=(1, 0))
            track = bar_canvas.create_rectangle(0, 0, 0, 0, fill="#2b2f36", outline="")
            fill = bar_canvas.create_rectangle(0, 0, 0, 0, fill="#12b886", outline="")
            text = bar_canvas.create_text(0, 0, text="--.-%", fill="#dfe7ef", font=("Segoe UI", 7, "bold"))

            self.multi_rows.append(
                {
                    "frame": row,
                    "account_label": account_label,
                    "pct_label": pct_label,
                    "canvas": bar_canvas,
                    "track": track,
                    "fill": fill,
                    "text": text,
                    "percent": 0.0,
                    "color": "#12b886",
                    "label": "--.-%",
                }
            )

    def on_drag_move(self, event: tk.Event) -> None:
        if self.taskbar_compact_mode:
            return
        x = event.x_root - self._drag_origin_x
        y = 0 if self.dock_top else event.y_root - self._drag_origin_y
        if not self.dock_top:
            self.last_normal_x = max(0, x)
            self.last_normal_y = max(0, y)
        self.root.geometry(f"+{x}+{y}")

    def on_resize(self, _event) -> None:
        w = max(80, self.canvas.winfo_width())
        h = max(12, self.canvas.winfo_height())
        self.canvas.coords(self.track, 0, 0, w, h)
        fill_w = int((max(0.0, min(100.0, self.current_percent)) / 100.0) * w)
        self.canvas.coords(self.fill, 0, 0, fill_w, h)
        self.canvas.itemconfig(self.fill, fill=self.current_fill_color)
        text_x = (w / 2) - (10 if self.compact_refresh_visible else 0)
        self.canvas.coords(self.bar_text, text_x, h / 2)
        self.canvas.itemconfig(self.bar_text, text=self.current_bar_label)
        self.canvas.coords(self.compact_refresh_icon, w - 10, h / 2)

        if self.multi_mode and not self.taskbar_compact_mode:
            for row in self.multi_rows:
                cw = max(80, row["canvas"].winfo_width())
                ch = max(8, row["canvas"].winfo_height())
                pct = max(0.0, min(100.0, row["percent"]))
                row["canvas"].coords(row["track"], 0, 0, cw, ch)
                row["canvas"].coords(row["fill"], 0, 0, int((pct / 100.0) * cw), ch)
                row["canvas"].itemconfig(row["fill"], fill=row["color"])
                row["canvas"].coords(row["text"], cw / 2, ch / 2)
                row["canvas"].itemconfig(row["text"], text=row["label"])

    def on_canvas_click(self, event) -> str | None:
        if not self.taskbar_compact_mode:
            return None
        if self.multi_mode and len(self.multi_rows) > 1:
            self.compact_active_index = (self.compact_active_index + 1) % len(self.multi_rows)
            self.update_compact_from_active_row()
            return "break"
        w = max(80, self.canvas.winfo_width())
        if event.x >= (w - 22):
            self.refresh_now()
            return "break"
        return None

    def on_double_click(self, _event) -> str | None:
        if self.taskbar_compact_mode:
            self.restore_from_taskbar_compact()
            return "break"
        return None

    def restore_from_taskbar_compact(self) -> None:
        if not self.taskbar_compact_mode:
            return

        if self.restore_geometry is not None:
            target_width, target_x, target_y = self.restore_geometry
        else:
            target_x = self.last_normal_x
            target_y = self.last_normal_y
            target_width = self.normal_window_width

        self.last_normal_x = target_x
        self.last_normal_y = target_y
        self.normal_window_width = target_width
        self.set_taskbar_compact_mode(False)

        # Forzamos la misma geometria guardada para que menu y doble clic restauren igual.
        self.last_normal_x = target_x
        self.last_normal_y = target_y
        self.apply_window_geometry(self.normal_window_width)

    def apply_window_geometry(self, width: int) -> None:
        if self.taskbar_compact_mode:
            compact_width = self.taskbar_compact_width
        else:
            width = max(380, width)
            self.normal_window_width = width
            self.window_width = width
        if self.dock_top:
            screen_w = self.root.winfo_screenwidth()
            x = max(0, (screen_w - (compact_width if self.taskbar_compact_mode else self.window_width)) // 2)
            y = 0
        elif self.taskbar_compact_mode:
            x, y = self.get_compact_taskbar_position(compact_width, self.window_height)
        else:
            x = max(0, self.last_normal_x)
            y = max(0, self.last_normal_y)
            x, y = self.clamp_to_work_area(x, y, self.window_width, self.window_height)
            self.last_normal_x = x
            self.last_normal_y = y
        final_width = compact_width if self.taskbar_compact_mode else self.window_width
        self.root.geometry(f"{final_width}x{self.window_height}+{x}+{y}")

    def clamp_to_work_area(self, x: int, y: int, width: int, height: int) -> tuple[int, int]:
        left, top, right, bottom = self.get_work_area()
        max_x = max(left, right - width)
        max_y = max(top, bottom - height)
        clamped_x = min(max(x, left), max_x)
        clamped_y = min(max(y, top), max_y)
        return clamped_x, clamped_y

    def get_work_area(self) -> tuple[int, int, int, int]:
        # Area util de Windows (sin barra de tareas), para ubicar modo compacto encima del reloj.
        try:
            rect = ctypes.wintypes.RECT()
            SPI_GETWORKAREA = 0x0030
            ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
            return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def get_taskbar_rect(self) -> tuple[int, int, int, int] | None:
        try:
            user32 = ctypes.windll.user32
            shell_hwnd = user32.FindWindowW("Shell_TrayWnd", None)
            if not shell_hwnd:
                return None
            rect = ctypes.wintypes.RECT()
            if not user32.GetWindowRect(shell_hwnd, ctypes.byref(rect)):
                return None
            return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            return None

    def get_tray_notify_rect(self) -> tuple[int, int, int, int] | None:
        try:
            user32 = ctypes.windll.user32
            shell_hwnd = user32.FindWindowW("Shell_TrayWnd", None)
            if not shell_hwnd:
                return None
            tray_notify = user32.FindWindowExW(shell_hwnd, 0, "TrayNotifyWnd", None)
            if not tray_notify:
                return None
            rect = ctypes.wintypes.RECT()
            if not user32.GetWindowRect(tray_notify, ctypes.byref(rect)):
                return None
            return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            return None

    def get_compact_taskbar_position(self, width: int, height: int) -> tuple[int, int]:
        # Ubica el widget dentro de la taskbar, a la izquierda del area de notificacion.
        taskbar = self.get_taskbar_rect()
        tray = self.get_tray_notify_rect()

        if taskbar and tray:
            t_left, t_top, t_right, t_bottom = taskbar
            n_left, _, _, _ = tray

            x = max(t_left + 8, n_left - width - 8)
            y = t_top + max(0, ((t_bottom - t_top) - height) // 2)
            return x, y

        if taskbar:
            t_left, t_top, t_right, t_bottom = taskbar
            x = max(t_left + 8, t_right - width - 240)
            y = t_top + max(0, ((t_bottom - t_top) - height) // 2)
            return x, y

        left, top, right, bottom = self.get_work_area()
        x = max(left, right - width - 8)
        y = max(top, bottom - height - 8)
        return x, y

    def update_width_for_content(self) -> None:
        if not self.auto_width:
            return
        self.root.update_idletasks()
        needed = (
            22
            + self.title_container.winfo_reqwidth()
            + 8
            + self.metrics_label.winfo_reqwidth()
            + 8
            + self.time_label.winfo_reqwidth()
            + 8
            + self.close_button.winfo_reqwidth()
            + 4
            + self.tray_button.winfo_reqwidth()
            + 4
            + self.taskbar_button.winfo_reqwidth()
            + 4
            + self.refresh_button.winfo_reqwidth()
            + 6
            + self.percent_label.winfo_reqwidth()
            + 10
            + 22
        )
        max_width = int(self.root.winfo_screenwidth() * 0.95)
        target = max(420, min(max_width, needed))
        self.apply_window_geometry(target)

    def popup_current_menu(self, x_root: int, y_root: int) -> None:
        self.rebuild_settings_menu()
        menu = self.menu_taskbar if self.taskbar_compact_mode else self.menu_full
        try:
            menu.tk_popup(x_root, y_root)
        finally:
            menu.grab_release()

    def open_menu_button(self, _event: tk.Event) -> None:
        x_root = self.menu_button.winfo_rootx()
        y_root = self.menu_button.winfo_rooty() + self.menu_button.winfo_height() + 2
        self.popup_current_menu(x_root, y_root)

    def toggle_dock_top(self) -> None:
        if self.taskbar_compact_mode:
            return
        self.dock_top = not self.dock_top
        self.apply_window_geometry(self.window_width)
        self.persist_runtime_config()
        self.rebuild_settings_menu()

    def apply_always_on_top(self) -> None:
        self.root.attributes("-topmost", self.always_on_top)

    def toggle_always_on_top(self) -> None:
        self.always_on_top = not self.always_on_top
        self.apply_always_on_top()
        self.persist_runtime_config()
        self.refresh_menu_state_labels()

    def set_taskbar_compact_mode(self, enabled: bool, persist_config: bool = True) -> None:
        was_compact = self.taskbar_compact_mode
        self.taskbar_compact_mode = enabled
        if enabled:
            if not was_compact:
                self.last_non_compact_geometry = self.root.geometry()
                self.last_normal_x = max(0, self.root.winfo_x())
                self.last_normal_y = max(0, self.root.winfo_y())
                self.restore_geometry = (self.normal_window_width, self.last_normal_x, self.last_normal_y)
            self.window_height = 30
            self.header_frame.pack_forget()
            if self.multi_mode:
                self.rows_container.pack_forget()
                self.canvas.pack(fill="x", padx=6, pady=(7, 7))
            self.canvas.configure(height=14)
            self.canvas.pack_configure(padx=6, pady=(7, 7))
            self.canvas.itemconfig(self.bar_text, font=("Segoe UI", 7, "bold"))
            self.canvas.itemconfig(self.compact_refresh_icon, state="normal")
            self.compact_refresh_visible = True
            self.auto_width = False
            self.dock_top = False
            if self.multi_mode:
                self.update_compact_from_active_row()
        else:
            self.window_height = (34 + (len(self.multi_rows) * 26)) if self.multi_mode else 60
            self.header_frame.pack(fill="x", padx=8, pady=(0, 0), before=self.canvas)
            if self.multi_mode:
                self.canvas.pack_forget()
                self.rows_container.pack(fill="x", padx=8, pady=(2, 4))
            else:
                self.canvas.configure(height=14 if self.mini_mode else 16)
                self.canvas.pack_configure(padx=8, pady=(0, 2))
            self.canvas.itemconfig(
                self.bar_text,
                font=("Segoe UI", 7 if self.mini_mode else 8, "bold"),
            )
            self.canvas.itemconfig(self.compact_refresh_icon, state="hidden")
            self.compact_refresh_visible = False
            self.update_width_for_content()
        self.apply_window_geometry(self.normal_window_width)
        if persist_config:
            self.persist_runtime_config()
            self.rebuild_settings_menu()

    def toggle_taskbar_compact_mode(self) -> None:
        self.set_taskbar_compact_mode(not self.taskbar_compact_mode)

    def activate_taskbar_compact_width(self, width: int) -> None:
        self.taskbar_compact_width = normalize_taskbar_width(width)
        self.set_taskbar_compact_mode(True, persist_config=False)
        self.persist_runtime_config()
        self.rebuild_settings_menu()

    def on_map_restore(self, _event) -> None:
        if self.closed:
            return
        try:
            self.root.overrideredirect(True)
            self.apply_always_on_top()
            self.apply_window_geometry(self.window_width)
        except Exception:
            pass

    def bring_to_front(self, source: str = "manual") -> None:
        log_single_instance_event(f"bring_to_front solicitado ({source})")
        if self.is_hidden_to_tray:
            self.restore_from_tray()
            return
        self.root.deiconify()
        self.root.lift()
        self.apply_always_on_top()
        try:
            self.root.focus_force()
        except Exception:
            pass

    def poll_single_instance_signal(self) -> None:
        if self.closed or self.single_instance_server is None:
            return
        try:
            while True:
                conn, _addr = self.single_instance_server.accept()
                with conn:
                    payload = conn.recv(64).decode("utf-8", errors="ignore").strip().upper()
                    if payload.startswith("SHOW"):
                        log_single_instance_event("SHOW recibido por instancia activa")
                        self.bring_to_front(source="signal")
        except BlockingIOError:
            pass
        except OSError:
            pass
        self.root.after(250, self.poll_single_instance_signal)

    def show_menu(self, event: tk.Event) -> None:
        self.popup_current_menu(event.x_root, event.y_root)

    def on_escape_key(self, _event: tk.Event) -> None:
        # En taskbar compacto, Escape puede dispararse por foco accidental.
        if self.taskbar_compact_mode:
            return
        self.close(reason="escape_key")

    def relogin(self) -> None:
        try:
            ensure_login_state(self.primary_state_file)
            self.metrics_label.config(text=f" | {self.tr('session_updated')}")
            self.refresh_now()
        except Exception as exc:  # pylint: disable=broad-except
            self.metrics_label.config(text=f" | Login error: {exc}")

    def update_compact_from_active_row(self) -> None:
        if not self.multi_rows:
            return
        row = self.multi_rows[self.compact_active_index % len(self.multi_rows)]
        self.current_percent = row["percent"]
        self.current_bar_label = row["label"]
        self.current_fill_color = row["color"]
        self.on_resize(None)

    def update_multi_visuals(self, snapshots: list[UsageSnapshot | Exception]) -> None:
        ok_count = 0
        for idx, result in enumerate(snapshots):
            row = self.multi_rows[idx]
            if isinstance(result, UsageSnapshot):
                pct = max(0.0, min(100.0, result.usage_percent))
                color = quality_color(pct)
                row["percent"] = pct
                row["color"] = color
                row["label"] = result.usage_label
                row["account_label"].config(text=result.account_label)
                row["pct_label"].config(text=result.usage_label, fg=color)
                ok_count += 1
            else:
                row["percent"] = 0.0
                row["color"] = self.theme_colors["error"]
                row["label"] = "ERR"
                row["account_label"].config(text=self.tr("account_default", n=idx + 1))
                row["pct_label"].config(text="ERR", fg=self.theme_colors["error"])

        self.metrics_label.config(text=f" | {self.tr('accounts_ok', ok=ok_count, total=len(snapshots))}")
        self.on_resize(None)
        if self.taskbar_compact_mode:
            self.update_compact_from_active_row()

    def periodic_clock(self) -> None:
        if self.closed:
            return
        self.time_label.config(text=f"{dt.datetime.now():%H:%M:%S}")
        self.root.after(1000, self.periodic_clock)

    def create_tray_image(self) -> object:
        c = self.theme_colors
        img = Image.new("RGBA", (64, 64), color=c["tray_bg"])
        draw = ImageDraw.Draw(img)
        draw.rectangle((8, 8, 56, 56), fill=c["tray_card"], outline=c["tray_card_border"], width=2)
        draw.rectangle((14, 30, 50, 42), fill=c["track"])
        draw.rectangle((14, 30, 34, 42), fill="#12b886")
        draw.text((16, 12), "GH", fill=c["text_clock"])

        icon_path = Path("assets") / "github_favicon.png"
        if icon_path.exists():
            try:
                favicon = Image.open(icon_path).convert("RGBA").resize((20, 20), Image.Resampling.LANCZOS)
                img.alpha_composite(favicon, (22, 12))
                return img
            except Exception:
                pass

        return img

    def restore_from_tray(self) -> None:
        def _restore() -> None:
            self.is_hidden_to_tray = False
            self.root.deiconify()
            self.root.lift()
            self.apply_always_on_top()
            if not self.taskbar_compact_mode:
                self.apply_window_geometry(self.normal_window_width)

        self.root.after(0, _restore)

    def _stop_tray(self) -> None:
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None

    def minimize_to_tray(self) -> None:
        if self.closed or self.is_hidden_to_tray:
            return

        if not TRAY_SUPPORTED:
            self.metrics_label.config(text=" | Instala pystray y pillow para minimizar a bandeja")
            return

        if not self.taskbar_compact_mode:
            self.last_normal_x = max(0, self.root.winfo_x())
            self.last_normal_y = max(0, self.root.winfo_y())

        self.is_hidden_to_tray = True
        self.root.withdraw()

        if self.tray_icon is None:
            menu = pystray.Menu(
                pystray.MenuItem(
                    "Restaurar",
                    lambda _icon, _item: self.restore_from_tray(),
                    default=True,
                ),
                pystray.MenuItem("Actualizar", lambda _icon, _item: self.root.after(0, self.refresh_now)),
                pystray.MenuItem(
                    "Salir",
                    lambda _icon, _item: self.root.after(0, lambda: self.close(reason="tray_menu")),
                ),
            )
            self.tray_icon = pystray.Icon(
                "copilot_usage_bar",
                self.create_tray_image(),
                "Copilot Usage Bar",
                menu,
            )
            self.tray_icon.title = "Copilot Usage Bar (doble clic para restaurar)"
            self.tray_icon.run_detached()

    def update_visuals(self, snapshot: UsageSnapshot) -> None:
        percent = max(0.0, min(100.0, snapshot.usage_percent))
        self.current_percent = percent
        self.current_bar_label = snapshot.usage_label
        self.current_fill_color = quality_color(percent)
        elapsed_percent, pace_ratio, projected_end_month = month_metrics(percent)
        color = self.current_fill_color

        self.percent_label.config(text=snapshot.usage_label, fg=color)
        if self.mini_mode:
            self.current_metrics_label = self.tr(
                "metrics_mini",
                account=snapshot.account_label,
                pace=pace_ratio,
                elapsed=elapsed_percent,
            )
        else:
            self.current_metrics_label = self.tr(
                "metrics_full",
                account=snapshot.account_label,
                pace=pace_ratio,
                elapsed=elapsed_percent,
                proj=projected_end_month,
            )
        self.metrics_label.config(text=self.current_metrics_label)

        w = max(80, self.canvas.winfo_width())
        h = max(12, self.canvas.winfo_height())
        fill_w = int((percent / 100.0) * w)
        self.canvas.coords(self.track, 0, 0, w, h)
        self.canvas.coords(self.fill, 0, 0, fill_w, h)
        self.canvas.itemconfig(self.fill, fill=color)
        self.canvas.coords(self.bar_text, w / 2, h / 2)
        self.canvas.itemconfig(self.bar_text, text=snapshot.usage_label)
        self.update_width_for_content()

    def set_error_state(self, message: str) -> None:
        self.current_percent = 0.0
        self.current_bar_label = self.tr("no_data")
        self.current_fill_color = self.theme_colors["track"]
        self.percent_label.config(text="ERR", fg=self.theme_colors["error"])
        self.current_metrics_label = f" | {self.tr('error_prefix')}: {message}"
        self.metrics_label.config(text=self.current_metrics_label)
        w = max(80, self.canvas.winfo_width())
        h = max(12, self.canvas.winfo_height())
        self.canvas.coords(self.fill, 0, 0, 0, h)
        self.canvas.coords(self.bar_text, w / 2, h / 2)
        self.canvas.itemconfig(self.bar_text, text=self.tr("no_data"))
        self.update_width_for_content()

    def refresh_now(self) -> None:
        if self.closed:
            return
        self.metrics_label.config(text=f" | {self.tr('updating')}")
        if self.multi_mode:
            snapshots: list[UsageSnapshot | Exception] = []
            for client in self.clients:
                try:
                    snapshots.append(client.fetch_snapshot())
                except Exception as exc:  # pylint: disable=broad-except
                    snapshots.append(exc)
            self.update_multi_visuals(snapshots)
            return

        try:
            snapshot = self.clients[0].fetch_snapshot()
            self.update_visuals(snapshot)
        except Exception as exc:  # pylint: disable=broad-except
            self.set_error_state(str(exc))

    def periodic_refresh(self) -> None:
        if self.closed:
            return
        self.refresh_now()
        self.root.after(self.interval_s * 1000, self.periodic_refresh)

    def on_tk_callback_exception(self, exc_type: type, exc_value: BaseException, exc_tb: object) -> None:
        trace = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        log_runtime_event(f"Tk callback exception:\n{trace}")
        try:
            self.metrics_label.config(text=f" | {self.tr('error_internal_ui')}")
        except Exception:
            pass

    def close(self, reason: str = "unknown") -> None:
        if self.closed:
            return
        log_runtime_event(f"Close requested: {reason}")
        self.closed = True
        self._stop_tray()
        if self.single_instance_server is not None:
            try:
                self.single_instance_server.close()
            except Exception:
                pass
            self.single_instance_server = None
        for client in self.clients:
            try:
                client.close()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self) -> int:
        log_runtime_event("App iniciada")
        for client in self.clients:
            client.start()
        self.root.after(100, self.periodic_clock)
        self.root.after(120, self.refresh_now)
        self.root.after(self.interval_s * 1000, self.periodic_refresh)
        self.root.mainloop()
        log_runtime_event("Mainloop finished")
        if not self.closed:
            log_runtime_event("Unexpected mainloop exit (without explicit close)")
            self.close(reason="unexpected_mainloop_exit")
            return 2
        return 0


def run_monitor(args: argparse.Namespace) -> int:
    if args.login or not args.state_file.exists():
        try:
            ensure_login_state(args.state_file)
        except PlaywrightError:
            print("Could not open Playwright Chromium.")
            print("Run: python -m playwright install chromium")
            return 1

    (
        interval_s,
        mini_mode,
        opacity,
        auto_width,
        dock_top,
        window_width,
        always_on_top,
        taskbar_compact_mode,
        taskbar_compact_width,
        theme,
        language,
        extra_state_files,
    ) = resolve_settings(args)

    all_state_files = [args.state_file] + extra_state_files
    normalized: list[Path] = []
    seen: set[str] = set()
    for sf in all_state_files:
        key = str(sf.resolve()) if sf.exists() else str(sf)
        if key in seen:
            continue
        seen.add(key)
        if sf.exists():
            normalized.append(sf)

    if not normalized:
        normalized = [args.state_file]

    if args.gui:
        for attempt in range(2):
            instance_server = create_single_instance_server()
            app = FloatingBarApp(
                state_files=normalized,
                interval_s=interval_s,
                mini_mode=mini_mode,
                opacity=opacity,
                auto_width=auto_width,
                dock_top=dock_top,
                window_width=window_width,
                always_on_top=always_on_top,
                taskbar_compact_mode=taskbar_compact_mode,
                taskbar_compact_width=taskbar_compact_width,
                theme=theme,
                language=language,
                single_instance_server=instance_server,
                config_path=args.config,
            )
            result = app.run()
            if result != 2:
                return result
            log_runtime_event(f"Automatic restart after unexpected exit (attempt {attempt + 1}/1)")

        return 1

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=args.headless)
        context = browser.new_context(storage_state=str(args.state_file))
        page = context.new_page()

        while True:
            try:
                snapshot = read_snapshot(page)
                print_snapshot(snapshot)
            except (PermissionError, ValueError, PlaywrightTimeoutError, PlaywrightError) as exc:
                print("\n" + "!" * 72)
                print(f"Error reading Copilot usage: {exc}")
                print("Tip: re-authenticate with --login")
                print("!" * 72)
                return 1

            if args.once:
                return 0

            time.sleep(interval_s)


def main() -> int:
    args = parse_arguments()

    assistant_result = run_account_assistant(args)
    if assistant_result is not None:
        return assistant_result

    if not any((args.gui, args.headless, args.once, args.login)):
        args.gui = True
        args.headless = True

    if args.gui and not args.login and try_signal_existing_instance():
        return 0

    try:
        return run_monitor(args)
    except KeyboardInterrupt:
        print("\nMonitor stopped by user.")
        log_runtime_event("Closed by KeyboardInterrupt")
        return 0
    except Exception:
        log_runtime_event("Unhandled exception in main:\n" + traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
