import customtkinter as ctk

from app_theme import apply_saved_theme
from windows import SettingsWindow


def main():
    apply_saved_theme()

    app = SettingsWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
