/*
 * ═══════════════════════════════════════════════════════════════
 *  PotholeTrack — ESP32 Firmware
 *  Sensors: MPU6050 (vibration) + NEO-6M GPS + NTP (timestamp)
 *  Sends pothole events via HTTP POST to Django backend
 * ═══════════════════════════════════════════════════════════════
 *
 *  Required Libraries (install via Arduino IDE → Manage Libraries):
 *    - Adafruit MPU6050       (by Adafruit)
 *    - Adafruit Unified Sensor (by Adafruit)
 *    - TinyGPS++              (by Mikal Hart)
 *    - ArduinoJson            (by Benoit Blanchon)
 *    - NTPClient              (by Fabrice Weinberg)
 *
 *  Board: "ESP32 Dev Module" (install esp32 board package by Espressif)
 *
 *  Wiring:
 *    MPU6050  → SDA=GPIO21, SCL=GPIO22, VCC=3.3V, GND=GND
 *    NEO-6M   → TX→GPIO16 (ESP RX2), RX→GPIO17 (ESP TX2), VCC=3.3V, GND=GND
 *    Built-in LED (GPIO2) flashes on pothole detection
 * ═══════════════════════════════════════════════════════════════
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <TinyGPSPlus.h>
#include <HardwareSerial.h>
#include <NTPClient.h>
#include <WiFiUDP.h>

// ══════════════════════════════════════════
//  ✏️  USER CONFIGURATION — EDIT THESE
// ══════════════════════════════════════════
const char* WIFI_SSID       = "Redmi Note 7 Pro";
const char* WIFI_PASSWORD   = "1234567800";

// Your PC's local IP + port (run: ipconfig on your PC to get it)
// Example: "http://192.168.1.105:8000/api/pothole-data/"
const char* SERVER_URL      = "https://brussels-grad-oriented-computed.trycloudflare.com/api/pothole-data/";

// Unique name for this device
const char* DEVICE_ID       = "ESP32-001";

// Vibration threshold for LOCAL pre-filtering (saves WiFi bandwidth)
// The server also applies its own threshold from .env (VIBRATION_THRESHOLD)
const float LOCAL_VIB_THRESHOLD = 150.0;   // m/s² magnitude above gravity

// How long to wait between consecutive detections (ms)
const unsigned long DETECTION_COOLDOWN_MS = 3000;
// ══════════════════════════════════════════

// ── Pin Definitions ────────────────────────────────────────────
#define LED_PIN       2     // Built-in LED
#define GPS_RX_PIN    16    // ESP32 RX2 ← GPS TX
#define GPS_TX_PIN    17    // ESP32 TX2 → GPS RX
#define GPS_BAUD      9600

// ── Object Instances ───────────────────────────────────────────
Adafruit_MPU6050 mpu;
TinyGPSPlus      gps;
HardwareSerial   gpsSerial(2);  // UART2

WiFiUDP  ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", 19800, 60000);
// offset 19800 = UTC+5:30 (India). Change to 0 for UTC.

// ── State ──────────────────────────────────────────────────────
unsigned long lastDetectionTime = 0;
bool          gpsReady          = false;

// ══════════════════════════════════════════════════════════════
//  Helpers
// ══════════════════════════════════════════════════════════════

/** Flash the LED n times */
void flashLED(int times, int onMs = 100, int offMs = 100) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(onMs);
    digitalWrite(LED_PIN, LOW);
    delay(offMs);
  }
}

/** Read combined vibration magnitude from MPU6050 (minus gravity) */
float readVibrationMagnitude() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  // Euclidean magnitude of acceleration vector
  float ax = a.acceleration.x;
  float ay = a.acceleration.y;
  float az = a.acceleration.z;
  float magnitude = sqrt(ax*ax + ay*ay + az*az);

  // Subtract 1g (≈9.81 m/s²) to get the net vibration above resting
  float vibration = abs(magnitude - 9.81);
  return vibration;
}

/** Get ISO-8601 timestamp from NTP */
String getTimestamp() {
  timeClient.update();
  time_t rawTime = timeClient.getEpochTime();
  struct tm* timeInfo = gmtime(&rawTime);

  char buf[25];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S", timeInfo);
  return String(buf);
}

/** Feed GPS serial data and return true once a valid fix is obtained */
bool updateGPS() {
  unsigned long start = millis();
  while (millis() - start < 200) {
    while (gpsSerial.available()) {
      gps.encode(gpsSerial.read());
    }
  }
  return gps.location.isValid();
}

