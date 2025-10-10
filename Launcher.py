import os
import sys
import threading
import subprocess
import queue
import signal
import time
import tkinter.filedialog as fd
import tkinter.messagebox as mb

import customtkinter as ctk

APP_TITLE="Virtual Input Launcher"
ACCENT_COLOR="#0EA5E9" # sky-500
PRIMARY_TEXT="Run one tool at a time. Use Stop to end the current process."
DEFAULT_MOUSE="virtual_mouse.py"
DEFAULT_KEYBOARD = "multi_hand_virtual_keyboard.py"


class LauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("880x600")
        self.minsize(820,520)

        # theming
        ctk.set_appearance_mode("system") #"Dark" |"Light"|"System"
        ctk.set_default_color_theme("blue") # ctk built-in theme
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)

        # Runtime state
        self.process: subprocess.Popen | None=None
        self.log_queue =queue.Queue()
        self.reader_threads:list[threading.Thread]=[]
        self._stop_reader=threading.Event()

        # Script paths (defaluts assume same Folder)
        self.mouse_script=os.path.abspath(DEFAULT_MOUSE)
        self.keyboard_script=os.path.abspath(DEFAULT_KEYBOARD)

        # Build UI
        self._build_layout()
        self._wire_events()
        self._refresh_button_state()
        self.after(100,self._draun_log_queue)

    def _build_layout(self):
        # Root grid: 2 rows -> top controls / bottom logs
        self.grid_rowconfigure(1,weight=1)
        self.grid_columnconfigure(0,weight=1)

        # Header 
        header = ctk.CTkFrame(self,corner_radius=12)
        header.grid(row=0,column=0,sticky="ew",padx=16,pady=(16,8))
        header.grid_coiumnconfigure(0,weight=1)

        title = ctk.CTkLabel(
            header,
            text=APP_TITLE,
            font=ctk.CTkFont(size=22,weight="bold"),
        )
        subtitle=ctk.CTkLabel(
            header,text=PRIMARY_TEXT,
            font=ctk.CTkFont(size=13),
            text_color=("gray20","gray80")
        )
        title.grid(row=0,column=0,stickt="w",padx=14,pady=
                   (12,4))
        subtitle.grid(row=1,column=0,sticky="w",padx=14,pady=(0,12))

        # righht header controls
        right_controls=ctk.CTkFrame(header,fg_color="transparent")
        right_controls.grid(row=0,column=1,rowspan=2,sticky="e",padx=12,pady=8)
        right_controls.grid_columnconfigure((0,1,2),weight=0)

        self.theme_option=ctk.CTkOptionMenu(
            right_controls,
            values=["System","Light","Dark"],
            command=self._on_theme_change,
            width=120
        )
        self.theme_option.set("System")
        self.clear_btn=ctk.CTkButton(right_controls,text="Clear Logs",command=self._clear_logs,width=110)
        self.stop_btn=ctk.CTkButton(
            right_controls,text="Stop",command=self._stop_process,fg_color="#EF4444",hover_color="#DC2626",width=90
        )
        self.theme_option.grid(row=0,column=0,padx=6)
        self.clear_btn.grid(row=0,column=1,padx=6)
        self.stop_btn.grid(row=0,column=2,padx=6)

        # Main Content split: actions (top) + logs (Bottom)
        content = ctk.CTkFrame(self,corner_radius=12)
        content.grid(row=1,column=0,sticky="nsew",padx=16,pady=(8,16))
        content.grid_columnconfigure((0,1),weight=1)

        # Action Card
        actions=ctk.CTkFrame(content,fg_color="transparent")
        
        self.mouse_card=self._make_card(
            actions,
            title="Virtual Mouse",
            desc="Controls cursor with gestures or other inputs.",
            default_path=self.mouse_script,
            on_browse=lambda:self._browse_file("mouse"),
            on_run=lambda:self._run_program("mouse")
        )
        self.keyboard_card = self._make_card(
            actions,
            title="Virtual Keyboard",
            desc="Type via virtual input methods.",
            default_path=self.keyboard_script,
            on_browse=lambda: self._browse_file("keyboard"),
            on_run=lambda: self._run_program("keyboard"),
        )
        self.mouse_card.grid(row=0,column=0,sticky="nsew",padx=(8,6),pady=4)
        self.keyboard_card.grid(row=0,column=1,sticky="nsew",padx=(6,8),pady=4)
