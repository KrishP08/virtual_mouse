import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import time
import math

# Disable pyautogui failsafe for smoother operation
pyautogui.FAILSAFE = False

# Initialize MediaPipe Hand solution
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_drawing = mp.solutions.drawing_utils

# Get screen dimensions
screen_width, screen_height = pyautogui.size()
print(f"Screen resolution: {screen_width}x{screen_height}")

# Set up webcam
cap = cv2.VideoCapture(0)
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Camera resolution: {frame_width}x{frame_height}")

# Parameters
smoothening = 12  # Increased for smoother movement
prev_x, prev_y = 0, 0
curr_x, curr_y = 0, 0

# Additional smoothing parameters
velocity_smoothening = 8
dead_zone = 5  # Minimum movement threshold
movement_history = []
max_history = 5

# Gesture detection parameters
gesture_threshold = 25  # More restrictive threshold for actual pinching
click_delay = 0.3
scroll_sensitivity = 3

# State variables
is_left_clicking = False
is_right_clicking = False
is_double_clicking = False
is_dragging = False
drag_start_time = 0
last_scroll_time = 0
scroll_start_y = 0

# Timing variables
left_click_start_time = 0
right_click_start_time = 0
double_click_start_time = 0

def calculate_distance(p1, p2):
    """Calculate Euclidean distance between two points"""
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p2[1])**2)

def smooth_movement(new_x, new_y, prev_x, prev_y):
    """Apply advanced smoothing to cursor movement"""
    global movement_history
    
    # Calculate raw movement
    raw_dx = new_x - prev_x
    raw_dy = new_y - prev_y
    
    # Apply dead zone to prevent micro-movements
    if abs(raw_dx) < dead_zone and abs(raw_dy) < dead_zone:
        return prev_x, prev_y
    
    # Add to movement history for velocity smoothing
    movement_history.append((raw_dx, raw_dy))
    if len(movement_history) > max_history:
        movement_history.pop(0)
    
    # Calculate average velocity
    if len(movement_history) > 1:
        avg_dx = sum(dx for dx, dy in movement_history) / len(movement_history)
        avg_dy = sum(dy for dx, dy in movement_history) / len(movement_history)
        
        # Apply velocity-based smoothing
        smooth_dx = prev_x + (new_x - prev_x) / smoothening + avg_dx / velocity_smoothening
        smooth_dy = prev_y + (new_y - prev_y) / smoothening + avg_dy / velocity_smoothening
    else:
        smooth_dx = prev_x + (new_x - prev_x) / smoothening
        smooth_dy = prev_y + (new_y - prev_y) / smoothening
    
    return smooth_dx, smooth_dy

def get_finger_positions(landmarks):
    """Extract key finger positions from hand landmarks"""
    positions = {}
    
    # Finger tip landmarks
    positions['thumb_tip'] = [
        int(landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].x * frame_width),
        int(landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].y * frame_height)
    ]
    positions['index_tip'] = [
        int(landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].x * frame_width),
        int(landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y * frame_height)
    ]
    positions['middle_tip'] = [
        int(landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].x * frame_width),
        int(landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y * frame_height)
    ]
    positions['ring_tip'] = [
        int(landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].x * frame_width),
        int(landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].y * frame_height)
    ]
    positions['pinky_tip'] = [
        int(landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP].x * frame_width),
        int(landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP].y * frame_height)
    ]
    
    # Finger MCP (base) landmarks for finger state detection
    positions['index_mcp'] = [
        int(landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].x * frame_width),
        int(landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP].y * frame_height)
    ]
    positions['middle_mcp'] = [
        int(landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].x * frame_width),
        int(landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y * frame_height)
    ]
    positions['ring_mcp'] = [
        int(landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP].x * frame_width),
        int(landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP].y * frame_height)
    ]
    positions['pinky_mcp'] = [
        int(landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP].x * frame_width),
        int(landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP].y * frame_height)
    ]
    
    return positions

def is_finger_up(tip_pos, mcp_pos):
    """Check if a finger is extended (up)"""
    return tip_pos[1] < mcp_pos[1]

