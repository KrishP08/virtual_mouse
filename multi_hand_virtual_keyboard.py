import cv2
import mediapipe as mp
import numpy as np
import time
from pynput.keyboard import Key, Controller as KeyboardController
import math
import threading
import tkinter as tk
from tkinter import ttk
import json
import os

class MultiHandOverlayKeyboard:
    def __init__(self):
        # Initialize MediaPipe with multi-hand support
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,  # Track both hands
            min_detection_confidence=0.7,  # Slightly lower for better detection
            min_tracking_confidence=0.5    # Lower for more stable tracking
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Initialize keyboard controller
        self.keyboard = KeyboardController()
        
        # Camera setup
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Multi-hand settings
        self.multi_hand_settings = {
            "enabled": True,
            "simultaneous_typing": True,
            "hand_priority": "both",  # "left", "right", "both"
            "conflict_resolution": "first_detected"  # "first_detected", "left_priority", "right_priority"
        }
        
        # Input mode settings
        self.input_modes = {
            "point_only": {"point": True, "pinch": False},
            "pinch_only": {"point": False, "pinch": True},
            "both": {"point": True, "pinch": True}
        }
        self.current_input_mode = "both"
        
        # Keyboard layouts
        self.current_layout = "letters"
        self.keyboard_layouts = {
            "letters": [
                ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
                ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
                ['Z', 'X', 'C', 'V', 'B', 'N', 'M'],
                ['SPACE', 'BACKSPACE', 'ENTER', 'NUMBERS'],
                ['POINT', 'PINCH', 'BOTH', 'QUIT']
            ],
            "numbers": [
                ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
                ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')'],
                ['-', '=', '[', ']', ';', "'", ',', '.', '/'],
                ['SPACE', 'BACKSPACE', 'ENTER', 'LETTERS'],
                ['POINT', 'PINCH', 'BOTH', 'QUIT']
            ]
        }
        
        # Display settings with full overlay support
        self.display_settings = {
            "background_mode": False,
            "window_alpha": 0.8,
            "show_camera": True,
            "always_on_top": True,
            "keyboard_size": 0.6,
            "window_transparency": 0.7,  # Overall window transparency
            "selection_duration": 2.0,
            "show_hand_labels": True
        }
        
        # Multi-hand gesture state
        self.hand_states = {
            "left": {
                "gesture": "none",
                "pointing_pos": None,
                "selected_key": None,
                "selection_start_time": 0,
                "last_gesture_time": 0
            },
            "right": {
                "gesture": "none",
                "pointing_pos": None,
                "selected_key": None,
                "selection_start_time": 0,
                "last_gesture_time": 0
            }
        }
        
        # Global state
        self.selection_duration = self.display_settings["selection_duration"]
        self.last_typed_key = None
        self.last_typed_time = 0
        self.same_key_cooldown = 1.0
        
        # Visual state
        self.keyboard_visible = True
        self.show_help = True
        self.show_mode_indicator = True
        
        # Stable overlay to prevent flickering
        self.overlay_cache = None
        self.overlay_dirty = True
        
        # Control flags
        self.running = True

        # Debug mode
        self.debug_mode = False
        
        # Load settings
        self.load_settings()
        
        # Setup control window
        self.setup_control_window()
        
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists('keyboard_settings.json'):
                with open('keyboard_settings.json', 'r') as f:
                    settings = json.load(f)
                    self.current_input_mode = settings.get('input_mode', 'both')
                    self.display_settings.update(settings.get('display', {}))
                    self.multi_hand_settings.update(settings.get('multi_hand', {}))
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def save_settings(self):
        """Save settings to file"""
        try:
            settings = {
                'input_mode': self.current_input_mode,
                'display': self.display_settings,
                'multi_hand': self.multi_hand_settings
            }
            with open('keyboard_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def setup_control_window(self):
        """Setup control window for settings"""
        self.control_window = tk.Tk()
        self.control_window.title("Multi-Hand Overlay Gesture Keyboard")
        self.control_window.geometry("450x700+50+50")
        self.control_window.configure(bg='#2b2b2b')
        
        # Make it always on top
        self.control_window.attributes('-topmost', True)
        
        # Multi-Hand Settings Section
        multi_hand_frame = tk.LabelFrame(self.control_window, text="Multi-Hand Settings", 
                                        bg='#2b2b2b', fg='white', font=('Arial', 12, 'bold'))
        multi_hand_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Enable multi-hand
        self.multi_hand_var = tk.BooleanVar(value=self.multi_hand_settings["enabled"])
        tk.Checkbutton(multi_hand_frame, text="Enable Multi-Hand Tracking", 
                      variable=self.multi_hand_var, command=self.toggle_multi_hand,
                      bg='#2b2b2b', fg='white', selectcolor='#404040',
                      font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=2)
        
        # Simultaneous typing
        self.simultaneous_var = tk.BooleanVar(value=self.multi_hand_settings["simultaneous_typing"])
        tk.Checkbutton(multi_hand_frame, text="Allow Simultaneous Typing", 
                      variable=self.simultaneous_var, command=self.toggle_simultaneous_typing,
                      bg='#2b2b2b', fg='white', selectcolor='#404040',
                      font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=2)

        #Hand Priority
        tk.Label(multi_hand_frame,text='Hand Priority:',bg='#2b2b2b',fg='white',font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=(10,2))

        self.prioruty_var=tk.StringVar(value=self.multi_hand_settings["hand_priority"])
        priority_frame=tk.Frame(multi_hand_frame,bg='#2b2b2b')
        priority_frame.pack(anchor=tk.W,padx=20)

        tk.Radiobutton(priority_frame,text="Both hands",variable=self.prioruty_var,value="both",
                       command=self.change_hand_priority,bg='#2b2b2b',fg='white',
                       selectcolor='#404040',font=('Arial',9)).pack(anchor=tk.W)
        tk.Radiobutton(priority_frame, text="Left Hand Only", variable=self.priority_var, value="left",
                      command=self.change_hand_priority, bg='#2b2b2b', fg='white',
                      selectcolor='#404040', font=('Arial', 9)).pack(anchor=tk.W)
        tk.Radiobutton(priority_frame, text="Right Hand Only", variable=self.priority_var, value="right",
                      command=self.change_hand_priority, bg='#2b2b2b', fg='white',
                      selectcolor='#404040', font=('Arial', 9)).pack(anchor=tk.W)
        
        #Input Mode Section
        mode_frame=tk.LabelFrame(self.control_window,text="Input Mode",
                                 bg='#2b2b2b',fg='white',font=('Arial',12,'bold'))
        mode_frame.pack(fill=tk.X,padx=10,pady=10)

        self.mode_var=tk.StringVar(value=self.current_input_mode)

        tk.Radiobutton(mode_frame,text="Point only (Hold 2.0s)",
                       variable=self.mode_var,value="point_only",
                       command=self.change_input_mode,bg='#2b2b2b',fg='white',
                       selectcolor='#404040',font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=2)
        
        tk.Radiobutton(mode_frame,text="Pinch only(instant)",
                       variable=self.mode_var,value="pinch_only",
                       command=self.change_input_mode,bg='#2b2b2b',fg='white',
                       selectcolor='#404040',font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=2)
        
        tk.Radiobutton(mode_frame,text="Both (Point + Pinch)",
                       variable=self.mode_var,value="both",
                       command=self.change_input_mode,bg='#2b2b2b',fg='white',
                       selectcolor='#404040',font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=2)
        
        #Display Sttings Section
        display_frame=tk.LabelFrame(self.control_window,text="Display Setting",
                                    bg='#2b2b2b',fg='white',font=('Arial',12,'bold'))
        display_frame.pack(fill=tk.X,padx=10,pady=10)

        #Background Mode toggle
        self.bg_mode_var = tk.BooleanVar(value=self.display_settings["background_mode"])
        tk.Checkbutton(display_frame, text="Background Mode (Transparent)", 
                      variable=self.bg_mode_var, command=self.toggle_background_mode,
                      bg='#2b2b2b', fg='white', selectcolor='#404040',
                      font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=2)
        
        #Show Camera toggle
        self.show_camera_var=tk.BooleanVar(value=self.display_settings["show_camera"])
        tk.Checkbutton(display_frame,text="Show Camera Feed",
                       variable=self.show_camera_var,command=self.toggle_camera_display,
                       bg='#2b2b2b',fg='white',selectcolor='#404040',
                       font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=2)
        
        #Show hand labels
        self.show_labels_var=tk.BooleanVar(value=self.display_settings["show_hand_labels"])
        tk.Checkbutton(display_frame,text="Show Hand Labels",
                       variable=self.show_labels_var,command=self.toggle_hand_labels,
                       bg='#2b2b2b',fg='white',selectcolor='#404040',
                       font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=2)
        
        #Window Transparency
        tk.Label(display_frame,text="Keyboard Transparency:",
                 bg='#2b2b2b',fg='white',font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=(10,2))
        self.alpha_var=tk.DoubleVar(value=self.display_settings["window_alpha"])
        alpha_scale=tk.Scale(display_frame,from_=0.3,to=1.0,resolution=0.1,
                             variable=self.alpha_var,orient=tk.HORIZONTAL,
                             command=self.change_transparency,
                             bg='#2b2b2b',fg='white',highlightbackground='#2b2b2b',
                             length=200)
        alpha_scale.pack(padx=10,pady=2)

        #Keyboard size
        