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
            bh_mode_text=f"Background:{'ON' if self.display_settings['background_mode'] else 'OFF'}"
            