def detect_gesture(positions):
    """Detect various hand gestures with precise pinch detection"""
    # Calculate distances
    thumb_index_dist = calculate_distance(positions['thumb_tip'], positions['index_tip'])
    thumb_middle_dist = calculate_distance(positions['thumb_tip'], positions['middle_tip'])
    thumb_pinky_dist = calculate_distance(positions['thumb_tip'], positions['pinky_tip'])
    index_middle_dist = calculate_distance(positions['index_tip'], positions['middle_tip'])
    
    # Check which fingers are up
    fingers_up = []
    fingers_up.append(is_finger_up(positions['index_tip'], positions['index_mcp']))  # Index
    fingers_up.append(is_finger_up(positions['middle_tip'], positions['middle_mcp']))  # Middle
    fingers_up.append(is_finger_up(positions['ring_tip'], positions['ring_mcp']))  # Ring
    fingers_up.append(is_finger_up(positions['pinky_tip'], positions['pinky_mcp']))  # Pinky
    
    gesture = "none"
    
    # More restrictive gesture detection - only trigger on actual pinches
    if thumb_pinky_dist < gesture_threshold and thumb_pinky_dist > 10:  # Avoid false positives
        gesture = "double_click"
    elif thumb_index_dist < gesture_threshold and thumb_index_dist > 10:
        gesture = "left_click"
    elif thumb_middle_dist < gesture_threshold and thumb_middle_dist > 10:
        gesture = "right_click"
    elif fingers_up == [True, True, False, False] and index_middle_dist < 50:
        gesture = "scroll"
    elif fingers_up == [True, False, False, False]:
        gesture = "cursor"
    elif sum(fingers_up) == 0:
        gesture = "fist"
    
    return gesture, thumb_index_dist, thumb_middle_dist, thumb_pinky_dist

