# ─── Camera ───────────────────────────────────────────────────────────────────
CAMERA_INDEX  = 0
FRAME_WIDTH   = 1280
FRAME_HEIGHT  = 720
TARGET_FPS    = 30
FLIP_FRAME    = True

# ─── Serial (Arduino) ─────────────────────────────────────────────────────────
SERIAL_PORT    = 'COM7'   # Linux: /dev/ttyACM0   Mac: /dev/cu.usbmodem...
SERIAL_BAUD    = 9600
SERIAL_TIMEOUT = 0.08     # seconds between serial writes (max ~12 Hz to LCD)

# ─── MediaPipe ────────────────────────────────────────────────────────────────
MAX_HANDS            = 1
DETECTION_CONFIDENCE = 0.70
TRACKING_CONFIDENCE  = 0.60
MODEL_COMPLEXITY     = 0    # 0 = fast (better for real-time), 1 = more accurate

# ─── Gesture Smoothing ────────────────────────────────────────────────────────
GESTURE_BUFFER_SIZE    = 12    # rolling window of frames considered
CONFIRMATION_THRESHOLD = 0.60  # fraction of buffer that must agree
MIN_GESTURE_CONFIDENCE = 0.70  # minimum per-frame score to count
NO_HAND_RESET_FRAMES   = 10    # consecutive "no hand" frames before state reset

# ─── Sentence Builder ─────────────────────────────────────────────────────────
MAX_SENTENCE_WORDS     = 6     # words kept in rolling sentence
SENTENCE_COOLDOWN      = 1.8   # seconds before same gesture adds again
SENTENCE_CLEAR_TIMEOUT = 12.0  # seconds idle before auto-clear

# ─── TTS ──────────────────────────────────────────────────────────────────────
TTS_ENABLED = True
TTS_RATE    = 150    # words per minute
TTS_VOLUME  = 1.0

# ─── UI ───────────────────────────────────────────────────────────────────────
PANEL_WIDTH       = 230
PANEL_ALPHA       = 0.78
SHOW_LANDMARKS    = True
SHOW_FINGER_ICONS = True
ACCENT_COLOR      = (0, 210, 120)    # BGR  teal-green
WARN_COLOR        = (30, 130, 255)   # BGR  orange
TEXT_COLOR        = (235, 235, 235)  # BGR  near-white
DIM_COLOR         = (110, 110, 110)  # BGR  grey
BG_COLOR          = (18, 18, 18)     # BGR  near-black
