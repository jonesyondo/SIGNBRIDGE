"""
main.py  –  Sign Language Recognition System
─────────────────────────────────────────────
Entry point. Orchestrates camera, MediaPipe, gesture engine, UI, serial, and TTS.

Run:
    python main.py

Keys while running:
    q  – quit
    c  – clear sentence buffer
    s  – toggle text-to-speech
    l  – toggle landmark overlay
"""

import sys
import time

import cv2
import mediapipe as mp

import config
from gesture_engine import (
    FeatureExtractor, GestureClassifier,
    GestureSmoothing, SentenceBuffer, GESTURE_MESSAGES,
)
from ui_overlay   import (
    draw_landmarks, draw_bounding_box,
    draw_side_panel, draw_sentence_bar, draw_no_hand_notice,
)
from serial_comm  import SerialComm
from tts_engine   import TTSEngine


def main():
    # ── Camera ───────────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        sys.exit("ERROR: Could not open webcam.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          config.TARGET_FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # keeps latency low

    # ── MediaPipe ─────────────────────────────────────────────────────────────
    mp_hands = mp.solutions.hands
    mp_draw  = mp.solutions.drawing_utils
    hands    = mp_hands.Hands(
        max_num_hands=config.MAX_HANDS,
        min_detection_confidence=config.DETECTION_CONFIDENCE,
        min_tracking_confidence=config.TRACKING_CONFIDENCE,
        model_complexity=config.MODEL_COMPLEXITY,
    )

    # ── Components ────────────────────────────────────────────────────────────
    extractor  = FeatureExtractor()
    classifier = GestureClassifier()
    smoother   = GestureSmoothing()
    sentence   = SentenceBuffer()
    serial     = SerialComm()
    tts        = TTSEngine()

    # ── State ─────────────────────────────────────────────────────────────────
    cur_gesture     : str | None = None
    cur_confidence  : float      = 0.0
    cur_fingers     : list[bool] = [False] * 5
    fps             : float      = 0.0
    prev_t          : float      = time.time()

    print("\n" + "=" * 50)
    print(" Sign Language Translator  |  Ready")
    print("=" * 50)
    print(" Gestures  : HELLO  STOP  YES  NO  HELP")
    print("             PEACE  I LOVE YOU  CALL ME  OK  GOOD")
    print(" Keys      : [q] quit  [c] clear  [s] speech  [l] landmarks")
    print("=" * 50 + "\n")

    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        if config.FLIP_FRAME:
            frame = cv2.flip(frame, 1)

        fh, fw = frame.shape[:2]
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        hand_detected = result.multi_hand_landmarks is not None

        if hand_detected:
            hand_lms = result.multi_hand_landmarks[0]

            handedness = "Right"
            if result.multi_handedness:
                handedness = result.multi_handedness[0].classification[0].label

            # Extract + classify
            cur_fingers              = extractor.extract(hand_lms, handedness)
            cur_gesture, _, cur_confidence = classifier.classify(cur_fingers, hand_lms)

            # Smooth and confirm
            confirmed = smoother.update(cur_gesture, cur_confidence)

            # Draw hand
            draw_landmarks(frame, hand_lms, mp_hands, mp_draw)
            bbox = extractor.hand_bbox(hand_lms, fw, fh)
            live_name, live_ratio = smoother.current_best()
            draw_bounding_box(frame, bbox, live_name or cur_gesture, cur_confidence)

            # Act on newly confirmed gesture
            if confirmed:
                msg   = GESTURE_MESSAGES.get(confirmed, confirmed)
                added = sentence.add(confirmed, msg)
                if added:
                    lcd_text = sentence.sentence()
                    serial.send(lcd_text)
                    tts.speak(msg)
                    print(f"  ✓  {confirmed:<14} → \"{lcd_text}\"")

        else:
            smoother.update(None, 0.0)
            cur_gesture    = None
            cur_confidence = 0.0
            draw_no_hand_notice(frame)

        # Auto-clear idle sentence
        if sentence.auto_clear():
            serial.send("", force=True)
            print("  (sentence cleared — idle timeout)")

        # ── FPS (exponential moving average) ─────────────────────────────────
        now    = time.time()
        fps    = 0.92 * fps + 0.08 * (1.0 / max(1e-6, now - prev_t))
        prev_t = now

        # ── Render UI ─────────────────────────────────────────────────────────
        display_name = cur_gesture if hand_detected else ("No Hand" if not hand_detected else cur_gesture)
        draw_side_panel(
            frame, display_name, cur_confidence, cur_fingers,
            sentence.display(), fps, serial.connected, tts.enabled,
        )
        draw_sentence_bar(frame, sentence.display())

        cv2.imshow("Sign Language Translator", frame)

        # ── Key handling ──────────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("c"):
            sentence.clear()
            smoother.reset()
            serial.send("CLEARED", force=True)
            print("  Sentence cleared.")
        elif key == ord("s"):
            on = tts.toggle()
            print(f"  Speech {'ON' if on else 'OFF'}")
        elif key == ord("l"):
            config.SHOW_LANDMARKS = not config.SHOW_LANDMARKS

    # ── Cleanup ───────────────────────────────────────────────────────────────
    cap.release()
    hands.close()
    cv2.destroyAllWindows()
    serial.close()
    tts.shutdown()
    print("\nSystem stopped.")


if __name__ == "__main__":
    main()
