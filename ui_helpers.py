import customtkinter as ctk


class ToolTip:
    """
    Простая всплывающая подсказка для customtkinter-виджетов.
    """

    def __init__(self, widget, text: str, delay_ms: int = 500):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id = None
        self._window = None

        self.widget.bind("<Enter>", self._schedule, add="+")
        self.widget.bind("<Leave>", self._hide, add="+")
        self.widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._cancel_schedule()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel_schedule(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        if self._window is not None or not self.text:
            return

        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        except Exception:
            return

        self._window = ctk.CTkToplevel(self.widget)
        self._window.withdraw()
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)

        label = ctk.CTkLabel(
            self._window,
            text=self.text,
            padx=10,
            pady=6,
            fg_color=("#eeeeee", "#252525"),
            text_color=("#111111", "#eeeeee"),
            corner_radius=8,
        )
        label.pack()

        self._window.geometry(f"+{x}+{y}")
        self._window.deiconify()

    def _hide(self, _event=None):
        self._cancel_schedule()
        if self._window is not None:
            try:
                self._window.destroy()
            except Exception:
                pass
            self._window = None


def attach_tooltip(widget, text: str):
    return ToolTip(widget, text)
