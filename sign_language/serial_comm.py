"""
serial_comm.py
──────────────
Non-blocking serial link to Arduino. Rate-limited to avoid flooding the LCD.
Automatically marks itself as disconnected on any write error.
"""

import time
import config


class SerialComm:
    def __init__(self):
        self._ser        = None
        self._last_text  = ""
        self._last_write = 0.0
        self._connect()

    def _connect(self):
        try:
            import serial
            self._ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=1)
            time.sleep(2)          # give Arduino time to reset
            print(f"[Serial] Connected on {config.SERIAL_PORT}")
        except Exception as e:
            print(f"[Serial] {e} — running without Arduino.")
            self._ser = None

    @property
    def connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def send(self, text: str, force: bool = False):
        """
        Transmit text to the Arduino.
        Skipped unless the text changed or force=True.
        Rate-limited to SERIAL_TIMEOUT seconds between writes.
        Text is truncated to 80 characters (well beyond any LCD's width).
        """
        if not self.connected:
            return
        now = time.time()
        if not force:
            if text == self._last_text:
                return
            if now - self._last_write < config.SERIAL_TIMEOUT:
                return
        try:
            payload = (text[:80] + "\n").encode("utf-8")
            self._ser.write(payload)
            self._last_text  = text
            self._last_write = now
        except Exception as e:
            print(f"[Serial] Write error: {e}")
            self._ser = None   # mark as disconnected

    def close(self):
        if self.connected:
            self._ser.close()
