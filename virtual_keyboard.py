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
        
        #gesture state management
        self.gesture_queue=queue.Queue()
        self.selection_state={
            'key':None,
            'start_time':0,
            'duration':1.2,
            'confirmed':False   
        }

        #Performance tracking
        self.typing_stats={
            'key_typed':0,
            'session_start':datetime.now(),
            'accuracy':0.0
        }

        #background operaction
        self.running = True
        self.background_mode = False

        #Setup GUI
        self.setup_advanced_gui()

    def load_calibration(self):
        """Load calibration data from file"""
        try:
            if os.path.exists('keyboard_calibration.json'):
                with open('keyboard_calibration.json', 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading calibration: {e}")
        return{}
    def save_calibration(self):
        """Save Calibration date to file"""
        try:
            with open('keyboard_calibration.json','w') as f:
                json.dump(self.calibration_data,f)
        except Exception as e:
            print(f"Error saving calibration: {e}")

    def setup_advanced_gui(self):
        """Setup advarced GUI with more features"""
        self.root=tk.Tk()
        self.root.title("Advanced Gesturr Virtual Keyboard")
        self.root.attributes('-topmost',True)
        self.root.attributes('-alpha',0.95)
        self.root.configure(bg='#1a1a1a')

        #Create main frames
        self.create_control_panel()
        self.create_keyboard_display()
        self.create_status_panel()

        #Position and size
        self.root.grmoetry("1000x400+50+50")

        #Bind events
        self.root.protocol("WM_DELETE_WINDOW",self)

    def create_control_panel(self):
        """Create control panel with advanced opection"""
        control_frame=tk.Frame(self,root,bg='#1a1a1a')
        control_frame.pack(fill=tk.X,padx=10,pady=5)

        #Main controls
        tk.Button(
            
        )