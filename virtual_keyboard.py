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
        
        #Stats
        self.stats_label=tk.label(
            status_frame,text="Keys:0",
            bg='#1a1a1a',fg='#ff9900',font=('Arial',10)
        )
        self.stats_label.pack(side=tk.RIGHT)

    def create_keyboard_layout(self):
        """Create Keyboard Layout based on current selection"""
        # Clear existing Layout
        for widget in self.keyboard_frame.winfo_children():
            widget.destroy()
        self.key_buttons={}
        layout=self.keyboard_layouts[self.current_layout]

        for row_idx,row in enumerate(layout):
            row_frame=tk.Frame(self.keyboard_frame,bg='#1a1a1a')
            row_frame.pack(pady=2)

            for key in row:
                #Determine button properties
                if key in ['SPACE']:
                    widht,height=20,2
                    bg_color='#333333'
                elif key in ['BACKSPACE','ENTER','SHIFT','CTRL']:
                    width,height=12,2
                    bg_color='#0066cc'
                elif key in['qwerty']:
                    width,height=10,2
                    bg_color='#cc6600'
                else:
                    width,height=4,2
                    bg_color='#4a4a4a'
                
                btn=tk.Button(
                    row_frame,text=key,width=width,height=height,
                    bg=bg_color,fg='white',font=('ARial',10,'bold'),
                    relief=tk.RAISED,bd=2
                )
                btn.pack(side=tk.LEFT,padx=1,pady=1)
                self.key_button[key]=btn
    def change_layout(self,event=None):
        """Change keyboard layout"""
        self.current_layout=self.layout_var.get()
        self.create_keyboard_layout()

    def toggle_keyboard(self):
        """Toggle keyboard visibility"""
        if self.keyboard_frame.winfo_viewable():
            self.keyboard_frame.pack_forget()
        else:
            self.keyboard_frame.pack(fill=tk.BOTH,expand=True,padx=10,pady=5)

    def toggle_background(self):
        """Toggle background mode"""
        self.background_mode = not self.background_mode
        if self.background_mode:
            self.root.withdraw()  # Hide window
            self.status_label.config(text="Status: Background Mode")
        else:
            self.root.deiconify()  # Show window
            self.status_label.config(text="Status: Active")
    
    def start_calibration(self):
        """Start Calibration process"""
        self.status_label.config(text="Status :Calibrating")
        #Calibration logic go here
        #but for now i just simulate calibration
        self.root.after(3000,lambda:self.status_label.config(text="Status:Calibrated"))
    
    def detect_advanced_gesture(self,landmarks):
        """Advanced gesture detection with stability checking"""
        if not landmarks:
            return "none"
        
        #get landmark positions
        thumb_tip=landmarks[4]
        thumb_pip=landmarks[3]
        index_tip=landmarks[8]
        index_pip=landmarks[6]
        middle_tip=landmarks[12]
        middle_pip=landmarks[10]
        ring_tip=landmarks[16]
        ring_pip=landmarks[14]
        pinky_tip=landmarks[20]
        pinky_pip=landmarks[18]

        #Calcuate finger states
        fingers = []

        #Thumb(Different logic for left & right hand)
        if thumb_tip.x>landmarks[3].x:
            fingers.append(thumb_tip.x>thumb_pip.x)
        else:
            fingers.append(thumb_tip.x<thumb_pip.x)

        #Other fingers
        fingers.append(index_tip.y<index_pip.y)
        fingers.append(middle_tip.y<middle_pip.y)
        fingers.append(ring_tip.y<ring_pip.y)
        fingers.append(pinky_tip.ypinkyx_pip.y)

        #Calculate distances for pinch detection
        thumb_index_dist = self.calculate_distance(thumb_tip, index_tip)
        thumb_middle_dist = self.calculate_distance(thumb_tip, middle_tip)
        
        # GEsture Classification
        total_fingers=sum(fingers)

        if thumb_index_dist<0.04: #Tight pinch
            gesture="select"
        elif thumb_middle_dist<0.04: #Middle finger pinch
            gesture="right_click"
        elif total_fingers==1 and fingers[1]: #index finger only
            gesture="point"
        elif total_fingers==2 and fingers[1] and fingers[2]: #Peace sing
            gesture="scroll"
        elif total_fingers==3 and fingers[1] and fingers[2] and fingers[3]:
            gesture="drag"
        elif total_fingers==5: #Open hand
            gesture="open_hand"
        elif total_fingers==0: # fist
            gesture="fist"
        else:
            gesture="none"

        #Add to history for stability
        self.gesture_history.append(gesture)
        if len(self.gesture_history)>self.gesture_stability_threshold:
            self.gesture_history.pop(0)

        #Check for stable gesture
        if len (self.gesture_history)>=self.gesture_stability_threshold:
            if all(g== gesture for g in self.gesture_history[-3:]):
                self.last_stable_gesture=gesture
                return gesture
            
        return self.last_stable_gesture
    
    def calculate_distance(self,point1,point2):
        """Calculate Euclidean distance between two points"""
        return math.sqrt((point1.x-point2.x)**2+(point1.y-point2.y)**2)
    
    def get_precise_pointing_position(self,landmarks,frame_shape):
        """Get precise pointing position with calibration"""
        if not landmarks:
            return None
        
        index_tip=landmarks[8]
        h,w=frame_shape[:2]

        #Apply calibration if available
        x=index_tip.x
        y=index_tip.y

        if self.is_calibrated and 'offset_x' in self.calibration_data:
            x+=self.calibration_data['offset_x']
            y+=self.calibration_data['offset_y']

        #convert to pixel xoordinates
        pixel_x=int(x*w)
        pixel_y=int(y*h)

        return(pixel_x,pixel_y)
    
    def map_to_keyboard_advanced(self, point, frame_shape):
        """Advanced mapping with better accuracy"""
        if not point:
            return None
        
        x,y=point
        h,w,=frame_shape[:2]

        #get current layout
        layout=self.keyboard_layouts[self.current_layout]

        #Calculate grid dimensions
        total_rows=len(layout)
        row_height=h/(total_rows+1) #+1 to add padding

        #Determine row
        row_idx=int((y-row_height/2)/row_height)
        row_idx=max(0,min(row_idx,total_rows-1))

        if row_idx>=len(layout):
            return None
        
        #Determine Column within row
        row =layout[row_idx]
        col_width=w/len(row)
        col_idx=int(x/col_width)
        col_idx=max(0,min(col_idx,len(row)-1))

        return row[col_idx]
    
    def camera_loop(self):
        """Enhanced Camera processing loop"""
        while self.running:
            ret,frame=self.cap.read()
            if not ret:
                continue

            #Flip and process frame
            frame=cv2.flip(frame,1)
            rgb_frame=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)

            #Hand Detection
            results=self.hands.process(rgb_frame)

            gesture="none"
            pointing_pos=None

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    #Draw landmarks
                    self.mp_draw.draw_landmarks(
                        frame,hand_landmarks,self.mp_hands.HAND_CONNECTIONS
                    )

                    #Detect Gesture
                    gesture=self.detect_advanced_gesture(hand_landmarks.landmark)
                    pointing_pos=self.get_precise_pointing_position(hand_landmarks.landmark,frame.shape)
            
            #Add visual feedback
            self.add_visual_feedback(frame,gesture,pointing_pos)

            #Show frame (Only if not in background mode)
            if not self.background_mode:
                cv2.imshow('Advanced Gesture Keyboard',frame)

            #Process gesture
            if gesture!="none":
                self.gesture_queue.put((gesture,pointing_pos,frame.shape))

            #Handle window events
            if cv2.waitKey(1)&0xFF==('q'):
                break
        self.cleanup_camera()
    def add_visual_feedback(self,frame,gesture,pointing_pos):
        """Add visual feedback to camera frame"""
        h,w=frame.shape[:2]

        #Add gesture info
        cv2.putText(frame,f"Gesture:{gesture}",(10,30),
                    cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,255,0),2)
        
        #Add pointing Indicator
        if pointing_pos:
            cv2.circle(frame,pointing_pos,8,(255,0,0),-1)
            cv2.circle(frame,pointing_pos,15,(255,0,0),2)

            #Map to keyboard and show
            key=self.map_to_keyboard_advanced(pointing_pos,frame.shape)
            if key:
                cv2.putText(frame,f"Key:{key}",(10,70),
                            cv2.FONT_HERSHEY_SIMPLEX,0.8,(255,255,0),2)
            
        #Add keyboard grid overlay
        self.draw_keyboard_overlay(frame)

        #Add Status info
        cv2.putText(frame,f"Layout:{self.current_layout}",(10,h-60),
                    cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),1)
        cv2.putText(frame,f"Keys typed:{self.typing_stats['keys_typed']}",(10,h-40),
                    cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),1)
        cv2.putText(frame,f"Press 'q' to Quit",(10,h-20),
                    cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),1)
        
    def draw_keyboard_overlay(self,frame):
        """Draw keyboard grid overlay on camera frame"""
        h,w=frame.shape[:2]
        layout=self.keyboard_layouts[self.current_layout]

        #draw grid lines
        total_rows=len(layout)
        row_height=h//(total_rows+1)

        for i in range(1,total_rows+1):
            y=i*row_height
            cv2.line(frame,(0,y),(w,y),(100,100,100),1)
        
        #Draw column lines for each row
        for row_idx,row in enumerate(layout):
            y=(row_idx+1)*row_height
            col_width=w//len(row)
            for i in range(1,len(row)):
                x=i*col_width
                cv2.line(frame,(x,y-row_height//2),(x,y+row_height//2),(100,100,100),1)
    
    def gesture_processing(self):
        """Enhanced gesture processing"""
        while self.running:
            try:
                gesture,pointing_pos,frame_shape=self.gesture_queue.get(timeout=0.1)
                current_time=time.time()

                #GUI
                self.root.after(0,lambda g=gesture:self.gesture_label.config(text=f"Gesture: {g}"))

                #process different gestures
                if gesture == "point" and pointing_pos:
                    self.handle_pointing(pointing_pos,frame_shape,current_time)
                elif gesture=="select":
                    self.handle_selection(pointing_pos,frame_shape,current_time)
                elif gesture=="fist":
                    self.handle_fist()
                elif gesture=="open":
                    self.handle_open_hand()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Gesture processing error: {e}")

    def handle_pointing(self,pointing_pos,frame_shape,current_time):
        """Handle pointing gesture"""
        key=self.map_to_keyboard_advanced(pointing_pos,frame_shape)
        if key:
            if key !=self.selection_state['key']:
                #new key selected
                self.selection_state={
                    'key':key,
                    'start_time':current_time,
                    'duration':self.sensitivity_var.get(),
                    'confirmed':False
                }
                self.highlight_key(key)
                self.root.after(0,lambda:self.selection_label.config(text=f"Selection: {key}"))
            else:
                #continue selection
                elapsed=current_time-self.selection_state['start_time']
                progress=min(elapsed/self.selection_state['duration'],1.0)

                if progress>-1.0 and not self.selection_state['confirmed']:
                    self.type_key(key)
                    self.selection_state['confirmed']=True
                    self.root.after(0,lambda:self.selection_label.config(text=f"Typed: {key}"))
                else:
                    #show progress
                    self.root.after(0,lambda p=progress:self.selection_label.config(text=f"selection: {key} ({int(p*100)}%)"))
                
    def handle_selection(self,pointing_pos,frame_shape,current_time):
        """Handle pinch selection gesture"""
        if pointing_pos:
            key=self.map_to_keyboard_advanced(pointing_pos,frame_shape)
            if key:
                self.type_key(key)
                self.root.after(0,lambda:self.selection_label.config(text=f"Quick select: {key}"))

    def handle_fist(self):
        """Handle fist gesture (Clear selection)"""
        self.selection_state={'key':None,'start_time':0,'duration':0,'confirmed':False}
        self.clear_highlights()
        self.root.after(0,lambda:self.selection_label.config(text="Selection Cleared"))

    def handle_open_hand(self):
        """Handle open hand gesture (Spectial actions)"""
        #Could be used for special functions like switching layouts pass
    
    def highlight_key(self,key):
        """Highlight selected key"""
        self.clear_highlights()
        if key in self.key_buttons:
            self.key_buttons[key].config(bg='#ff4444',relief=tk.SUNKEN)
    
    def clear_highlights(self):
        """Clear all key highlights"""
        for key,btn in self.key_buttons.items():
            if key in['SPACE']:
                btn.config(bg='#333333',relief=tk.RAISED)
            elif key in ['BACKSPACE','ENTER','SHIFT','CTRL']:
                btn.config(bg='#0066cc',relief=tk.RAISED)
            elif key in ['QWERTY']:
                btn.config(bg='#cc6600',relief=tk.RAISED)
            else:
                btn.config(bg='#4a4a4a',relief=tk.RAISED)
            
    def type_key(self,key):
        """"Type a key with enhanced functionality"""
        try:
            if key =='SPACE':
                self.keyboard.press(Key.space)
                self.keyboard.release(Key.space)
            elif key == 'BACKSPACE':
                self.keyboard.press(Key.backspace)
                self.keyboard.release(Key.backspace)
            elif key=='ENTER':
                self.keyboard.press(Key.enter)
                self.keyboard.release(Key.enter)
            elif key=='SHIFT':
                self.keyboard.press(Key.shift)
                self.keyboard.release(Key.shift)
            elif key =='CTRL':
                self.keyboard.press(Key.ctrl)
                self.keyboard.release(Key.ctrl)
            elif key =='QWERTY':
                self.layout_var.set('qwerty')
                self.change_layout()
                return
            else:
                self.keyboard.type(key.lower())
            
            #Update stats
            self.typing_stats['keys_typed']+=1
            self.root.after(0,lambda:self.stats_label.config(text=f"keys:{self.typing_stats['keys_typed']}"))

            print(f"Typed:{key}")
        except Exception as e:
            print(f"Error typing key {key}: {e}")
