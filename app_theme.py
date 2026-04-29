import json
from dataclasses import dataclass
from pathlib import Path

import customtkinter as ctk

from app_config import BASE_DIR
from settings_storage import load_settings_json


THEMES_DIR = BASE_DIR / "themes"
APPEARANCE_MODES = ["System", "Light", "Dark"]
DEFAULT_APPEARANCE_MODE = "System"
DEFAULT_THEME_ID = "default"
DEFAULT_COLOR_THEME = "blue"


@dataclass(frozen=True)
class ThemeDefinition:
    theme_id: str
    name: str
    path: Path
    color_theme: str
    light_icons_dir: Path
    dark_icons_dir: Path
    light_logos_dir: Path
    dark_logos_dir: Path


def get_theme_settings(data: dict | None = None) -> dict:
    data = data if isinstance(data, dict) else load_settings_json()
    appearance_mode = str(data.get("appearance_mode", DEFAULT_APPEARANCE_MODE))
    theme_id = str(data.get("theme_id") or data.get("color_theme") or DEFAULT_THEME_ID)

    if appearance_mode not in APPEARANCE_MODES:
        appearance_mode = DEFAULT_APPEARANCE_MODE

    if not theme_exists(theme_id):
        theme_id = DEFAULT_THEME_ID

    return {
        "theme_mode": "folder",
        "theme_id": theme_id,
        "appearance_mode": appearance_mode,
        "color_theme": theme_id,
    }


def apply_saved_theme():
    settings = get_theme_settings()
    theme = load_theme(settings["theme_id"])
    ctk.set_appearance_mode(settings["appearance_mode"])
    ctk.set_default_color_theme(theme.color_theme)


def get_active_theme() -> ThemeDefinition:
    return load_theme(get_theme_settings()["theme_id"])


def list_themes() -> list[ThemeDefinition]:
    if not THEMES_DIR.exists():
        return [load_theme(DEFAULT_THEME_ID)]

    themes = []
    for theme_dir in sorted(path for path in THEMES_DIR.iterdir() if path.is_dir()):
        try:
            themes.append(load_theme(theme_dir.name))
        except Exception:
            continue

    if not themes:
        return [load_theme(DEFAULT_THEME_ID)]

    return themes


def theme_exists(theme_id: str) -> bool:
    return (THEMES_DIR / theme_id / "theme.json").is_file()


def load_theme(theme_id: str) -> ThemeDefinition:
    theme_dir = THEMES_DIR / theme_id
    data = load_theme_json(theme_dir)

    assets = data.get("assets") if isinstance(data.get("assets"), dict) else {}
    icons = assets.get("icons") if isinstance(assets.get("icons"), dict) else {}
    logos = assets.get("logos") if isinstance(assets.get("logos"), dict) else {}

    return ThemeDefinition(
        theme_id=str(data.get("id") or theme_id),
        name=str(data.get("name") or theme_id),
        path=theme_dir,
        color_theme=str(data.get("customtkinter_color_theme") or DEFAULT_COLOR_THEME),
        light_icons_dir=resolve_theme_path(theme_dir, icons.get("light"), "icons/light"),
        dark_icons_dir=resolve_theme_path(theme_dir, icons.get("dark"), "icons/dark"),
        light_logos_dir=resolve_theme_path(theme_dir, logos.get("light"), "logos/light"),
        dark_logos_dir=resolve_theme_path(theme_dir, logos.get("dark"), "logos/dark"),
    )


def load_theme_json(theme_dir: Path) -> dict:
    theme_file = theme_dir / "theme.json"
    try:
        data = json.loads(theme_file.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        if theme_dir.name == DEFAULT_THEME_ID:
            return {"id": DEFAULT_THEME_ID, "name": "Default", "customtkinter_color_theme": DEFAULT_COLOR_THEME}
        raise


def resolve_theme_path(theme_dir: Path, value, fallback: str) -> Path:
    path = Path(str(value or fallback))
    if path.is_absolute():
        return path
    return theme_dir / path
