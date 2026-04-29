from functools import lru_cache

import customtkinter as ctk
from PIL import Image, ImageDraw

from app_theme import get_active_theme


ICON_ASSET_SIZE = 64
ICON_DRAW_SIZE = 24
ICON_DISPLAY_SIZE = 24
LOGO_ASSET_SIZE = 64
LOGO_DRAW_SIZE = 32
LOGO_DISPLAY_SIZE = 32

LIGHT_STROKE = "#1f2937"
DARK_STROKE = "#f3f4f6"
LIGHT_ACCENT = "#2563eb"
DARK_ACCENT = "#60a5fa"


def get_icon(name: str) -> ctk.CTkImage:
    theme = get_active_theme()
    return _get_icon(theme.theme_id, name)


def get_logo() -> ctk.CTkImage:
    theme = get_active_theme()
    return _get_logo(theme.theme_id)


@lru_cache(maxsize=None)
def _get_icon(theme_id: str, name: str) -> ctk.CTkImage:
    theme = get_active_theme()
    light_image = load_theme_image(theme.light_icons_dir / f"{name}.png", ICON_ASSET_SIZE) or _draw_icon(
        name, LIGHT_STROKE, LIGHT_ACCENT
    )
    dark_image = load_theme_image(theme.dark_icons_dir / f"{name}.png", ICON_ASSET_SIZE) or _draw_icon(
        name, DARK_STROKE, DARK_ACCENT
    )

    return ctk.CTkImage(
        light_image=light_image,
        dark_image=dark_image,
        size=(ICON_DISPLAY_SIZE, ICON_DISPLAY_SIZE),
    )


@lru_cache(maxsize=1)
def _get_logo(theme_id: str) -> ctk.CTkImage:
    theme = get_active_theme()
    light_image = load_theme_image(theme.light_logos_dir / "logo.png", LOGO_ASSET_SIZE) or _draw_logo()
    dark_image = load_theme_image(theme.dark_logos_dir / "logo.png", LOGO_ASSET_SIZE) or _draw_logo()

    return ctk.CTkImage(
        light_image=light_image,
        dark_image=dark_image,
        size=(LOGO_DISPLAY_SIZE, LOGO_DISPLAY_SIZE),
    )


def clear_icon_cache():
    _get_icon.cache_clear()
    _get_logo.cache_clear()


def load_theme_image(path, asset_size: int) -> Image.Image | None:
    try:
        if path.is_file():
            image = Image.open(path).convert("RGBA")
            if image.size != (asset_size, asset_size):
                return image.resize((asset_size, asset_size), Image.Resampling.LANCZOS)
            return image
    except Exception:
        return None
    return None


