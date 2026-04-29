import threading
import traceback
from tkinter import messagebox

import customtkinter as ctk

from app_theme import load_theme
from ui_icons import clear_icon_cache

from app_config import (
    AI_COOLDOWN_SECONDS,
    AI_MODELS,
    AI_SCALES,
    AI_THREAD_CONFIGS,
    AI_TILE_SIZES,
)
from windows.base import BaseDialog


class AssetDownloadDialog(BaseDialog):
    def __init__(self, owner, title: str, message: str, download_func):
        super().__init__(owner, title=title, width=560, height=260, autosize=True)
        self.owner = owner
        self.download_func = download_func
        self.result = None
        self.error = None
        self.thread = None

        self.message_var = ctk.StringVar(value=message)
        self.progress_var = ctk.StringVar(value=owner.t("assets.download.starting"))

        self.build()
        self.autosize_modal(min_width=560, min_height=260)
        self.activate()
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.after(80, self.start_download)

    def build(self):
        frame = ctk.CTkFrame(self)
        frame.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            textvariable=self.message_var,
            anchor="w",
            justify="left",
            wraplength=480,
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))

        self.progress_bar = ctk.CTkProgressBar(frame)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        self.progress_bar.set(0)

        ctk.CTkLabel(frame, textvariable=self.progress_var, anchor="w").grid(
            row=2, column=0, sticky="ew", padx=16, pady=(0, 16)
        )

    def start_download(self):
        self.thread = threading.Thread(target=self.run_download, daemon=True)
        self.thread.start()

    def run_download(self):
        try:
            self.result = self.download_func(self.on_progress)
        except Exception:
            self.error = traceback.format_exc()

        self.after(0, self.finish)

    def on_progress(self, done: int, total: int):
        def _update():
            if total > 0:
                percent = max(0, min(100, int(done / total * 100)))
                self.progress_bar.set(percent / 100)
                self.progress_var.set(
                    self.owner.t(
                        "assets.download.progress",
                        percent=percent,
                        done=self.format_bytes(done),
                        total=self.format_bytes(total),
                    )
                )
            else:
                self.progress_bar.set(0)
                self.progress_var.set(self.owner.t("assets.download.progress_unknown", done=self.format_bytes(done)))

        self.after(0, _update)

    def finish(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    @staticmethod
    def format_bytes(value: int) -> str:
        size = float(max(0, value))
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024 or unit == "GB":
                if unit == "B":
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024


class ThemeDialog(BaseDialog):
    def __init__(self, owner):
        super().__init__(owner, title=owner.t("settings.design.title"), width=500, height=360, autosize=True)
        self.owner = owner

        try:
            self.build()
            self.autosize_modal(min_width=500, min_height=360)
            self.activate()
        except Exception as exc:
            self.abort(owner.t("common.error"), owner.t("settings.dialog.open_dialog_error", error=exc))

    def build(self):
        frame = ctk.CTkFrame(self)
        frame.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text=self.owner.t("settings.design.section"),
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        ctk.CTkLabel(frame, text=self.owner.t("settings.design.appearance")).grid(
            row=1, column=0, sticky="w", padx=16, pady=(8, 6)
        )
        modes = [
            (self.owner.t("settings.design.appearance_system"), "System"),
            (self.owner.t("settings.design.appearance_light"), "Light"),
            (self.owner.t("settings.design.appearance_dark"), "Dark"),
        ]
        for index, (label, value) in enumerate(modes, start=2):
            ctk.CTkRadioButton(
                frame,
                text=label,
                variable=self.owner.appearance_mode_var,
                value=value,
            ).grid(row=index, column=0, sticky="w", padx=16, pady=(0, 8))

        ctk.CTkLabel(frame, text=self.owner.t("settings.design.theme")).grid(
            row=5, column=0, sticky="w", padx=16, pady=(4, 6)
        )
        self.owner.theme_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.owner.theme_var,
            values=list(self.owner.theme_label_to_id.keys()),
            width=240,
        )
        self.owner.theme_menu.grid(row=6, column=0, sticky="w", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            frame,
            text=self.owner.t("settings.design.apply_note"),
            anchor="w",
            justify="left",
            wraplength=380,
        ).grid(row=7, column=0, sticky="ew", padx=16, pady=(2, 14))

        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.grid(row=8, column=0, sticky="ew", padx=16, pady=(0, 16))
        buttons.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(buttons, text=self.owner.t("settings.design.save"), command=self.save).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ctk.CTkButton(
            buttons,
            text=self.owner.t("common.close"),
            command=self.destroy,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
        ).grid(row=0, column=1, sticky="e")

    def save(self):
        selected_mode = self.owner.appearance_mode_var.get()
        selected_theme = load_theme(self.owner.get_selected_theme_id())

        if not self.owner.save_current_settings_if_needed(force=True):
            return

        try:
            self.grab_release()
        except Exception:
            pass

        self.destroy()

        try:
            ctk.set_appearance_mode(selected_mode)
            ctk.set_default_color_theme(selected_theme.color_theme)
            clear_icon_cache()
        except Exception as exc:
            messagebox.showerror(
                self.owner.t("common.error"),
                self.owner.t("settings.dialog.open_dialog_error", error=exc),
                parent=self.owner,
            )
            return

        messagebox.showinfo(
            self.owner.t("settings.design.saved_title"),
            self.owner.t("settings.design.saved_message"),
            parent=self.owner,
        )


