"""
gesture_engine.py
─────────────────
Classes
  FeatureExtractor  – raw landmarks → [thumb, index, middle, ring, pinky] booleans
  GestureClassifier – finger states → (gesture_name, message, confidence)
  GestureSmoothing  – temporal buffer, confirmation, debounce
  SentenceBuffer    – accumulates confirmed gestures into a short sentence
"""

import time
from collections import deque, Counter

import config

# ─── Gesture Definitions ─────────────────────────────────────────────────────
# fingers: [thumb, index, middle, ring, pinky]  (1=extended, 0=curled, None=ignore)
# All 10 patterns are mutually exclusive → no ambiguity
GESTURES = [
    {"name": "I LOVE YOU", "msg": "I love you",  "fingers": [1, 1, 0, 0, 1], "extra": None},
    {"name": "CALL ME",    "msg": "Call me",      "fingers": [1, 0, 0, 0, 1], "extra": None},
    {"name": "PEACE",      "msg": "Peace",        "fingers": [0, 1, 1, 0, 0], "extra": None},
    {"name": "GOOD",       "msg": "Good",         "fingers": [1, 1, 1, 1, 0], "extra": None},
    {"name": "STOP",       "msg": "Stop",         "fingers": [1, 1, 1, 1, 1], "extra": None},
    {"name": "HELLO",      "msg": "Hello",        "fingers": [0, 1, 1, 1, 1], "extra": None},
    {"name": "OK",         "msg": "OK",           "fingers": [0, 0, 1, 1, 1], "extra": "pinch"},
    {"name": "YES",        "msg": "Yes",          "fingers": [1, 0, 0, 0, 0], "extra": None},
    {"name": "NO",         "msg": "No",           "fingers": [0, 1, 0, 0, 0], "extra": None},
    {"name": "HELP",       "msg": "Help",         "fingers": [0, 0, 0, 0, 0], "extra": None},
]

GESTURE_MESSAGES = {g["name"]: g["msg"] for g in GESTURES}


class FeatureExtractor:
    """Converts MediaPipe hand landmarks into normalized feature vectors."""

    # Small deadzone prevents borderline positions from flickering
    _DEADZONE = 0.018

    @staticmethod
    def extract(landmarks, handedness: str = "Right") -> list[bool]:
        lm = landmarks.landmark
        dz = FeatureExtractor._DEADZONE

        # Thumb: compare tip (4) x vs IP (3) x along the thumb axis
        # For a mirrored ("Right") hand, extended thumb moves toward screen-left
        if handedness == "Right":
            thumb = lm[4].x < lm[3].x - dz
        else:
            thumb = lm[4].x > lm[3].x + dz

        # Fingers: tip.y < pip.y means finger is raised (y=0 is top of frame)
        index  = lm[8].y  < lm[6].y  - dz
        middle = lm[12].y < lm[10].y - dz
        ring   = lm[16].y < lm[14].y - dz
        pinky  = lm[20].y < lm[18].y - dz

        return [bool(thumb), bool(index), bool(middle), bool(ring), bool(pinky)]

    @staticmethod
    def thumb_index_distance(landmarks) -> float:
        """Thumb-tip to index-tip distance, normalised by hand size."""
        lm = landmarks.landmark
        dx = lm[4].x - lm[8].x
        dy = lm[4].y - lm[8].y
        raw = (dx * dx + dy * dy) ** 0.5
        # Normalise by wrist→middle-MCP span
        sx = lm[9].x - lm[0].x
        sy = lm[9].y - lm[0].y
        span = max(0.01, (sx * sx + sy * sy) ** 0.5)
        return raw / span

    @staticmethod
    def hand_bbox(landmarks, frame_w: int, frame_h: int, pad: int = 20):
        lm = landmarks.landmark
        xs = [int(p.x * frame_w) for p in lm]
        ys = [int(p.y * frame_h) for p in lm]
        return (
            max(0, min(xs) - pad),
            max(0, min(ys) - pad),
            min(frame_w, max(xs) + pad),
            min(frame_h, max(ys) + pad),
        )


