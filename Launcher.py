import os
import sys
import subprocess
import time
import signal
import customtkinter as ctk
import tkinter.messagebox as mb

APP_TITLE = "Virtual Input Launcher"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MOUSE_SCRIPT = os.path.join(SCRIPT_DIR, "virtual_mouse.py")
KEYBOARD_SCRIPT = os.path.join(SCRIPT_DIR, "multi_hand_overlay_keyboard.py")
MOUSE_EXE = os.path.join(SCRIPT_DIR, "virtual_mouse.exe")
KEYBOARD_EXE = os.path.join(SCRIPT_DIR, "multi_hand_overlay_keyboard.exe")

class LauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("720x380")
        self.minsize(680, 340)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.process = None
        self._build_ui()
        self._refresh_buttons()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        root= ctk.CTkFrame(root,corner_radius=12)
        root.pack(fill="both",expand=True,padx=16,pady=16)

        header=ctk.CTkFrame(root,corner_radius=12)
        header.pack(fill="x")
        left=ctk.CTkFrame(header,fg_color="transparent")
        left.pack(side="left",fill="x",expand=True,padx=12,pady=10)
        right=ctk.CTkFrame(header,fg_color="transparent")
        right.pack(side="right",padx=12,pady=10)

        title = ctk.CTkLabel(left, text=APP_TITLE, font=ctk.CTkFont(size=22, weight="bold"))
        subtitle = ctk.CTkLabel(left, text="Run either tool below. Stop before starting another.", text_color=("gray25", "gray75"))
        title.pack(anchor="w")
        subtitle.pack(anchor="w", pady=(2, 0))

        self.theme_option = ctk.CTkOptionMenu(right, values=["System", "Light", "Dark"], command=self._on_theme_change, width=120)
        self.theme_option.set("System")
        self.theme_option.pack(side="left", padx=6)

        self.stop_btn=ctk.CTkButton(right,text="Stop",command=self._stop_process,fg_color="#EF4444",hover_color="#DC2626",width=90)
        self.stop_btn.pack(side="left",padx=6)

        cards=ctk.CTkFrame(root,corner_radius=12)
        cards.pack(fill="x",pady=(12,8))
        cards.grid_columnconfigure(0,weight=1)