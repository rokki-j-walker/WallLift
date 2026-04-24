import json
import os
import re
import subprocess
from pathlib import Path

from app_config import get_settings_dir, get_settings_file, REAL_ESRGAN_EXE


def get_settings_file_path() -> Path:
    return get_settings_file()


def load_settings_json() -> dict:
    settings_file = get_settings_file()

    if not settings_file.exists():
        return {}

    try:
        data = json.loads(settings_file.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings_json(data: dict):
    settings_file = get_settings_file()
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def open_settings_folder():
    settings_dir = get_settings_dir()

    try:
        os.startfile(settings_dir)
    except Exception:
        try:
            subprocess.Popen(["explorer", str(settings_dir)])
        except Exception:
            pass


def _add_gpu(result: list[str], gpu_id: int, name: str):
    name = " ".join(str(name).replace("\t", " ").split()).strip()

    if not name:
        return

    junk_words = [
        "usage",
        "input",
        "output",
        "model",
        "thread",
        "tile",
        "format",
        "scale",
        "help",
        "license",
    ]

    lower_name = name.lower()
    if any(word in lower_name for word in junk_words):
        return

    item = f"{gpu_id} — {name}"

    if item not in result:
        result.append(item)


def _parse_real_esrgan_gpu_output(text: str) -> list[str]:
    """
    Пытается вытащить Vulkan GPU из разных вариантов вывода ncnn-vulkan.
    В разных сборках формат отличается, поэтому парсер намеренно широкий.
    """
    result: list[str] = []

    patterns = [
        # [0 NVIDIA GeForce RTX 4060 Laptop GPU]  queueC=...
        re.compile(r"^\[(\d+)\s+([^\]]+)\]"),

        # 0 = NVIDIA GeForce RTX 4060 Laptop GPU
        # 1: AMD Radeon(TM) Graphics
        re.compile(r"^(\d+)\s*[:=]\s*(.+)$"),

        # GPU 0: NVIDIA GeForce RTX ...
        re.compile(r"^gpu\s*(\d+)\s*[:=]\s*(.+)$", re.IGNORECASE),

        # gpu[0] NVIDIA GeForce RTX ...
        re.compile(r"^gpu\[(\d+)\]\s*[:=]?\s*(.+)$", re.IGNORECASE),

        # device 0: NVIDIA GeForce RTX ...
        re.compile(r"^device\s*(\d+)\s*[:=]\s*(.+)$", re.IGNORECASE),
    ]

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        for pattern in patterns:
            match = pattern.search(line)
            if not match:
                continue

            try:
                gpu_id = int(match.group(1))
                name = match.group(2)
            except Exception:
                continue

            # Отрезаем технические хвосты, если они попали в имя.
            for marker in [" queue", " type=", " api=", " fp16", " bf16", " subgroup"]:
                if marker in name:
                    name = name.split(marker, 1)[0]

            _add_gpu(result, gpu_id, name)
            break

    return result


def _run_real_esrgan_for_gpu_text() -> str:
    exe = Path(REAL_ESRGAN_EXE)

    if not exe.is_file():
        return ""

    commands = [
        [str(exe)],
        [str(exe), "-h"],
    ]

    chunks: list[str] = []

    for cmd in commands:
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=8,
                cwd=str(exe.parent),
            )
            chunks.append(process.stdout or "")
            chunks.append(process.stderr or "")
        except Exception:
            continue

    return "\n".join(chunks)


def _detect_windows_video_controllers() -> list[str]:
    """
    Запасной способ: берёт видеокарты из Windows.
    Это не гарантия совпадения с Vulkan ID, но лучше, чем показывать одну карту.
    """
    try:
        process = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
            ],
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception:
        return []

    names: list[str] = []

    for line in (process.stdout or "").splitlines():
        name = " ".join(line.strip().split())
        if name and name not in names:
            names.append(name)

    return [f"{index} — {name}" for index, name in enumerate(names)]


def detect_real_esrgan_gpus() -> list[str]:
    """
    Возвращает список для выпадающего меню видеокарт.

    Приоритет:
    1. Vulkan GPU из вывода realesrgan-ncnn-vulkan.exe.
    2. Если Real-ESRGAN не дал нормальный список — видеокарты Windows через PowerShell.
    3. Безопасный дефолт.
    """
    default_items = ["0 — основная видеокарта / авто"]

    text = _run_real_esrgan_for_gpu_text()
    vulkan_items = _parse_real_esrgan_gpu_output(text)

    windows_items = _detect_windows_video_controllers()

    if len(vulkan_items) >= 2:
        return vulkan_items

    if len(vulkan_items) == 1 and len(windows_items) <= 1:
        return vulkan_items

    if len(windows_items) >= 2:
        return windows_items

    if vulkan_items:
        return vulkan_items

    return default_items
