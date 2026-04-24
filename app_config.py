import os
import shutil
from pathlib import Path

OLD_APP_NAME = "ImageSizer"
APP_NAME = "WallLift"
DISPLAY_NAME = "WallLift"
BASE_DIR = Path(__file__).resolve().parent

REAL_ESRGAN_EXE = BASE_DIR / "rnv" / "realesrgan-ncnn-vulkan.exe"

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"
}

DEFAULT_MIN_WIDTH = 2560
DEFAULT_MIN_HEIGHT = 1080
DEFAULT_JPEG_QUALITY = 100
DEFAULT_OUTPUT_FORMAT = "jpg"
DEFAULT_OUTPUT_FOLDER_NAME = f"{DISPLAY_NAME}_result"
OUTPUT_FORMATS = ["keep", "jpg", "png", "webp", "bmp", "tiff"]

SIZE_PRESETS = {
    "hd": ("HD 1280×720", (1280, 720)),
    "full_hd": ("Full HD 1920×1080", (1920, 1080)),
    "wfhd": ("WFHD 2560×1080", (2560, 1080)),
    "qhd": ("2K / QHD 2560×1440", (2560, 1440)),
    "uwqhd": ("UWQHD 3440×1440", (3440, 1440)),
    "4k": ("4K 3840×2160", (3840, 2160)),
    "8k": ("8K 7680×4320", (7680, 4320)),
    "custom": ("", None),
}

AI_MODELS = [
    "realesrgan-x4plus",
    "realesrnet-x4plus",
    "realesrgan-x4plus-anime",
    "realesr-animevideov3",
]

AI_SCALES = ["2", "3", "4"]
AI_TILE_SIZES = ["0", "64", "96", "128", "160", "192", "256", "320", "384", "512"]
AI_THREAD_CONFIGS = ["1:1:1", "1:2:1", "1:2:2", "2:2:2", "2:3:2"]
AI_COOLDOWN_SECONDS = ["0", "0.2", "0.5", "1", "2", "3", "5"]

DEFAULT_AI_MODEL = "realesrgan-x4plus"
DEFAULT_AI_SCALE = 4
DEFAULT_AI_GPU_ID = "0"
DEFAULT_AI_TILE_SIZE = "128"
DEFAULT_AI_THREAD_CONFIG = "1:1:1"
DEFAULT_AI_COOLDOWN_SECONDS = "0.5"


def get_settings_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        settings_dir = Path(appdata) / APP_NAME
        old_settings_dir = Path(appdata) / OLD_APP_NAME
    else:
        settings_dir = Path.home() / f".{APP_NAME}"
        old_settings_dir = Path.home() / f".{OLD_APP_NAME}"

    migrate_settings_dir(old_settings_dir, settings_dir)
    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir


def get_settings_file() -> Path:
    return get_settings_dir() / "settings.json"


def migrate_settings_dir(old_settings_dir: Path, settings_dir: Path):
    if old_settings_dir == settings_dir or not old_settings_dir.exists():
        return

    if not settings_dir.exists():
        try:
            old_settings_dir.rename(settings_dir)
            return
        except Exception:
            pass

    old_settings_file = old_settings_dir / "settings.json"
    settings_file = settings_dir / "settings.json"

    if old_settings_file.exists() and not settings_file.exists():
        try:
            settings_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old_settings_file, settings_file)
        except Exception:
            pass
