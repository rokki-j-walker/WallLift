import math
import shutil
import subprocess
import tempfile
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps

from app_config import SUPPORTED_EXTENSIONS
from app_models import AppSettings, ProcessingStats, ProcessResult
from style_analyzer import StyleAnalyzer


class ImageProcessor:
    def __init__(self, source_dir: Path, settings: AppSettings, callbacks: dict | None = None):
        self.source_dir = Path(source_dir)
        self.settings = settings
        self.callbacks = callbacks or {}

        self.result_dir = self.source_dir / "result"
        self.result_dir.mkdir(exist_ok=True)

        self.files = self.find_images()
        self.stats = ProcessingStats(total_count=len(self.files))
        self.total_count = len(self.files)
        self.errors: list[str] = []

        self.pause_event = threading.Event()
        self.pause_event.set()
        self.cancel_event = threading.Event()

        self.current_ai_process: subprocess.Popen | None = None
        self.lock = threading.Lock()
        self.worker_thread: threading.Thread | None = None
        self.style_analyzer = StyleAnalyzer()

    # =========================
    # Worker control
    # =========================

    def start(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return

        self.worker_thread = threading.Thread(
            target=self.process_all_images,
            daemon=True,
        )
        self.worker_thread.start()

    def is_paused(self) -> bool:
        return not self.pause_event.is_set()

    def pause(self):
        self.pause_event.clear()
        self.notify_status("Состояние: пауза")

    def resume(self):
        self.pause_event.set()
        self.notify_status("Состояние: обработка продолжается")

    def cancel(self):
        self.cancel_event.set()
        self.pause_event.set()
        self.notify_status("Состояние: отмена обработки...")

        try:
            if self.current_ai_process is not None:
                self.current_ai_process.terminate()
        except Exception:
            pass

    def wait_if_paused(self):
        while not self.cancel_event.is_set():
            if self.pause_event.wait(timeout=0.2):
                return

    # =========================
    # Callbacks
    # =========================

    def call_callback(self, name: str, *args):
        callback = self.callbacks.get(name)
        if callable(callback):
            callback(*args)

    def notify_status(self, text: str):
        self.call_callback("status", text)

    def notify_total_progress(self):
        self.call_callback(
            "total_progress",
            self.stats.done_count,
            self.stats.total_count,
            self.stats.total_percent(),
        )

    def notify_current_progress(self, percent: int, text: str = ""):
        percent = max(0, min(100, int(percent)))
        self.call_callback("current_progress", percent, text)

    def notify_stats(self):
        self.call_callback("stats", self.stats)

    # =========================
    # File search
    # =========================

    def find_images(self) -> list[Path]:
        if not self.source_dir.exists():
            return []

        files = [
            item for item in self.source_dir.iterdir()
            if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        return sorted(files, key=lambda x: x.name.lower())

    # =========================
    # Main processing
    # =========================

    def process_all_images(self):
        self.notify_status("Состояние: обработка запущена")
        self.notify_total_progress()
        self.notify_stats()

        if not self.files:
            self.notify_status("Состояние: изображения не найдены")
            self.finish()
            return

        try:
            if self.settings.use_threads and not self.settings.use_ai:
                self.process_with_threads()
            else:
                self.process_single_thread()
        finally:
            if self.cancel_event.is_set():
                self.notify_status("Состояние: обработка отменена")
            elif self.errors:
                self.notify_status("Состояние: завершено с ошибками")
            else:
                self.notify_status("Состояние: завершено")

            self.finish()

    def finish(self):
        self.call_callback(
            "finished",
            self.cancel_event.is_set(),
            len(self.errors),
            self.result_dir,
        )

    def process_single_thread(self):
        for file_path in self.files:
            if self.cancel_event.is_set():
                break

            self.wait_if_paused()

            if self.cancel_event.is_set():
                break

            self.call_callback("file_started", file_path.name)
            result = self.safe_process_one_image(file_path, ui_enabled=True)
            self.apply_result(file_path, result)

    def process_with_threads(self):
        max_workers = max(1, int(self.settings.max_workers))
        self.notify_current_progress(0, f"Многопоточная обработка: {max_workers} поток(а/ов)")

        pending_files = list(self.files)
        futures = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while pending_files or futures:
                if self.cancel_event.is_set():
                    break

                self.wait_if_paused()

                if self.cancel_event.is_set():
                    break

                while pending_files and len(futures) < max_workers and not self.cancel_event.is_set():
                    file_path = pending_files.pop(0)
                    self.call_callback("file_started", file_path.name)
                    future = executor.submit(self.safe_process_one_image, file_path, False)
                    futures[future] = file_path

                done_futures = [future for future in futures if future.done()]

                for future in done_futures:
                    file_path = futures.pop(future)

                    try:
                        result = future.result()
                    except Exception:
                        result = ProcessResult(status="error", error=traceback.format_exc())

                    self.apply_result(file_path, result)

                if not done_futures:
                    time.sleep(0.1)

            if self.cancel_event.is_set():
                for future in futures:
                    future.cancel()

    def safe_process_one_image(self, file_path: Path, ui_enabled: bool = False) -> ProcessResult:
        try:
            return self.process_one_image(file_path, ui_enabled=ui_enabled)
        except Exception:
            return ProcessResult(status="error", error=traceback.format_exc())

    def apply_result(self, file_path: Path, result: ProcessResult):
        if result.is_cancelled:
            return

        error_text = None

        with self.lock:
            if result.is_copied:
                self.stats.add_copied(file_path.name)
                self.call_callback("file_copied", file_path.name)
            elif result.is_processed:
                self.stats.add_processed(file_path.name)
                self.call_callback("file_processed", file_path.name)
            elif result.is_error:
                self.stats.add_error(file_path.name)
                error_text = (
                    f"Файл: {file_path.name}\n"
                    f"Ошибка:\n{result.error}\n"
                    f"{'-' * 80}\n"
                )
                self.errors.append(error_text)
                self.call_callback("file_error", file_path.name, result.error or "")
            else:
                self.stats.add_error(file_path.name)
                error_text = (
                    f"Файл: {file_path.name}\n"
                    f"Ошибка:\nНеизвестный статус обработки: {result.status}\n"
                    f"{'-' * 80}\n"
                )
                self.errors.append(error_text)
                self.call_callback("file_error", file_path.name, error_text)

        self.notify_total_progress()
        self.notify_stats()

    # =========================
    # Single image
    # =========================

    def process_one_image(self, file_path: Path, ui_enabled: bool = False) -> ProcessResult:
        if self.cancel_event.is_set():
            return ProcessResult(status="cancelled")

        self.wait_if_paused()

        if ui_enabled:
            self.notify_current_progress(0, "Открытие файла...")

        with Image.open(file_path) as img:
            img = ImageOps.exif_transpose(img)
            original_width, original_height = img.size

            if ui_enabled:
                self.notify_current_progress(20, f"Исходный размер: {original_width}×{original_height}")

            new_width, new_height = self.calculate_new_size(original_width, original_height)
            resize_needed = new_width != original_width or new_height != original_height
            upscale_needed = new_width > original_width or new_height > original_height

            if ui_enabled:
                self.notify_current_progress(35, f"Целевой размер: {new_width}×{new_height}")

            if self.cancel_event.is_set():
                return ProcessResult(status="cancelled")

            self.wait_if_paused()

            if not resize_needed and self.settings.keep_original_if_no_resize:
                output_path = self.make_output_path(file_path, file_path.suffix)

                if ui_enabled:
                    self.notify_current_progress(70, "Копирование без изменений...")

                shutil.copy2(file_path, output_path)

                if ui_enabled:
                    self.notify_current_progress(100, "Скопировано без изменений")

                return ProcessResult(status="copied", output_path=str(output_path))

            if self.settings.use_ai and upscale_needed:
                if ui_enabled:
                    self.notify_current_progress(45, "ИИ-апскейл Real-ESRGAN...")

                ai_image_path = self.run_ai_upscale(file_path)

                if self.cancel_event.is_set():
                    return ProcessResult(status="cancelled")

                self.wait_if_paused()

                with Image.open(ai_image_path) as ai_img:
                    ai_img = ImageOps.exif_transpose(ai_img)
                    ai_img = self.prepare_for_jpeg(ai_img)

                    if ui_enabled:
                        self.notify_current_progress(75, f"Финальный ресайз до {new_width}×{new_height}...")

                    ai_img = ai_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    output_path = self.make_output_path(file_path, ".jpg")

                    if ui_enabled:
                        self.notify_current_progress(90, "Сохранение JPG...")

                    ai_img.save(
                        output_path,
                        format="JPEG",
                        quality=self.settings.jpeg_quality,
                        optimize=True,
                        progressive=True,
                        subsampling=0,
                    )

                try:
                    Path(ai_image_path).unlink(missing_ok=True)
                except Exception:
                    pass

                if ui_enabled:
                    self.notify_current_progress(100, "Готово")

                return ProcessResult(status="processed", output_path=str(output_path))

            if ui_enabled:
                self.notify_current_progress(55, "Обычное изменение размера...")

            img = self.prepare_for_jpeg(img)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            output_path = self.make_output_path(file_path, ".jpg")

            if ui_enabled:
                self.notify_current_progress(85, "Сохранение JPG...")

            img.save(
                output_path,
                format="JPEG",
                quality=self.settings.jpeg_quality,
                optimize=True,
                progressive=True,
                subsampling=0,
            )

            if ui_enabled:
                self.notify_current_progress(100, "Готово")

            return ProcessResult(status="processed", output_path=str(output_path))

    # =========================
    # Real-ESRGAN
    # =========================

    def get_ai_model_for_file(self, file_path: Path) -> str:
        if not self.settings.auto_style_analysis:
            return self.settings.ai_model

        try:
            model = self.style_analyzer.choose_model_for_image(file_path, self.settings.ai_model)
            self.notify_current_progress(43, f"Автовыбор модели: {model}")
            return model
        except Exception:
            return self.settings.ai_model

    def run_ai_upscale(self, file_path: Path) -> Path:
        ai_exe_path = Path(self.settings.ai_exe_path)

        if not ai_exe_path.is_file():
            raise FileNotFoundError(f"Real-ESRGAN EXE не найден:\n{ai_exe_path}")

        temp_dir = Path(tempfile.mkdtemp(prefix="wallpaper_ai_"))

        try:
            input_for_ai = file_path

            if file_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                input_for_ai = temp_dir / "input.png"
                with Image.open(file_path) as img:
                    img = ImageOps.exif_transpose(img)
                    img = self.prepare_for_png(img)
                    img.save(input_for_ai, format="PNG")

            output_from_ai = temp_dir / "ai_output.png"
            model = self.get_ai_model_for_file(file_path)

            cmd = [
                str(ai_exe_path),
                "-i", str(input_for_ai),
                "-o", str(output_from_ai),
                "-n", model,
                "-s", str(self.settings.ai_scale),
                "-f", "png",
                "-g", str(self.settings.ai_gpu_id),
                "-t", str(self.settings.ai_tile_size),
                "-j", str(self.settings.ai_thread_config),
            ]

            self.current_ai_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
                cwd=str(ai_exe_path.parent),
            )

            stdout, stderr = self.current_ai_process.communicate()
            return_code = self.current_ai_process.returncode
            self.current_ai_process = None

            if self.cancel_event.is_set():
                raise RuntimeError("Обработка отменена пользователем.")

            if return_code != 0:
                raise RuntimeError(
                    "Real-ESRGAN завершился с ошибкой.\n\n"
                    f"CMD: {' '.join(cmd)}\n\n"
                    f"STDOUT:\n{stdout}\n\n"
                    f"STDERR:\n{stderr}"
                )

            if not output_from_ai.exists():
                raise RuntimeError(
                    "Real-ESRGAN не создал выходной файл.\n\n"
                    f"CMD: {' '.join(cmd)}\n\n"
                    f"STDOUT:\n{stdout}\n\n"
                    f"STDERR:\n{stderr}"
                )

            final_temp_output = Path(tempfile.mkstemp(suffix=".png", prefix="ai_result_")[1])
            shutil.copy2(output_from_ai, final_temp_output)

            if self.settings.ai_cooldown_seconds > 0:
                time.sleep(float(self.settings.ai_cooldown_seconds))

            return final_temp_output

        finally:
            self.current_ai_process = None
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    # =========================
    # Helpers
    # =========================

    def calculate_new_size(self, width: int, height: int) -> tuple[int, int]:
        scale = max(self.settings.min_width / width, self.settings.min_height / height)
        return math.ceil(width * scale), math.ceil(height * scale)

    def prepare_for_jpeg(self, img: Image.Image) -> Image.Image:
        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (0, 0, 0))
            alpha = img.getchannel("A")
            background.paste(img.convert("RGBA"), mask=alpha)
            return background

        if img.mode == "P":
            if "transparency" in img.info:
                rgba = img.convert("RGBA")
                background = Image.new("RGB", rgba.size, (0, 0, 0))
                background.paste(rgba, mask=rgba.getchannel("A"))
                return background
            return img.convert("RGB")

        if img.mode != "RGB":
            return img.convert("RGB")

        return img

    def prepare_for_png(self, img: Image.Image) -> Image.Image:
        if img.mode in ("RGB", "RGBA"):
            return img

        if img.mode == "P":
            if "transparency" in img.info:
                return img.convert("RGBA")
            return img.convert("RGB")

        return img.convert("RGB")

    def make_output_path(self, source_file: Path, extension: str) -> Path:
        base_name = source_file.stem
        output_path = self.result_dir / f"{base_name}{extension}"

        if self.settings.overwrite_files:
            return output_path

        counter = 1
        while output_path.exists():
            output_path = self.result_dir / f"{base_name}_{counter}{extension}"
            counter += 1

        return output_path
