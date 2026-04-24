import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from app_config import (
    CLIP_MODEL_REPO,
    REAL_ESRGAN_MODELS_ARCHIVE_NAME,
    REAL_ESRGAN_MODELS_DOWNLOAD_URL,
    REAL_ESRGAN_RUNTIME_ARCHIVE_NAME,
    REAL_ESRGAN_RUNTIME_DOWNLOAD_URL,
    get_clip_model_dir,
    get_downloaded_real_esrgan_exe,
    get_real_esrgan_tool_dir,
)


CLIP_FILES = [
    ("config.json", 4_190),
    ("preprocessor_config.json", 316),
    ("tokenizer_config.json", 592),
    ("special_tokens_map.json", 389),
    ("merges.txt", 525_000),
    ("vocab.json", 862_000),
    ("tokenizer.json", 2_220_000),
    ("pytorch_model.bin", 605_000_000),
]


def get_real_esrgan_runtime_download_target() -> Path:
    return get_real_esrgan_tool_dir() / REAL_ESRGAN_RUNTIME_ARCHIVE_NAME


def get_real_esrgan_models_download_target() -> Path:
    return get_real_esrgan_tool_dir() / REAL_ESRGAN_MODELS_ARCHIVE_NAME


def is_real_esrgan_available() -> bool:
    return get_downloaded_real_esrgan_exe().is_file() and (get_real_esrgan_tool_dir() / "models").is_dir()


def is_clip_model_available() -> bool:
    model_dir = get_clip_model_dir()
    return all((model_dir / filename).is_file() for filename, _size in CLIP_FILES)


def get_clip_download_size() -> int:
    return sum(size for _filename, size in CLIP_FILES)


def download_file(url: str, target_path: Path, progress_callback=None):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    part_path = target_path.with_suffix(target_path.suffix + ".part")

    request = urllib.request.Request(url, headers={"User-Agent": "WallLift"})

    with urllib.request.urlopen(request, timeout=30) as response:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0

        with part_path.open("wb") as output:
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break

                output.write(chunk)
                done += len(chunk)

                if progress_callback:
                    progress_callback(done, total)

    part_path.replace(target_path)


def download_real_esrgan(progress_callback=None) -> Path:
    tool_dir = get_real_esrgan_tool_dir()
    runtime_archive_path = get_real_esrgan_runtime_download_target()
    models_archive_path = get_real_esrgan_models_download_target()
    tool_dir.mkdir(parents=True, exist_ok=True)

    def _runtime_progress(done: int, total: int):
        if progress_callback:
            progress_callback(done, total * 2 if total else 0)

    download_file(REAL_ESRGAN_RUNTIME_DOWNLOAD_URL, runtime_archive_path, _runtime_progress)

    def _models_progress(done: int, total: int):
        if progress_callback:
            progress_callback(total + done if total else done, total * 2 if total else 0)

    download_file(REAL_ESRGAN_MODELS_DOWNLOAD_URL, models_archive_path, _models_progress)

    temp_dir = Path(tempfile.mkdtemp(prefix="walllift_realesrgan_"))
    try:
        runtime_dir = temp_dir / "runtime"
        models_dir = temp_dir / "models"
        runtime_dir.mkdir()
        models_dir.mkdir()

        with zipfile.ZipFile(runtime_archive_path, "r") as archive:
            archive.extractall(runtime_dir)

        exe_candidates = list(runtime_dir.rglob("realesrgan-ncnn-vulkan.exe"))
        if not exe_candidates:
            raise FileNotFoundError("realesrgan-ncnn-vulkan.exe was not found in the runtime archive")

        runtime_root = exe_candidates[0].parent

        for item in runtime_root.iterdir():
            destination = tool_dir / item.name
            if destination.exists():
                if destination.is_dir():
                    shutil.rmtree(destination)
                else:
                    destination.unlink()

            if item.is_dir():
                shutil.copytree(item, destination)
            else:
                shutil.copy2(item, destination)

        with zipfile.ZipFile(models_archive_path, "r") as archive:
            archive.extractall(models_dir)

        model_dirs = [path for path in models_dir.rglob("models") if path.is_dir()]
        if not model_dirs:
            raise FileNotFoundError("models folder was not found in the Real-ESRGAN models archive")

        destination_models = tool_dir / "models"
        if destination_models.exists():
            shutil.rmtree(destination_models)
        shutil.copytree(model_dirs[0], destination_models)

        return get_downloaded_real_esrgan_exe()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def get_huggingface_file_url(filename: str) -> str:
    return f"https://huggingface.co/{CLIP_MODEL_REPO}/resolve/main/{filename}"


def download_clip_model(progress_callback=None) -> Path:
    model_dir = get_clip_model_dir()
    model_dir.mkdir(parents=True, exist_ok=True)

    expected_total = get_clip_download_size()
    completed_before_file = 0

    for filename, expected_size in CLIP_FILES:
        target_path = model_dir / filename
        if target_path.is_file() and target_path.stat().st_size > 0:
            completed_before_file += target_path.stat().st_size
            continue

        def _progress(file_done: int, file_total: int):
            current_file_total = file_total or expected_size
            total = max(expected_total, completed_before_file + current_file_total)
            done = completed_before_file + file_done
            if progress_callback:
                progress_callback(done, total)

        download_file(get_huggingface_file_url(filename), target_path, _progress)
        completed_before_file += target_path.stat().st_size

    if progress_callback:
        progress_callback(completed_before_file, max(expected_total, completed_before_file))

    return model_dir