def draw_hand_indicator(image, hand_detected):
    """Draw hand detection status indicator"""
    indicator_color = (0, 255, 0) if hand_detected else (0, 0, 255)
    indicator_text = "HAND DETECTED" if hand_detected else "NO HAND DETECTED"
    
    # Draw indicator circle
    cv2.circle(image, (frame_width - 50, 50), 20, indicator_color, -1)
    
    # Draw indicator text
    cv2.putText(image, indicator_text, (frame_width - 200, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, indicator_color, 2)

def draw_gesture_info(image, gesture, positions, thumb_index_dist, thumb_middle_dist, thumb_pinky_dist):
    """Draw gesture information and visual feedback with distance indicators"""
    # Draw finger tip circles
    colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
    finger_names = ['thumb_tip', 'index_tip', 'middle_tip', 'ring_tip', 'pinky_tip']
    
    for i, finger in enumerate(finger_names):
        cv2.circle(image, tuple(positions[finger]), 8, colors[i], cv2.FILLED)
    
    # Draw gesture status with color coding
    gesture_color = (0, 255, 0)  # Default green
    if gesture == "left_click":
        gesture_color = (0, 0, 255)  # Red
    elif gesture == "right_click":
        gesture_color = (255, 0, 0)  # Blue
    elif gesture == "scroll":
        gesture_color = (0, 255, 255)  # Cyan
    elif gesture == "double_click":
        gesture_color = (255, 0, 255)  # Magenta
    
    cv2.putText(image, f"Gesture: {gesture}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, gesture_color, 2)
    
    # Show pinch status for each gesture
    pinch_status_y = 130
    if thumb_index_dist < 25:
        cv2.putText(image, "LEFT PINCH READY", (10, pinch_status_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    if thumb_middle_dist < 25:
        cv2.putText(image, "RIGHT PINCH READY", (10, pinch_status_y + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    if thumb_pinky_dist < 25:
        cv2.putText(image, "DOUBLE PINCH READY", (10, pinch_status_y + 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)

print("Advanced Virtual Mouse Control Started!")
print("Hand Gestures:")
print("- Index finger pointing: Move cursor")
print("- Thumb + Index pinch: Left click")
print("- Thumb + Index hold: Draw/Select mode")
print("- Thumb + Pinky pinch: Double click")
print("- Thumb + Middle pinch: Right click")
print("- Index + Middle up: Scroll mode")
print("- Fist: Stop all actions")
print("Press 'q' to quit.")

while cap.isOpened():
    success, image = cap.read()
    if not success:
        print("Failed to capture image from camera.")
        break
        
    # Flip the image horizontally for mirror view
    image = cv2.flip(image, 1)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Process the image and detect hands
    results = hands.process(image_rgb)
    
    if results.multi_hand_landmarks:
        # Add this right after processing hand landmarks:
        draw_hand_indicator(image, True)  # Hand detected
        for hand_landmarks in results.multi_hand_landmarks:
            # Draw hand landmarks
            mp_drawing.draw_landmarks(
                image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Get finger positions
            positions = get_finger_positions(hand_landmarks)
            
            # Detect gesture
            gesture, thumb_index_dist, thumb_middle_dist, thumb_pinky_dist = detect_gesture(positions)

            # Draw gesture information
            draw_gesture_info(image, gesture, positions, thumb_index_dist, thumb_middle_dist, thumb_pinky_dist)
            
            # Cursor movement (always active with index finger)
            index_x, index_y = positions['index_tip']
            screen_x = np.interp(index_x, (100, frame_width-100), (0, screen_width))
            screen_y = np.interp(index_y, (100, frame_height-100), (0, screen_height))

            # Apply advanced smoothing
            curr_x, curr_y = smooth_movement(screen_x, screen_y, prev_x, prev_y)

            # Move mouse cursor
            pyautogui.moveTo(curr_x, curr_y)
            prev_x, prev_y = curr_x, curr_y
            
            # Handle different gestures
            current_time = time.time()
            
            if gesture == "double_click":
                # Only proceed if it's a clear pinch gesture
                if thumb_pinky_dist < gesture_threshold and thumb_pinky_dist > 10:
                    cv2.line(image, tuple(positions['thumb_tip']), 
                            tuple(positions['pinky_tip']), (255, 0, 255), 3)
                    
                    if not is_double_clicking:
                        is_double_clicking = True
                        double_click_start_time = current_time
                    elif current_time - double_click_start_time > click_delay:
                        pyautogui.doubleClick()
                        cv2.putText(image, "DOUBLE CLICK!", (200, 50), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 3)
                        double_click_start_time = current_time

            elif gesture == "left_click":
                # Only proceed if it's a clear pinch gesture
                if thumb_index_dist < gesture_threshold and thumb_index_dist > 10:
                    cv2.line(image, tuple(positions['thumb_tip']), 
                            tuple(positions['index_tip']), (0, 0, 255), 3)
                    
                    if not is_left_clicking:
                        is_left_clicking = True
                        left_click_start_time = current_time
                    elif current_time - left_click_start_time > click_delay:
                        if not is_dragging:
                            # Single click for quick pinch
                            if current_time - left_click_start_time < 0.8:
                                pyautogui.click()
                                cv2.putText(image, "LEFT CLICK!", (200, 50), 
                                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                            # Enable drawing/selection mode for held pinch
                            else:
                                is_dragging = True
                                pyautogui.mouseDown()
                                cv2.putText(image, "DRAWING/SELECTING", (200, 100), 
                                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 3)
                        left_click_start_time = current_time

            elif gesture == "right_click":
                # Only proceed if it's a clear pinch gesture
                if thumb_middle_dist < gesture_threshold and thumb_middle_dist > 10:
                    cv2.line(image, tuple(positions['thumb_tip']), 
                            tuple(positions['middle_tip']), (255, 0, 0), 3)
                    
                    if not is_right_clicking:
                        is_right_clicking = True
                        right_click_start_time = current_time
                    elif current_time - right_click_start_time > click_delay:
                        pyautogui.rightClick()
                        cv2.putText(image, "RIGHT CLICK!", (200, 50), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
                        right_click_start_time = current_time
            
            elif gesture == "scroll":
                cv2.line(image, tuple(positions['index_tip']), 
                        tuple(positions['middle_tip']), (0, 255, 255), 3)
                
                if current_time - last_scroll_time > 0.1:  # Scroll throttling
                    if scroll_start_y == 0:
                        scroll_start_y = index_y
                    
                    scroll_diff = scroll_start_y - index_y
                    if abs(scroll_diff) > 20:
                        if scroll_diff > 0:
                            pyautogui.scroll(scroll_sensitivity)
                            cv2.putText(image, "SCROLL UP", (200, 50), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
                        else:
                            pyautogui.scroll(-scroll_sensitivity)
                            cv2.putText(image, "SCROLL DOWN", (200, 50), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
                        
                        scroll_start_y = index_y
                        last_scroll_time = current_time
            
            else:
                # Reset all states when no gesture is detected
                if is_left_clicking:
                    is_left_clicking = False
                if is_right_clicking:
                    is_right_clicking = False
                if is_double_clicking:
                    is_double_clicking = False
                if is_dragging:
                    is_dragging = False
                    pyautogui.mouseUp()
                scroll_start_y = 0
            
            # Display distances for debugging
            cv2.putText(image, f"T-I: {int(thumb_index_dist)}", (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(image, f"T-M: {int(thumb_middle_dist)}", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(image, f"T-P: {int(thumb_pinky_dist)}", (10, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    else:
        # Reset all states when no hand is detected
        draw_hand_indicator(image, False)  # No hand detected
        if is_dragging:
            is_dragging = False
            pyautogui.mouseUp()
        is_left_clicking = False
        is_right_clicking = False
        is_double_clicking = False
        scroll_start_y = 0
    
    # Display status
    status_text = "Virtual Mouse: Active"
    if is_dragging:
        status_text += " | DRAWING/SELECTING"
    
    cv2.putText(image, status_text, (10, frame_height - 20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    # Display the image
    cv2.imshow('Advanced Virtual Mouse Control', image)
    
    # Break the loop if 'q' is pressed
    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

# Cleanup
if is_dragging:
    pyautogui.mouseUp()

cap.release()
cv2.destroyAllWindows()
print("Advanced Virtual Mouse Control Ended")