class GestureClassifier:
    """Matches finger-state vectors against gesture definitions."""

    def classify(
        self, finger_states: list[bool], landmarks=None
    ) -> tuple[str, str, float]:
        """Returns (gesture_name, message, confidence 0..1)."""
        best_name = "UNKNOWN"
        best_msg  = ""
        best_conf = 0.0

        for g in GESTURES:
            defined = [(i, v) for i, v in enumerate(g["fingers"]) if v is not None]
            if not defined:
                continue

            matches = sum(1 for i, v in defined if bool(v) == finger_states[i])
            # Normalise over all 5 fingers so more-specific gestures score higher
            conf = matches / 5.0

            # Bonus for OK pinch (thumb-index close together)
            if g["extra"] == "pinch" and landmarks is not None:
                dist = FeatureExtractor.thumb_index_distance(landmarks)
                pinch = max(0.0, 1.0 - dist / 0.20)   # full bonus when dist < 0.20
                conf = conf * 0.7 + pinch * 0.3

            if conf > best_conf:
                best_conf = conf
                best_name = g["name"]
                best_msg  = g["msg"]

        return best_name, best_msg, round(best_conf, 3)


class GestureSmoothing:
    """
    Temporal buffer: a gesture is 'confirmed' when it occupies ≥ CONFIRMATION_THRESHOLD
    of the rolling window and confidence ≥ MIN_GESTURE_CONFIDENCE.

    Once confirmed, the same gesture won't fire again until the hand is removed
    and reappears (or a different gesture takes over).
    """

    def __init__(self):
        self._buf           = deque(maxlen=config.GESTURE_BUFFER_SIZE)
        self._no_hand_count = 0
        self._confirmed     = None

    def update(self, gesture_name: str | None, confidence: float) -> str | None:
        """Feed one frame. Returns the newly confirmed gesture name, or None."""
        if gesture_name is None:
            self._no_hand_count += 1
            if self._no_hand_count >= config.NO_HAND_RESET_FRAMES:
                self._buf.clear()
                self._confirmed = None
            return None

        self._no_hand_count = 0

        if confidence < config.MIN_GESTURE_CONFIDENCE:
            return None

        self._buf.append(gesture_name)

        if len(self._buf) < max(3, config.GESTURE_BUFFER_SIZE // 2):
            return None   # not enough data yet

        counter = Counter(self._buf)
        top_name, top_count = counter.most_common(1)[0]
        ratio = top_count / len(self._buf)

        if ratio >= config.CONFIRMATION_THRESHOLD and top_name != self._confirmed:
            self._confirmed = top_name
            return top_name   # ← newly stable gesture

        return None

    def current_best(self) -> tuple[str | None, float]:
        """Best candidate right now (for live UI display, not for triggering)."""
        if not self._buf:
            return None, 0.0
        counter = Counter(self._buf)
        top_name, top_count = counter.most_common(1)[0]
        return top_name, top_count / len(self._buf)

    def reset(self):
        self._buf.clear()
        self._confirmed = None
        self._no_hand_count = 0


class SentenceBuffer:
    """Accumulates up to MAX_SENTENCE_WORDS confirmed gestures."""

    def __init__(self):
        self._words: list[tuple[str, str]] = []   # [(name, message), ...]
        self._last_add  = 0.0
        self._last_name = None

    def add(self, name: str, message: str) -> bool:
        """Returns True if the word was actually added."""
        now = time.time()
        if name == self._last_name and now - self._last_add < config.SENTENCE_COOLDOWN:
            return False
        if len(self._words) >= config.MAX_SENTENCE_WORDS:
            self._words.pop(0)
        self._words.append((name, message))
        self._last_add  = now
        self._last_name = name
        return True

    def display(self) -> str:
        """Bracket-labelled string for the screen: [HELLO]  [YES]"""
        return "  ".join(f"[{n}]" for n, _ in self._words)

    def sentence(self) -> str:
        """Natural sentence for TTS / LCD: 'Hello Yes Peace'"""
        return " ".join(m for _, m in self._words)

    def clear(self):
        self._words.clear()
        self._last_name = None

    def auto_clear(self) -> bool:
        """Returns True if buffer was cleared due to inactivity."""
        if self._words and time.time() - self._last_add > config.SENTENCE_CLEAR_TIMEOUT:
            self.clear()
            return True
        return False

    @property
    def empty(self) -> bool:
        return len(self._words) == 0
