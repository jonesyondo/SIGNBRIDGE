#include <Servo.h>

// Pins — change to match your wiring
const uint8_t PAN_PIN  = 9;   // base servo (left/right)
const uint8_t TILT_PIN = 10;  // tilt servo (up/down)

// Match the Python side's mechanical limits
const int PAN_MIN  = 20,  PAN_MAX  = 160;
const int TILT_MIN = 40,  TILT_MAX = 140;

Servo panServo;
Servo tiltServo;

String buffer = "";

int clampi(int v, int lo, int hi) {
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

void setup() {
  Serial.begin(9600);
  panServo.attach(PAN_PIN);
  tiltServo.attach(TILT_PIN);

  // Center on boot
  panServo.write((PAN_MIN + PAN_MAX) / 2);
  tiltServo.write((TILT_MIN + TILT_MAX) / 2);
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      int comma = buffer.indexOf(',');
      if (comma > 0) {
        int pan  = buffer.substring(0, comma).toInt();
        int tilt = buffer.substring(comma + 1).toInt();
        pan  = clampi(pan,  PAN_MIN,  PAN_MAX);
        tilt = clampi(tilt, TILT_MIN, TILT_MAX);
        panServo.write(pan);
        tiltServo.write(tilt);
      }
      buffer = "";
    } else if (c != '\r') {
      buffer += c;
      if (buffer.length() > 16) buffer = "";  // overflow guard
    }
  }
}
