from tkinter import messagebox

import customtkinter as ctk


class WindowGeometryMixin:
    def configure_window(
        self,
        title: str,
        min_size: tuple[int, int] | None = None,
        resizable: tuple[bool, bool] = (True, True),
        close_command=None,
    ):
        self.title(title)
        self.resizable(*resizable)

        if min_size:
            self.minsize(*min_size)

        if close_command:
            self.protocol("WM_DELETE_WINDOW", close_command)

    def center_on_screen(self, width: int, height: int):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = max(0, int((screen_width - width) / 2))
        y = max(0, int((screen_height - height) / 2))
        self.geometry(f"{width}x{height}+{x}+{y}")

    def center_over_parent(self, parent, width: int, height: int):
        x = max(0, int(parent.winfo_x() + (parent.winfo_width() - width) / 2))
        y = max(0, int(parent.winfo_y() + (parent.winfo_height() - height) / 2))
        self.geometry(f"{width}x{height}+{x}+{y}")

    def autosize_to_content(self, min_width: int, min_height: int, center: bool = True):
        self.update_idletasks()

        width = max(min_width, self.winfo_reqwidth() + 24)
        height = max(min_height, self.winfo_reqheight() + 24)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        width = min(width, screen_width - 80)
        height = min(height, screen_height - 100)

        if center:
            self.center_on_screen(width, height)
        else:
            self.geometry(f"{width}x{height}")

        return width, height


class BaseMainWindow(WindowGeometryMixin, ctk.CTk):
    pass


class BaseToplevelWindow(WindowGeometryMixin, ctk.CTkToplevel):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent_window = parent


class BaseDialog(BaseToplevelWindow):
    def __init__(
        self,
        parent,
        title: str,
        width: int,
        height: int,
        autosize: bool = False,
        resizable: tuple[bool, bool] = (False, False),
    ):
        super().__init__(parent)
        self.transient(parent)
        self.configure_window(title=title, resizable=resizable)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        if autosize:
            self.geometry(f"{width}x{height}")
        else:
            self.center_over_parent(parent, width, height)

        self.lift()
        self.focus_force()

    def activate(self):
        self.lift()
        self.focus_force()
        self.grab_set()

    def autosize_modal(self, min_width: int, min_height: int):
        self.update_idletasks()

        width = max(min_width, self.winfo_reqwidth() + 24)
        height = max(min_height, self.winfo_reqheight() + 24)
        width = min(width, self.winfo_screenwidth() - 80)
        height = min(height, self.winfo_screenheight() - 100)

        self.center_over_parent(self.parent_window, width, height)
        return width, height

    def abort(self, title: str, message: str):
        try:
            self.destroy()
        except Exception:
            pass

        messagebox.showerror(title, message)
