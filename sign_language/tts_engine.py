"""
tts_engine.py
─────────────
Offline text-to-speech via pyttsx3 running on a daemon thread
so it never blocks the camera loop.
"""

import queue
import threading
import config


class TTSEngine:
    def __init__(self):
        self._enabled = config.TTS_ENABLED
        self._queue   = queue.Queue(maxsize=3)
        self._running = False
        self._engine  = None
        self._thread  = None
        self._init()

    def _init(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate",   config.TTS_RATE)
            engine.setProperty("volume", config.TTS_VOLUME)
            self._engine  = engine
            self._running = True
            self._thread  = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()
            print("[TTS] pyttsx3 ready")
        except Exception as e:
            print(f"[TTS] Unavailable ({e}). Speech disabled.")
            self._enabled = False

    def _worker(self):
        while self._running:
            try:
                text = self._queue.get(timeout=0.5)
                if self._engine:
                    self._engine.say(text)
                    self._engine.runAndWait()
            except Exception:
                pass    # queue.Empty or engine hiccup

    def speak(self, text: str):
        if not self._enabled or not self._engine:
            return
        try:
            # put_nowait: if queue full, drop (non-blocking, never stalls the loop)
            self._queue.put_nowait(text)
        except queue.Full:
            pass

    def toggle(self) -> bool:
        self._enabled = not self._enabled
        return self._enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def shutdown(self):
        self._running = False
