# ESP32 Wiring Guide

## MPU6050 Accelerometer → ESP32

| MPU6050 Pin | ESP32 Pin | Notes |
|------------|-----------|-------|
| VCC | 3.3V | Do NOT connect to 5V |
| GND | GND | |
| SDA | GPIO 21 | I2C Data |
| SCL | GPIO 22 | I2C Clock |
| AD0 | GND | Sets I2C address to 0x68 |
| INT | (optional) | Not used in this sketch |

---

## NEO-6M GPS Module → ESP32

| NEO-6M Pin | ESP32 Pin | Notes |
|-----------|-----------|-------|
| VCC | 3.3V | Do NOT connect to 5V |
| GND | GND | |
| TX | GPIO 16 (RX2) | GPS TX → ESP32 RX |
| RX | GPIO 17 (TX2) | GPS RX → ESP32 TX |

---

## Built-in LED (Status Indicator)

The sketch uses **GPIO 2** (built-in LED on most ESP32 dev boards):

| Pattern | Meaning |
|---------|---------|
| 3 short flashes at startup | WiFi connected |
| 2 medium flashes | Pothole detected (sending...) |
| 1 long flash (300ms) | ✅ Data stored successfully |
| 5 rapid flashes | ❌ HTTP POST failed |
| 3 flashes repeated | MPU6050 not found |

---

## Full Wiring Diagram (Text)

```
    ┌─────────────────────────────────┐
    │         ESP32 Dev Board         │
    │                                 │
    │  3.3V ──┬──── VCC (MPU6050)    │
    │          └──── VCC (NEO-6M)    │
    │  GND  ──┬──── GND (MPU6050)    │
    │          └──── GND (NEO-6M)    │
    │  GPIO21 ───── SDA (MPU6050)    │
    │  GPIO22 ───── SCL (MPU6050)    │
    │  GPIO16 ───── TX  (NEO-6M)     │
    │  GPIO17 ───── RX  (NEO-6M)     │
    │  GPIO2  ───── Built-in LED      │
    └─────────────────────────────────┘
```

---

## Arduino IDE Setup

1. **Install ESP32 board package**:
   - File → Preferences → Additional Board URLs:
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Tools → Board → Boards Manager → search "esp32" → Install "esp32 by Espressif Systems"

2. **Select board**: Tools → Board → ESP32 Arduino → **ESP32 Dev Module**

3. **Select port**: Tools → Port → (your ESP32 COM port)

4. **Install libraries** (Sketch → Manage Libraries):
   - `Adafruit MPU6050`
   - `Adafruit Unified Sensor`
   - `TinyGPS++`
   - `ArduinoJson`
   - `NTPClient`

5. **Open**: `esp32/pothole_detector/pothole_detector.ino`

6. **Edit** the 3 config lines at the top:
   ```cpp
   const char* WIFI_SSID   = "YOUR_WIFI_SSID";
   const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
   const char* SERVER_URL  = "http://YOUR_PC_IP:8000/api/pothole-data/";
   ```

7. **Upload** → Open Serial Monitor at 115200 baud to see live logs
