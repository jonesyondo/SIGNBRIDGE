# Sign Language Translator — Setup Guide

## 1. Install Python dependencies

```
cd sign_language
pip install -r requirements.txt
```

If you want text-to-speech on Windows, pyttsx3 uses the built-in SAPI5 engine — no extra install needed.

---

## 2. Install the Arduino library

1. Open Arduino IDE
2. **Sketch → Include Library → Manage Libraries**
3. Search: `LiquidCrystal I2C`
4. Install the one by **Frank de Brabander**

---

## 3. Wiring — I2C LCD to Arduino UNO

```
I2C LCD module       Arduino UNO
─────────────       ──────────────
  GND          →    GND
  VCC          →    5V
  SDA          →    A4
  SCL          →    A5
```

For **Arduino Mega**: SDA = pin 20, SCL = pin 21

The I2C module (PCF8574 backpack) is the small board soldered to the back of the LCD.
Most ship with address **0x27**. If your display stays blank after upload, change
`LCD_ADDR` in the `.ino` file from `0x27` to `0x3F`.

**Finding your LCD address** — upload and run this I2C scanner sketch:
https://playground.arduino.cc/Main/I2cScanner/

---

## 4. Upload the Arduino sketch

1. Open `SignLanguageLCD/SignLanguageLCD.ino` in Arduino IDE
2. Select your board: **Tools → Board → Arduino UNO**
3. Select your port: **Tools → Port → COM3** (or whatever your port is)
4. Click **Upload**
5. The LCD should show "Sign Language / Translator v1" for 2 seconds, then "Waiting..."

---

## 5. Configure the Python side

Open `sign_language/config.py` and set:

```python
SERIAL_PORT = 'COM3'    # match the port from Arduino IDE
```

Linux/Mac examples: `/dev/ttyACM0`, `/dev/cu.usbmodem14101`

---

## 6. Run the system

```
cd sign_language
python main.py
```

Close the Arduino IDE Serial Monitor first — two programs can't share the same port.

---

## 7. Keyboard controls

| Key | Action |
|-----|--------|
| `q` | Quit   |
| `c` | Clear sentence buffer |
| `s` | Toggle text-to-speech on/off |
| `l` | Toggle landmark overlay |

---

## 8. Recognized gestures

| Gesture | Hand shape |
|---------|-----------|
| HELLO | 4 fingers up (index–pinky), thumb down |
| STOP | All 5 fingers up |
| YES | Thumbs up only |
| NO | Index finger only |
| HELP | Closed fist |
| PEACE | Index + middle (V sign) |
| I LOVE YOU | Thumb + index + pinky |
| CALL ME | Thumb + pinky (shaka) |
| OK | Middle + ring + pinky up, thumb-index pinch |
| GOOD | Thumb + index + middle + ring (pinky down) |

---

## 9. Tuning tips

- **Jitter / false triggers**: raise `CONFIRMATION_THRESHOLD` (e.g. 0.70) or `GESTURE_BUFFER_SIZE` (e.g. 15)
- **Slow to respond**: lower `CONFIRMATION_THRESHOLD` (e.g. 0.55) or `GESTURE_BUFFER_SIZE` (e.g. 8)
- **Thumb detection wrong direction**: set `INVERT_THUMB = True` in config (add logic to gesture_engine)
- **Low FPS**: set `MODEL_COMPLEXITY = 0` and lower `FRAME_WIDTH`/`FRAME_HEIGHT`

---

## 10. Future improvements

### Gesture ML model
Replace the rule-based classifier with a small neural network (scikit-learn `MLPClassifier` or TensorFlow Lite) trained on recorded landmark sequences. Collect ~200 samples per gesture using a data-recording script, train offline, and swap in the `.predict()` call inside `GestureClassifier.classify()`.

### Dynamic gestures (motion)
Add an `MotionBuffer` that stores landmark sequences over ~0.5 seconds and feeds them to an LSTM or 1D-CNN to recognise gestures that require movement (e.g. THANK YOU, PLEASE, SORRY).

### Mobile app
Stream the `sentence` string via WebSocket (`websockets` library or Flask-SocketIO) to a React Native app that displays the text and can send spoken replies back to the Python side.

### Cloud logging
Send each confirmed gesture to a REST endpoint (FastAPI + SQLite) for session replay, analytics, and calibration data collection.

### Multi-user calibration
Record a short calibration sequence per user (hand size, camera distance) and normalise landmarks against that baseline before classification — improves accuracy across different hands.

### Raspberry Pi / ESP32-CAM deployment
The system runs on Raspberry Pi 4 at ~18 FPS with `MODEL_COMPLEXITY = 0`.
For ESP32-CAM, stream MJPEG to a Pi or laptop over Wi-Fi and process centrally.