// ══════════════════════════════════════════════════════════════
//  HTTP POST to Django API
// ══════════════════════════════════════════════════════════════
bool sendPotholeData(float lat, float lng, float speed,
                     float vibration, const String& timestamp) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Not connected — skipping POST");
    return false;
  }

  // Build JSON payload
  StaticJsonDocument<256> doc;
  doc["device_id"]       = DEVICE_ID;
  doc["latitude"]        = lat;
  doc["longitude"]       = lng;
  doc["vehicle_speed"]   = speed;
  doc["vibration_value"] = vibration;
  doc["timestamp"]       = timestamp;

  String payload;
  serializeJson(doc, payload);

  Serial.println("[HTTP] Sending: " + payload);

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(8000);  // 8 second timeout

  int responseCode = http.POST(payload);

  if (responseCode > 0) {
    String response = http.getString();
    Serial.printf("[HTTP] %d → %s\n", responseCode, response.c_str());
    http.end();
    return (responseCode == 200);
  } else {
    Serial.printf("[HTTP] Error: %s\n", http.errorToString(responseCode).c_str());
    http.end();
    return false;
  }
}

// ══════════════════════════════════════════════════════════════
//  SETUP
// ══════════════════════════════════════════════════════════════
void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);

  // ── MPU6050 ───────────────────────────────────────────────
  Wire.begin();
  if (!mpu.begin()) {
    Serial.println("[MPU6050] NOT FOUND — check wiring!");
    while (true) { flashLED(3, 200, 200); delay(1000); }
  }
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  Serial.println("[MPU6050] OK");

  // ── GPS ───────────────────────────────────────────────────
  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  Serial.println("[GPS] NEO-6M initialised on UART2");

  // ── WiFi ──────────────────────────────────────────────────
  Serial.printf("[WiFi] Connecting to %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
    flashLED(3, 50, 50);
  } else {
    Serial.println("\n[WiFi] FAILED — running offline (data will not be sent)");
  }

  // ── NTP ───────────────────────────────────────────────────
  timeClient.begin();
  timeClient.update();
  Serial.println("[NTP] Time synced: " + timeClient.getFormattedTime());

  Serial.println("\n[PotholeTrack] Ready — monitoring for potholes...\n");
}

// ══════════════════════════════════════════════════════════════
//  MAIN LOOP
// ══════════════════════════════════════════════════════════════
void loop() {
  // ── 1. Read vibration ─────────────────────────────────────
  float vibration = readVibrationMagnitude();

  // ── 2. Local pre-filter ───────────────────────────────────
  if (vibration < LOCAL_VIB_THRESHOLD) {
    // Quiet road — no pothole, don't spam the server
    delay(50);
    return;
  }

  // ── 3. Cooldown check ─────────────────────────────────────
  unsigned long now = millis();
  if (now - lastDetectionTime < DETECTION_COOLDOWN_MS) {
    delay(50);
    return;
  }
  lastDetectionTime = now;

  // ── 4. Pothole detected! ──────────────────────────────────
  Serial.printf("\n🚧 POTHOLE DETECTED — vibration: %.2f m/s²\n", vibration);
  flashLED(2, 80, 80);  // visual feedback

  // ── 5. Read GPS ───────────────────────────────────────────
  float lat   = 0.0, lng   = 0.0, speed = 0.0;
  bool  gpsFix = updateGPS();

  if (gpsFix) {
    lat   = (float)gps.location.lat();
    lng   = (float)gps.location.lng();
    speed = (float)gps.speed.kmph();
    Serial.printf("[GPS] Fix → lat=%.6f lng=%.6f speed=%.1f km/h\n", lat, lng, speed);
  } else {
    Serial.println("[GPS] No fix yet — using last known / zeros");
    // If GPS has a cached location, use it
    if (gps.location.age() < 30000) {
      lat   = (float)gps.location.lat();
      lng   = (float)gps.location.lng();
      speed = (float)gps.speed.kmph();
    }
  }

  // ── 6. Get timestamp ──────────────────────────────────────
  String timestamp = getTimestamp();
  Serial.println("[NTP] Timestamp: " + timestamp);

  // ── 7. Send to server ─────────────────────────────────────
  bool ok = sendPotholeData(lat, lng, speed, vibration, timestamp);

  if (ok) {
    Serial.println("[✓] Data stored in Google Sheets!\n");
    flashLED(1, 300, 0);  // long flash = success
  } else {
    Serial.println("[✗] Failed to send data\n");
    flashLED(5, 50, 50);  // rapid flashes = error
  }
}
