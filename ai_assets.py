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

REAL_ESRGAN_REQUIRED_MODEL_FILES = [
    "realesr-animevideov3-x2.bin",
    "realesr-animevideov3-x2.param",
    "realesr-animevideov3-x3.bin",
    "realesr-animevideov3-x3.param",
    "realesr-animevideov3-x4.bin",
    "realesr-animevideov3-x4.param",
    "realesrgan-x4plus-anime.bin",
    "realesrgan-x4plus-anime.param",
    "realesrgan-x4plus.bin",
    "realesrgan-x4plus.param",
]


def get_real_esrgan_runtime_download_target() -> Path:
    return get_real_esrgan_tool_dir() / REAL_ESRGAN_RUNTIME_ARCHIVE_NAME


def get_real_esrgan_models_download_target() -> Path:
    return get_real_esrgan_tool_dir() / REAL_ESRGAN_MODELS_ARCHIVE_NAME


def is_real_esrgan_available() -> bool:
    ok, _messages = verify_real_esrgan_assets()
    return ok


def is_clip_model_available() -> bool:
    ok, _messages = verify_clip_assets()
    return ok


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

    if total > 0 and done != total:
        raise OSError(f"Incomplete download: expected {total} bytes, got {done} bytes")

    if done <= 0:
        raise OSError("Downloaded file is empty")

    part_path.replace(target_path)


def verify_zip_archive(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Archive was not found: {path}")

    if path.stat().st_size <= 0:
        raise OSError(f"Archive is empty: {path}")

    try:
        with zipfile.ZipFile(path, "r") as archive:
            bad_file = archive.testzip()
    except zipfile.BadZipFile as exc:
        raise OSError(f"Archive is not a valid ZIP file: {path}") from exc

    if bad_file:
        raise OSError(f"Archive integrity check failed for {path}: {bad_file}")


def verify_min_size(path: Path, expected_size: int):
    if not path.is_file():
        raise FileNotFoundError(f"File was not found: {path}")

    actual_size = path.stat().st_size
    if actual_size <= 0:
        raise OSError(f"File is empty: {path}")

    minimum_size = int(expected_size * 0.8)
    if minimum_size > 0 and actual_size < minimum_size:
        raise OSError(
            f"File looks incomplete: {path} ({actual_size} bytes, expected about {expected_size} bytes)"
        )


def verify_real_esrgan_assets() -> tuple[bool, list[str]]:
    messages = []
    ok = True

    runtime_archive_path = get_real_esrgan_runtime_download_target()
    models_archive_path = get_real_esrgan_models_download_target()

    for label, archive_path in [
        ("Real-ESRGAN runtime archive", runtime_archive_path),
        ("Real-ESRGAN models archive", models_archive_path),
    ]:
        if archive_path.is_file():
            try:
                verify_zip_archive(archive_path)
                messages.append(f"OK: {label}")
            except Exception as exc:
                ok = False
                messages.append(f"ERROR: {label}: {exc}")

    exe_path = get_downloaded_real_esrgan_exe()
    if exe_path.is_file() and exe_path.stat().st_size > 0:
        messages.append("OK: Real-ESRGAN executable")
    else:
        ok = False
        messages.append(f"ERROR: Real-ESRGAN executable is missing: {exe_path}")

    models_dir = get_real_esrgan_tool_dir() / "models"
    if not models_dir.is_dir():
        ok = False
        messages.append(f"ERROR: Real-ESRGAN models folder is missing: {models_dir}")
    else:
        for filename in REAL_ESRGAN_REQUIRED_MODEL_FILES:
            path = models_dir / filename
            if path.is_file() and path.stat().st_size > 0:
                continue
            ok = False
            messages.append(f"ERROR: Real-ESRGAN model file is missing or empty: {path}")

        if ok:
            messages.append("OK: Real-ESRGAN model files")

    return ok, messages


def verify_clip_assets() -> tuple[bool, list[str]]:
    messages = []
    ok = True
    model_dir = get_clip_model_dir()

    if not model_dir.is_dir():
        return False, [f"ERROR: CLIP model folder is missing: {model_dir}"]

    for filename, expected_size in CLIP_FILES:
        path = model_dir / filename
        try:
            verify_min_size(path, expected_size)
        except Exception as exc:
            ok = False
            messages.append(f"ERROR: CLIP file: {exc}")

    if ok:
        messages.append("OK: CLIP model files")

    return ok, messages


def verify_ai_assets() -> tuple[bool, list[str]]:
    real_ok, real_messages = verify_real_esrgan_assets()
    clip_ok, clip_messages = verify_clip_assets()
    return real_ok and clip_ok, real_messages + clip_messages


def download_real_esrgan(progress_callback=None) -> Path:
    tool_dir = get_real_esrgan_tool_dir()
    runtime_archive_path = get_real_esrgan_runtime_download_target()
    models_archive_path = get_real_esrgan_models_download_target()
    tool_dir.mkdir(parents=True, exist_ok=True)

    def _runtime_progress(done: int, total: int):
        if progress_callback:
            progress_callback(done, total * 2 if total else 0)

    download_file(REAL_ESRGAN_RUNTIME_DOWNLOAD_URL, runtime_archive_path, _runtime_progress)
    verify_zip_archive(runtime_archive_path)

    def _models_progress(done: int, total: int):
        if progress_callback:
            progress_callback(total + done if total else done, total * 2 if total else 0)

    download_file(REAL_ESRGAN_MODELS_DOWNLOAD_URL, models_archive_path, _models_progress)
    verify_zip_archive(models_archive_path)

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

        ok, messages = verify_real_esrgan_assets()
        if not ok:
            raise OSError("Real-ESRGAN verification failed:\n" + "\n".join(messages))

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
        if target_path.is_file() and target_path.stat().st_size >= int(expected_size * 0.8):
            completed_before_file += target_path.stat().st_size
            continue

        def _progress(file_done: int, file_total: int):
            current_file_total = file_total or expected_size
            total = max(expected_total, completed_before_file + current_file_total)
            done = completed_before_file + file_done
            if progress_callback:
                progress_callback(done, total)

        download_file(get_huggingface_file_url(filename), target_path, _progress)
        verify_min_size(target_path, expected_size)
        completed_before_file += target_path.stat().st_size

    if progress_callback:
        progress_callback(completed_before_file, max(expected_total, completed_before_file))

    ok, messages = verify_clip_assets()
    if not ok:
        raise OSError("CLIP verification failed:\n" + "\n".join(messages))

    return model_dir
