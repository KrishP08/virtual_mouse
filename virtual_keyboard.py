import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import ttk
import threading
import time
from pynput.keyboard import Key, Controller as KeyboardController
import math
import queue
import json
import os
from datetime import datetime

class AdvancedGestureKeyboard:
    def __init__(self):
        # Initialize MediaPipe with better settings
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,  # Single hand for better accuracy
            min_detection_confidence=0.8,
            min_tracking_confidence=0.7
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Initialize keyboard controller
        self.keyboard = KeyboardController()
        
        # Camera setup
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Advanced gesture detection
        self.gesture_history = []
        self.gesture_stability_threshold = 5
        self.last_stable_gesture = "none"
        
        # Calibration data
        self.calibration_data = self.load_calibration()
        self.is_calibrated = len(self.calibration_data) > 0
        
        # Enhanced keyboard layouts
        self.current_layout = "qwerty"
        self.keyboard_layouts = {
            "qwerty": [
                ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
                ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
                ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
                ['Z', 'X', 'C', 'V', 'B', 'N', 'M'],
                ['SPACE', 'BACKSPACE', 'ENTER', 'SHIFT', 'CTRL']
            ],
            "symbols": [
                ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')'],
                ['-', '=', '[', ']', '\\', ';', "'", ',', '.', '/'],
                ['<', '>', '?', ':', '"', '{', '}', '|'],
                ['SPACE', 'BACKSPACE', 'ENTER', 'QWERTY']
            ]
        }
        
        # Gesture state management
        self.gesture_queue = queue.Queue()
        self.selection_state = {
            'key': None,
            'start_time': 0,
            'duration': 1.2,
            'confirmed': False
        }
        
        # Performance tracking
        self.typing_stats = {
            'keys_typed': 0,
            'session_start': datetime.now(),
            'accuracy': 0.0
        }
        
        # Background operation
        self.running = True
        self.background_mode = False
        
        # Setup GUI
        self.setup_advanced_gui()
        
    def load_calibration(self):
        """Load calibration data from file"""
        try:
            if os.path.exists('keyboard_calibration.json'):
                with open('keyboard_calibration.json', 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading calibration: {e}")
        return {}
    
    def save_calibration(self):
        """Save calibration data to file"""
        try:
            with open('keyboard_calibration.json', 'w') as f:
                json.dump(self.calibration_data, f)
        except Exception as e:
            print(f"Error saving calibration: {e}")
    
    def setup_advanced_gui(self):
        """Setup advanced GUI with more features"""
        self.root = tk.Tk()
        self.root.title("Advanced Gesture Virtual Keyboard")
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.95)
        self.root.configure(bg='#1a1a1a')
        
        # Create main frames
        self.create_control_panel()
        self.create_keyboard_display()
        self.create_status_panel()
        
        # Position and size
        self.root.geometry("1000x400+50+50")
        
        # Bind events
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_control_panel(self):
        """Create control panel with advanced options"""
        control_frame = tk.Frame(self.root, bg='#1a1a1a')
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Main controls
        tk.Button(
            control_frame, text="Toggle Keyboard", command=self.toggle_keyboard,
            bg='#4a4a4a', fg='white', font=('Arial', 10)
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            control_frame, text="Calibrate", command=self.start_calibration,
            bg='#0066cc', fg='white', font=('Arial', 10)
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            control_frame, text="Background Mode", command=self.toggle_background,
            bg='#cc6600', fg='white', font=('Arial', 10)
        ).pack(side=tk.LEFT, padx=5)
        
        # Layout selector
        tk.Label(control_frame, text="Layout:", bg='#1a1a1a', fg='white').pack(side=tk.LEFT, padx=5)
        self.layout_var = tk.StringVar(value=self.current_layout)
        layout_menu = ttk.Combobox(
            control_frame, textvariable=self.layout_var, 
            values=list(self.keyboard_layouts.keys()),
            state="readonly", width=10
        )
        layout_menu.pack(side=tk.LEFT, padx=5)
        layout_menu.bind('<<ComboboxSelected>>', self.change_layout)
        
        # Sensitivity slider
        tk.Label(control_frame, text="Sensitivity:", bg='#1a1a1a', fg='white').pack(side=tk.LEFT, padx=5)
        self.sensitivity_var = tk.DoubleVar(value=1.2)
        sensitivity_scale = tk.Scale(
            control_frame, from_=0.5, to=3.0, resolution=0.1,
            variable=self.sensitivity_var, orient=tk.HORIZONTAL,
            bg='#1a1a1a', fg='white', length=100
        )
        sensitivity_scale.pack(side=tk.LEFT, padx=5)
        
    def create_keyboard_display(self):
        """Create the virtual keyboard display"""
        self.keyboard_frame = tk.Frame(self.root, bg='#1a1a1a')
        self.keyboard_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.key_buttons = {}
        self.create_keyboard_layout()
        
    def create_status_panel(self):
        """Create status and information panel"""
        status_frame = tk.Frame(self.root, bg='#1a1a1a')
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Status labels
        self.status_label = tk.Label(
            status_frame, text="Status: Ready", 
            bg='#1a1a1a', fg='#00ff00', font=('Arial', 10)
        )
        self.status_label.pack(side=tk.LEFT)
        
        self.gesture_label = tk.Label(
            status_frame, text="Gesture: None", 
            bg='#1a1a1a', fg='#ffff00', font=('Arial', 10)
        )
        self.gesture_label.pack(side=tk.LEFT, padx=20)
        
        self.selection_label = tk.Label(
            status_frame, text="", 
            bg='#1a1a1a', fg='#00ffff', font=('Arial', 10)
        )
        self.selection_label.pack(side=tk.LEFT, padx=20)
        