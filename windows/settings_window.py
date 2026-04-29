import os
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app_theme import (
    DEFAULT_COLOR_THEME,
    get_theme_settings,
    list_themes,
)
from app_config import (
    CLIP_MODEL_REPO,
    DISPLAY_NAME,
    DEFAULT_MIN_WIDTH,
    DEFAULT_MIN_HEIGHT,
    DEFAULT_JPEG_QUALITY,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_OUTPUT_FOLDER_NAME,
    SIZE_PRESETS,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_SCALE,
    DEFAULT_AI_GPU_ID,
    DEFAULT_AI_TILE_SIZE,
    DEFAULT_AI_THREAD_CONFIG,
    DEFAULT_AI_COOLDOWN_SECONDS,
    SUPPORTED_REAL_ESRGAN_MODELS_RELEASE,
    SUPPORTED_REAL_ESRGAN_RUNTIME_RELEASE,
    get_clip_model_dir,
    get_downloaded_real_esrgan_exe,
    get_real_esrgan_tool_dir,
)
from ai_assets import (
    download_clip_model,
    download_real_esrgan,
    get_clip_download_size,
    is_real_esrgan_available,
    is_clip_model_available,
)
from app_models import AppSettings
from localization import Translator, list_languages, normalize_language_code
from settings_storage import (
    load_settings_json,
    save_settings_json,
    open_settings_folder,
    detect_real_esrgan_gpus,
)
from ui_icons import get_icon, get_logo
from ui_helpers import attach_tooltip
from windows.base import BaseDialog, BaseMainWindow
from windows.progress_window import ProgressWindow
from windows.settings_dialogs import AiDialog, AssetDownloadDialog, ThemeDialog


ICON_BUTTON_SIZE = 46


