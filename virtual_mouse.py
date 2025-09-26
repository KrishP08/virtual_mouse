import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import time

#Initialize MediaPipe Hand Solution
mp_hands =mp.solution.hands
hands=mp_hands.Hands(
    ststic_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_drawing=mp.solutions.drawing_utils

#Get Screen dimensions
screen_width,screen_height=pyautogui.size()
print(f"Screen Resolution:{screen_width}x{screen_height}")

#Initialize Webcam or Set up Webcam
cap=cv2.VideoCapture(0)
frame_width= int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Webcam Resolution:{frame_width}x{frame_height}")

#Parameters
smoothening=5
prev_x,prev_y=0,0
curr_x,curr_y=0,0

#For click gesture detection
pinch_start=0
is_pinching= False
click_delay=0.3 #seconds

def calculate_distance(p1,p2):
    """Caculate Euclidean distance between two points"""
    return np.sqrt((p2[0]-p1[0])**2+(p2[1]-p1[1])**2)

print("Virtual Mouse Control Started! Press 'Q' to Quit.")

while cap.isOpened():
    success,image=cap.read()
    if not success:
        print("Failed to capture Image From Camera.")
        break

    #Flip the Image Horizontally for a more intuitive mirror View
    image=cv2.flip(image,1)

    #Convert the image to RGB
    image_rgb=cv2.cvtColor(image,cv2.COLOR_BGR2RGB)

    #print the Image and Detect Hands
    results=hands.process(image_rgb)

    #Draw Hand Landmarks on the Image
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(
                image,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS
            )

            #Get Index Finger Tip Coordinates
            index_finger_tip=hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            index_x=int(index_finger_tip.x*frame_width)
            index_y=int(index_finger_tip.y*frame_height)

            #get Thumb Tip coordinates
            thumb_tip=hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            thumb_x=int(thumb_tip.x*frame_width)
            thumb_y=int(thumb_tip.y*frame_height)

            #Draw Circles at the Tips of index Finger and Thumb
            cv2.circle(image,(index_x,index_y),10,(0,255,0),cv2.FILLED)
            cv2.circle(image,(thumb_x,thumb_y),10,(0,255,0),cv2.FILLED)

            #Convert Coordinates To screen Position WIth Smoothening
            screen_x=np.interp(index_x,(100,frame_width-100),(0,screen_width))
            screen_y=np.interp(index_y,(100,frame_height-100),(0,screen_height))

            #smoothen values
            curr_x=prev_x+(screen_x-prev_x)/smoothening
            curr_y=prev_y+(screen_y-prev_y)/smoothening

            #Mouse Movement
            pyautogui.moveTo(curr_x,curr_y)
            prev_x,prev_y=curr_x,curr_y

            #Check for pinch Gesture (Thumb and index Finger close togetger)
            pinch_distance = calculate_distance((thumb_x,thumb_y),(index_x,index_y))

            #Draw Line Between index finger and thumb
            cv2.line(image,(thumb_x,thumb_y),(index_x,index_y),(0,255,0),2)

            #Display the Distance
            cv2.putText(image,f"Distance: {int(pinch_distance)}",(50,50),cv2.FONT_HERSHEY_SIMPLEX,1,(255,0,0),2)

            #Detect click gesture (pinch)
            if pinch_distance < 40:#threshold for pinch detection
                cv2.circle(image,(index_x,index_y),15,(0,0,255),cv2.FILLED)
                if not is_pinching:
                    is_pinching=True
                    pinch_start_time=time.time()
                elif time.time() - pinch_start_time>click_delay:
                    #Perform click after holding pinch for click_delay seconds
                    pyautogui.click()
                    cv2.putText(image,"Click!",(200,50),
                                cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),3)
                    pinch_start_time=time.time()#reset time
            else:
                is_pinching=False
        
        #Display Status
        cv2.putText(image,"Virtual Mouse: Active",(10,frame_height-20),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,0),2)

        #Display the image
        cv2.imshow('Virtual Mouse Control',image)

        #Break the Loop if 'Q' is Pressed
        if cv2.waitKey(5)&0xff==ord('q'):
            break
# Release Resources
cap.release()
cv2.destroyAllWindows()
print("Virtual Mouse Control Ended.")