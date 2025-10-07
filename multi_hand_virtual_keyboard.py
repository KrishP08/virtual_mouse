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
    #here5/10/2025
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
        
        # Hand priority
        tk.Label(multi_hand_frame, text="Hand Priority:", 
                bg='#2b2b2b', fg='white', font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=(10,2))
        
        self.priority_var = tk.StringVar(value=self.multi_hand_settings["hand_priority"])
        priority_frame = tk.Frame(multi_hand_frame, bg='#2b2b2b')
        priority_frame.pack(anchor=tk.W, padx=20)
        
        tk.Radiobutton(priority_frame, text="Both Hands", variable=self.priority_var, value="both",
                      command=self.change_hand_priority, bg='#2b2b2b', fg='white',
                      selectcolor='#404040', font=('Arial', 9)).pack(anchor=tk.W)
        tk.Radiobutton(priority_frame, text="Left Hand Only", variable=self.priority_var, value="left",
                      command=self.change_hand_priority, bg='#2b2b2b', fg='white',
                      selectcolor='#404040', font=('Arial', 9)).pack(anchor=tk.W)
        tk.Radiobutton(priority_frame, text="Right Hand Only", variable=self.priority_var, value="right",
                      command=self.change_hand_priority, bg='#2b2b2b', fg='white',
                      selectcolor='#404040', font=('Arial', 9)).pack(anchor=tk.W)
        
        # Input Mode Section
        mode_frame = tk.LabelFrame(self.control_window, text="Input Mode", 
                                  bg='#2b2b2b', fg='white', font=('Arial', 12, 'bold'))
        mode_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.mode_var = tk.StringVar(value=self.current_input_mode)
        
        tk.Radiobutton(mode_frame, text="Point Only (Hold 2.0s)", 
                      variable=self.mode_var, value="point_only",
                      command=self.change_input_mode, bg='#2b2b2b', fg='white',
                      selectcolor='#404040', font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=2)
        
        tk.Radiobutton(mode_frame, text="Pinch Only (Instant)", 
                      variable=self.mode_var, value="pinch_only",
                      command=self.change_input_mode, bg='#2b2b2b', fg='white',
                      selectcolor='#404040', font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=2)
        
        tk.Radiobutton(mode_frame, text="Both (Point + Pinch)", 
                      variable=self.mode_var, value="both",
                      command=self.change_input_mode, bg='#2b2b2b', fg='white',
                      selectcolor='#404040', font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=2)
        
        # Display Settings Section
        display_frame = tk.LabelFrame(self.control_window, text="Display Settings", 
                                     bg='#2b2b2b', fg='white', font=('Arial', 12, 'bold'))
        display_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Background mode toggle
        self.bg_mode_var = tk.BooleanVar(value=self.display_settings["background_mode"])
        tk.Checkbutton(display_frame, text="Background Mode (Transparent)", 
                      variable=self.bg_mode_var, command=self.toggle_background_mode,
                      bg='#2b2b2b', fg='white', selectcolor='#404040',
                      font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=2)
        
        # Show camera toggle
        self.show_camera_var = tk.BooleanVar(value=self.display_settings["show_camera"])
        tk.Checkbutton(display_frame, text="Show Camera Feed", 
                      variable=self.show_camera_var, command=self.toggle_camera_display,
                      bg='#2b2b2b', fg='white', selectcolor='#404040',
                      font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=2)
        
        # Show hand labels
        self.show_labels_var = tk.BooleanVar(value=self.display_settings["show_hand_labels"])
        tk.Checkbutton(display_frame, text="Show Hand Labels", 
                      variable=self.show_labels_var, command=self.toggle_hand_labels,
                      bg='#2b2b2b', fg='white', selectcolor='#404040',
                      font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=2)
        
        # Window transparency
        tk.Label(display_frame, text="Keyboard Overlay Transparency:", 
                bg='#2b2b2b', fg='white', font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=(10,2))
        
        self.alpha_var = tk.DoubleVar(value=self.display_settings["window_alpha"])
        alpha_scale = tk.Scale(display_frame, from_=0.3, to=1.0, resolution=0.1,
                              variable=self.alpha_var, orient=tk.HORIZONTAL,
                              command=self.change_transparency,
                              bg='#2b2b2b', fg='white', highlightbackground='#2b2b2b',
                              length=200)
        alpha_scale.pack(padx=10, pady=2)
        
        # Keyboard size
        tk.Label(display_frame, text="Keyboard Size:", 
                bg='#2b2b2b', fg='white', font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=(10,2))
        
        self.size_var = tk.DoubleVar(value=self.display_settings["keyboard_size"])
        size_scale = tk.Scale(display_frame, from_=0.4, to=0.8, resolution=0.1,
                             variable=self.size_var, orient=tk.HORIZONTAL,
                             command=self.change_keyboard_size,
                             bg='#2b2b2b', fg='white', highlightbackground='#2b2b2b',
                             length=200)
        size_scale.pack(padx=10, pady=2)

        # Selection duration
        tk.Label(display_frame, text="Point Hold Duration (seconds):", 
                bg='#2b2b2b', fg='white', font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=(10,2))

        self.duration_var = tk.DoubleVar(value=self.display_settings["selection_duration"])
        duration_scale = tk.Scale(display_frame, from_=1.0, to=5.0, resolution=0.5,
                                 variable=self.duration_var, orient=tk.HORIZONTAL,
                                 command=self.change_selection_duration,
                                 bg='#2b2b2b', fg='white', highlightbackground='#2b2b2b',
                                 length=200)
        duration_scale.pack(padx=10, pady=2)

        # Window transparency
        tk.Label(display_frame, text="Window Transparency:", 
                bg='#2b2b2b', fg='white', font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=(10,2))
        
        self.window_transparency_var = tk.DoubleVar(value=self.display_settings["window_transparency"])
        window_transparency_scale = tk.Scale(display_frame, from_=0.2, to=1.0, resolution=0.1,
                             variable=self.window_transparency_var, orient=tk.HORIZONTAL,
                             command=self.change_window_transparency,
                             bg='#2b2b2b', fg='white', highlightbackground='#2b2b2b',
                             length=200)
        window_transparency_scale.pack(padx=10, pady=2)
        
        # Control Buttons Section
        control_frame = tk.LabelFrame(self.control_window, text="Controls", 
                                     bg='#2b2b2b', fg='white', font=('Arial', 12, 'bold'))
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        button_frame = tk.Frame(control_frame, bg='#2b2b2b')
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Toggle Keyboard", command=self.toggle_keyboard_visibility,
                 bg='#404040', fg='white', font=('Arial', 10), width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Reset Position", command=self.reset_window_position,
                 bg='#404040', fg='white', font=('Arial', 10), width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Recalibrate", command=self.recalibrate_hand_tracking,
                 bg='#404040', fg='white', font=('Arial', 10), width=15).pack(side=tk.LEFT, padx=5)
        
        # Status Section
        status_frame = tk.LabelFrame(self.control_window, text="Status", 
                                    bg='#2b2b2b', fg='white', font=('Arial', 12, 'bold'))
        status_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.status_label = tk.Label(status_frame, text="Ready", 
                                    bg='#2b2b2b', fg='#00ff00', font=('Arial', 10))
        self.status_label.pack(pady=5)
        
        self.left_hand_status = tk.Label(status_frame, text="Left Hand: None", 
                                        bg='#2b2b2b', fg='#ffff00', font=('Arial', 10))
        self.left_hand_status.pack(pady=2)
        
        self.right_hand_status = tk.Label(status_frame, text="Right Hand: None", 
                                         bg='#2b2b2b', fg='#ffff00', font=('Arial', 10))
        self.right_hand_status.pack(pady=2)
        
        self.mode_status = tk.Label(status_frame, text=f"Mode: {self.current_input_mode}", 
                                   bg='#2b2b2b', fg='#00ffff', font=('Arial', 10))
        self.mode_status.pack(pady=2)
        
        # Instructions
        instructions = tk.Text(self.control_window, height=8, width=50, 
                              bg='#1a1a1a', fg='white', font=('Arial', 9))
        instructions.pack(padx=10, pady=10)
        
        instructions.insert(tk.END, """MULTI-HAND OVERLAY CONTROLS:
• Both hands can type simultaneously
• Left hand = Blue indicators
• Right hand = Red indicators
• Background mode for transparent overlay
• Works over other applications

GESTURES: POINT, PINCH, FIST (same for both hands)

KEYBOARD SHORTCUTS:
• R: Recalibrate hand tracking
• B: Toggle background mode
• C: Toggle camera display
• H: Toggle help text
• K: Toggle keyboard visibility
• T: Toggle transparency
• D: Toggle debug mode
• Q: Quit application""")
        
        instructions.config(state=tk.DISABLED)
        
        # Handle window closing
        self.control_window.protocol("WM_DELETE_WINDOW", self.on_control_window_close)
        
        # Start control window in separate thread
        self.control_thread = threading.Thread(target=self.run_control_window, daemon=True)
        self.control_thread.start()
    
    def run_control_window(self):
        """Run control window mainloop"""
        self.control_window.mainloop()
    
    def on_control_window_close(self):
        """Handle control window closing"""
        self.save_settings()
        self.running = False
        self.control_window.quit()
    
    def toggle_multi_hand(self):
        """Toggle multi-hand tracking"""
        self.multi_hand_settings["enabled"] = self.multi_hand_var.get()
        # Update MediaPipe settings
        max_hands = 2 if self.multi_hand_settings["enabled"] else 1
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        print(f"Multi-hand tracking: {self.multi_hand_settings['enabled']}")
    
    def toggle_simultaneous_typing(self):
        """Toggle simultaneous typing"""
        self.multi_hand_settings["simultaneous_typing"] = self.simultaneous_var.get()
        print(f"Simultaneous typing: {self.multi_hand_settings['simultaneous_typing']}")
    
    def change_hand_priority(self):
        """Change hand priority"""
        self.multi_hand_settings["hand_priority"] = self.priority_var.get()
        print(f"Hand priority: {self.multi_hand_settings['hand_priority']}")
    
    def toggle_hand_labels(self):
        """Toggle hand labels display"""
        self.display_settings["show_hand_labels"] = self.show_labels_var.get()
        print(f"Show hand labels: {self.display_settings['show_hand_labels']}")
    
    def change_input_mode(self):
        """Change input mode based on selection"""
        self.current_input_mode = self.mode_var.get()
        self.overlay_dirty = True
        self.mode_status.config(text=f"Mode: {self.current_input_mode}")
        print(f"Input mode changed to: {self.current_input_mode}")
    
    def toggle_background_mode(self):
        """Toggle background mode"""
        self.display_settings["background_mode"] = self.bg_mode_var.get()
        print(f"Background mode: {self.display_settings['background_mode']}")
    
    def toggle_camera_display(self):
        """Toggle camera display"""
        self.display_settings["show_camera"] = self.show_camera_var.get()
        print(f"Show camera: {self.display_settings['show_camera']}")
    
    def change_transparency(self, value):
        """Change keyboard overlay transparency"""
        self.display_settings["window_alpha"] = float(value)
    
    def change_keyboard_size(self, value):
        """Change keyboard size"""
        self.display_settings["keyboard_size"] = float(value)
        self.overlay_dirty = True
    
    def change_selection_duration(self, value):
        """Change selection duration for POINT gesture"""
        self.display_settings["selection_duration"] = float(value)
        self.selection_duration = float(value)
        print(f"Point hold duration changed to: {value} seconds")
    
    def change_window_transparency(self, value):
        """Change overall window transparency"""
        self.display_settings["window_transparency"] = float(value)
    
    def toggle_keyboard_visibility(self):
        """Toggle keyboard visibility"""
        self.keyboard_visible = not self.keyboard_visible
        print(f"Keyboard visible: {self.keyboard_visible}")
    
    def reset_window_position(self):
        """Reset camera window position"""
        print("Window position reset")

    def recalibrate_hand_tracking(self):
        """Recalibrate hand tracking parameters"""
        print("Recalibrating hand tracking...")
        # Recreate the hands object with adjusted parameters
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        # Reset hand states
        for hand_label in ["left", "right"]:
            self.hand_states[hand_label]["gesture"] = "none"
            self.hand_states[hand_label]["selected_key"] = None
        
        self.status_label.config(text="Recalibrated hand tracking")
    
    def calculate_distance(self, point1, point2):
        """Calculate distance between two points"""
        return math.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)**2)
    
    def detect_hand_gesture(self, landmarks):
        """Detect gesture for a single hand with improved accuracy"""
        if not landmarks:
            return "none"
        
        # Get key points
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        index_tip = landmarks[8]
        index_pip = landmarks[6]
        index_mcp = landmarks[5]
        middle_tip = landmarks[12]
        middle_pip = landmarks[10]
        ring_tip = landmarks[16]
        ring_pip = landmarks[14]
        pinky_tip = landmarks[20]
        pinky_pip = landmarks[18]
        
        # Calculate relative positions (more robust than absolute y coordinates)
        index_extended = (index_tip.y < index_pip.y) and (index_tip.y < index_mcp.y)
        middle_extended = middle_tip.y < middle_pip.y
        ring_extended = ring_tip.y < ring_pip.y
        pinky_extended = pinky_tip.y < pinky_pip.y
        
        # Calculate thumb-index distance for pinch
        thumb_index_dist = self.calculate_distance(thumb_tip, index_tip)
        
        # Gesture classification with improved logic
        if thumb_index_dist < 0.06:  # Slightly more lenient pinch threshold
            return "pinch"
        elif index_extended and not middle_extended and not ring_extended and not pinky_extended:
            # Only index finger extended - POINT gesture
            return "point"
        elif not index_extended and not middle_extended and not ring_extended and not pinky_extended:
            # All fingers closed - FIST gesture
            return "fist"
        else:
            return "none"
    
    def get_hand_pointing_position(self, landmarks, frame_shape):
        """Get index finger tip position for a hand"""
        if landmarks:
            index_tip = landmarks[8]
            h, w = frame_shape[:2]
            x = int(index_tip.x * w)
            y = int(index_tip.y * h)
            return (x, y)
        return None
    
    def determine_hand_label(self, hand_landmarks, handedness):
        """Determine if hand is left or right"""
        if handedness and len(handedness.classification) > 0:
            # MediaPipe returns "Left" or "Right" from camera perspective
            label = handedness.classification[0].label
            # Fix the hand labeling - don't flip since camera is already mirrored
            return label.lower()
        
        # Fallback: determine by thumb position
        thumb_tip = hand_landmarks.landmark[4]
        thumb_ip = hand_landmarks.landmark[3]
        
        if thumb_tip.x > thumb_ip.x:
            return "right"
        else:
            return "left"
    
    def create_fullscreen_overlay(self, frame_shape):#here5/10/2025
        """Create fullscreen keyboard overlay with multi-hand indicators and improved bottom row detection"""
        h, w = frame_shape[:2]
        overlay = np.zeros((h, w, 3), dtype=np.uint8)
        
        layout = self.keyboard_layouts[self.current_layout]
        
        # Calculate keyboard dimensions with better spacing
        keyboard_height = int(h * self.display_settings["keyboard_size"])
        keyboard_width = int(w * 0.95)  # Slightly wider for better key spacing
        
        # Move keyboard up to ensure bottom rows are more accessible
        keyboard_start_y = int(h * 0.35)  # Start at 35% from top instead of bottom-based
        keyboard_start_x = (w - keyboard_width) // 2
        
        # Calculate key dimensions with improved spacing
        total_rows = len(layout)
        key_height = (keyboard_height - 20) // total_rows  # Account for row spacing
        
        self.key_positions = {}
        
        for row_idx, row in enumerate(layout):
            # Add spacing between rows
            row_y = keyboard_start_y + (row_idx * (key_height + 4))
            
            # Calculate key width for this specific row
            row_key_width = (keyboard_width - 20) // len(row)  # Account for key spacing
            
            # Center the row
            row_start_x = keyboard_start_x + (keyboard_width - (len(row) * row_key_width)) // 2
            
            for col_idx, key in enumerate(row):
                key_x = row_start_x + (col_idx * row_key_width)
                
                # Store key position with improved bounds
                self.key_positions[key] = {
                    'x': key_x + 2,
                    'y': row_y + 2,
                    'width': row_key_width - 4,
                    'height': key_height - 4,
                    'row': row_idx,  # Store row index for better mapping
                    'col': col_idx   # Store column index for better mapping
                }
                
                # Determine key color based on selection state
                color = (50, 50, 50)  # Default gray
                border_color = (255, 255, 255)  # Default white border
                
                # Check if key is selected by either hand
                left_selected = self.hand_states["left"]["selected_key"] == key
                right_selected = self.hand_states["right"]["selected_key"] == key
                
                if left_selected and right_selected:
                    color = (128, 0, 128)  # Purple for both hands
                    border_color = (255, 0, 255)
                elif left_selected:
                    color = (100, 0, 0)  # Dark blue for left hand
                    border_color = (255, 0, 0)
                elif right_selected:
                    color = (0, 0, 100)  # Dark red for right hand
                    border_color=(0,0,255)
                elif key in ['POINT','PINCH','BOTH']:
                    if (key.lower()==self.current_input_mode or key=='BOTH' and self.current_input_mode=='both'):
                        color=(0,255,0)
                        border_color=(0,255,0)
                    else:
                        color=(100,100,0)
                elif key=='QUIT':
                    color=(0,0,150)
                elif key in['SPACE','BACKSPACE','ENTER']:
                    color(100,100,100)
                elif key in ['NUMBERS','LETTERS']:
                    color=(0,100,200)
                    
                #Make bottom row keys more visible
                if row_idx>=total_rows-2:
                    border_color=(0,255,255)
                    #Slightly brighter color for bottom rows
                    color=(min(color[0]+3,255),min(color[1]+30,255),min(color[2]+30,255))
                
                #Draw key background
                cv2.rectangle(overlay,
                              (key_x+2,row_y+2),
                              (key_x+row_key_width-2,row_y+key_height-2),
                              color,-1)
                
                #Draw key border
                cv2.rectangle(overlay,
                             (key_x + 2, row_y + 2), 
                             (key_x + row_key_width - 2, row_y + key_height - 2), 
                             border_color, 3)  # Thicker border for better visibility
                
                #Draw kry text with better sizing
                font_scale=min(row_key_width,key_height)/100.0
                font_scale=max(0.5,min(font_scale,1.2))

                text_size=cv2.getTextSize(key,cv2.FONT_HERSHEY_SIMPLEX,font_scale,2)[0]
                text_x=key_x+(row_key_width-text_size[0])//2
                text_y=row_y+(key_height+text_size[1])//2

                cv2.putText(overlay,key,(text_x,text_y),cv2.FONT_HERSHEY_SIMPLEX,font_scale,(255,255,255),2)
        
        # Draw mode and multi-hand indicators
        if self.show_mode_indicator:
            mode_text=f"Mode: {self.current_input_mode.upper}"
            multi_hand_text=f"Multi-Hand:{'ON' if self.multi_hand_settings['enabled']else 'OFF'}"
            duration_text=f"Hold Duration: {self.selection_duration}s"
            bg_mode_text=f"Background:{'ON' if self.display_settings['background_mode'] else 'OFF'}"

            cv2.putText(overlay,mode_text,(20,30),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,255,255),2)
            cv2.putText(overlay,multi_hand_text,(20,60),cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,255,0),2)
            cv2.putText(overlay,duration_text,(20,90),cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,0),2)
            cv2.putText(overlay,bg_mode_text,(20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if self.display_settings['background_mode'] else (255, 0, 0), 2)

            #Add help text for recalibration
            cv2.putText(overlay,"Press 'R' to recalibrate hand tracking",(w-400,h-30),cv2.FONT_HERSHEY_SIMPLEX,0.6,(200,200,200),2)
        
        return overlay
    def map_point_to_key(self,point):
        """Map screen point to keyboard key with improved accuracy for all rows"""
        if not point or not hasattr(self,'key_positions'):
            return None
        
        x,y=point

        #Find the closet key to the pointing position
        closets_key=None
        min_distance=float('inf')

        for key,pos in self.key_positions.items():
            #Calculate center of key
            key_center_x=pos['x']+pos['width']/2
            key_center_y=pos['y']+pos['height']/2

            #Calculate distance to key center
            distance=math.sqrt((x-key_center_x)**2+(y-key_center_y)**2)

            #Apply row-based weighting (give more weight to bottom rows)
            row_weight=1.0
            if 'row' in pos:
                #Bottom rows get more weight(easier to select)
                if pos['row']>=len(self.keyboard_layouts[self.current_layout])-2:
                    row_weight=1.3
            
            #Apply weighted distance
            weighted_distance=distance/row_weight

            #Update closest key if this one is closer
            if weighted_distance<min_distance:
                min_distance=weighted_distance
                closets_key=key
        #Only return the key if it's within a reasonable distance
        max_distance=50
        if min_distance<=max_distance:
            return closets_key
        
        return None
    
    def can_type_key(self,key):
        """Check if key can be typed"""
        current_time=time.time()

        if key==self.last_typed_key:
            if current_time - self.last_typed_time<self.same_key_cooldown:
                return False
            
        return True
    
    def handle_special_keys(self,key):
        """Handle special control keys"""
        if key=='POINT':
            self.current_input_mode='point_only'
            self.mode_var.set('point_only')
            self.overlay_dirty=True
            self.mode_status.config(text=f"Mode: {self.current_input_mode}")
            return True
        elif key=='PINCH':
            self.current_input_mode='pinch_only'
            self.mode_var.set('pinch_only')
            self.overlay_dirty=True
            self.mode_status.config(text=f"Mode: {self.current_input_mode}")
            return True
        elif key=="BOTH":
            self.current_input_mode='both'
            self.mode_var.set('both')
            self.overlay_dirty=True
            self.mode_status.config(text=f"Mode: {self.current_input_mode}")
            return True
        elif key =='QUIT':
            self.running=False
            return True

        return False
    def type_key(self,key,hand_label=""):
        """Type a key with hand identification"""
        # Handle sepcial keys first
        if self.handle_special_keys(key):
            return True
        
        if not self.can_type_key(key):
            return False
        
        try:
            if key =='SPACE':
                self.keyboard.press(Key.space)
                self.keyboard.release(Key.space)
            elif key=='BACKSPACE':
                self.keyboard.press(key.backspace)
                self.keyboard.release(key.backspace)
            elif key=='ENTER':
                self.keyboard.press(key.enter)
                self.keyboard.release(key.enter)
            elif key=='NUMBER':
                self.current_layout="numbers"
                self.overlay_dirty=True
                return True
            elif key =='LETTERS':
                self.current_layout="letters"
                self.overlay_dirty=True
                return True
            else:
                self.keyboard.type(key.lower())

            #Update last typed key info
            self.last_typed_key=key
            self.last_typed_time=time.time()

            print(f"Typed: {key} (by {hand_label} hand)")
            return True
        
        except Exception as e:
            print(f"Error typing key {key}: {e}")
            return False
    def draw_multi_hand_indicators(self,frame,hand_data):
        """Draw indicators for both hands"""
        # Draw indicators for hands that were recently detected but might be temorarliy lost
        for hand_label in ["left","right"]:
            if self.hand_states[hand_label]["pointing_pos"] and self.hand_states[hand_label]["selected_key"]:
                pointing_pos=self.hand_states[hand_label]["pointing_pos"]
                if hand_label=="left":
                    color=(255,0,0)
                    text_color=(255,100,100)
                else:
                    color=(0,0,255)
                    text_color=(100,100,255)

                #Draw a faded indicator for temporarily lost hands
                cv2.circle(frame,pointing_pos,8,color,1)

        for hand_info in hand_data:
            hand_label=hand_info["label"]
            pointing_pos=hand_info["pointing_pos"]
            gesture=hand_info["gesture"]

            if not pointing_pos:
                continue

            #Choose colors bases on hand
            if hand_label=="left":
                color=(255,0,0)
                text_color=(255,100,100)
            else:
                color=(0,0,255)
                text_color=(100,100,255)

            x,y=pointing_pos

            #Draw pointing indicator
            cv2.circle(frame,(x,y),8,color,-1)
            cv2.circle(frame,(x,y),15,color,2)

            #Draw hand label if enabled
            if self.display_settings["show_hand_labels"]:
                label_text=f"{hand_label.upper()}"
                cv2.putText(frame,label_text,(x-20,y-25),cv2.FONT_HERSHEY_SIMPLEX,0.5,text_color,2)

            #Draw selection progress for point mode
            selected_key=self.hand_states[hand_label]["selected_key"]
            if (gesture=="point" and selected_key and self.input_modes[self.current_input_mode]["point"]):
                self.draw_selection_progress(frame,pointing_pos,hand_label)

    def draw_selection_progress(self,frame,point,hand_label):
        """Draw selection progress indicator for a sepcific hand"""
        if not point:
            return
        
        current_time=time.time()
        start_time=self.hand_states[hand_label]["selection_start_time"]
        elapsed=current_time-start_time
        progress=min(elapsed/self.selection_duration,1.0)

        x,y=point
        radius=25

        #CHoose color based on hand
        if hand_label=="left":
            progress_color=(255,0,0)
        else:
            progress_color=(0,0,255)
        
        #Draw progress arc
        angle=int(360*progress)
        if angle>0:
            axes=(radius,radius)
            cv2.ellipse(frame,(x,y),axes,-90,0,angle,progress_color,4)

        #Draw progress text
        progress_text=f"{int(progress * 100)}"
        text_size=cv2.getTextSize(progress_text,cv2.FONT_HERSHEY_SIMPLEX,0.5,2)[0]
        text_x=x-text_size[0]//2
        text_y=y-35
        cv2.putText(frame,progress_text,(text_x,text_y),cv2.FONT_HERSHEY_SIMPLEX,progress_color,2)
    
    def draw_status_info(self,frame):
        """Draw status information with multi-hand support"""
        h,w=frame.shape[:2]

        if not self.display_settings["show_camera"]:
            return
        
        #Multi-hand status
        left_gesture=self.hand_states["left"]["gesture"]
        right_gesture=self.hand_states["right"]["gesture"]

        cv2.putText(frame,f"Left Hand: {left_gesture}",(10,30),cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,0,0),2)
        cv2.putText(frame,f"Right Hand: {right_gesture}",(10,60),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,255),2)

        #Selected keys
        left_key=self.hand_states["left"]["selected_key"]
        right_key=self.hand_states["right"]["selected_key"]

        if left_key:
            cv2.putText(frame,f"Left Selected: {left_key}",(10,90),cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,100,100),2)
        if right_key:
            cv2.putText(frame,f"Right Selected: {right_key}",(10,120),cv2.FONT_HERSHEY_SIMPLEX,0.6,(100,100,255),2)

        #Input mode and Settings
        cv2.putText(frame,f"Mode: {self.current_input_mode.upper()}",(10,150),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,255),2)

        multi_status = "ON" if self.multi_hand_settings["enabled"] else "OFF"
        cv2.putText(frame, f"Multi-Hand: {multi_status}", (10, 180), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        bg_status = "ON" if self.display_settings["background_mode"] else "OFF"
        cv2.putText(frame, f"Background: {bg_status}", (10, 210), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if self.display_settings["background_mode"] else (255, 0, 0), 2)

        #help text
        if self.show_help:
            help_text=[
                f"Hold Duration: {self.selection_duration}s",
                "Blue = Left Hand,Red = Right Hand",
                "Both hands can type simultaneously",
                "Background mode for overlayoperation",
                "Q: Quit, H: Toggle help,T: Toggle transparency"
            ]

            for i,text in enumerate(help_text):
                cv2.putText(frame,"DEBUG MODE ON",(w-200,h-60),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,255),2)

                #Show hand positions
                left_pos=self.hand_states["left"]["pointing_pos"]
                right_pos=self.hand_states["right"]["pointing_pos"]

                if left_pos:
                    cv2.putText(frame,f"Left pos: {left_pos}",(10,h-90),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,0,0),1)
                
                if right_pos:
                    cv2.putText(frame,f"Right pos: {right_pos}",(10,h-60),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,255),1)

                #Show key mapping info
                if left_pos:
                    left_key=self.map_point_to_key(left_pos)
                    cv2.putText(frame,f"Left maps to: {left_key}",(10,h-30),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,0,0),1)

                if right_pos:
                    right_key=self.map_point_to_key(right_pos)
                    cv2.putText(frame,f"Right maps to: {right_key}",(255,h-30),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,255),1)

    def process_multi_hand_gestures(self,hand_data):
        """Process gestures for multiple hands"""
        current_time=time.time()
        mode_settings=self.input_modes[self.current_input_mode]

        #Update hand states for hands that are no longwe detected
        current_hand_labels=[hand_info["label"] for hand_info in hand_data]
        for hand_label in ["left","right"]:
            if hand_label not in current_hand_labels:
                #Hand is not currently detected,update its state
                self.hand_states[hand_label]["gesture"]="none"
                #Don't clear pointing position or selection immediately to prevernt flickering
                #Only clear if it's been gone for a while
                if self.hand_states[hand_label]["selected_key"] and current_time - self.hand_states[hand_label]["selection_start_time"]>3.0:
                    self.hand_states[hand_label]["selected_key"]=None
                    self.overlay_dirty=True
        
        #Process each hand
        for hand_info in hand_data:
            hand_label = hand_info["label"]
            gesture=hand_info["gesture"]
            pointing_pos = hand_info["pointing_pos"]

            #Skip if hand is disabled by priority settings
            priority=self.multi_hand_settings["hand_priority"]
            if priority != "both" and priority != hand_label:
                continue

            #update hand state
            self.hand_states[hand_label]["gesture"]=gesture
            self.hand_states[hand_label]["pointing_pos"]=pointing_pos

            #Process point gesture
            if gesture =="point" and pointing_pos and mode_settings["point"]:
                key =self.map_point_to_key(pointing_pos)

                if key and key !=self.hand_states[hand_label]["selected_key"]:
                    #New key selected
                    self.hand_states[hand_label]["selected_key"]=key
                    self.hand_states[hand_label]["selection_start_time"]=current_time
                    self.overlay_dirty=True

                elif key==self.hand_states[hand_label]["selected_key"]:
                    #Continue selecting same key
                    start_time=self.hand_states[hand_label]["selection_start_time"]
                    elapsed=current_time-start_time

                    if elapsed >= self.selection_duration:
                        #Type the key
                        if self.type_key(key,hand_label):
                            self.hand_states[hand_label]["selected_key"]=None
                            self.overlay_dirty=True
                
            #process pinch gesture
            elif gesture == "pinch" and pointing_pos and mode_settings["pinch"]:
                key=self.map_point_to_key(pointing_pos)
                if key:
                    if self.type_key(key,hand_label):
                        self.hand_states[hand_label]["selected_key"]=None
                        self.overlay_dirty=True
            
            #Process fist gesture
            elif gesture == f"fist":
                if self.hand_states[hand_label]["selected_key"]:
                    self.hand_states[hand_label]["selected_key"]=None
                    self.overlay_dirty=True
            
            #Clear selection if not gesture for while
            elif gesture == "none":
                if (self.hand_states[hand_label]["selected_key"] and current_time-self.hand_states[hand_label]["selection_start_time"]>3.0):
                    self.hand_states[hand_label]["selected_key"]=None
                    self.overlay_dirty=True
    
    def run(self):
        """Main application loop with multi-hand overlay suppeort"""
        print("Starting Multi-hand Overlay Gesture Keyboard...")
        print(f"Multi-hand tracking: {self.multi_hand_settings['enabled']}")
        print(f"Current input mode: {self.current_input_mode}")
        print("Use the control window to change settings!")

        #Create camera window with transparency support
        cv2.namedWindow('Multi-Hand Gesture Keyboard Overlay',cv2.WINDOW_NORMAL)

        #set initial window properties
        cv2.setWindowProperty('Multi-hand Gesture Keyboard Overlay',cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_NORMAL)

        #Enable transparency (platform-specific)
        try:
            # For Windows
            import ctypes
            hwnd = ctypes.windll.user32.FindWindowW(None, 'Multi-Hand Gesture Keyboard Overlay')
            style = ctypes.windll.user32.GetWindowLongA(hwnd, -20)  # GWL_EXSTYLE
            ctypes.windll.user32.SetWindowLongA(hwnd, -20, style | 0x00080000)  # WS_EX_LAYERED
            # Set initial transparency
            ctypes.windll.user32.SetLayerWindowAttributes(hwnd,0,int(255*self.display_settings["window_transparency"]),2)# LWA_ALPHA
        except Exception as e:
            print(f"Window transparency might not be fully supported on this platform: {e}")
            print("Using alternative transparency method...")

        while self.running:
            ret,feame =self.cap.read()
            if not ret:
                continue

            #Flip frame for mirror effect
            frame=cv2.flip(frame,1)
            h,w=frame.shape[:2]

            #Create a transparent base frame for background mode
            if self.display_settings["background_mode"]:
                #Create transparent background
                display_frame=np.zeros((h,w,4),dtype=np.uint8) # RGBA
                display_frame[:,:,3]=int(255 * self.display_settings["window_transparency"])#Alpha channel
            else:
                #Use camera feed with adjusted transparency
                display_frame=frame.copy()

            #Process hand detection
            rgb_frame=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
            results=self.hands.process(rgb_frame)

            hand_data=[]

            if results.multi_hand_landmarks and results.multi_handedness:
                for hand_landmarks,handedness in zip(results.multi_hand_landmarks,results.multi_handedness):
                    #Determine hand label
                    hand_label=self.determine_hand_label(hand_landmarks,handedness)

                    #Draw haand landmarks if camera is visible
                    if self.display_settings["show_camera"]:
                        #Use different color for different hands
                        if hand_label =="left":
                            landmark_color=(255,0,0)
                            connection_color=(200,0,0)
                        else:
                            landmark_color=(0,0,255)
                            connection_color=(0,0,200)
                        
                        self.mp_draw.draw_landmarks(
                            display_frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                            landmark_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
                                color=landmark_color, thickness=1, circle_radius=1),
                            connection_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
                                color=connection_color, thickness=1)
                        )

                    # Detect gesture and pointing position
                    gesture=self.detect_hand_gesture(hand_landmarks.landmark)
                    pointing_pos=self.get_hand_pointing_position(hand_landmarks.landmark,frame.shape)

                    hand_data.append({
                        "label":hand_label,
                        "gesture":gesture,
                        "pointing_pos":pointing_pos,
                        "landmaeks":hand_landmarks
                    })
            
            # Update status labels
            left_gesture="none"
            right_gesture="none"

            for hand_info in hand_data:
                if hand_info["label"]=="left":
                    left_gesture=hand_info["gesture"]
                elif hand_info["label"]=="right":
                    right_gesture=hand_info["gesture"]
            
            self.left_hand_status.config(text=f"Left Hand: {left_gesture}")
            self.right_hand_status.config(text=f"Right Hand: {right_gesture}")

            #Process multi-hand gestures
            if self.multi_hand_settings["enabled"]:
                self.process_multi_hand_gestures(hand_data)
            else:
                #Single hand mode - use first deteceted hand
                if hand_data:
                    self.process_multi_hand_gestures([hand_data[0]])

            #Create or update overlay if needed
            if self.overlay_dirty or self.overlay_cache is None:
                self.overlay_cache=self.create_fullscreen_overlay(frame.shape)
                self.overlay_dirty=False
            
            #Handle display modes
            if self.display_settings["background_mode"]:
                # Background mode -show only keyboard overlay with transparency
                if not self.display_settings["show_camera"]:
                    #Create a semi-teansparent black background
                    bg=np.zeros_like(frame)
                    #Belnd overlay with transparent bachground
                    alpha=self.display_settings["window_alpha"]
                    display_frame=cv2.addWeighted(bg,1-alpha,self.overlay_cache,alpha,0)
                else:
                    #Blend camera with overlay
                    alpha =self.display_settings["window_alpha"]
                    display_frame=cv2.addWeighted(display_frame,1-alpha,self.overlay_cache,alpha,0)
            else:
                #Normal mode - blend overlay with camera
                if self.display_settings["show_camera"]:
                    display_frame=frame.copy()
                else:
                    #Show only overlay without camrea
                    display_frame=np.zeros_like(frame)
                
                if self.keyboard_visible:
                    alpha =self.display_settings["window_alpha"]
                    display_frame=cv2.addWeighted(display_frame,1-alpha,self.overlay_cache,alpha,0)
            
            #Draw multi-hand indicators
            if hand_data:
                self.draw_multi_hand_indicators(display_frame,hand_data)

            #Draw status information
            self.draw_status_info(display_frame)

            #Show frame
            cv2.imshow('Multi-Hand Gesture Keyboard Overlay',display_frame)

            #Set window properties
            if self.display_settings["always_on_top"]:
                cv2.setWindowProperty('Multi-Hand Gesture Keyboard Overlay',cv2.WND_PROP_TOPMOST,1)

                #Update window transparency (platform-specific)
                try:
                    # For Windows
                    import ctypes
                    hwnd=ctypes.windll.user32.FindWindowW(None,'Multi-hand Gesture Keyboard Overlay')
                    if hwnd:
                        ctypes.windll.user32.SetLayeredWindowAttributes(hwnd,0,int(255 * self.display_settings["window_transparency"]),2)
                except:
                    pass

                # Handle key presses
                key_pressed=cv2.waitKey(1) & 0xFF
                if key_pressed == ord('q'):
                    break
                elif key_pressed ==ord('h'):
                    self.show_help=not self.show_help
                elif key_pressed == ord('k'):
                    self.keyboard_visible =not self.keyboard_visible
                elif key_pressed == ord('t'):
                    #Toggle transparency with hotkey
                    new_transparency=0.3 if self.display_settings["window_transparency"]>0.5 else 0.8
                    self.display_settings["window_transparency"]=new_transparency
                    self.window_transparency_var.set(new_transparency)