class SettingsWindow(BaseMainWindow):
    def __init__(self):
        super().__init__()

        self.configure_window(
            title=DISPLAY_NAME,
            min_size=(920, 650),
            resizable=(True, True),
            close_command=self.on_close_attempt,
        )

        self.progress_window = None
        self.processing_started = False
        self.initial_settings_snapshot = None
        self._initial_autosized = False
        self._settings_window_was_maximized = False

        self.loaded_settings = self.safe_load_settings()
        self.theme_settings = get_theme_settings(self.loaded_settings)
        self.available_languages = list_languages()
        self.language_code = self.get_initial_language_code()
        self.translator = Translator(self.language_code)
        self.t = self.translator.t
        self.title(self.t("app.settings_title"))

        self.folder_path_var = ctk.StringVar(value=self.loaded_settings.get("last_folder", ""))
        self.selected_file_paths: list[Path] = []
        self.selected_files_count_var = ctk.StringVar(value="")
        self.source_mode_labels = {}
        self.source_mode_var = ctk.StringVar(value=self.get_source_mode_label(self.loaded_settings.get("source_mode", "folder")))
        self.preset_label_to_id = {}
        self.size_preset_var = ctk.StringVar(value=self.get_preset_label(self.get_saved_preset_id()))
        self.min_width_var = ctk.StringVar(value=str(self.loaded_settings.get("min_width", DEFAULT_MIN_WIDTH)))
        self.min_height_var = ctk.StringVar(value=str(self.loaded_settings.get("min_height", DEFAULT_MIN_HEIGHT)))
        self.quality_var = ctk.StringVar(value=str(self.loaded_settings.get("jpeg_quality", DEFAULT_JPEG_QUALITY)))
        self.output_format_labels = {}
        self.output_format_var = ctk.StringVar(
            value=self.get_output_format_label(self.loaded_settings.get("output_format", DEFAULT_OUTPUT_FORMAT))
        )
        self.output_folder_name_var = ctk.StringVar(
            value=str(self.loaded_settings.get("output_folder_name", DEFAULT_OUTPUT_FOLDER_NAME))
        )
        self.process_mode_var = ctk.StringVar(value=self.loaded_settings.get("process_mode", "threads"))
        self.max_workers_var = ctk.StringVar(value=str(self.loaded_settings.get("max_workers", 4)))
        self.ai_model_var = ctk.StringVar(value=self.loaded_settings.get("ai_model", DEFAULT_AI_MODEL))
        self.auto_style_analysis_var = ctk.BooleanVar(value=bool(self.loaded_settings.get("auto_style_analysis", False)))
        self.ai_scale_var = ctk.StringVar(value=str(self.loaded_settings.get("ai_scale", DEFAULT_AI_SCALE)))
        self.keep_original_var = ctk.BooleanVar(value=bool(self.loaded_settings.get("keep_original_if_no_resize", True)))
        self.overwrite_files_var = ctk.BooleanVar(value=bool(self.loaded_settings.get("overwrite_files", False)))
        self.save_settings_var = ctk.BooleanVar(value=bool(self.loaded_settings.get("save_settings", True)))
        self.advanced_monitoring_var = ctk.BooleanVar(value=bool(self.loaded_settings.get("advanced_monitoring", True)))
        self.language_label_to_code = {language.name: language.code for language in self.available_languages}
        self.language_var = ctk.StringVar(value=self.get_language_label(self.language_code))
        self.appearance_mode_var = ctk.StringVar(value=self.theme_settings["appearance_mode"])
        self.available_themes = list_themes()
        self.theme_label_to_id = {theme.name: theme.theme_id for theme in self.available_themes}
        self.theme_var = ctk.StringVar(value=self.get_theme_label(self.theme_settings["theme_id"]))

        self.gpu_labels = detect_real_esrgan_gpus()
        if not self.gpu_labels or self.gpu_labels == ["0 — основная видеокарта / авто"]:
            self.gpu_labels = [self.t("gpu.default")]
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

    def get_initial_language_code(self) -> str:
        saved_language = self.loaded_settings.get("language")
        available_codes = {language.code for language in self.available_languages}

        if saved_language in available_codes:
            return str(saved_language)

        if self.available_languages:
            selected_language = self.choose_language_on_first_launch()
            self.loaded_settings["language"] = selected_language

            try:
                save_settings_json(self.loaded_settings)
            except Exception:
                pass

            return selected_language

        return normalize_language_code(saved_language)

    def choose_language_on_first_launch(self) -> str:
        selected = {"code": normalize_language_code(None)}

        try:
            self.withdraw()

            dialog = BaseDialog(self, title="Choose language / Выбор языка", width=320, height=220, autosize=True)
            dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

            frame = ctk.CTkFrame(dialog)
            frame.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
            frame.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                frame,
                text="Choose interface language\nВыберите язык интерфейса",
                font=ctk.CTkFont(size=18, weight="bold"),
                justify="center",
            ).grid(row=0, column=0, sticky="ew", pady=(4, 8))

            ctk.CTkLabel(
                frame,
                text="Language packs are loaded from the lang folder.",
                justify="center",
            ).grid(row=1, column=0, sticky="ew", pady=(0, 14))

            for row, language in enumerate(self.available_languages, start=2):
                button = ctk.CTkButton(
                    frame,
                    text=language.name,
                    width=240,
                    command=lambda code=language.code: self.finish_language_choice(dialog, selected, code),
                )
                button.grid(row=row, column=0, sticky="ew", pady=4)

            self.update_idletasks()
            dialog.autosize_modal(min_width=320, min_height=220)
            dialog.activate()

            self.wait_window(dialog)
        except Exception:
            pass
        finally:
            try:
                self.deiconify()
            except Exception:
                pass

        return normalize_language_code(selected["code"])

    @staticmethod
    def finish_language_choice(dialog, selected: dict, code: str):
        selected["code"] = code
        dialog.destroy()

    def collect_settings_for_json(self) -> dict:
        return {
            "last_folder": self.folder_path_var.get().strip(),
            "size_preset": self.size_preset_var.get(),
            "min_width": self.safe_int(self.min_width_var.get(), DEFAULT_MIN_WIDTH),
            "min_height": self.safe_int(self.min_height_var.get(), DEFAULT_MIN_HEIGHT),
            "jpeg_quality": self.safe_int(self.quality_var.get(), DEFAULT_JPEG_QUALITY),
            "output_format": self.get_output_format(),
            "output_folder_name": self.output_folder_name_var.get().strip() or DEFAULT_OUTPUT_FOLDER_NAME,
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
            "window_maximized": self.is_window_maximized(),
            "language": self.language_code,
            "size_preset_id": self.get_selected_preset_id(),
            "source_mode": self.get_source_mode(),
            "theme_mode": "folder",
            "theme_id": self.get_selected_theme_id(),
            "appearance_mode": self.appearance_mode_var.get(),
            "color_theme": self.get_selected_theme_id(),
        }

    def save_current_settings_if_needed(self, force: bool = False) -> bool:
        if not force and not self.save_settings_var.get():
            return True

        try:
            save_settings_json(self.collect_settings_for_json())
            self.initial_settings_snapshot = self.collect_settings_for_json()
            return True
        except Exception as exc:
            messagebox.showwarning(
                self.t("settings.dialog.save_warning"),
                self.t("settings.dialog.save_warning_message", error=exc),
            )
            return False

    def get_preset_labels(self) -> list[str]:
        self.preset_label_to_id = {}
        labels = []

        for preset_id, (label, _size) in SIZE_PRESETS.items():
            display_label = self.t("settings.preset.custom") if preset_id == "custom" else label
            self.preset_label_to_id[display_label] = preset_id
            labels.append(display_label)

        return labels

    def get_preset_label(self, preset_id: str) -> str:
        label, _size = SIZE_PRESETS.get(preset_id, SIZE_PRESETS["custom"])
        return self.t("settings.preset.custom") if preset_id == "custom" else label

    def get_selected_preset_id(self) -> str:
        return self.preset_label_to_id.get(self.size_preset_var.get(), "custom")

    def get_saved_preset_id(self) -> str:
        saved_preset_id = self.loaded_settings.get("size_preset_id")
        if saved_preset_id in SIZE_PRESETS:
            return str(saved_preset_id)

        saved_label = self.loaded_settings.get("size_preset", "")
        if saved_label == "Указать вручную":
            return "custom"

        for preset_id, (label, _size) in SIZE_PRESETS.items():
            if saved_label == label:
                return preset_id

        return "custom"

    def get_output_format_labels(self) -> list[str]:
        self.output_format_labels = {
            self.t("settings.format.keep"): "keep",
            "JPG": "jpg",
            "PNG": "png",
            "WEBP": "webp",
            "BMP": "bmp",
            "TIFF": "tiff",
        }
        return list(self.output_format_labels.keys())

    def get_output_format_label(self, output_format: str) -> str:
        output_format = str(output_format).lower()
        labels = self.get_output_format_labels()
        for label, value in self.output_format_labels.items():
            if value == output_format:
                return label
        return labels[1]

    def get_output_format(self) -> str:
        return self.output_format_labels.get(self.output_format_var.get(), DEFAULT_OUTPUT_FORMAT)

    def get_language_label(self, language_code: str) -> str:
        for language in self.available_languages:
            if language.code == language_code:
                return language.name
        return language_code

    def get_source_mode_labels(self) -> list[str]:
        self.source_mode_labels = {
            self.t("settings.source.folder_tab"): "folder",
            self.t("settings.source.files_tab"): "files",
        }
        return list(self.source_mode_labels.keys())

    def get_source_mode_label(self, source_mode: str) -> str:
        if source_mode == "files":
            return self.t("settings.source.files_tab")
        return self.t("settings.source.folder_tab")

    def get_source_mode(self) -> str:
        return self.source_mode_labels.get(self.source_mode_var.get(), "folder")

    def get_theme_label(self, theme_id: str) -> str:
        for theme in self.available_themes:
            if theme.theme_id == theme_id:
                return theme.name
        return self.available_themes[0].name if self.available_themes else DEFAULT_COLOR_THEME

    def get_selected_theme_id(self) -> str:
        return self.theme_label_to_id.get(self.theme_var.get(), self.theme_settings["theme_id"])

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

        header = ctk.CTkFrame(self.scroll, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="", image=get_logo()).grid(row=0, column=0, sticky="w", padx=(0, 10))

        ctk.CTkLabel(
            header,
            text=DISPLAY_NAME,
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(header, text=self.t("settings.program.language")).grid(row=0, column=2, sticky="e", padx=(12, 8))
        self.language_menu = ctk.CTkOptionMenu(
            header,
            variable=self.language_var,
            values=[language.name for language in self.available_languages],
            command=self.on_language_changed,
            width=160,
        )
        self.language_menu.grid(row=0, column=3, sticky="e", padx=(0, 10))

        self.design_button = ctk.CTkButton(
            header,
            text="",
            image=get_icon("palette"),
            width=ICON_BUTTON_SIZE,
            height=ICON_BUTTON_SIZE,
            command=self.open_design_dialog,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        self.design_button.grid(row=0, column=4, sticky="e")
        attach_tooltip(self.design_button, self.t("settings.design.open_tooltip"))

        self.build_folder_section(self.scroll, row=1)

        self.left_column = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.left_column.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
        self.left_column.grid_columnconfigure(0, weight=1)
        self.left_column.grid_rowconfigure(0, weight=1)

        self.right_column = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.right_column.grid(row=2, column=1, sticky="nsew", padx=(8, 0))
        self.right_column.grid_columnconfigure(0, weight=1)
        self.right_column.grid_rowconfigure(1, weight=1)

        self.build_size_section(self.left_column, row=1)
        self.build_save_section(self.left_column, row=2)

        self.build_mode_section(self.right_column, row=0)
        self.build_settings_storage_section(self.right_column, row=2)

        self.build_buttons(self.buttons_bar)

    def build_folder_section(self, parent, row: int):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=self.t("settings.source.section"),
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        self.source_mode_switch = ctk.CTkSegmentedButton(
            header,
            values=self.get_source_mode_labels(),
            variable=self.source_mode_var,
            command=lambda _value: self.on_source_mode_changed(),
        )
        self.source_mode_switch.grid(row=0, column=1, sticky="e")

        self.folder_source_panel = ctk.CTkFrame(frame, fg_color="transparent")
        self.folder_source_panel.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.folder_source_panel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.folder_source_panel, text=self.t("settings.folder.path")).grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=0
        )

        self.folder_entry = ctk.CTkEntry(self.folder_source_panel, textvariable=self.folder_path_var)
        self.folder_entry.configure(height=ICON_BUTTON_SIZE)
        self.folder_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=0)

        self.choose_folder_button = ctk.CTkButton(
            self.folder_source_panel,
            text="",
            image=get_icon("folder"),
            width=ICON_BUTTON_SIZE,
            height=ICON_BUTTON_SIZE,
            command=self.choose_folder,
        )
        self.choose_folder_button.grid(row=0, column=2, sticky="e", padx=(0, 8), pady=0)
        attach_tooltip(self.choose_folder_button, self.t("settings.folder.choose_tooltip"))

        self.open_folder_button = ctk.CTkButton(
            self.folder_source_panel,
            text="",
            image=get_icon("external_link"),
            width=ICON_BUTTON_SIZE,
            height=ICON_BUTTON_SIZE,
            command=self.open_selected_folder,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        self.open_folder_button.grid(row=0, column=3, sticky="e", pady=0)
        attach_tooltip(self.open_folder_button, self.t("settings.folder.open_tooltip"))

        self.files_source_panel = ctk.CTkFrame(frame, fg_color="transparent")
        self.files_source_panel.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.files_source_panel.grid_columnconfigure(0, weight=1)
        self.files_source_panel.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            self.files_source_panel,
            textvariable=self.selected_files_count_var,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 8))

        self.files_list_frame = ctk.CTkScrollableFrame(
            self.files_source_panel,
            height=132,
            fg_color=("gray88", "gray18"),
        )
        self.files_list_frame.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.files_list_frame.grid_columnconfigure(0, weight=1)
        self.bind_files_list_mousewheel(self.files_list_frame)

        self.files_actions_frame = ctk.CTkFrame(self.files_source_panel, fg_color="transparent")
        self.files_actions_frame.grid(row=1, column=1, sticky="ns")

        self.add_file_button = ctk.CTkButton(
            self.files_actions_frame,
            text="",
            image=get_icon("add_file"),
            width=ICON_BUTTON_SIZE,
            height=ICON_BUTTON_SIZE,
            command=self.add_files_to_selection,
        )
        self.add_file_button.grid(row=0, column=0, sticky="n", pady=(0, 8))
        attach_tooltip(self.add_file_button, self.t("settings.folder.add_files_tooltip"))

        self.clear_files_button = ctk.CTkButton(
            self.files_actions_frame,
            text="",
            image=get_icon("clear"),
            width=ICON_BUTTON_SIZE,
            height=ICON_BUTTON_SIZE,
            command=self.clear_selected_files,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        self.clear_files_button.grid(row=1, column=0, sticky="n")
        attach_tooltip(self.clear_files_button, self.t("settings.folder.clear_files_tooltip"))

        self.refresh_selected_files_list()
        self.on_source_mode_changed()

    def build_size_section(self, parent, row: int):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text=self.t("settings.size.section"), font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(14, 8)
        )

        ctk.CTkLabel(frame, text=self.t("settings.size.preset")).grid(row=1, column=0, sticky="w", padx=(16, 8), pady=8)
        self.size_preset_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.size_preset_var,
            values=self.get_preset_labels(),
            command=lambda _: self.on_size_preset_changed(),
            width=250,
        )
        self.size_preset_menu.grid(row=1, column=1, sticky="w", padx=(0, 16), pady=8)

        self.manual_size_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.manual_size_frame.grid(row=2, column=0, columnspan=4, sticky="w", padx=16, pady=(4, 10))

        ctk.CTkLabel(self.manual_size_frame, text=self.t("settings.size.width")).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.width_entry = ctk.CTkEntry(self.manual_size_frame, textvariable=self.min_width_var, width=110)
        self.width_entry.grid(row=0, column=1, sticky="w", padx=(0, 18))

        ctk.CTkLabel(self.manual_size_frame, text=self.t("settings.size.height")).grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.height_entry = ctk.CTkEntry(self.manual_size_frame, textvariable=self.min_height_var, width=110)
        self.height_entry.grid(row=0, column=3, sticky="w")

        ctk.CTkLabel(
            frame,
            text=self.t("settings.size.note"),
            anchor="w",
            justify="left",
            wraplength=360,
        ).grid(row=3, column=0, columnspan=4, sticky="ew", padx=16, pady=(2, 14))

    def build_save_section(self, parent, row: int):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text=self.t("settings.save.section"), font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(14, 8)
        )

        ctk.CTkLabel(frame, text=self.t("settings.format.output")).grid(
            row=1, column=0, sticky="w", padx=(16, 8), pady=8
        )
        self.output_format_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.output_format_var,
            values=self.get_output_format_labels(),
            command=lambda _value: self.update_save_quality_controls(),
            width=150,
        )
        self.output_format_menu.grid(row=1, column=1, sticky="w", pady=8)

        self.save_quality_label = ctk.CTkLabel(frame, text=self.t("settings.save.quality"))
        self.save_quality_label.grid(row=2, column=0, sticky="w", padx=(16, 8), pady=8)
        self.save_quality_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.quality_var,
            values=["85", "90", "95", "98", "100"],
            width=90,
        )
        self.save_quality_menu.grid(row=2, column=1, sticky="w", pady=8)

        self.save_quality_note = ctk.CTkLabel(
            frame,
            text=self.t("settings.format.quality_note"),
            anchor="w",
            justify="left",
            wraplength=520,
            text_color=("gray35", "gray65"),
        )
        self.save_quality_note.grid(row=3, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 8))

        ctk.CTkLabel(frame, text=self.t("settings.output_folder.name")).grid(
            row=4, column=0, sticky="w", padx=(16, 8), pady=8
        )
        self.output_folder_name_entry = ctk.CTkEntry(frame, textvariable=self.output_folder_name_var)
        self.output_folder_name_entry.configure(height=ICON_BUTTON_SIZE)
        self.output_folder_name_entry.grid(row=4, column=1, sticky="ew", pady=8)

        self.output_folder_default_button = ctk.CTkButton(
            frame,
            text=self.t("settings.output_folder.default"),
            command=lambda: self.output_folder_name_var.set(DEFAULT_OUTPUT_FOLDER_NAME),
            width=130,
            height=ICON_BUTTON_SIZE,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        self.output_folder_default_button.grid(row=4, column=2, sticky="e", padx=(10, 16), pady=8)

        ctk.CTkCheckBox(
            frame,
            text=self.t("settings.save.keep_original"),
            variable=self.keep_original_var,
        ).grid(row=5, column=0, columnspan=3, sticky="w", padx=16, pady=(10, 4))

        ctk.CTkCheckBox(frame, text=self.t("settings.save.overwrite"), variable=self.overwrite_files_var).grid(
            row=6, column=0, columnspan=3, sticky="w", padx=16, pady=(6, 8)
        )

        ctk.CTkCheckBox(frame, text=self.t("settings.save.advanced_monitoring"), variable=self.advanced_monitoring_var).grid(
            row=7, column=0, columnspan=3, sticky="w", padx=16, pady=(6, 14)
        )
        self.update_save_quality_controls()

    def update_save_quality_controls(self):
        if not hasattr(self, "save_quality_label"):
            return

        if self.get_output_format() in {"jpg", "webp"}:
            self.save_quality_label.grid()
            self.save_quality_menu.grid()
            self.save_quality_note.grid()
        else:
            self.save_quality_label.grid_remove()
            self.save_quality_menu.grid_remove()
            self.save_quality_note.grid_remove()

    def build_settings_storage_section(self, parent, row: int):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(14, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text=self.t("settings.program.section"), font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )

        self.open_settings_button = ctk.CTkButton(
            frame,
            text=self.t("settings.program.open_settings_button"),
            height=ICON_BUTTON_SIZE,
            command=open_settings_folder,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )

        ctk.CTkCheckBox(frame, text=self.t("settings.program.save_last"), variable=self.save_settings_var).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(4, 8)
        )

        self.open_settings_button.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14))
        attach_tooltip(self.open_settings_button, self.t("settings.program.open_settings_tooltip"))

    def build_mode_section(self, parent, row: int):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        frame.grid_columnconfigure(0, weight=0)
        frame.grid_columnconfigure(1, weight=0)
        frame.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(frame, text=self.t("settings.mode.section"), font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(14, 8)
        )

        ctk.CTkRadioButton(
            frame,
            text=self.t("settings.mode.normal"),
            variable=self.process_mode_var,
            value="normal",
            command=self.on_process_mode_changed,
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=16, pady=5)

        ctk.CTkRadioButton(
            frame,
            text=self.t("settings.mode.threads"),
            variable=self.process_mode_var,
            value="threads",
            command=self.on_process_mode_changed,
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=16, pady=5)

        ctk.CTkRadioButton(
            frame,
            text=self.t("settings.mode.ai"),
            variable=self.process_mode_var,
            value="ai",
            command=self.on_process_mode_changed,
        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=16, pady=5)

        ctk.CTkLabel(frame, text=self.t("settings.mode.workers")).grid(row=4, column=0, sticky="w", padx=(16, 8), pady=(10, 14))
        self.workers_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.max_workers_var,
            values=["1", "2", "3", "4", "6", "8", "12", "16"],
            width=90,
        )
        self.workers_menu.grid(row=4, column=1, sticky="w", pady=(10, 14))

        ctk.CTkLabel(
            frame,
            text=self.t("settings.mode.note"),
            anchor="w",
            justify="left",
            wraplength=360,
        ).grid(row=5, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 14))

        self.ai_settings_button = ctk.CTkButton(
            frame,
            text=self.t("settings.ai.open_button"),
            command=self.open_ai_dialog,
            height=ICON_BUTTON_SIZE,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        self.ai_settings_button.grid(row=6, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 14))

    def build_buttons(self, parent):
        parent.grid_columnconfigure(0, weight=1)

        self.reset_button = ctk.CTkButton(
            parent,
            text="",
            image=get_icon("reset"),
            command=self.reset_to_defaults,
            width=ICON_BUTTON_SIZE,
            height=ICON_BUTTON_SIZE,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        self.reset_button.grid(row=0, column=0, sticky="w")
        attach_tooltip(self.reset_button, self.t("settings.buttons.reset_tooltip"))

        self.close_button = ctk.CTkButton(
            parent,
            text=self.t("common.close"),
            command=self.on_close_attempt,
            width=120,
            height=ICON_BUTTON_SIZE,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        self.close_button.grid(row=0, column=1, sticky="e", padx=(0, 10))

        self.start_button = ctk.CTkButton(
            parent,
            text=self.t("settings.buttons.start"),
            command=self.start_processing,
            width=170,
            height=ICON_BUTTON_SIZE,
        )
        self.start_button.grid(row=0, column=2, sticky="e")

    # =========================
    # Actions
    # =========================

    def choose_folder(self):
        initial_dir = self.folder_path_var.get().strip()
        if not initial_dir or not Path(initial_dir).exists():
            initial_dir = str(Path.home())

        selected = filedialog.askdirectory(title=self.t("settings.dialog.choose_folder"), initialdir=initial_dir)
        if selected:
            self.folder_path_var.set(selected)

    def choose_files_replace(self):
        selected_files = self.ask_image_files()
        if not selected_files:
            return

        self.selected_file_paths = []
        self.add_selected_files(selected_files)
        self.update_folder_from_selected_files()

    def add_files_to_selection(self):
        selected_files = self.ask_image_files()
        if not selected_files:
            return

        self.add_selected_files(selected_files)
        self.update_folder_from_selected_files()

    def ask_image_files(self) -> list[Path]:
        initial_dir = self.folder_path_var.get().strip()
        if not initial_dir or not Path(initial_dir).exists():
            initial_dir = str(Path.home())

        selected = filedialog.askopenfilenames(
            title=self.t("settings.dialog.choose_files"),
            initialdir=initial_dir,
            filetypes=[
                (self.t("settings.dialog.image_files"), "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"),
                (self.t("settings.dialog.all_files"), "*.*"),
            ],
        )
        return [Path(file_path) for file_path in selected]

    def add_selected_files(self, file_paths: list[Path]):
        known_paths = {file_path.resolve() for file_path in self.selected_file_paths if file_path.exists()}

        for file_path in file_paths:
            if file_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}:
                continue

            try:
                resolved_path = file_path.resolve()
            except Exception:
                resolved_path = file_path

            if resolved_path in known_paths:
                continue

            self.selected_file_paths.append(file_path)
            known_paths.add(resolved_path)

        self.refresh_selected_files_list()

    def remove_selected_file(self, index: int):
        if 0 <= index < len(self.selected_file_paths):
            self.selected_file_paths.pop(index)

        self.refresh_selected_files_list()

    def clear_selected_files(self):
        self.selected_file_paths = []
        self.refresh_selected_files_list()

    def refresh_selected_files_list(self):
        if not hasattr(self, "files_list_frame"):
            return

        for child in self.files_list_frame.winfo_children():
            child.destroy()

        for file_path in self.selected_file_paths:
            self.add_selected_file_row(file_path)

        if self.selected_file_paths:
            self.selected_files_count_var.set(
                self.t("settings.folder.selected_files_count", count=len(self.selected_file_paths))
            )
        else:
            self.add_empty_files_row()
            self.selected_files_count_var.set(self.t("settings.folder.no_files"))

    def add_selected_file_row(self, file_path: Path):
        index = len(self.files_list_frame.winfo_children())
        row_frame = ctk.CTkFrame(self.files_list_frame, fg_color=("gray92", "gray22"))
        row_frame.grid(row=index, column=0, sticky="ew", padx=5, pady=(5, 0))
        row_frame.grid_columnconfigure(0, weight=1)
        self.bind_files_list_mousewheel(row_frame)

        text_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        text_frame.grid(row=0, column=0, sticky="ew", padx=9, pady=5)
        text_frame.grid_columnconfigure(0, weight=1)
        self.bind_files_list_mousewheel(text_frame)

        name_label = ctk.CTkLabel(
            text_frame,
            text=file_path.name,
            anchor="w",
            justify="left",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        name_label.grid(row=0, column=0, sticky="ew")
        attach_tooltip(name_label, str(file_path))
        self.bind_files_list_mousewheel(name_label)

        parent_label = ctk.CTkLabel(
            text_frame,
            text=str(file_path.parent),
            anchor="w",
            justify="left",
            text_color=("gray35", "gray65"),
            font=ctk.CTkFont(size=11),
        )
        parent_label.grid(row=1, column=0, sticky="ew", pady=(0, 1))
        attach_tooltip(parent_label, str(file_path))
        self.bind_files_list_mousewheel(parent_label)

        remove_button = ctk.CTkButton(
            row_frame,
            text="",
            image=get_icon("remove_file"),
            width=32,
            height=32,
            command=lambda row_index=index: self.remove_selected_file(row_index),
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )
        remove_button.grid(row=0, column=1, sticky="e", padx=(0, 7), pady=5)
        attach_tooltip(remove_button, self.t("settings.folder.remove_file_tooltip"))
        self.bind_files_list_mousewheel(remove_button)


    def add_empty_files_row(self):
        row_frame = ctk.CTkFrame(self.files_list_frame, fg_color="transparent")
        row_frame.grid(row=0, column=0, sticky="ew", padx=6, pady=14)
        row_frame.grid_columnconfigure(0, weight=1)
        self.bind_files_list_mousewheel(row_frame)

        empty_label = ctk.CTkLabel(
            row_frame,
            text=self.t("settings.folder.no_files"),
            text_color=("gray45", "gray60"),
        )
        empty_label.grid(row=0, column=0, sticky="ew")
        self.bind_files_list_mousewheel(empty_label)

    def bind_files_list_mousewheel(self, widget):
        widget.bind("<MouseWheel>", self.on_files_list_mousewheel)
        widget.bind("<Button-4>", self.on_files_list_mousewheel)
        widget.bind("<Button-5>", self.on_files_list_mousewheel)

        canvas = getattr(widget, "_parent_canvas", None)
        if canvas is not None:
            canvas.bind("<MouseWheel>", self.on_files_list_mousewheel)
            canvas.bind("<Button-4>", self.on_files_list_mousewheel)
            canvas.bind("<Button-5>", self.on_files_list_mousewheel)

    def on_files_list_mousewheel(self, event):
        canvas = getattr(self.files_list_frame, "_parent_canvas", None)
        if canvas is None:
            return "break"

        if getattr(event, "num", None) == 4:
            units = -1
        elif getattr(event, "num", None) == 5:
            units = 1
        else:
            delta = getattr(event, "delta", 0)
            units = int(-1 * (delta / 120)) if delta else 0

        if units:
            canvas.yview_scroll(units, "units")

        return "break"

    def update_folder_from_selected_files(self):
        if not self.selected_file_paths:
            return

        first_parent = self.selected_file_paths[0].parent
        self.folder_path_var.set(str(first_parent))

    def open_selected_folder(self):
        folder = Path(self.folder_path_var.get().strip())
        if not folder.exists() or not folder.is_dir():
            messagebox.showerror(self.t("common.error"), self.t("settings.dialog.folder_not_found"))
            return

        try:
            os.startfile(folder)
        except Exception as exc:
            messagebox.showerror(self.t("common.error"), self.t("settings.dialog.open_folder_error", error=exc))

    def open_design_dialog(self):
        ThemeDialog(self)

    def open_ai_dialog(self):
        AiDialog(self)

    def start_processing(self):
        source_mode = self.get_source_mode()
        selected_files = self.get_existing_selected_files() if source_mode == "files" else []
        source_dir = Path(self.folder_path_var.get().strip())

        if selected_files:
            source_dir = selected_files[0].parent

        if source_mode == "files" and not selected_files:
            messagebox.showerror(self.t("common.error"), self.t("settings.dialog.select_files"))
            return

        if source_mode == "folder" and (not source_dir.exists() or not source_dir.is_dir()):
            messagebox.showerror(self.t("common.error"), self.t("settings.dialog.select_valid_folder"))
            return

        settings = self.make_settings()
        if settings is None:
            return

        if selected_files and self.has_multiple_source_folders(selected_files):
            output_base_dir = filedialog.askdirectory(title=self.t("settings.dialog.choose_output_folder"))
            if not output_base_dir:
                return
            settings.output_base_dir = output_base_dir

        if self.save_settings_var.get():
            if not self.save_current_settings_if_needed():
                return

        self.remember_window_state_for_processing()
        self.processing_started = True
        self.withdraw()

        self.progress_window = ProgressWindow(
            root=self,
            source_dir=source_dir,
            settings=settings,
            translator=self.translator,
            selected_files=selected_files,
            on_back_to_settings=self.show_settings_again,
        )

    def get_existing_selected_files(self) -> list[Path]:
        return [
            file_path for file_path in self.selected_file_paths
            if file_path.is_file()
        ]

    @staticmethod
    def has_multiple_source_folders(files: list[Path]) -> bool:
        return len({file_path.parent.resolve() for file_path in files}) > 1

    def show_settings_again(self):
        try:
            if self.progress_window is not None and self.progress_window.winfo_exists():
                self.progress_window.destroy()
        except Exception:
            pass

        self.progress_window = None
        self.processing_started = False
        self.deiconify()
        self.after(0, self.restore_window_state_after_processing)

    def ensure_real_esrgan_ready(self) -> bool:
        exe_path = get_downloaded_real_esrgan_exe()
        if exe_path.is_file() and (exe_path.parent / "models").is_dir():
            return True

        target_path = get_downloaded_real_esrgan_exe()
        answer = messagebox.askyesno(
            self.t("assets.realesrgan.title"),
            self.t(
                "assets.realesrgan.prompt",
                runtime_version=SUPPORTED_REAL_ESRGAN_RUNTIME_RELEASE,
                models_version=SUPPORTED_REAL_ESRGAN_MODELS_RELEASE,
                path=target_path,
                folder=get_real_esrgan_tool_dir(),
            ),
            parent=self,
        )
        if not answer:
            return False

        dialog = AssetDownloadDialog(
            self,
            self.t("assets.realesrgan.title"),
            self.t(
                "assets.realesrgan.downloading",
                runtime_version=SUPPORTED_REAL_ESRGAN_RUNTIME_RELEASE,
                models_version=SUPPORTED_REAL_ESRGAN_MODELS_RELEASE,
                path=target_path,
            ),
            download_real_esrgan,
        )
        self.wait_window(dialog)

        if dialog.error:
            messagebox.showerror(
                self.t("common.error"),
                self.t("assets.download.failed", error=dialog.error),
                parent=self,
            )
            return False

        ready = is_real_esrgan_available()
        if ready:
            self.refresh_gpu_options()
        return ready

    def ensure_clip_model_ready(self) -> bool:
        if is_clip_model_available():
            return True

        model_dir = get_clip_model_dir()
        answer = messagebox.askyesno(
            self.t("assets.clip.title"),
            self.t(
                "assets.clip.prompt",
                model=CLIP_MODEL_REPO,
                size=AssetDownloadDialog.format_bytes(get_clip_download_size()),
                path=model_dir,
            ),
            parent=self,
        )
        if not answer:
            return False

        dialog = AssetDownloadDialog(
            self,
            self.t("assets.clip.title"),
            self.t("assets.clip.downloading", model=CLIP_MODEL_REPO, path=model_dir),
            download_clip_model,
        )
        self.wait_window(dialog)

        if dialog.error:
            messagebox.showerror(
                self.t("common.error"),
                self.t("assets.download.failed", error=dialog.error),
                parent=self,
            )
            return False

        return is_clip_model_available()

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
            messagebox.showerror(self.t("common.error"), self.t("settings.dialog.check_numeric"))
            return None

        if min_width < 1 or min_height < 1:
            messagebox.showerror(self.t("common.error"), self.t("settings.dialog.positive_size"))
            return None

        if jpeg_quality < 1 or jpeg_quality > 100:
            messagebox.showerror(self.t("common.error"), self.t("settings.dialog.quality_range"))
            return None

        if max_workers < 1:
            messagebox.showerror(self.t("common.error"), self.t("settings.dialog.workers_positive"))
            return None

        mode = self.process_mode_var.get()
        use_ai = mode == "ai"
        use_threads = mode == "threads"

        if use_ai:
            if not self.ensure_real_esrgan_ready():
                return None
            ai_exe_path = str(get_downloaded_real_esrgan_exe())

            if self.auto_style_analysis_var.get() and not self.ensure_clip_model_ready():
                return None
        else:
            ai_exe_path = ""

        return AppSettings(
            min_width=min_width,
            min_height=min_height,
            jpeg_quality=jpeg_quality,
            output_format=self.get_output_format(),
            output_folder_name=self.output_folder_name_var.get().strip() or DEFAULT_OUTPUT_FOLDER_NAME,
            output_base_dir=None,
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
            self.t("settings.dialog.reset_title"),
            self.t("settings.dialog.reset_message"),
        )

        if not answer:
            return

        self.size_preset_var.set(self.get_preset_label("custom"))
        self.min_width_var.set(str(DEFAULT_MIN_WIDTH))
        self.min_height_var.set(str(DEFAULT_MIN_HEIGHT))
        self.quality_var.set(str(DEFAULT_JPEG_QUALITY))
        self.output_format_var.set(self.get_output_format_label(DEFAULT_OUTPUT_FORMAT))
        self.output_folder_name_var.set(DEFAULT_OUTPUT_FOLDER_NAME)

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
        if self.initial_settings_snapshot is None:
            self.initial_settings_snapshot = current_snapshot

        if self.initial_settings_snapshot == current_snapshot:
            self.destroy()
            return

        if self.only_window_state_changed(self.initial_settings_snapshot, current_snapshot):
            if self.save_settings_var.get():
                if not self.save_current_settings_if_needed(force=True):
                    return
            self.destroy()
            return

        answer = messagebox.askyesnocancel(
            self.t("settings.dialog.save_changed_title"),
            self.t("settings.dialog.save_changed_message"),
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
        preset_id = self.get_selected_preset_id()
        _label, preset = SIZE_PRESETS.get(preset_id, SIZE_PRESETS["custom"])

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
        elif mode == "threads":
            self.workers_menu.configure(state="normal")
        else:
            self.max_workers_var.set("1")
            self.workers_menu.configure(state="disabled")

        if hasattr(self, "ai_settings_button"):
            if mode == "ai":
                self.ai_settings_button.configure(state="normal")
            else:
                self.ai_settings_button.configure(state="disabled")

    def on_auto_style_changed(self):
        if not hasattr(self, "ai_model_menu"):
            return

        if self.auto_style_analysis_var.get():
            self.ai_model_menu.configure(state="disabled")
        else:
            self.ai_model_menu.configure(state="normal")

    def on_source_mode_changed(self):
        if self.get_source_mode() == "files":
            self.folder_source_panel.grid_remove()
            self.files_source_panel.grid()
        else:
            self.files_source_panel.grid_remove()
            self.folder_source_panel.grid()

    def on_language_changed(self, label: str):
        new_language_code = self.language_label_to_code.get(label, self.language_code)

        if new_language_code == self.language_code:
            return

        self.language_code = normalize_language_code(new_language_code)
        self.translator = Translator(self.language_code)
        self.t = self.translator.t

        if self.save_settings_var.get():
            self.save_current_settings_if_needed(force=True)

        messagebox.showinfo(
            self.t("settings.program.language_restart_title"),
            self.t("settings.program.language_restart_message"),
        )

    def autosize_window(self):
        if self._initial_autosized:
            return

        self.autosize_to_content(min_width=920, min_height=650)
        self._initial_autosized = True
        self.after(60, self.restore_saved_window_state)
        self.after(140, self.capture_initial_settings_snapshot)

    def restore_saved_window_state(self):
        if bool(self.loaded_settings.get("window_maximized", False)):
            try:
                self.state("zoomed")
            except Exception:
                pass

    def remember_window_state_for_processing(self):
        self._settings_window_was_maximized = self.is_window_maximized()

    def restore_window_state_after_processing(self):
        try:
            self.state("zoomed" if self._settings_window_was_maximized else "normal")
        except Exception:
            pass

        self.lift()
        self.focus_force()

    def capture_initial_settings_snapshot(self):
        self.initial_settings_snapshot = self.collect_settings_for_json()

    def is_window_maximized(self) -> bool:
        try:
            return self.state() == "zoomed"
        except Exception:
            return False

    @staticmethod
    def only_window_state_changed(old_settings: dict, new_settings: dict) -> bool:
        old_without_window = dict(old_settings)
        new_without_window = dict(new_settings)

        old_without_window.pop("window_maximized", None)
        new_without_window.pop("window_maximized", None)

        return old_without_window == new_without_window

    # =========================
    # GPU helpers
    # =========================

    @staticmethod
    def extract_gpu_id(label: str) -> int:
        try:
            normalized = label.replace("—", "-")
            first = normalized.split("-", 1)[0].strip()
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

    def refresh_gpu_options(self):
        current_gpu_id = self.get_selected_gpu_id()
        self.gpu_labels = detect_real_esrgan_gpus()
        if not self.gpu_labels or self.gpu_labels == ["0 — основная видеокарта / авто"]:
            self.gpu_labels = [self.t("gpu.default")]

        self.gpu_label_to_id = {label: self.extract_gpu_id(label) for label in self.gpu_labels}
        self.ai_gpu_var.set(self.get_gpu_label_by_id(current_gpu_id))

        if hasattr(self, "ai_gpu_menu"):
            self.ai_gpu_menu.configure(values=self.gpu_labels)

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
