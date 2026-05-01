import customtkinter as ctk

from windows.base import BaseDialog


class CustomMessageDialog(BaseDialog):
    def __init__(
        self,
        parent,
        title: str,
        message: str,
        kind: str = "info",
        buttons: tuple[str, ...] = ("OK",),
    ):
        super().__init__(parent, title=title, width=520, height=260, autosize=True)
        self.result = None
        self.buttons = buttons
        self.kind = kind
        self.message = message
        self.build()
        self.autosize_modal(min_width=520, min_height=220)
        self.activate()

    def build(self):
        frame = ctk.CTkFrame(self, corner_radius=12)
        frame.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        frame.grid_columnconfigure(0, weight=1)

        accent = {
            "error": "#d84f4f",
            "warning": "#d99a28",
            "question": "#2f7fd1",
            "info": "#2f7fd1",
        }.get(self.kind, "#2f7fd1")

        ctk.CTkLabel(
            frame,
            text=self.title(),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=accent,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))

        ctk.CTkLabel(
            frame,
            text=self.message,
            anchor="w",
            justify="left",
            wraplength=440,
        ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 18))

        buttons_frame = ctk.CTkFrame(frame, fg_color="transparent")
        buttons_frame.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        buttons_frame.grid_columnconfigure(0, weight=1)

        for index, label in enumerate(self.buttons, start=1):
            ctk.CTkButton(
                buttons_frame,
                text=label,
                width=120,
                command=lambda value=label: self.finish(value),
                fg_color="transparent" if index < len(self.buttons) else None,
                border_width=1 if index < len(self.buttons) else 0,
                text_color=("gray10", "gray90") if index < len(self.buttons) else None,
            ).grid(row=0, column=index, sticky="e", padx=(8, 0))

    def finish(self, value: str):
        self.result = value
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


def show_message(parent, title: str, message: str, kind: str = "info") -> str | None:
    dialog = CustomMessageDialog(parent, title=title, message=message, kind=kind, buttons=("OK",))
    parent.wait_window(dialog)
    return dialog.result


def ask_yes_no(parent, title: str, message: str) -> bool:
    dialog = CustomMessageDialog(parent, title=title, message=message, kind="question", buttons=("No", "Yes"))
    parent.wait_window(dialog)
    return dialog.result == "Yes"


def ask_yes_no_cancel(parent, title: str, message: str) -> bool | None:
    dialog = CustomMessageDialog(
        parent,
        title=title,
        message=message,
        kind="question",
        buttons=("Cancel", "No", "Yes"),
    )
    parent.wait_window(dialog)
    if dialog.result == "Yes":
        return True
    if dialog.result == "No":
        return False
    return None
