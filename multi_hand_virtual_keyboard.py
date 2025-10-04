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

        #Multi-hand gesture state
        self.hand_states={
            "left":{
                "gesture": "none",
                "pointing_pos": None,
                "selected_key": None,
                "selection_start_time": 0,
                "last_gesture_time": 0
            },
            "right":{
                "gesture": "none",
                "pointing_pos": None,
                "selected_key": None,
                "selection_start_time": 0,
                "last_gesture_time": 0
            }
        }

        #Global state
        self.selection_duration=self.display_settings["selection_duration"]
        self.last_typed_key=None
        self.last_typed_time=0
        self.same_key_cooldown=1.0

        #Visual state
        self.keyboard_visible=True
        self.show_help=True
        self.show_mode_indicator=True

        #Stable overlay to prevent flickering
        self.overlay_cache=None
        self.overlay_dirty=True

        #control flags
        self,running=True

        #debug mode
        self.debug_mode=False

        #Load Settings
        self.load_settings()

        #Setup control window
        self.setup_control_window()

    def load_settings(self):
        """Load settings from the file"""
        try:
            if os.path.exists('keyboard_settings.json'):
                with open('keyboard_settings.json','r') as f:
                    settings=json.load(f)
                    self.current_input_mode=settings.get('input_mode','both')
                    self.display_settings.update(settings.get('display',{}))
                    self.multi_hand_settings.update(settings.get('multi_hand',{}))

        except Exception as e:
            print(f"Error loading Settings: {e}")
            