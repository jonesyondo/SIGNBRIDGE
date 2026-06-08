/*
 * SignLanguageLCD.ino
 * ───────────────────
 * Receives gesture sentences from Python over Serial (9600 baud).
 * Displays them on a 16×2 I2C LCD without flickering.
 * Long line 2 text scrolls automatically.
 *
 * Required library: "LiquidCrystal I2C" by Frank de Brabander
 *   Install: Arduino IDE → Sketch → Include Library → Manage Libraries
 *   Search: LiquidCrystal I2C
 *
 * Wiring (I2C LCD module with PCF8574 backpack):
 *   LCD GND  → Arduino GND
 *   LCD VCC  → Arduino 5V
 *   LCD SDA  → Arduino A4   (Mega: pin 20)
 *   LCD SCL  → Arduino A5   (Mega: pin 21)
 *
 * If your LCD address is 0x3F instead of 0x27, change the line below.
 */

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ── Configuration ─────────────────────────────────────────────────────────────
#define LCD_ADDR   0x27    // try 0x3F if display stays blank
#define LCD_COLS   16
#define LCD_ROWS   2

const unsigned long SCROLL_MS    = 380;   // ms between scroll steps
const unsigned long IDLE_MS      = 12000; // ms before idle message appears
const unsigned long BLINK_MS     = 600;   // ms for "new gesture" blink
// ─────────────────────────────────────────────────────────────────────────────

LiquidCrystal_I2C lcd(LCD_ADDR, LCD_COLS, LCD_ROWS);

// Serial receive buffer
String  rxBuf       = "";
bool    newData     = false;

// LCD state (only write when content actually changes → no flicker)
char    line1Buf[LCD_COLS + 1] = {0};
char    line2Buf[LCD_COLS + 1] = {0};

// Scroll state
String  scrollSrc   = "";
int     scrollPos   = 0;
unsigned long lastScroll  = 0;

// Timing
unsigned long lastReceived = 0;
bool    idleShown   = false;

// Blink: briefly invert backlight on new gesture
bool    blinkPending = false;
unsigned long blinkStart = 0;


// ── Helpers ───────────────────────────────────────────────────────────────────

// Write a line only if its content changed (prevents flicker)
void setLine(int row, const char* text) {
  char* buf = (row == 0) ? line1Buf : line2Buf;
  // Build padded string
  char padded[LCD_COLS + 1];
  int len = strlen(text);
  for (int i = 0; i < LCD_COLS; i++) {
    padded[i] = (i < len) ? text[i] : ' ';
  }
  padded[LCD_COLS] = '\0';

  if (strcmp(padded, buf) != 0) {
    strncpy(buf, padded, LCD_COLS + 1);
    lcd.setCursor(0, row);
    lcd.print(padded);
  }
}

// Extract the last word from a space-separated string
String lastWord(const String& s) {
  int pos = s.lastIndexOf(' ');
  return (pos >= 0) ? s.substring(pos + 1) : s;
}

// Prefix a line with a label, truncate to LCD_COLS
String prefixed(const String& label, const String& value) {
  String result = label + value;
  if ((int)result.length() > LCD_COLS) result = result.substring(0, LCD_COLS);
  return result;
}


// ── Setup ─────────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(9600);

  lcd.init();
  lcd.backlight();
  lcd.clear();
  // Reset internal buffers so first real write always updates the display
  memset(line1Buf, 0xFF, sizeof(line1Buf));
  memset(line2Buf, 0xFF, sizeof(line2Buf));

  setLine(0, "Sign Language");
  setLine(1, "Translator v1");
  delay(2000);
  setLine(0, "Waiting...");
  setLine(1, "");
}


// ── Main loop ─────────────────────────────────────────────────────────────────

void loop() {
  // ── Read serial ─────────────────────────────────────────────────────────────
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      rxBuf.trim();
      newData = true;
      lastReceived = millis();
      idleShown = false;
    } else if (c != '\r') {
      if (rxBuf.length() < 100) rxBuf += c;   // overflow guard
    }
  }

  // ── Process new text ────────────────────────────────────────────────────────
  if (newData) {
    newData = false;
    String text = rxBuf;
    rxBuf = "";

    if (text.length() == 0 || text == "CLEARED") {
      setLine(0, "Ready...");
      setLine(1, "");
      scrollSrc = "";
      scrollPos = 0;
    } else {
      // Line 1: "Sign: <latest gesture>"  (last word of sentence)
      String latest = lastWord(text);
      latest.toUpperCase();
      String l1 = prefixed("Sign: ", latest);
      setLine(0, l1.c_str());

      // Line 2: full sentence — scrolls if longer than LCD_COLS
      scrollSrc = text;
      scrollPos = 0;
      lastScroll = millis();

      // Show initial window immediately
      String first = (scrollSrc.length() <= LCD_COLS)
                     ? scrollSrc
                     : scrollSrc.substring(0, LCD_COLS);
      setLine(1, first.c_str());

      // Brief blink to signal new gesture
      blinkPending = true;
      blinkStart   = millis();
      lcd.noBacklight();
    }
  }

  // ── Blink restore ───────────────────────────────────────────────────────────
  if (blinkPending && millis() - blinkStart > BLINK_MS) {
    lcd.backlight();
    blinkPending = false;
  }

  // ── Scroll line 2 ───────────────────────────────────────────────────────────
  if ((int)scrollSrc.length() > LCD_COLS && millis() - lastScroll >= SCROLL_MS) {
    lastScroll = millis();
    scrollPos++;
    int maxPos = (int)scrollSrc.length() - LCD_COLS;

    // Pause at the end before wrapping back
    if (scrollPos > maxPos + 4) scrollPos = 0;

    int from    = constrain(scrollPos, 0, maxPos);
    String view = scrollSrc.substring(from, from + LCD_COLS);
    setLine(1, view.c_str());
  }

  // ── Idle message ────────────────────────────────────────────────────────────
  if (!idleShown && lastReceived > 0 && millis() - lastReceived > IDLE_MS) {
    idleShown = true;
    scrollSrc = "";
    setLine(0, "Sign Language");
    setLine(1, "System Ready");
  }
}
