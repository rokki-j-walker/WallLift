import customtkinter as ctk

from settings_storage import load_settings_json


APPEARANCE_MODES = ["System", "Light", "Dark"]
DEFAULT_APPEARANCE_MODE = "System"
DEFAULT_COLOR_THEME = "blue"


def get_theme_settings(data: dict | None = None) -> dict:
    data = data if isinstance(data, dict) else load_settings_json()
    appearance_mode = str(data.get("appearance_mode", DEFAULT_APPEARANCE_MODE))

    if appearance_mode not in APPEARANCE_MODES:
        appearance_mode = DEFAULT_APPEARANCE_MODE

    return {
        "theme_mode": "builtin",
        "appearance_mode": appearance_mode,
        "color_theme": DEFAULT_COLOR_THEME,
    }


def apply_saved_theme():
    settings = get_theme_settings()
    ctk.set_appearance_mode(settings["appearance_mode"])
    ctk.set_default_color_theme(DEFAULT_COLOR_THEME)
