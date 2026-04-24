from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from app_models import ProcessingStats
from image_processing import ImageProcessor
from localization import Translator
from ui_helpers import attach_tooltip
from ui_icons import get_icon, get_logo
from windows.base import BaseToplevelWindow


ICON_BUTTON_SIZE = 46


class ProgressWindow(BaseToplevelWindow):
    def __init__(
        self,
        root,
        source_dir: Path,
        settings,
        translator: Translator | None = None,
        selected_files: list[Path] | None = None,
        on_back_to_settings=None,
    ):
        super().__init__(root)

        self.root = root
        self.source_dir = Path(source_dir)
        self.settings = settings
        self.selected_files = [Path(file_path) for file_path in selected_files] if selected_files else []
        self.translator = translator or Translator("en")
        self.t = self.translator.t
        self.on_back_to_settings = on_back_to_settings

        self.processor: ImageProcessor | None = None
        self.processing_finished = False
        self.cancel_requested = False
        self._initial_autosized = False

        self.copied_files: list[str] = []
        self.processed_files: list[str] = []
        self.error_files: list[str] = []

        self.configure_window(
            title=self.t("app.processing_title"),
            min_size=(820, 520),
            resizable=(True, True),
            close_command=self.on_close_attempt,
        )

        self.current_file_var = ctk.StringVar(value=self.t("progress.initial.file"))
        self.total_progress_var = ctk.StringVar(value=self.t("progress.total", done=0, total=0, percent=0))
        self.current_progress_var = ctk.StringVar(value=self.t("progress.current.percent", percent=0))
        self.state_var = ctk.StringVar(value=self.t("progress.state.preparing"))

        self.copied_counter_var = ctk.StringVar(value=self.t("progress.copied", count=0, total=0, percent=0))
        self.processed_counter_var = ctk.StringVar(value=self.t("progress.processed", count=0, total=0, percent=0))
        self.error_counter_var = ctk.StringVar(value=self.t("progress.errors", count=0, total=0, percent=0))

        self.build_ui()
        self.after(80, self.autosize_window)

        self.lift()
        self.focus_force()

        self.start_processing()

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

        content = ctk.CTkFrame(root_frame)
        content.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(9, weight=1)

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

        ctk.CTkLabel(header, text="", image=get_logo()).grid(row=0, column=0, sticky="w", padx=(0, 10))

        ctk.CTkLabel(
            header,
            text=self.t("progress.header"),
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            content,
            text=self.get_source_text(),
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        mode_text = self.t("progress.mode.ai") if self.settings.use_ai else self.t("progress.mode.pillow")
        thread_text = (
            self.t("progress.threads.many", count=self.settings.max_workers)
            if self.settings.use_threads
            else self.t("progress.threads.one")
        )

        ctk.CTkLabel(
            content,
            text=self.t(
                "progress.mode",
                mode=mode_text,
                threads=thread_text,
                width=self.settings.min_width,
                height=self.settings.min_height,
            ),
            anchor="w",
            justify="left",
        ).grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))

        ctk.CTkLabel(content, textvariable=self.state_var, anchor="w").grid(
            row=3, column=0, sticky="ew", padx=16, pady=(0, 8)
        )

        if self.settings.advanced_monitoring:
            ctk.CTkLabel(content, textvariable=self.current_file_var, anchor="w").grid(
                row=4, column=0, sticky="ew", padx=16, pady=(0, 10)
            )

        ctk.CTkLabel(content, textvariable=self.total_progress_var, anchor="w").grid(
            row=5, column=0, sticky="ew", padx=16
        )

        self.total_bar = ctk.CTkProgressBar(content)
        self.total_bar.grid(row=6, column=0, sticky="ew", padx=16, pady=(4, 12))
        self.total_bar.set(0)

        ctk.CTkLabel(content, textvariable=self.current_progress_var, anchor="w").grid(
            row=7, column=0, sticky="ew", padx=16
        )

        self.current_bar = ctk.CTkProgressBar(content)
        self.current_bar.grid(row=8, column=0, sticky="ew", padx=16, pady=(4, 16))
        self.current_bar.set(0)

        self.advanced_frame = ctk.CTkFrame(content)
        self.advanced_frame.grid(row=9, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.advanced_frame.grid_columnconfigure(0, weight=1, uniform="stats")
        self.advanced_frame.grid_columnconfigure(1, weight=1, uniform="stats")
        self.advanced_frame.grid_columnconfigure(2, weight=1, uniform="stats")
        self.advanced_frame.grid_rowconfigure(0, weight=1)
        self.build_advanced_monitoring(self.advanced_frame)

        if not self.settings.advanced_monitoring:
            self.advanced_frame.grid_remove()

        self.buttons_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.buttons_frame.grid(row=10, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.buttons_frame.grid_columnconfigure(0, weight=1)

        self.pause_button = ctk.CTkButton(
            self.buttons_frame,
            text="",
            image=get_icon("pause"),
            width=ICON_BUTTON_SIZE,
            height=ICON_BUTTON_SIZE,
            command=self.toggle_pause,
        )
        self.pause_button.grid(row=0, column=1, sticky="e", padx=(0, 10))
        self.pause_tooltip = attach_tooltip(self.pause_button, self.t("progress.pause_tooltip"))

        self.cancel_button = ctk.CTkButton(
            self.buttons_frame,
            text=self.t("progress.cancel"),
            width=130,
            height=ICON_BUTTON_SIZE,
            fg_color="#8a1f1f",
            hover_color="#6f1818",
            command=self.cancel_processing,
        )
        self.cancel_button.grid(row=0, column=2, sticky="e")

        self.back_button = ctk.CTkButton(
            self.buttons_frame,
            text=self.t("progress.back_to_settings"),
            width=170,
            height=ICON_BUTTON_SIZE,
            command=self.back_to_settings,
        )

        self.close_button = ctk.CTkButton(
            self.buttons_frame,
            text=self.t("progress.close"),
            width=130,
            height=ICON_BUTTON_SIZE,
            command=self.close_all,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        )

    def build_advanced_monitoring(self, parent):
        copied_frame = ctk.CTkFrame(parent)
        copied_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)
        copied_frame.grid_columnconfigure(0, weight=1)
        copied_frame.grid_rowconfigure(1, weight=1)

        processed_frame = ctk.CTkFrame(parent)
        processed_frame.grid(row=0, column=1, sticky="nsew", padx=6, pady=0)
        processed_frame.grid_columnconfigure(0, weight=1)
        processed_frame.grid_rowconfigure(1, weight=1)

        error_frame = ctk.CTkFrame(parent)
        error_frame.grid(row=0, column=2, sticky="nsew", padx=(6, 0), pady=0)
        error_frame.grid_columnconfigure(0, weight=1)
        error_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            copied_frame,
            textvariable=self.copied_counter_var,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        self.copied_box = ctk.CTkTextbox(copied_frame, height=140, width=240)
        self.copied_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.copied_box.configure(state="disabled")

        ctk.CTkLabel(
            processed_frame,
            textvariable=self.processed_counter_var,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        self.processed_box = ctk.CTkTextbox(processed_frame, height=140, width=240)
        self.processed_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.processed_box.configure(state="disabled")

        ctk.CTkLabel(
            error_frame,
            textvariable=self.error_counter_var,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        self.error_box = ctk.CTkTextbox(error_frame, height=140, width=240)
        self.error_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.error_box.configure(state="disabled")

    # =========================
    # Processing
    # =========================

    def start_processing(self):
        self.processor = ImageProcessor(
            source_dir=self.source_dir,
            settings=self.settings,
            selected_files=self.selected_files,
            callbacks={
                "status": self.on_status,
                "total_progress": self.on_total_progress,
                "current_progress": self.on_current_progress,
                "file_started": self.on_file_started,
                "file_copied": self.on_file_copied,
                "file_processed": self.on_file_processed,
                "file_error": self.on_file_error,
                "stats": self.on_stats,
                "finished": self.on_finished,
                "translate": self.t,
            },
        )
        self.processor.start()

    def get_source_text(self) -> str:
        if self.selected_files:
            return self.t(
                "progress.selected_files",
                count=len(self.selected_files),
                folder=self.settings.output_base_dir or self.source_dir,
                result_folder=self.settings.output_folder_name,
            )

        return self.t("progress.folder", path=self.source_dir)

    def toggle_pause(self):
        if not self.processor or self.processing_finished:
            return

        if self.processor.is_paused():
            self.processor.resume()
            self.pause_button.configure(image=get_icon("pause"))
            self.pause_tooltip.text = self.t("progress.pause_tooltip")
            self.state_var.set(self.t("processor.state.resumed"))
        else:
            self.processor.pause()
            self.pause_button.configure(image=get_icon("play"))
            self.pause_tooltip.text = self.t("progress.resume_tooltip")
            self.state_var.set(self.t("processor.state.paused"))

    def cancel_processing(self):
        if not self.processor or self.processing_finished:
            return

        answer = messagebox.askyesno(
            self.t("progress.cancel_title"),
            self.t("progress.cancel_message"),
        )

        if not answer:
            return

        self.cancel_requested = True
        self.processor.cancel()
        self.pause_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")
        self.state_var.set(self.t("processor.state.cancelling"))

    # =========================
    # Callbacks from processor
    # =========================

    def on_status(self, text: str):
        self.safe_ui(lambda: self.state_var.set(text))

    def on_file_started(self, filename: str):
        self.safe_ui(lambda: self.current_file_var.set(self.t("progress.file", filename=filename)))

    def on_total_progress(self, done: int, total: int, percent: int):
        def _update():
            self.total_bar.set(percent / 100)
            self.total_progress_var.set(self.t("progress.total", done=done, total=total, percent=percent))
            self.update_counters(total)

        self.safe_ui(_update)

    def on_current_progress(self, percent: int, text: str = ""):
        def _update():
            percent_fixed = max(0, min(100, int(percent)))
            self.current_bar.set(percent_fixed / 100)
            if text:
                self.current_progress_var.set(self.t("progress.current.text", text=text))
            else:
                self.current_progress_var.set(self.t("progress.current.percent", percent=percent_fixed))

        self.safe_ui(_update)

    def on_file_copied(self, filename: str):
        def _update():
            self.copied_files.append(filename)
            if self.settings.advanced_monitoring:
                self.append_textbox(self.copied_box, filename)
            self.update_counters(self.get_total_count())

        self.safe_ui(_update)

    def on_file_processed(self, filename: str):
        def _update():
            self.processed_files.append(filename)
            if self.settings.advanced_monitoring:
                self.append_textbox(self.processed_box, filename)
            self.update_counters(self.get_total_count())

        self.safe_ui(_update)

    def on_file_error(self, filename: str, error: str = ""):
        def _update():
            self.error_files.append(filename)
            if self.settings.advanced_monitoring:
                short = filename if not error else self.t("progress.file_error_short", filename=filename)
                self.append_textbox(self.error_box, short)
            self.update_counters(self.get_total_count())

        self.safe_ui(_update)

    def on_stats(self, stats: ProcessingStats):
        def _update():
            self.update_counters(stats.total_count)

        self.safe_ui(_update)

    def on_finished(self, cancelled: bool, errors_count: int, result_dir: Path):
        def _update():
            self.processing_finished = True

            self.pause_button.grid_remove()
            self.cancel_button.grid_remove()
            self.back_button.grid(row=0, column=1, sticky="e", padx=(0, 10))
            self.close_button.grid(row=0, column=2, sticky="e")

            if cancelled:
                self.state_var.set(self.t("progress.finished_cancelled"))
            elif errors_count:
                self.state_var.set(self.t("progress.finished_errors", count=errors_count))
            else:
                self.state_var.set(self.t("progress.finished_success"))

            self.current_progress_var.set(self.t("progress.result", path=result_dir))

        self.safe_ui(_update)

    # =========================
    # Helpers
    # =========================

    def safe_ui(self, func):
        try:
            self.after(0, func)
        except Exception:
            pass

    def append_textbox(self, box: ctk.CTkTextbox, text: str):
        box.configure(state="normal")
        box.insert("end", text + "\n")
        box.see("end")
        box.configure(state="disabled")

    def update_counters(self, total: int):
        copied_count = len(self.copied_files)
        processed_count = len(self.processed_files)
        error_count = len(self.error_files)

        copied_percent = int(copied_count / total * 100) if total else 0
        processed_percent = int(processed_count / total * 100) if total else 0
        error_percent = int(error_count / total * 100) if total else 0

        self.copied_counter_var.set(self.t("progress.copied", count=copied_count, total=total, percent=copied_percent))
        self.processed_counter_var.set(self.t("progress.processed", count=processed_count, total=total, percent=processed_percent))
        self.error_counter_var.set(self.t("progress.errors", count=error_count, total=total, percent=error_percent))

    def get_total_count(self) -> int:
        try:
            return self.processor.total_count if self.processor else 0
        except Exception:
            return len(self.copied_files) + len(self.processed_files) + len(self.error_files)

    def on_close_attempt(self):
        if self.processing_finished:
            self.close_all()
            return

        answer = messagebox.askyesno(
            self.t("progress.close_title"),
            self.t("progress.close_message"),
        )

        if answer:
            if self.processor:
                self.processor.cancel()
            self.close_all()

    def back_to_settings(self):
        if self.on_back_to_settings:
            self.on_back_to_settings()
        else:
            self.destroy()

    def close_all(self):
        try:
            if self.processor and not self.processing_finished:
                self.processor.cancel()
        except Exception:
            pass

        try:
            self.destroy()
        finally:
            try:
                self.root.destroy()
            except Exception:
                pass

    def autosize_window(self):
        if self._initial_autosized:
            return

        self.autosize_to_content(min_width=820, min_height=520)
        self._initial_autosized = True
