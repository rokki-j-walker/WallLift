import os
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app_config import (
    DEFAULT_MIN_WIDTH,
    DEFAULT_MIN_HEIGHT,
    DEFAULT_JPEG_QUALITY,
    SIZE_PRESETS,
    AI_MODELS,
    AI_SCALES,
    AI_TILE_SIZES,
    AI_THREAD_CONFIGS,
    AI_COOLDOWN_SECONDS,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_SCALE,
    DEFAULT_AI_GPU_ID,
    DEFAULT_AI_TILE_SIZE,
    DEFAULT_AI_THREAD_CONFIG,
    DEFAULT_AI_COOLDOWN_SECONDS,
    REAL_ESRGAN_EXE,
)
from app_models import AppSettings
from progress_window import ProgressWindow
from settings_storage import (
    load_settings_json,
    save_settings_json,
    get_settings_file_path,
    open_settings_folder,
    detect_real_esrgan_gpus,
)
from ui_helpers import attach_tooltip


class SettingsWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ImageSizer — настройки")
        self.resizable(True, True)
        self.minsize(920, 650)
        self.protocol("WM_DELETE_WINDOW", self.on_close_attempt)

        self.progress_window = None
        self.processing_started = False
        self.initial_settings_snapshot = None
        self._initial_autosized = False

        self.loaded_settings = self.safe_load_settings()

        self.folder_path_var = ctk.StringVar(value=self.loaded_settings.get("last_folder", ""))
        self.size_preset_var = ctk.StringVar(value=self.loaded_settings.get("size_preset", "Указать вручную"))
        self.min_width_var = ctk.StringVar(value=str(self.loaded_settings.get("min_width", DEFAULT_MIN_WIDTH)))
        self.min_height_var = ctk.StringVar(value=str(self.loaded_settings.get("min_height", DEFAULT_MIN_HEIGHT)))
        self.quality_var = ctk.StringVar(value=str(self.loaded_settings.get("jpeg_quality", DEFAULT_JPEG_QUALITY)))
        self.process_mode_var = ctk.StringVar(value=self.loaded_settings.get("process_mode", "threads"))
        self.max_workers_var = ctk.StringVar(value=str(self.loaded_settings.get("max_workers", 4)))
        self.ai_model_var = ctk.StringVar(value=self.loaded_settings.get("ai_model", DEFAULT_AI_MODEL))
        self.auto_style_analysis_var = ctk.BooleanVar(value=bool(self.loaded_settings.get("auto_style_analysis", False)))
        self.ai_scale_var = ctk.StringVar(value=str(self.loaded_settings.get("ai_scale", DEFAULT_AI_SCALE)))
        self.keep_original_var = ctk.BooleanVar(value=bool(self.loaded_settings.get("keep_original_if_no_resize", True)))
        self.overwrite_files_var = ctk.BooleanVar(value=bool(self.loaded_settings.get("overwrite_files", False)))
        self.save_settings_var = ctk.BooleanVar(value=bool(self.loaded_settings.get("save_settings", True)))
        self.advanced_monitoring_var = ctk.BooleanVar(value=bool(self.loaded_settings.get("advanced_monitoring", True)))
        self.settings_path_var = ctk.StringVar(value=str(get_settings_file_path()))

        self.gpu_labels = detect_real_esrgan_gpus()
        if not self.gpu_labels:
            self.gpu_labels = ["0 — основная видеокарта / авто"]
        self.gpu_label_to_id = {label: self.extract_gpu_id(label) for label in self.gpu_labels}
        default_gpu_id = int(self.loaded_settings.get("ai_gpu_id", DEFAULT_AI_GPU_ID))
        self.ai_gpu_var = ctk.StringVar(value=self.get_gpu_label_by_id(default_gpu_id))

        self.ai_tile_size_var = ctk.StringVar(value=str(self.loaded_settings.get("ai_tile_size", DEFAULT_AI_TILE_SIZE)))
        self.ai_thread_config_var = ctk.StringVar(value=self.loaded_settings.get("ai_thread_config", DEFAULT_AI_THREAD_CONFIG))
        self.ai_cooldown_var = ctk.StringVar(value=str(self.loaded_settings.get("ai_cooldown_seconds", DEFAULT_AI_COOLDOWN_SECONDS)))

        self.build_ui()
        self.on_size_preset_changed(autosize=False)
        self.on_process_mode_changed(autosize=False)
        self.on_auto_style_changed()

        self.initial_settings_snapshot = self.collect_settings_for_json()
        self.after(80, self.autosize_window)

    # =========================
    # Settings storage
    # =========================

    def safe_load_settings(self) -> dict:
        try:
            data = load_settings_json()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def collect_settings_for_json(self) -> dict:
        return {
            "last_folder": self.folder_path_var.get().strip(),
            "size_preset": self.size_preset_var.get(),
            "min_width": self.safe_int(self.min_width_var.get(), DEFAULT_MIN_WIDTH),
            "min_height": self.safe_int(self.min_height_var.get(), DEFAULT_MIN_HEIGHT),
            "jpeg_quality": self.safe_int(self.quality_var.get(), DEFAULT_JPEG_QUALITY),
            "process_mode": self.process_mode_var.get(),
            "max_workers": self.safe_int(self.max_workers_var.get(), 4),
            "ai_model": self.ai_model_var.get(),
            "auto_style_analysis": self.auto_style_analysis_var.get(),
            "ai_scale": self.safe_int(self.ai_scale_var.get(), int(DEFAULT_AI_SCALE)),
            "keep_original_if_no_resize": self.keep_original_var.get(),
            "overwrite_files": self.overwrite_files_var.get(),
            "save_settings": self.save_settings_var.get(),
            "advanced_monitoring": self.advanced_monitoring_var.get(),
            "ai_gpu_id": self.get_selected_gpu_id(),
            "ai_tile_size": self.safe_int(self.ai_tile_size_var.get(), int(DEFAULT_AI_TILE_SIZE)),
            "ai_thread_config": self.ai_thread_config_var.get(),
            "ai_cooldown_seconds": self.safe_float(self.ai_cooldown_var.get(), float(DEFAULT_AI_COOLDOWN_SECONDS)),
        }

    def save_current_settings_if_needed(self, force: bool = False) -> bool:
        if not force and not self.save_settings_var.get():
            return True

        try:
            save_settings_json(self.collect_settings_for_json())
            self.initial_settings_snapshot = self.collect_settings_for_json()
            return True
        except Exception as exc:
            messagebox.showwarning("Настройки", f"Не удалось сохранить настройки:\n\n{exc}")
            return False

    # =========================
    # UI
    # =========================

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        root_frame = ctk.CTkFrame(self, corner_radius=0)
        root_frame.grid(row=0, column=0, sticky="nsew")
        root_frame.grid_columnconfigure(0, weight=1)
        root_frame.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(root_frame, fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=18, pady=(18, 0))
        self.scroll.grid_columnconfigure(0, weight=1)
        self.scroll.grid_columnconfigure(1, weight=1)

        self.buttons_bar = ctk.CTkFrame(root_frame, fg_color="transparent")
        self.buttons_bar.grid(row=1, column=0, sticky="ew", padx=18, pady=14)
        self.buttons_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.scroll,
            text="Настройки обработки изображений",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))

        self.build_folder_section(self.scroll, row=1)

        self.left_column = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.left_column.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
        self.left_column.grid_columnconfigure(0, weight=1)

        self.right_column = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.right_column.grid(row=2, column=1, sticky="nsew", padx=(8, 0))
        self.right_column.grid_columnconfigure(0, weight=1)

        self.build_size_section(self.left_column, row=0)
        self.build_save_section(self.left_column, row=1)
        self.build_settings_storage_section(self.left_column, row=2)

        self.build_mode_section(self.right_column, row=0)
        self.build_ai_section(self.right_column, row=1)
        self.build_ai_limit_section(self.right_column, row=2)

        self.build_buttons(self.buttons_bar)

    def build_folder_section(self, parent, row: int):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            frame,
            text="Папка с изображениями",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(14, 8))

        ctk.CTkLabel(frame, text="Путь:").grid(row=1, column=0, sticky="w", padx=(16, 8), pady=(4, 16))

        self.folder_entry = ctk.CTkEntry(frame, textvariable=self.folder_path_var)
        self.folder_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(4, 16))

        self.choose_folder_button = ctk.CTkButton(
            frame,
            text="📁",
            width=42,
            command=self.choose_folder,
        )
        self.choose_folder_button.grid(row=1, column=2, sticky="e", padx=(0, 8), pady=(4, 16))
        attach_tooltip(self.choose_folder_button, "Выбрать папку с изображениями")

        self.open_folder_button = ctk.CTkButton(
            frame,
            text="↗",
            width=42,
            command=self.open_selected_folder,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        self.open_folder_button.grid(row=1, column=3, sticky="e", padx=(0, 16), pady=(4, 16))
        attach_tooltip(self.open_folder_button, "Открыть выбранную папку в проводнике")

    def build_size_section(self, parent, row: int):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Размер результата", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(14, 8)
        )

        ctk.CTkLabel(frame, text="Пресет:").grid(row=1, column=0, sticky="w", padx=(16, 8), pady=8)
        self.size_preset_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.size_preset_var,
            values=list(SIZE_PRESETS.keys()),
            command=lambda _: self.on_size_preset_changed(),
            width=250,
        )
        self.size_preset_menu.grid(row=1, column=1, sticky="w", padx=(0, 16), pady=8)

        self.manual_size_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.manual_size_frame.grid(row=2, column=0, columnspan=4, sticky="w", padx=16, pady=(4, 10))

        ctk.CTkLabel(self.manual_size_frame, text="Ширина:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.width_entry = ctk.CTkEntry(self.manual_size_frame, textvariable=self.min_width_var, width=110)
        self.width_entry.grid(row=0, column=1, sticky="w", padx=(0, 18))

        ctk.CTkLabel(self.manual_size_frame, text="Высота:").grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.height_entry = ctk.CTkEntry(self.manual_size_frame, textvariable=self.min_height_var, width=110)
        self.height_entry.grid(row=0, column=3, sticky="w")

        ctk.CTkLabel(
            frame,
            text="Размер считается минимальным. Пропорции сохраняются.",
            anchor="w",
            justify="left",
            wraplength=360,
        ).grid(row=3, column=0, columnspan=4, sticky="ew", padx=16, pady=(2, 14))

    def build_save_section(self, parent, row: int):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Сохранение", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(14, 8)
        )

        ctk.CTkLabel(frame, text="Качество JPG:").grid(row=1, column=0, sticky="w", padx=(16, 8), pady=8)
        self.quality_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.quality_var,
            values=["85", "90", "95", "98", "100"],
            width=90,
        )
        self.quality_menu.grid(row=1, column=1, sticky="w", pady=8)

        ctk.CTkCheckBox(
            frame,
            text="Копировать оригинал без изменений, если размер менять не нужно",
            variable=self.keep_original_var,
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=16, pady=(8, 4))

        ctk.CTkCheckBox(frame, text="Перезаписывать файлы не спрашивая", variable=self.overwrite_files_var).grid(
            row=3, column=0, columnspan=3, sticky="w", padx=16, pady=(6, 8)
        )

        ctk.CTkCheckBox(frame, text="Расширенный мониторинг", variable=self.advanced_monitoring_var).grid(
            row=4, column=0, columnspan=3, sticky="w", padx=16, pady=(6, 14)
        )

    def build_settings_storage_section(self, parent, row: int):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="Настройки программы", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )

        self.open_settings_button = ctk.CTkButton(
            header,
            text="📂",
            width=42,
            command=open_settings_folder,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        self.open_settings_button.grid(row=0, column=1, sticky="e")
        attach_tooltip(self.open_settings_button, "Открыть папку с настройками")

        ctk.CTkCheckBox(frame, text="Сохранять последние настройки", variable=self.save_settings_var).grid(
            row=1, column=0, sticky="w", padx=16, pady=(4, 8)
        )

        self.settings_path_entry = ctk.CTkEntry(frame, textvariable=self.settings_path_var, state="disabled")
        self.settings_path_entry.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

    def build_mode_section(self, parent, row: int):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Режим обработки", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(14, 8)
        )

        ctk.CTkRadioButton(
            frame,
            text="Обычный режим, 1 поток",
            variable=self.process_mode_var,
            value="normal",
            command=self.on_process_mode_changed,
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=16, pady=5)

        ctk.CTkRadioButton(
            frame,
            text="Многопоточная обработка без ИИ",
            variable=self.process_mode_var,
            value="threads",
            command=self.on_process_mode_changed,
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=16, pady=5)

        ctk.CTkRadioButton(
            frame,
            text="ИИ-апскейл для увеличения, 1 поток",
            variable=self.process_mode_var,
            value="ai",
            command=self.on_process_mode_changed,
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=16, pady=5)

        ctk.CTkLabel(frame, text="Потоков:").grid(row=4, column=0, sticky="w", padx=(16, 8), pady=(10, 14))
        self.workers_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.max_workers_var,
            values=["1", "2", "3", "4", "6", "8", "12", "16"],
            width=90,
        )
        self.workers_menu.grid(row=4, column=1, sticky="w", pady=(10, 14))

        ctk.CTkLabel(
            frame,
            text="ИИ и многопоточность взаимоисключаются.",
            anchor="w",
            justify="left",
            wraplength=360,
        ).grid(row=5, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 14))

    def build_ai_section(self, parent, row: int):
        self.ai_frame = ctk.CTkFrame(parent)
        self.ai_frame.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        self.ai_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.ai_frame, text="ИИ-апскейл Real-ESRGAN", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(14, 8)
        )

        self.auto_style_checkbox = ctk.CTkCheckBox(
            self.ai_frame,
            text="Автоматически анализировать стиль и выбирать модель",
            variable=self.auto_style_analysis_var,
            command=self.on_auto_style_changed,
        )
        self.auto_style_checkbox.grid(row=1, column=0, columnspan=3, sticky="w", padx=16, pady=(4, 10))

        ctk.CTkLabel(self.ai_frame, text="Модель:").grid(row=2, column=0, sticky="w", padx=(16, 8), pady=8)
        self.ai_model_menu = ctk.CTkOptionMenu(self.ai_frame, variable=self.ai_model_var, values=AI_MODELS, width=260)
        self.ai_model_menu.grid(row=2, column=1, sticky="w", pady=8)

        ctk.CTkLabel(self.ai_frame, text="AI scale:").grid(row=3, column=0, sticky="w", padx=(16, 8), pady=(8, 14))
        self.ai_scale_menu = ctk.CTkOptionMenu(self.ai_frame, variable=self.ai_scale_var, values=[str(x) for x in AI_SCALES], width=90)
        self.ai_scale_menu.grid(row=3, column=1, sticky="w", pady=(8, 14))

    def build_ai_limit_section(self, parent, row: int):
        self.ai_limit_frame = ctk.CTkFrame(parent)
        self.ai_limit_frame.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        self.ai_limit_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.ai_limit_frame, text="Ограничение нагрузки ИИ", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(14, 8)
        )

        ctk.CTkLabel(self.ai_limit_frame, text="Видеокарта:").grid(row=1, column=0, sticky="w", padx=(16, 8), pady=8)
        self.ai_gpu_menu = ctk.CTkOptionMenu(self.ai_limit_frame, variable=self.ai_gpu_var, values=self.gpu_labels, width=330)
        self.ai_gpu_menu.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(0, 16), pady=8)

        ctk.CTkLabel(self.ai_limit_frame, text="Tile size:").grid(row=2, column=0, sticky="w", padx=(16, 8), pady=8)
        self.ai_tile_menu = ctk.CTkOptionMenu(self.ai_limit_frame, variable=self.ai_tile_size_var, values=AI_TILE_SIZES, width=120)
        self.ai_tile_menu.grid(row=2, column=1, sticky="w", pady=8)

        ctk.CTkLabel(self.ai_limit_frame, text="Thread config:").grid(row=3, column=0, sticky="w", padx=(16, 8), pady=8)
        self.ai_thread_menu = ctk.CTkOptionMenu(self.ai_limit_frame, variable=self.ai_thread_config_var, values=AI_THREAD_CONFIGS, width=120)
        self.ai_thread_menu.grid(row=3, column=1, sticky="w", pady=8)

        ctk.CTkLabel(self.ai_limit_frame, text="Пауза между файлами:").grid(row=4, column=0, sticky="w", padx=(16, 8), pady=(8, 14))
        self.ai_cooldown_menu = ctk.CTkOptionMenu(self.ai_limit_frame, variable=self.ai_cooldown_var, values=AI_COOLDOWN_SECONDS, width=120)
        self.ai_cooldown_menu.grid(row=4, column=1, sticky="w", pady=(8, 14))

        ctk.CTkLabel(
            self.ai_limit_frame,
            text="Меньше tile size и слабее thread config — ниже пиковая нагрузка, но дольше обработка.",
            anchor="w",
            justify="left",
            wraplength=360,
        ).grid(row=5, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 14))

    def build_buttons(self, parent):
        parent.grid_columnconfigure(0, weight=1)

        self.reset_button = ctk.CTkButton(
            parent,
            text="↺",
            command=self.reset_to_defaults,
            width=42,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        self.reset_button.grid(row=0, column=0, sticky="w")
        attach_tooltip(self.reset_button, "Сбросить настройки к значениям по умолчанию")

        self.close_button = ctk.CTkButton(
            parent,
            text="Закрыть",
            command=self.on_close_attempt,
            width=120,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        self.close_button.grid(row=0, column=1, sticky="e", padx=(0, 10))

        self.start_button = ctk.CTkButton(parent, text="Начать обработку", command=self.start_processing, width=170)
        self.start_button.grid(row=0, column=2, sticky="e")

    # =========================
    # Actions
    # =========================

    def choose_folder(self):
        initial_dir = self.folder_path_var.get().strip()
        if not initial_dir or not Path(initial_dir).exists():
            initial_dir = str(Path.home())

        selected = filedialog.askdirectory(title="Выберите папку с изображениями", initialdir=initial_dir)
        if selected:
            self.folder_path_var.set(selected)

    def open_selected_folder(self):
        folder = Path(self.folder_path_var.get().strip())
        if not folder.exists() or not folder.is_dir():
            messagebox.showerror("Ошибка", "Папка не найдена.")
            return

        try:
            os.startfile(folder)
        except Exception as exc:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку:\n\n{exc}")

    def start_processing(self):
        source_dir = Path(self.folder_path_var.get().strip())

        if not source_dir.exists() or not source_dir.is_dir():
            messagebox.showerror("Ошибка", "Укажи существующую папку с изображениями.")
            return

        settings = self.make_settings()
        if settings is None:
            return

        if self.save_settings_var.get():
            if not self.save_current_settings_if_needed():
                return

        self.processing_started = True
        self.withdraw()

        self.progress_window = ProgressWindow(
            root=self,
            source_dir=source_dir,
            settings=settings,
            on_back_to_settings=self.show_settings_again,
        )

    def show_settings_again(self):
        try:
            if self.progress_window is not None and self.progress_window.winfo_exists():
                self.progress_window.destroy()
        except Exception:
            pass

        self.progress_window = None
        self.processing_started = False
        self.deiconify()
        self.lift()
        self.focus_force()

    def make_settings(self):
        try:
            min_width = int(self.min_width_var.get())
            min_height = int(self.min_height_var.get())
            jpeg_quality = int(self.quality_var.get())
            max_workers = int(self.max_workers_var.get())
            ai_scale = int(self.ai_scale_var.get())
            ai_tile_size = int(self.ai_tile_size_var.get())
            ai_cooldown_seconds = float(self.ai_cooldown_var.get())
        except Exception:
            messagebox.showerror("Ошибка", "Проверь числовые параметры.")
            return None

        if min_width < 1 or min_height < 1:
            messagebox.showerror("Ошибка", "Минимальная ширина и высота должны быть больше 0.")
            return None

        if jpeg_quality < 1 or jpeg_quality > 100:
            messagebox.showerror("Ошибка", "Качество JPG должно быть от 1 до 100.")
            return None

        if max_workers < 1:
            messagebox.showerror("Ошибка", "Количество потоков должно быть больше 0.")
            return None

        mode = self.process_mode_var.get()
        use_ai = mode == "ai"
        use_threads = mode == "threads"

        if use_ai:
            ai_exe_path = str(REAL_ESRGAN_EXE)
            if not Path(ai_exe_path).is_file():
                messagebox.showerror(
                    "Ошибка",
                    "Файл Real-ESRGAN не найден.\n\n"
                    "Ожидаемый путь:\n"
                    f"{ai_exe_path}\n\n"
                    "Проверь папку rnv рядом с .py файлами.",
                )
                return None
        else:
            ai_exe_path = ""

        return AppSettings(
            min_width=min_width,
            min_height=min_height,
            jpeg_quality=jpeg_quality,
            use_ai=use_ai,
            use_threads=use_threads,
            max_workers=1 if use_ai or not use_threads else max_workers,
            ai_exe_path=ai_exe_path,
            ai_model=self.ai_model_var.get(),
            ai_scale=ai_scale,
            keep_original_if_no_resize=self.keep_original_var.get(),
            overwrite_files=self.overwrite_files_var.get(),
            auto_style_analysis=self.auto_style_analysis_var.get(),
            advanced_monitoring=self.advanced_monitoring_var.get(),
            save_settings=self.save_settings_var.get(),
            ai_gpu_id=self.get_selected_gpu_id(),
            ai_tile_size=ai_tile_size,
            ai_thread_config=self.ai_thread_config_var.get(),
            ai_cooldown_seconds=ai_cooldown_seconds,
        )

    def reset_to_defaults(self):
        answer = messagebox.askyesno(
            "Сброс настроек",
            "Вернуть настройки обработки к значениям по умолчанию?\n\nПуть к выбранной папке не будет очищен.",
        )

        if not answer:
            return

        self.size_preset_var.set("Указать вручную")
        self.min_width_var.set(str(DEFAULT_MIN_WIDTH))
        self.min_height_var.set(str(DEFAULT_MIN_HEIGHT))
        self.quality_var.set(str(DEFAULT_JPEG_QUALITY))

        self.process_mode_var.set("threads")
        self.max_workers_var.set("4")

        self.ai_model_var.set(DEFAULT_AI_MODEL)
        self.auto_style_analysis_var.set(False)
        self.ai_scale_var.set(str(DEFAULT_AI_SCALE))

        self.keep_original_var.set(True)
        self.overwrite_files_var.set(False)
        self.advanced_monitoring_var.set(True)
        self.save_settings_var.set(True)

        self.ai_gpu_var.set(self.get_gpu_label_by_id(int(DEFAULT_AI_GPU_ID)))
        self.ai_tile_size_var.set(str(DEFAULT_AI_TILE_SIZE))
        self.ai_thread_config_var.set(DEFAULT_AI_THREAD_CONFIG)
        self.ai_cooldown_var.set(str(DEFAULT_AI_COOLDOWN_SECONDS))

        self.on_size_preset_changed()
        self.on_process_mode_changed()
        self.on_auto_style_changed()

    def on_close_attempt(self):
        if self.processing_started:
            self.destroy()
            return

        current_snapshot = self.collect_settings_for_json()
        if self.initial_settings_snapshot == current_snapshot:
            self.destroy()
            return

        answer = messagebox.askyesnocancel(
            "Сохранение настроек",
            "Настройки были изменены. Сохранить их перед закрытием?",
        )

        if answer is None:
            return

        if answer:
            if not self.save_current_settings_if_needed(force=True):
                return

        self.destroy()

    # =========================
    # UI state
    # =========================

    def on_size_preset_changed(self, autosize: bool = True):
        preset = SIZE_PRESETS.get(self.size_preset_var.get())

        if preset is None:
            self.manual_size_frame.grid()
            return

        width, height = preset
        self.min_width_var.set(str(width))
        self.min_height_var.set(str(height))
        self.manual_size_frame.grid_remove()

    def on_process_mode_changed(self, autosize: bool = True):
        mode = self.process_mode_var.get()

        if mode == "ai":
            self.max_workers_var.set("1")
            self.workers_menu.configure(state="disabled")
            self.ai_frame.grid()
            self.ai_limit_frame.grid()
        elif mode == "threads":
            self.workers_menu.configure(state="normal")
            self.ai_frame.grid_remove()
            self.ai_limit_frame.grid_remove()
        else:
            self.max_workers_var.set("1")
            self.workers_menu.configure(state="disabled")
            self.ai_frame.grid_remove()
            self.ai_limit_frame.grid_remove()

    def on_auto_style_changed(self):
        if self.auto_style_analysis_var.get():
            self.ai_model_menu.configure(state="disabled")
        else:
            self.ai_model_menu.configure(state="normal")

    def autosize_window(self):
        if self._initial_autosized:
            return

        self.update_idletasks()

        width = max(920, self.winfo_reqwidth() + 24)
        height = max(650, self.winfo_reqheight() + 24)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        width = min(width, screen_width - 80)
        height = min(height, screen_height - 100)

        x = max(0, int((screen_width - width) / 2))
        y = max(0, int((screen_height - height) / 2))

        self.geometry(f"{width}x{height}+{x}+{y}")
        self._initial_autosized = True

    # =========================
    # GPU helpers
    # =========================

    @staticmethod
    def extract_gpu_id(label: str) -> int:
        try:
            first = label.split("—", 1)[0].strip()
            return int(first)
        except Exception:
            return 0

    def get_gpu_label_by_id(self, gpu_id: int) -> str:
        for label in self.gpu_labels:
            if self.extract_gpu_id(label) == gpu_id:
                return label
        return self.gpu_labels[0]

    def get_selected_gpu_id(self) -> int:
        return int(self.gpu_label_to_id.get(self.ai_gpu_var.get(), 0))

    # =========================
    # Helpers
    # =========================

    @staticmethod
    def safe_int(value, fallback: int) -> int:
        try:
            return int(value)
        except Exception:
            return fallback

    @staticmethod
    def safe_float(value, fallback: float) -> float:
        try:
            return float(value)
        except Exception:
            return fallback
