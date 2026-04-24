from functools import lru_cache

import customtkinter as ctk
from PIL import Image, ImageDraw


ICON_SIZE = 24
ICON_DISPLAY_SIZE = 20
LOGO_SIZE = 32
LOGO_DISPLAY_SIZE = 28

LIGHT_STROKE = "#1f2937"
DARK_STROKE = "#f3f4f6"
LIGHT_ACCENT = "#2563eb"
DARK_ACCENT = "#60a5fa"


def get_icon(name: str) -> ctk.CTkImage:
    return _get_icon(name)


def get_logo() -> ctk.CTkImage:
    return _get_logo()


@lru_cache(maxsize=None)
def _get_icon(name: str) -> ctk.CTkImage:
    light_image = _draw_icon(name, LIGHT_STROKE, LIGHT_ACCENT)
    dark_image = _draw_icon(name, DARK_STROKE, DARK_ACCENT)

    return ctk.CTkImage(
        light_image=light_image,
        dark_image=dark_image,
        size=(ICON_DISPLAY_SIZE, ICON_DISPLAY_SIZE),
    )


@lru_cache(maxsize=1)
def _get_logo() -> ctk.CTkImage:
    light_image = _draw_logo()
    dark_image = _draw_logo()

    return ctk.CTkImage(
        light_image=light_image,
        dark_image=dark_image,
        size=(LOGO_DISPLAY_SIZE, LOGO_DISPLAY_SIZE),
    )


def _draw_logo() -> Image.Image:
    image = Image.new("RGBA", (LOGO_SIZE, LOGO_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((2, 2, 30, 30), radius=7, fill="#1d8cf8")
    draw.rounded_rectangle((2, 2, 30, 30), radius=7, outline="#58b7ff", width=2)

    draw.line([(10, 12), (10, 8), (14, 8)], fill="#ffffff", width=3)
    draw.line([(22, 20), (22, 24), (18, 24)], fill="#ffffff", width=3)
    draw.line([(11, 21), (21, 11)], fill="#ffffff", width=3)
    draw.polygon([(19, 9), (24, 8), (23, 13)], fill="#ffffff")

    return image


def _draw_icon(name: str, stroke: str, accent: str) -> Image.Image:
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    if name == "folder":
        _draw_folder(draw, stroke, accent)
    elif name == "folder_settings":
        _draw_folder(draw, stroke, accent)
        _draw_gear(draw, stroke, 16, 16)
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

    return image


def _draw_folder(draw: ImageDraw.ImageDraw, stroke: str, accent: str):
    draw.line([(3, 8), (8, 8), (10, 10), (21, 10)], fill=accent, width=2)
    draw.rounded_rectangle((3, 9, 21, 19), radius=3, outline=stroke, width=2)
    draw.line([(4, 12), (20, 12)], fill=stroke, width=2)


def _draw_external_link(draw: ImageDraw.ImageDraw, stroke: str, accent: str):
    draw.rounded_rectangle((4, 8, 16, 20), radius=2, outline=stroke, width=2)
    draw.line([(10, 14), (19, 5)], fill=accent, width=2)
    draw.line([(14, 5), (19, 5), (19, 10)], fill=accent, width=2)


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
