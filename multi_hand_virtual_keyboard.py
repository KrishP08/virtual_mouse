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
        tk.Label(display_frame,text="Keyboard Size:",
                 bg='#2b2b2b',fg='white',font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=(10,2))
        
        self.size_var = tk.DoubleVar(value=self.display_settings["keyboard_size"])
        size_scale = tk.Scale(display_frame, from_=0.4, to=0.8, resolution=0.1,
                             variable=self.size_var, orient=tk.HORIZONTAL,
                             command=self.change_keyboard_size,
                             bg='#2b2b2b', fg='white', highlightbackground='#2b2b2b',
                             length=200)
        size_scale.pack(padx=10, pady=2)

        #Selection duration
        tk.Label(display_frame,text="point Hold Duration(Seconds):",
                 bg='#2b2b2b',fg='white',font=('Arial,10')).pack(anchor=tk.W,padx=10,pady=(10,2))
        
        self.duration_var=tk.DoubleVar(value=self.display_settings["selection_duration"])
        duration_scale=tk.Scale(display_frame,from_=1.0,to=5.0,resolution=0.5,
                                variable=self.duration_var,orient=tk.HORIZONTAL,
                                command=self.change_selection_duration,
                                bg='#2b2b2b',fg='white',highlightbackground='#2b2b2b',
                                length=200)
        duration_scale.pack(padx=10,pady=2)

        #Window transparency
        tk.Label(display_frame,text="Window Transparency:",
                 bg='#2b2b2b',fg='white',font=('Arial',10)).pack(anchor=tk.W,padx=10,pady=(10,2))
        
        self.window_transparency_var=tk.DoubleVar(value=self.display_settings["window_transparency"])
        window_transparency_scale=tk.Scale(display_frame,from_=0.2,to=1.0,resolution=0.1,
                                           variable=self.window_transparency_var,orient=tk.HORIZONTAL,
                                           command=self.change_window_transparemcy,
                                           bg='@2b2b2b',fg='white',highlightbackground='#2b2b2b',
                                           length=200)
        window_transparency_scale.pack(padx=10,pady=2)

        #Control Buttons Section
        control_frame=tk.LabelFrame(self.control_window,text="Controls",
                                    bg='#2b2b2b',fg='white',font=('Arial',12,'bold'))
        control_frame.pack(fill=tk.X,padx=10,pady=10)

        button_frame=tk.Frame(control_frame,bg='#2b2b2b')
        button_frame.pack(pady=10)

        tk.Button(button_frame,text="Toggle Keyboard",command=self.toggle_keyboard_visibility,
                  bh='#404040',fg='white',font=('Arial',10),width=15).pack(side=tk.LEFT,padx=5)
        
        tk.Button(button_frame,text="Reset Position",command=self.reset_window_position,
                  bg='#404040',fg='white',font=('Arial',10),width=15).pack(side=tk.LEFT,padx=5)
       
        tk.Button(button_frame,text="Recalibrate",command=self.recalibrate_hand_tracking,
                  bg='#2b2b2b',fg='white',font=('Arial',10),width=15).pack(side=tk.LEFT,padx=5)
        
        #Status Section
        status_frame=tk.LabelFrame(self.control_window,text="Status",
                                   bg='#2b2b2b',fg='white',font=('Arial',12,'bold'))
        status_frame.pack(fill=tk.X,padx=10,pady=10)

        self.status_label=tk.Label(status_frame,text="Ready",
                                   bg='#2b2b2b',fg='#00ff00',font=('Arial',10))
        self.status_label.pack(pady=5)

        self.left_hand_status=tk.Label(status_frame,text="Left Hand:None",
                                       bg='#2b2b2b',fg='#ffff00',font=('Arial',10))
        self.left_hand_status.pack(pady=2)

        self.right_hand_status=tk.Label(status_frame,text="Right Hand: None",
                                        bg='#2b2b2b',fg='#ffff00',font=('Arial',10))
        self.right_hand_status.pack(pady=2)

        self.mode_status=tk.Label(status_frame,text=f"Mode:{self.current_input_mode}",
                                  bg='#2b2b2b',fg='#00ffff',font=('Arial',10))
        self.mode_status.pack(pady=2)

        #Instructions
        instructions=tk.Text(self.control_window,height=8,width=50,
                             bg='#1a1a1a',fg='white',font=('Arial',2))
        instructions.pack(padx=10,pady=10)

        instructions.insert(tk.END,"""MULTI-HAND OVERLAY CONTROLS:
                            • Both hands can type simultaneously
                            • Left hand=Blue indicators
                            • Right hand = Red indicators
                            • Background mode for transprent overlay
                            • Works over other applications

                            GESTURES: POINT,PINCH,FIST(same for both hands)
                            
                            KEYBOARD SHORTCUTS:
                            • R: Recalibrate hand tracking
                            • B: Toggle background mode
                            • C: Toggle Camera display
                            • H: Toggle help text
                            • K: Toggle keyboard visibility
                            • T: Toggle transparency
                            • D: Toggle debug mode
                            • Q: Quit appliction""")
        instructions.config(state=tk.DISABLED)

        #Handle window closing
        self.control_window.protocol("WM_DELETE_WINDOW",self.on_control_window_close)

        #Start control window in separater thread
        self.control_thread=threading.thread(target=self.run_control_window,daemon=True)
        self.control_thread.start()
    def run_control_window(self):
        """Run control window mainloop"""
        self.control_window.mainloop()
    
    def on_control_window_close(self):
        """Handle control window closing"""
        self.save_settings()
        self.running=False
        self.controls_window.quit()
    
    