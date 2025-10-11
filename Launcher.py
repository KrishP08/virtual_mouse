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
        root = ctk.CTkFrame(self, corner_radius=12)
        root.pack(fill="both", expand=True, padx=16, pady=16)

        header = ctk.CTkFrame(root, corner_radius=12)
        header.pack(fill="x")
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=12, pady=10)
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", padx=12, pady=10)

        title = ctk.CTkLabel(left, text=APP_TITLE, font=ctk.CTkFont(size=22, weight="bold"))
        subtitle = ctk.CTkLabel(left, text="Run either tool below. Stop before starting another.", text_color=("gray25", "gray75"))
        title.pack(anchor="w")
        subtitle.pack(anchor="w", pady=(2, 0))

        self.theme_option = ctk.CTkOptionMenu(right, values=["System", "Light", "Dark"], command=self._on_theme_change, width=120)
        self.theme_option.set("System")
        self.theme_option.pack(side="left", padx=6)

        self.stop_btn = ctk.CTkButton(right, text="Stop", command=self._stop_process, fg_color="#EF4444", hover_color="#DC2626", width=90)
        self.stop_btn.pack(side="left", padx=6)

        cards = ctk.CTkFrame(root, corner_radius=12)
        cards.pack(fill="x", pady=(12, 8))
        cards.grid_columnconfigure(0, weight=1)
        cards.grid_columnconfigure(1, weight=1)

        self.mouse_card = self._make_card(cards, "Virtual Mouse", "Hand-gesture powered mouse.", MOUSE_SCRIPT, self._run_mouse)
        self.mouse_card.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=6)

        self.keyboard_card = self._make_card(cards, "Virtual Keyboard", "Overlay keyboard with multi-hand control.", KEYBOARD_SCRIPT, self._run_keyboard)
        self.keyboard_card.grid(row=0, column=1, sticky="nsew", padx=(6, 8), pady=6)

        status_row = ctk.CTkFrame(root, fg_color="transparent")
        status_row.pack(fill="x", pady=(4, 0))
        self.status_label = ctk.CTkLabel(status_row, text="Idle", text_color=("gray25", "gray75"))
        self.status_label.pack(anchor="w", padx=6)

    def _make_card(self, parent, title, desc, path, run_cb):
        card = ctk.CTkFrame(parent, corner_radius=16)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=12)

        ctk.CTkLabel(inner, text=title, font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(inner, text=desc, text_color=("gray25", "gray75")).pack(anchor="w", pady=(0, 8))

        path_value = ctk.CTkEntry(inner, height=40)
        path_value.insert(0, path)
        path_value.configure(state="disabled")
        path_value.pack(fill="x")

        ctk.CTkButton(inner, text=f"Run {title}", command=run_cb).pack(anchor="e", pady=(10, 0))
        return card

    def _on_theme_change(self, value):
        ctk.set_appearance_mode(value.lower())

    def _run_mouse(self):
        self._launch_tool("Virtual Mouse", MOUSE_EXE, MOUSE_SCRIPT)

    def _run_keyboard(self):
        self._launch_tool("Virtual Keyboard", KEYBOARD_EXE, KEYBOARD_SCRIPT)

    def _launch_tool(self, name, exe_path, py_path):
        if self.process and self.process.poll() is None:
            mb.showinfo("Already running", "Stop the current process before starting another.")
            return

        try:
            self.status_label.configure(text=f"Running: {name}")

            if os.path.exists(exe_path):
                # Run the packaged exe
                self.process = subprocess.Popen([exe_path])
            elif os.path.exists(py_path):
                # Run the .py file directly (for dev testing)
                self.process = subprocess.Popen([sys.executable, py_path])
            else:
                mb.showerror("File Not Found", f"Neither {exe_path} nor {py_path} exists.")
                return
        except Exception as e:
            mb.showerror("Failed to start", str(e))
            self.status_label.configure(text="Idle")
            self.process = None
        finally:
            self._refresh_buttons()

    def _stop_process(self):
        if not self.process or self.process.poll() is not None:
            return
        self.status_label.configure(text="Stopping...")
        try:
            if os.name == "nt":
                self.process.terminate()
            else:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            time.sleep(0.5)
        except Exception as e:
            mb.showerror("Stop failed", str(e))
        finally:
            self.process = None
            self.status_label.configure(text="Idle")
            self._refresh_buttons()

    def _refresh_buttons(self):
        running = self.process is not None and self.process.poll() is None
        self.stop_btn.configure(state=("normal" if running else "disabled"))

    def _on_close(self):
        if self.process and self.process.poll() is None:
            if not mb.askyesno("Quit", "A process is still running. Stop it and exit?"):
                return
            self._stop_process()
        self.destroy()

if __name__ == "__main__":
    app = LauncherApp()
    app.mainloop()