class AiDialog(BaseDialog):
    def __init__(self, owner):
        super().__init__(owner, title=owner.t("settings.ai.dialog_title"), width=600, height=680, autosize=True)
        self.owner = owner

        try:
            self.build()
            self.autosize_modal(min_width=600, min_height=680)
            self.activate()
        except Exception as exc:
            self.abort(owner.t("common.error"), owner.t("settings.dialog.open_dialog_error", error=exc))

    def build(self):
        frame = ctk.CTkScrollableFrame(self)
        frame.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text=self.owner.t("settings.ai.section"), font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 8)
        )

        self.owner.auto_style_checkbox = ctk.CTkCheckBox(
            frame,
            text=self.owner.t("settings.ai.auto_style"),
            variable=self.owner.auto_style_analysis_var,
            command=self.owner.on_auto_style_changed,
        )
        self.owner.auto_style_checkbox.grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(4, 10))

        ctk.CTkLabel(frame, text=self.owner.t("settings.ai.model")).grid(row=2, column=0, sticky="w", padx=(16, 8), pady=8)
        self.owner.ai_model_menu = ctk.CTkOptionMenu(frame, variable=self.owner.ai_model_var, values=AI_MODELS, width=260)
        self.owner.ai_model_menu.grid(row=2, column=1, sticky="w", pady=8)

        ctk.CTkLabel(frame, text=self.owner.t("settings.ai.scale")).grid(row=3, column=0, sticky="w", padx=(16, 8), pady=(8, 14))
        self.owner.ai_scale_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.owner.ai_scale_var,
            values=[str(x) for x in AI_SCALES],
            width=90,
        )
        self.owner.ai_scale_menu.grid(row=3, column=1, sticky="w", pady=(8, 14))

        ctk.CTkLabel(frame, text=self.owner.t("settings.ai_limit.section"), font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=4, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 8)
        )

        ctk.CTkLabel(frame, text=self.owner.t("settings.ai_limit.gpu")).grid(row=5, column=0, sticky="w", padx=(16, 8), pady=8)
        self.owner.ai_gpu_menu = ctk.CTkOptionMenu(frame, variable=self.owner.ai_gpu_var, values=self.owner.gpu_labels, width=330)
        self.owner.ai_gpu_menu.grid(row=5, column=1, sticky="ew", padx=(0, 16), pady=8)

        ctk.CTkLabel(frame, text=self.owner.t("settings.ai_limit.tile")).grid(row=6, column=0, sticky="w", padx=(16, 8), pady=8)
        self.owner.ai_tile_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.owner.ai_tile_size_var,
            values=AI_TILE_SIZES,
            width=120,
        )
        self.owner.ai_tile_menu.grid(row=6, column=1, sticky="w", pady=8)

        ctk.CTkLabel(frame, text=self.owner.t("settings.ai_limit.thread")).grid(row=7, column=0, sticky="w", padx=(16, 8), pady=8)
        self.owner.ai_thread_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.owner.ai_thread_config_var,
            values=AI_THREAD_CONFIGS,
            width=120,
        )
        self.owner.ai_thread_menu.grid(row=7, column=1, sticky="w", pady=8)

        ctk.CTkLabel(frame, text=self.owner.t("settings.ai_limit.cooldown")).grid(
            row=8, column=0, sticky="w", padx=(16, 8), pady=(8, 14)
        )
        self.owner.ai_cooldown_menu = ctk.CTkOptionMenu(
            frame,
            variable=self.owner.ai_cooldown_var,
            values=AI_COOLDOWN_SECONDS,
            width=120,
        )
        self.owner.ai_cooldown_menu.grid(row=8, column=1, sticky="w", pady=(8, 14))

        ctk.CTkLabel(
            frame,
            text=self.owner.t("settings.ai_limit.note"),
            anchor="w",
            justify="left",
            wraplength=460,
        ).grid(row=9, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14))

        ctk.CTkButton(frame, text=self.owner.t("common.close"), command=self.destroy, height=40).grid(
            row=10, column=1, sticky="e", padx=16, pady=(0, 16)
        )
        self.owner.on_auto_style_changed()
