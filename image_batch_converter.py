import customtkinter as ctk

from settings_window import SettingsWindow


def main():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = SettingsWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