def _draw_logo() -> Image.Image:
    image = Image.new("RGBA", (LOGO_DRAW_SIZE, LOGO_DRAW_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((2, 2, 30, 30), radius=7, fill="#1d8cf8")
    draw.rounded_rectangle((2, 2, 30, 30), radius=7, outline="#58b7ff", width=2)

    draw.line([(10, 12), (10, 8), (14, 8)], fill="#ffffff", width=3)
    draw.line([(22, 20), (22, 24), (18, 24)], fill="#ffffff", width=3)
    draw.line([(11, 21), (21, 11)], fill="#ffffff", width=3)
    draw.polygon([(19, 9), (24, 8), (23, 13)], fill="#ffffff")

    return image.resize((LOGO_ASSET_SIZE, LOGO_ASSET_SIZE), Image.Resampling.LANCZOS)


def _draw_icon(name: str, stroke: str, accent: str) -> Image.Image:
    image = Image.new("RGBA", (ICON_DRAW_SIZE, ICON_DRAW_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    if name == "folder":
        _draw_folder(draw, stroke, accent)
    elif name == "folder_settings":
        _draw_folder(draw, stroke, accent)
        _draw_gear(draw, stroke, 16, 16)
    elif name == "format":
        _draw_files(draw, stroke, accent)
        draw.text((6, 15), "F", fill=accent)
    elif name == "ai":
        draw.rounded_rectangle((4, 5, 20, 19), radius=4, outline=stroke, width=2)
        draw.line([(8, 12), (11, 8), (14, 12), (16, 8)], fill=accent, width=2)
        draw.line([(8, 12), (8, 16)], fill=accent, width=2)
        draw.line([(16, 8), (16, 16)], fill=accent, width=2)
    elif name == "palette":
        draw.ellipse((4, 4, 20, 20), outline=stroke, width=2)
        draw.ellipse((8, 8, 10, 10), fill=accent)
        draw.ellipse((13, 7, 15, 9), fill=accent)
        draw.ellipse((7, 14, 9, 16), fill=accent)
        draw.ellipse((14, 14, 17, 17), outline=stroke, width=2)
    elif name == "files":
        _draw_files(draw, stroke, accent)
    elif name == "add_file":
        _draw_files(draw, stroke, accent)
        _draw_plus(draw, accent, 17, 17)
    elif name == "remove_file":
        _draw_files(draw, stroke, accent)
        _draw_minus(draw, accent, 17, 17)
    elif name == "clear":
        _draw_clear(draw, stroke, accent)
    elif name == "external_link":
        _draw_external_link(draw, stroke, accent)
    elif name == "reset":
        _draw_reset(draw, stroke, accent)
    elif name == "pause":
        _draw_pause(draw, stroke)
    elif name == "play":
        _draw_play(draw, stroke, accent)
    else:
        _draw_fallback(draw, stroke)

    return image.resize((ICON_ASSET_SIZE, ICON_ASSET_SIZE), Image.Resampling.LANCZOS)


def _draw_folder(draw: ImageDraw.ImageDraw, stroke: str, accent: str):
    draw.line([(3, 8), (8, 8), (10, 10), (21, 10)], fill=accent, width=2)
    draw.rounded_rectangle((3, 9, 21, 19), radius=3, outline=stroke, width=2)
    draw.line([(4, 12), (20, 12)], fill=stroke, width=2)


def _draw_external_link(draw: ImageDraw.ImageDraw, stroke: str, accent: str):
    draw.rounded_rectangle((4, 8, 16, 20), radius=2, outline=stroke, width=2)
    draw.line([(10, 14), (19, 5)], fill=accent, width=2)
    draw.line([(14, 5), (19, 5), (19, 10)], fill=accent, width=2)


def _draw_files(draw: ImageDraw.ImageDraw, stroke: str, accent: str):
    draw.rounded_rectangle((5, 4, 15, 16), radius=2, outline=accent, width=2)
    draw.line([(8, 8), (13, 8)], fill=accent, width=1)
    draw.rounded_rectangle((9, 8, 19, 20), radius=2, outline=stroke, width=2)
    draw.line([(12, 12), (17, 12)], fill=stroke, width=1)


def _draw_plus(draw: ImageDraw.ImageDraw, accent: str, cx: int, cy: int):
    draw.line([(cx - 4, cy), (cx + 4, cy)], fill=accent, width=2)
    draw.line([(cx, cy - 4), (cx, cy + 4)], fill=accent, width=2)


def _draw_minus(draw: ImageDraw.ImageDraw, accent: str, cx: int, cy: int):
    draw.line([(cx - 4, cy), (cx + 4, cy)], fill=accent, width=2)


def _draw_clear(draw: ImageDraw.ImageDraw, stroke: str, accent: str):
    draw.line([(8, 8), (17, 17)], fill=accent, width=2)
    draw.line([(17, 8), (8, 17)], fill=accent, width=2)
    draw.rounded_rectangle((5, 5, 20, 20), radius=3, outline=stroke, width=2)


def _draw_reset(draw: ImageDraw.ImageDraw, stroke: str, accent: str):
    draw.arc((5, 5, 19, 19), start=35, end=315, fill=stroke, width=2)
    draw.polygon([(6, 7), (6, 13), (2, 10)], fill=accent)
    draw.line([(6, 10), (10, 10)], fill=accent, width=2)


def _draw_pause(draw: ImageDraw.ImageDraw, stroke: str):
    draw.rounded_rectangle((7, 5, 10, 19), radius=1, fill=stroke)
    draw.rounded_rectangle((14, 5, 17, 19), radius=1, fill=stroke)


def _draw_play(draw: ImageDraw.ImageDraw, stroke: str, accent: str):
    draw.polygon([(8, 5), (8, 19), (19, 12)], fill=accent)
    draw.line([(8, 5), (8, 19), (19, 12), (8, 5)], fill=stroke, width=1)


def _draw_gear(draw: ImageDraw.ImageDraw, stroke: str, cx: int, cy: int):
    for x1, y1, x2, y2 in [
        (cx, cy - 6, cx, cy - 4),
        (cx, cy + 4, cx, cy + 6),
        (cx - 6, cy, cx - 4, cy),
        (cx + 4, cy, cx + 6, cy),
    ]:
        draw.line([(x1, y1), (x2, y2)], fill=stroke, width=2)

    draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), outline=stroke, width=2)
    draw.ellipse((cx - 1, cy - 1, cx + 1, cy + 1), fill=stroke)


def _draw_fallback(draw: ImageDraw.ImageDraw, stroke: str):
    draw.ellipse((5, 5, 19, 19), outline=stroke, width=2)
