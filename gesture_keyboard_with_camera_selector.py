import cv2
import mediapipe as mp
import numpy as np
import time
from pynput.keyboard import Key, Controller as KeyboardController
import math
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from camera_selector import CameraSelector

class MultihandOverlayKeyboardWithCamera:
    def __init__(self):
        # Ititialize camera selector
        self.camera_selector=CameraSelector()
        self.selected_camera_index=0

        #Initialize MediaPipe
        self.mp_hands=mp.solutions.hands
        self.hands=self.me_hands.Hands(
            static_image_mode=False,
            max_num_hands=2, # Track both hands
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw= mp.solutions.drawing_utils

        #Initialize keyboard controller
        self.keyboard=KeyboardController()

        #Camera setup - will be initialized after camera selection
        self.cap=None

        #Multi-hand settings
        self.multi_hand_settings={
            "enabled":True,
            "simultaneous_typing":True,
            "hand_priority":"both",# "left","right","both"
            "conflict_resolution":"first_detected"
        }

        #Input mode settings
        self.input_modes={
            "point_only":{"point":True,"pinch":False},
            "pinch_only":{"point":False,"pinch:":True},
            "both":{"point":True,"pinch":True}
        }
        self.current_input_mode="both"

        #Keyboard layouts with camera control
        self.current_layout="letters"
        self.keyboard_layout={
            "letters":[
                ['Q','W','E','R','T','Y','U','I','O','P'],
                ['A','S','D','F','G','H','J','K','L'],
                ['Z','X','C','V','B','N','M'],
                ['SPACE','BACKSPACE','ENTER','NUMBER'],
                ['POINT','PINCH','BOTH','CAMERA']
            ],
            "numbers":[
                ['1','2','3','4','5','6','7','8','9','0'
            ],
                ['!','@','#','$','%','^','&','*','(',')'],
                ['-','=','[',']',';',"'",',','.','/'],
                ['SPACE','BACKSPACE','ENTER','LETTERS'],
                ['POINT','PINCH','BOTH','CAMERA']
            ]
        }
        # Display settings with camera support
        self.display_settings={
            "background_mode":False,
            "window_alpha":0.8,
            "show_camera":True,
            "always_on_top":True,
            "keyboard_size":0.6,
            "window_transparency":0.7,
            "selection_duration":2.0,
            "show_hand_labels":True,
            "camera_info_display":True
        }

        # Multi-hand gesture state
        self.hand_states={
            "left":{
                "gesture":"none",
                "pointing_pos":None,
                "selected_key":None,
                "selection_start_time":0,
                "last_gesture_time":0
            },
            "right":{
                "gesture":"none",
                "pointing_pos":None,
                "selected_key":None,
                "selection_start_time":0,
                "last_gesture_time":0
            }
        }

        # Gelobal state
        self.selection_duration =self.display_settings["se;ection_duration"]
        self.last_typed_key=None
        self.last_typed_time=0
        self.same_key_cooldown=1.0

        # Visual State
        self.keyboard_visible=True
        self.show_help=True
        self.show_mode_indicator =True

        # Stable overlay to prevent flickering
        self.overlay_cache=None
        self.overlay_dirty=None

        # Control flags
        self.running =True
        self.camera_ready=False
        self.debug_mode=False

        # Load srttings
        self.load_settings()

        # Setup control window
        self.setup_control_window()

    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists('keyboard_settings.json'):
                with open('keyboard_settings.json','r') as f:
                    settings=json.laod(f)
                    self.current_input_mode =settings.get('input_mode','both')
                    self.display_settings.update(settings.get('display',{}))
                    self.multi_hand_settings.update(settings.get('multi_hand',{}))
                    self.selected_camera_index = settings.get('camera_index',0)
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def save_settngs(self):
        """Save settings to file"""
        try:
            settings={
                'input_mode':self.current_input_mode,
                'display':self.display_settings,
                'multi_hand':self.multi_hand_settings,
                'camera_index':self.selected_camera_index
            }
            with open('keyboard_settings.json','w') as f:
                json.dump(settings,f,indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def setup_control_window(self):
        """Setup control window for settings"""
        self.control_window=tk.Tk()
        self.control_window.title("Multi-Hand Overlay Keyboard with Camera selector")
        self.control_window.geometry("500x750+50+50")
        self.control_window.configure(bg='#2b2b2b')

        # Make it always on top
        self.control_window.attributes('-topmost',True)

        # Camera Selection section
        camera_frame=tk.LabelFrame(self.control_window,text="Camera settings",bg='#2b2b2b',fg='white',font=('Arial',12,'bold'))
        camera_frame.pack(fill=tk.X,padx=10,pady=10)

        # Camera selection button
        self.camera_select_btn=tk.button(camera_frame,text="Select Camera",command=self.show_camera_selector,bg='#0066cc',fg='white',font=('Arial',10))
        self.camera_select_btn.pack(pady=10)

        # Camera info label
        self.camera_info_label=tk.Label(camera_frame,text=f"Camera {self.selected_camera_index} selected",bg='#2b2b2b',fg='cyan',font=('Arial',10))

        self.camera_info_label.pack(pady=5)

        