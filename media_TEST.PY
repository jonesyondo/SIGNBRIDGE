import cv2
import mediapipe as mp


webcam = cv2.VideoCapture(0)

mp_face = mp.solutions.face_mesh

mp_drawing = mp.solutions.drawing_utils
with mp_face.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5 ) as face_mesh:
    while True:
        control,fram= webcam.read()
        if control==False:
            break
        rgb= cv2.cvtColor(fram, cv2.COLOR_BGR2RGB)
        result = face_mesh.process(rgb)
        if result.multi_face_landmarks:
            for face_landmarks in result.multi_face_landmarks:
                mp_drawing.draw_landmarks(fram, face_landmarks, mp_face.FACEMESH_TESSELATION)
        cv2.imshow("test", fram)
        if  cv2.waitKey(10) ==27:
         break

webcam.release()
cv2.destroyAllWindows()