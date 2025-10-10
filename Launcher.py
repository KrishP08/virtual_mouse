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

        # Theming
        ctk.set_appearance_mode("system")  # "dark" | "light" | "system"
        ctk.set_default_color_theme("blue")  # ctk built-in theme
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)

        # Runtime state
        self.process: subprocess.Popen | None=None
        self.log_queue =queue.Queue()
        self.reader_threads:list[threading.Thread]=[]
        self._stop_reader=threading.Event()

        # Script paths (defaults assume same folder)
        self.mouse_script = os.path.abspath(DEFAULT_MOUSE)
        self.keyboard_script = os.path.abspath(DEFAULT_KEYBOARD)

        # Build UI
        self._build_layout()
        self._wire_events()
        self._refresh_buttons_state()
        self.after(100, self._drain_log_queue)

    def _build_layout(self):
        # Root grid: 2 rows -> top controls / bottom logs
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text=APP_TITLE,
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        subtitle = ctk.CTkLabel(
            header,
            text=PRIMARY_TEXT,
            font=ctk.CTkFont(size=13),
            text_color=("gray20", "gray80"),
        )
        title.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))
        subtitle.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))

        # Right header controls
        right_controls = ctk.CTkFrame(header, fg_color="transparent")
        right_controls.grid(row=0, column=1, rowspan=2, sticky="e", padx=12, pady=8)
        right_controls.grid_columnconfigure((0, 1, 2), weight=0)

        self.theme_option = ctk.CTkOptionMenu(
            right_controls,
            values=["System", "Light", "Dark"],
            command=self._on_theme_change,
            width=120,
        )
        self.theme_option.set("System")
        self.clear_btn = ctk.CTkButton(right_controls, text="Clear Logs", command=self._clear_logs, width=110)
        self.stop_btn = ctk.CTkButton(
            right_controls, text="Stop", command=self._stop_process, fg_color="#EF4444", hover_color="#DC2626", width=90
        )
        self.theme_option.grid(row=0, column=0, padx=6)
        self.clear_btn.grid(row=0, column=1, padx=6)
        self.stop_btn.grid(row=0, column=2, padx=6)

        # Main content split: actions (top) + logs (bottom)
        content = ctk.CTkFrame(self, corner_radius=12)
        content.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 16))
        content.grid_rowconfigure(1, weight=1)
        content.grid_columnconfigure(0, weight=1)

        # Action cards
        actions = ctk.CTkFrame(content, fg_color="transparent")
        actions.grid(row=0, column=0, sticky="ew", padx=8, pady=(12, 8))
        actions.grid_columnconfigure((0, 1), weight=1)

        self.mouse_card = self._make_card(
            actions,
            title="Virtual Mouse",
            desc="Control cursor with gestures or other inputs.",
            default_path=self.mouse_script,
            on_browse=lambda: self._browse_file("mouse"),
            on_run=lambda: self._run_program("mouse"),
        )
        self.keyboard_card = self._make_card(
            actions,
            title="Virtual Keyboard",
            desc="Type via virtual input methods.",
            default_path=self.keyboard_script,
            on_browse=lambda: self._browse_file("keyboard"),
            on_run=lambda: self._run_program("keyboard"),
        )
        self.mouse_card.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=4)
        self.keyboard_card.grid(row=0, column=1, sticky="nsew", padx=(6, 8), pady=4)

        # Logs area
        logs_frame = ctk.CTkFrame(content, corner_radius=12)
        logs_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(6, 12))
        logs_frame.grid_rowconfigure(1, weight=1)
        logs_frame.grid_columnconfigure(0, weight=1)

        logs_title = ctk.CTkLabel(logs_frame, text="Output", font=ctk.CTkFont(size=16, weight="bold"))
        self.status_label = ctk.CTkLabel(logs_frame, text="Idle", text_color=("gray25", "gray75"))
        logs_title.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 0))
        self.status_label.grid(row=0, column=0, sticky="e", padx=12, pady=(12, 0))

        self.log_text = ctk.CTkTextbox(logs_frame, wrap="word")
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        self.log_text.configure(state="disabled")

    def _make_card(self, parent, title, desc, default_path, on_browse, on_run):
        card = ctk.CTkFrame(parent, corner_radius=16)
        card.grid_rowconfigure(3, weight=1)
        card.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=18, weight="bold"))
        desc_label = ctk.CTkLabel(card, text=desc, text_color=("gray25", "gray75"))
        path_entry = ctk.CTkEntry(card, placeholder_text="Path to script", height=40)
        path_entry.insert(0, default_path)
        browse_btn = ctk.CTkButton(card, text="Browse...", command=on_browse, width=110)
        run_btn=ctk.CTkButton(card,text=f"Run {title}",command=on_run,fg_color=ACCENT_COLOR)

        title_label.grid(row=0,column=0,sticky="w",padx=14,pady=(14,2))
        desc_label.grd(row=1,column=0,sticky="w",padx=14,pady=(0,8))
        path_entry.grid(row=2,column=0,sticky="ew",padx=14,pady=(0,8))
        controls=ctk.CTkFrame(card,fg_color="transparent")
        controls.grid(row=3,column=0,stiscky="ew",padx=10,pady=(0,14))
        controls.frid_columnconfigure((0,1),weight=0)
        browse_btn.grid(in_=controls,row=0,column=0,padx=6)
        run_btn.grid(in_=controls,row=0,column=1,padx=6)

        # Attach for later access
        card.title=title
        card.path_entry=path_entry
        card.run_btn=run_btn
        card.browes_btn=browse_btn
        return card
    
    def _wire_events(self):
        self.protocol("WM_DELETE_WINDOW",self._on_close)

    def _on_theme_change(self,value:str):
        mode= value.lower()
        if mode not in ("system","light","dark"):
            mode = "system"
        ctk.set_appearance_mode(mode)
    
    def _append_log(self,text:str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end",text)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_logs(self):
        try:
            while True:
                line=self.log_queue.get_nowait()
                self._append_log(line)
        except queue.Empty:
            pass
        self.after(80,self.drain_log_queue)

    def _browse_file(self,which:str):
        file_path=fd.askopenfilename(
            title="Select Python Script",
            filetypes=[("Python files","*.py"),("All Files","*.*")]
        )
        if not file_path:
            return
        if which =="mouse":
            return
        if which=="mouse":
            self.mouse_script=file_path
            self.mouse_card.path_entry.delete(0,"end")
            self.mouse_card.path_entry.insert(0,file_path)
        elif which == "keyboard":
            self.keyboard_script=file_path
            self.keyboard_card.path_entry.delete(0,"end")
            self.keyboard_card.path_entry.insert(0,file_path)
        
    def _validate_script(self,path:str) -> bool:
        return os.path.isfile(path) and path.lower().endswith(".py")
    def _run_program(self,which:str):
        if self.process is not None and self.process.poll() is None:
            mb.showinfo("Process Running","Stop the current process before starting another.")
            return
        
        # Resolve script path
        if which == "mouse":
            path = self.mouse_card.path_entry.get().strip()
            title=self.mouse_card.title
        else:
            path=self.keyboard_card.path_entry.get().strip()
            title=self.keyboard_card.title
        
        if not self._validate_script(path):
            mb.showerror("Invalid Script","Please select a vaild .py file.")
            return
        
        # Start Process