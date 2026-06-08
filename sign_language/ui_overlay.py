"""
ui_overlay.py
─────────────
All OpenCV drawing helpers. No business logic here.
"""

import cv2
import config

_F  = cv2.FONT_HERSHEY_SIMPLEX
_FB = cv2.FONT_HERSHEY_DUPLEX


# ─── Primitives ───────────────────────────────────────────────────────────────

def _blend_rect(frame, x: int, y: int, w: int, h: int, color: tuple, alpha: float):
    """Draw a semi-transparent filled rectangle."""
    y2, x2 = min(frame.shape[0], y + h), min(frame.shape[1], x + w)
    if y2 <= y or x2 <= x:
        return
    roi     = frame[y:y2, x:x2]
    overlay = roi.copy()
    cv2.rectangle(overlay, (0, 0), (x2 - x, y2 - y), color, -1)
    cv2.addWeighted(overlay, alpha, roi, 1.0 - alpha, 0, roi)


def _text(frame, txt, x, y, scale, color, thickness=1, font=_F):
    cv2.putText(frame, txt, (x, y), font, scale, color, thickness, cv2.LINE_AA)


def _confidence_bar(frame, x: int, y: int, w: int, h: int, ratio: float):
    cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 50), -1)
    fill   = max(0, int(w * ratio))
    color  = config.ACCENT_COLOR if ratio > 0.70 else config.WARN_COLOR
    if fill:
        cv2.rectangle(frame, (x, y), (x + fill, y + h), color, -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), (80, 80, 80), 1)
    _text(frame, f"{ratio * 100:.0f}%", x + w + 6, y + h - 1, 0.40, config.TEXT_COLOR)


# ─── Public drawing functions ─────────────────────────────────────────────────

def draw_landmarks(frame, hand_lms, mp_hands, mp_draw):
    if not config.SHOW_LANDMARKS:
        return
    mp_draw.draw_landmarks(
        frame, hand_lms, mp_hands.HAND_CONNECTIONS,
        mp_draw.DrawingSpec(color=(80, 255, 130), thickness=2, circle_radius=3),
        mp_draw.DrawingSpec(color=(200, 200, 200), thickness=1),
    )


def draw_bounding_box(frame, bbox, label: str, confidence: float):
    x1, y1, x2, y2 = bbox
    color = config.ACCENT_COLOR if label not in ("UNKNOWN", "No Hand", "") else (80, 80, 80)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    tag  = f"{label}  {confidence * 100:.0f}%"
    (tw, th), _ = cv2.getTextSize(tag, _F, 0.62, 2)
    lx = max(0, x1)
    ly = max(th + 8, y1 - 6)
    cv2.rectangle(frame, (lx, ly - th - 4), (lx + tw + 8, ly + 2), color, -1)
    _text(frame, tag, lx + 4, ly - 2, 0.62, (0, 0, 0), 2)


def draw_side_panel(
    frame,
    gesture:      str | None,
    confidence:   float,
    finger_states: list[bool],
    sentence_str: str,
    fps:          float,
    arduino_ok:   bool,
    tts_on:       bool,
):
    fh, fw = frame.shape[:2]
    pw = config.PANEL_WIDTH
    _blend_rect(frame, fw - pw, 0, pw, fh, config.BG_COLOR, config.PANEL_ALPHA)
    cv2.line(frame, (fw - pw, 0), (fw - pw, fh), config.ACCENT_COLOR, 1)

    ox = fw - pw + 8   # left edge of text inside panel
    y  = 28

    # ── Header ────────────────────────────────────────────────────────────────
    _text(frame, "SIGN LANGUAGE", ox, y,      0.48, config.ACCENT_COLOR, 1)
    _text(frame, "TRANSLATOR",    ox, y + 18, 0.48, config.ACCENT_COLOR, 1)
    y += 34
    cv2.line(frame, (ox, y), (fw - 8, y), config.ACCENT_COLOR, 1)

    # ── Gesture name ──────────────────────────────────────────────────────────
    y += 24
    _text(frame, "GESTURE:", ox, y, 0.42, config.DIM_COLOR)
    y += 26
    name = gesture or "---"
    scale = 0.90 if len(name) <= 8 else (0.72 if len(name) <= 12 else 0.58)
    _text(frame, name, ox, y, scale, config.TEXT_COLOR, 2, _FB)

    # ── Confidence bar ────────────────────────────────────────────────────────
    y += 18
    _confidence_bar(frame, ox, y, pw - 50, 14, confidence)

    # ── Finger state icons ────────────────────────────────────────────────────
    if config.SHOW_FINGER_ICONS and finger_states:
        y += 30
        labels   = ["T", "I", "M", "R", "P"]
        spacing  = (pw - 22) // 5
        for i, (ext, lbl) in enumerate(zip(finger_states, labels)):
            cx    = ox + spacing * i + spacing // 2
            color = config.ACCENT_COLOR if ext else (70, 70, 70)
            cv2.circle(frame, (cx, y), 11, color, -1)
            _text(frame, lbl, cx - 5, y + 4, 0.35, (0, 0, 0), 1)

    # ── Divider ───────────────────────────────────────────────────────────────
    y += 28
    cv2.line(frame, (ox, y), (fw - 8, y), (55, 55, 55), 1)

    # ── Status row ───────────────────────────────────────────────────────────
    y += 18
    fps_col = config.ACCENT_COLOR if fps >= 20 else config.WARN_COLOR
    _text(frame, f"FPS  {fps:.1f}", ox, y, 0.46, fps_col)

    y += 20
    ard_col  = config.ACCENT_COLOR if arduino_ok else (80, 80, 190)
    ard_text = "Arduino  OK" if arduino_ok else "Arduino  --"
    _text(frame, ard_text, ox, y, 0.43, ard_col)

    y += 20
    tts_col  = config.ACCENT_COLOR if tts_on else config.DIM_COLOR
    tts_text = "Speech   ON" if tts_on else "Speech   OFF"
    _text(frame, tts_text, ox, y, 0.43, tts_col)

    # ── Key hints ─────────────────────────────────────────────────────────────
    y = fh - 78
    cv2.line(frame, (ox, y), (fw - 8, y), (55, 55, 55), 1)
    hints = ["[c] clear", "[s] speech", "[l] landmarks", "[q] quit"]
    for hint in hints:
        y += 16
        _text(frame, hint, ox, y, 0.37, config.DIM_COLOR)


def draw_sentence_bar(frame, sentence_str: str):
    fh, fw = frame.shape[:2]
    bar_h = 46
    _blend_rect(frame, 0, fh - bar_h, fw - config.PANEL_WIDTH, bar_h,
                config.BG_COLOR, config.PANEL_ALPHA)
    cv2.line(frame, (0, fh - bar_h), (fw - config.PANEL_WIDTH, fh - bar_h),
             config.ACCENT_COLOR, 1)
    label = "Sentence:  " + (sentence_str if sentence_str else "(empty — show a gesture)")
    _text(frame, label, 10, fh - 14, 0.58, config.TEXT_COLOR, 1)


def draw_no_hand_notice(frame):
    fh, fw = frame.shape[:2]
    msg = "No hand detected"
    (tw, _), _ = cv2.getTextSize(msg, _FB, 0.9, 2)
    _text(frame, msg, (fw - config.PANEL_WIDTH - tw) // 2, 45, 0.9,
          (70, 70, 70), 2, _FB)
