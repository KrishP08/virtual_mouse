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

        # Start/Stop camera button
        self.camera_control_btn = tk.Button(camera_frame,text="Start Camera",command=self.toggle_camera,bg='#006600',fg='white',font=('Arial',10))
        self.camera_control_btn.pack(pady=5)

        # Multi-Hand setting Section
        multi_hand_frame = tk.LabelFrame(self.control_window,text="Multi-Hand Setting",bg='#2b2b2b',fg='white',font=('Arial',12,'bold'))
        multi_hand_frame.pack(fill=tk.X,padx=10,pady=10)

        # Enable multi-hand
        self.multi_hand_var=tk.Booleanvar(value=self.multi_hand_settings["enabled"])
        tk.Checkbutton(multi_hand_frame,text="Enable Multi-Hand Tracking",variable=self.multi_hand_var,command=self.toggle_multi_hand,bg='#2b2b2b',fg='white',selectcolor='#404040',font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=2)

        # Simultaneous typing
        self.simultaneous_var= tk.booleanVar(value=self.multi_hand_settings["simultaneous_typing"])
        tk.Checkbutton(multi_hand_frame,text="Allow Simultaneous typing",variable=self.simultaneous_var,
                       command=self.toggle_simultaneous_typing,bg='#2b2b2b',fg='white',selectcolor='#404040',font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=2)
        
        # Input Mode Section
        mode_frame = tk.labelFrame(self.control_window,text="Input Mode",bg='#2b2b2b',fg='white',font=('Arial',12,'bold'))
        mode_frame.pack(fill=tk.X,padx=10,pady=10)

        self_mode_var = tk.StringVar(value=self.current_input_mode)

        tk.Radiobutton(mode_frame,text="Point only (Hold 2.0s)",variable=self.mode_var,value="point_only",command=self.change_input_mode,bg='#2b2b2b',fg='white',selectcolor='#404040',font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=2)

        tk.Radiobutton(mode_frame,text="Pinch Only (Instant)",variable=self.mode_var,value="pinch_only",command=self.change_input_mode,bg='#2b2b2b',fg='white',selectcolor='#404040',font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=2)

        tk.Radiobutton(mode_frame,text="Both (Point + Pinch)",variable=self.mode_var,value="both",command=self.change_input_mode,bg='#2b2b2b',fg='white',selectcolor='#404040',font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=2)

        #Display Settings Section
        display_frame=tk.LabelFrame(self.control_window,text="Display Settings",bg='#2b2b2b',f='white',font=('Arial',12,'bold'))
        display_frame.pack(fill=tk.X,padx=10,pady=10)

        #Background mode toggle
        self.bg_mode_var=tk.BooleanVar(value=self.display_settings["background_mode"])
        tk.Checkbutton(display_frame,text="Background Mode (Transparent)",variable=self.bg_mode_var,command=self.toggle_background_mode,bg='#2b2b2b',fg='white',selectcolor='#404040',font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=2)

        # Show hand labels
        self.show_labels_var=tk.BooleanVar(value=self.display_settings['show_hand_labels'])
        tk.Checkbutton(display_frame,text="show Hand Labels",variable=self.show_labels_var,command=self.toggle_hand_labels,bg='#2b2b2b',fg='white',selectcolor='#404040',font=('Arial',10,)).pack(anchor=tk.W,padx=10,pady=2)

        # Selection duration
        tk.Label(display_frame,text="Point Hold Diration (seconds):",bg='#2b2b2b',fg='white',font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=(10,2))

        self.duration_var=tk.Doublevar(value=self.display_settings["selection_duration"])
        duration_scale=tk.Scale(display_frame,from_=1.0,to=5.0,resolution=0.5,variable=self.duration_var,orient=tk.HORIZONTAL,command=self.change_selection_dration,bg='#2b2b2b',fg='white',highlightbackground='#2b2b2b',length=200)
        duration_scale.pack(padx=10,pady=2)

        #Status Section
        status_frame =tk.LabelFrame(self.control_window,text="Status",bg='#2b2b2b',fg='white',font=('Arial',12,'bold'))
        status_frame.pack(fill=tk.X,padx=10,pady=10)

        self.status_label=tk.Label(status_frame,text="ready - Select and Start Camera",bg='#2b2b2b',fg='#ffff00',font=('Arial',10))
        self.status_label.pack(pady=5)

        self.left_hand_status = tk.Label(status_frame,text="Left Hand: None",bg='#2b2b2b',fg='#ffff00',font=('Arial',10))
        self.left_hand_status.pack(pady=2)

        self.right_hand_status=tk.Label(status_frame,text="Right Hand: None",bg='#2b2b2b',fg='#ffff00',font=('Arial',10))
        self.right_hand_status.pack(pady=2)

        self.mode_status=tk.Label(status_frame,text=f"Mode: {self.current_input_mode}",bg='#2b2b2b',fg='#00ffff',font=('Arial',10))
        self.mode_status.pack(pady=2)

        #Instructions
        instructions=tk.Text(self.control_window,height=8,width=55,bg='#1a1a1a',fg='white',font=('Arial',9))
        instructions.pack(padx=10,pady=10)

        instructions.pack(padx=10,pady=10)

        instructions.insert(tk.END,"""MULTI_HAND OVERLAY WITH CAMERA SELECTOR:
                            CAMERA SETUP:
                            1. Click "Select Camera" to choose your camera
                            2. Click "Start Camera" to v=begin gesture detection
                            3. Use CAMERA key in overlay to change camera
                            
                            MULTI-HAND FEATURES:
                            > Both hands can type simultaneously
                            >Left hand= Blue indicators
                            >Right hand= Red indicators
                            >Background mode for transparent overlay
                            >Camera info display on overlay
                            
                            GESTURES: POINT,PINCH,FIST (same for both hands)
                            
                            SHORTCUTS: Q=Quit,C=Change camera,H=Help,R=Reclibrate""")
        
        instructions.config(state=tk.DISABLED)

        # Handle window closing
        self.control_window.protocol("WM_DELETE_WINDOW",self.on_control_window_close)

        # Start control window in separate thread
        self.control_thread=threading.Thread(target=self.run_control_window,daemon=True)
        self.control_thread.start()

    def run_control_window(self):
        """Run control window mainloop"""
        self.control_window.mainloo()
    
    def on_control_window_close(self):
        """Handle control window closing"""
        self.save_settngs()
        self.running= False
        self.control_window.quit()

    def show_camera_selector(self):
        """Show camera selector dialog"""
        def on_camera_selected(camera_index):
            if camera_index is not None:
                self.selected_camera_index=camera_index
                self.camera_info_label.config(text=f"Camera {camera_index} selected")
                self.status_label.config(text="Camera selected - Ready to start")

                # If Camera id currently running, restart with new camera
                if self.camera_ready:
                    self.stop_camera()
                    time.sleep(0.5)
                    self.start_camera()
        
        self.camera_selector.show_camera_selector(callback=on_camera_selected)
    
    def tooggle_camera(self):
        """Start or stop camera"""
        if not self.camera_ready:
            self.start_camera()
        else:
            self.stop_camera()

    