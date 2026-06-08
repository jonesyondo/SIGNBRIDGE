import cv2
import mediapipe as mp
import serial
import time

# --- CONFIGURATION ---
SERIAL_PORT = 'COM3'        # Change to your actual port (e.g., /dev/ttyACM0 on Linux)
SERIAL_BAUD = 9600
SEND_INTERVAL = 0.05        # seconds between serial sends (20 Hz) — avoids flooding Arduino
SHOW_MESH = True            # draw 468-point face mesh on top of detection box

# --- SERIAL SETUP (optional) ---
try:
    arduino = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
    time.sleep(2)  # let Arduino reset
    print(f"Connected to Arduino on {SERIAL_PORT}")
except Exception as e:
    print(f"Serial Error: {e}. Running without Arduino.")
    arduino = None

# --- MEDIAPIPE SETUP ---
mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh
mp_draw = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles

face_detector = mp_face_detection.FaceDetection(
    model_selection=0,            # 0 = short-range (<2m), 1 = full-range
    min_detection_confidence=0.6,
)
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6,
)

# --- CAMERA ---
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("Could not open webcam.")

last_send = 0.0
prev_t = time.time()
print("System Ready. Press 'q' to quit, 'm' to toggle mesh.")

while True:
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 1. DETECT
    det_results = face_detector.process(rgb)

    # 2. MESH (mapping)
    mesh_results = face_mesh.process(rgb) if SHOW_MESH else None

    face_center = None
    if det_results.detections:
        # Pick the largest detection (closest face)
        best = max(
            det_results.detections,
            key=lambda d: d.location_data.relative_bounding_box.width
            * d.location_data.relative_bounding_box.height,
        )
        bbox = best.location_data.relative_bounding_box
        x = max(0, int(bbox.xmin * w))
        y = max(0, int(bbox.ymin * h))
        bw = int(bbox.width * w)
        bh = int(bbox.height * h)
        cx = x + bw // 2
        cy = y + bh // 2
        face_center = (cx, cy)

        # Draw bounding box + center crosshair
        cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
        cv2.line(frame, (cx - 15, cy), (cx + 15, cy), (0, 0, 255), 1)
        cv2.line(frame, (cx, cy - 15), (cx, cy + 15), (0, 0, 255), 1)

        score = best.score[0] if best.score else 0.0
        cv2.putText(
            frame, f"Face {score*100:.0f}%", (x, max(20, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
        )

    # Overlay face mesh
    if SHOW_MESH and mesh_results and mesh_results.multi_face_landmarks:
        for lms in mesh_results.multi_face_landmarks:
            mp_draw.draw_landmarks(
                image=frame,
                landmark_list=lms,
                connections=mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_styles.get_default_face_mesh_tesselation_style(),
            )
            mp_draw.draw_landmarks(
                image=frame,
                landmark_list=lms,
                connections=mp_face_mesh.FACEMESH_CONTOURS,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_styles.get_default_face_mesh_contours_style(),
            )

    # 3. SEND TO ARDUINO (rate-limited)
    now = time.time()
    if arduino and face_center and (now - last_send) >= SEND_INTERVAL:
        nx = face_center[0] / w   # 0.0 .. 1.0  (left -> right)
        ny = face_center[1] / h   # 0.0 .. 1.0  (top -> bottom)
        try:
            arduino.write(f"{nx:.3f},{ny:.3f}\n".encode())
            last_send = now
        except Exception as e:
            print(f"Serial write failed: {e}")
            arduino = None

    # FPS overlay
    fps = 1.0 / max(1e-6, now - prev_t)
    prev_t = now
    cv2.putText(
        frame, f"FPS: {fps:.1f}", (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2,
    )
    if face_center:
        cv2.putText(
            frame, f"Center: ({face_center[0]}, {face_center[1]})",
            (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2,
        )

    cv2.imshow("Face Detection & Tracking", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    if key == ord('m'):
        SHOW_MESH = not SHOW_MESH

cap.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()
