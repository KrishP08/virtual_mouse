import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import time

#Initialize MediaPipe Hand Solution
mp_hands =mp.solution.hands
hands=mo_hands.Hands(
    ststic_image_mode=False,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_drawing=mp.solutions.drawing_utils

#Get Screen dimensions
screen_width,screen_height=pyautogui.size()
