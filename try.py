import mediapipe as mp
import cv2

mp_hands =mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands=mp_hands.hands()
print("mediapipe loaded succefully")