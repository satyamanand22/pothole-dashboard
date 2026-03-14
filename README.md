# PotholeTrack — ESP32 Pothole Detection System

A full-stack IoT application that collects pothole detection data from ESP32 devices, stores it in Google Sheets, and visualises it on an interactive Google Maps dashboard.

---

## Project Structure

```
pothole_system/
├── manage.py
├── requirements.txt
├── .env.example                   ← Copy to .env and fill in values
├── credentials.json               ← Your Google service account key (not committed)
├── pothole_system/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── pothole_api/
│   ├── serializers.py             ← Data validation
│   ├── sheets.py                  ← Google Sheets integration
│   ├── views.py                   ← API + Dashboard views
│   ├── urls.py                    ← /api/pothole-data/
│   └── dashboard_urls.py          ← /dashboard/
└── templates/
    └── pothole_api/
        └── dashboard.html         ← Interactive map dashboard
```

---

## Setup Instructions

### 1. Prerequisites

- Python 3.11+
- A Google account with Google Sheets + Drive API enabled
- A Google Cloud service account with a `credentials.json` key file
- A Google Maps JavaScript API key

---

### 2. Google Cloud Setup

#### Enable APIs
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Navigate to **APIs & Services → Library** and enable:
   - **Google Sheets API**
   - **Google Drive API**
   - **Maps JavaScript API**

#### Create a Service Account
1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → Service Account**
3. Give it a name (e.g. `pothole-tracker`) and click **Create and Continue**
4. Grant role: **Editor** → **Done**
5. Click the service account → **Keys** tab → **Add Key → Create new key → JSON**
6. Download the `credentials.json` file and place it in the project root

#### Create a Google Sheet
1. Go to [Google Sheets](https://sheets.google.com) and create a new spreadsheet
2. Copy the **Spreadsheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit
   ```
3. Share the spreadsheet with the service account email (found in `credentials.json` as `client_email`) with **Editor** access

---

### 3. Project Configuration

```bash
# Clone or navigate to project directory
cd pothole_system

# Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
```

Edit `.env` and fill in your values:
```ini
SECRET_KEY=your-random-django-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=your-spreadsheet-id-here

VIBRATION_THRESHOLD=200

GOOGLE_MAPS_API_KEY=your-google-maps-api-key-here
```

### 4. Run the Server

```bash
python manage.py migrate
python manage.py runserver
```

- **Dashboard**: http://127.0.0.1:8000/dashboard/
- **API endpoint**: http://127.0.0.1:8000/api/pothole-data/

---

## API Reference

### `POST /api/pothole-data/`

Receives pothole detection data from ESP32 devices.

**Content-Type:** `application/json`

#### Request Body

| Field | Type | Description |
|-------|------|-------------|
| `device_id` | string | Unique ESP32 device identifier |
| `latitude` | float | GPS latitude (-90 to 90) |
| `longitude` | float | GPS longitude (-180 to 180) |
| `vehicle_speed` | float | Speed in km/h (≥ 0) |
| `vibration_value` | float | Raw accelerometer reading (≥ 0) |
| `timestamp` | string | ISO-8601 datetime e.g. `2026-03-08T16:34:56` |

#### Example Request

```bash
curl -X POST http://127.0.0.1:8000/api/pothole-data/ \
  -H "Content-Type: application/json" \
  -d '{
    "device_id":       "ESP32-001",
    "latitude":        12.9716,
    "longitude":       77.5946,
    "vehicle_speed":   35.5,
    "vibration_value": 450.0,
    "timestamp":       "2026-03-08T16:34:56"
  }'
```

#### Responses

| Status | Body |
|--------|------|
| ✅ Stored | `{"status": "success", "message": "Pothole data stored successfully."}` |
| ⚠️ Filtered | `{"status": "ignored", "message": "Vibration value too low..."}` |
| ❌ Invalid | `{"status": "error", "errors": {...}}` |

---

## ESP32 Arduino Code

Upload this sketch to your ESP32. It reads the MPU6050 accelerometer and GPS module then POSTs data to this API.

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ── Configuration ─────────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL    = "http://YOUR_SERVER_IP:8000/api/pothole-data/";
const char* DEVICE_ID     = "ESP32-001";

// Vibration threshold to perform local pre-filtering (saves bandwidth)
const float LOCAL_VIB_THRESHOLD = 150.0;

// ── Simulated sensor readings (replace with real MPU6050 + GPS) ─
// Real implementation: use Adafruit_MPU6050 and TinyGPS++ libraries
float readVibration() {
  // Replace with: sensors_event_t a, g, temp; mpu.getEvent(&a,&g,&temp);
  // return sqrt(a.acceleration.x*a.acceleration.x + ...);
  return random(100, 800);  // simulation
}

float readSpeed() {
  // Replace with GPS speed: gps.speed.kmph()
  return random(20, 60);  // simulation
}

double readLatitude() {
  // Replace with: gps.location.lat()
  return 12.9716 + (random(-100, 100) / 10000.0);
}

double readLongitude() {
  // Replace with: gps.location.lng()
  return 77.5946 + (random(-100, 100) / 10000.0);
}

String getTimestamp() {
  // Replace with NTP time or RTC module
  return "2026-03-08T16:34:56";
}

// ── Setup ────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected! IP: " + WiFi.localIP().toString());
}

// ── Main Loop ────────────────────────────────────────────────
void loop() {
  float vibration = readVibration();

  // Local pre-filter to avoid unnecessary HTTP requests
  if (vibration < LOCAL_VIB_THRESHOLD) {
    Serial.printf("Vibration %.2f below local threshold, skipping.\n", vibration);
    delay(500);
    return;
  }

  float  speed = readSpeed();
  double lat   = readLatitude();
  double lng   = readLongitude();
  String ts    = getTimestamp();

  // Build JSON payload
  StaticJsonDocument<256> doc;
  doc["device_id"]       = DEVICE_ID;
  doc["latitude"]        = lat;
  doc["longitude"]       = lng;
  doc["vehicle_speed"]   = speed;
  doc["vibration_value"] = vibration;
  doc["timestamp"]       = ts;

  String payload;
  serializeJson(doc, payload);

  Serial.printf("Sending: %s\n", payload.c_str());

  // HTTP POST
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");

    int responseCode = http.POST(payload);

    if (responseCode > 0) {
      String response = http.getString();
      Serial.printf("Response [%d]: %s\n", responseCode, response.c_str());
    } else {
      Serial.printf("HTTP Error: %s\n", http.errorToString(responseCode).c_str());
    }

    http.end();
  }

  delay(2000);  // Send every 2 seconds when pothole detected
}
```

### Required Arduino Libraries

Install via **Arduino IDE → Sketch → Include Library → Manage Libraries**:

| Library | Purpose |
|---------|---------|
| `ArduinoJson` | JSON serialization |
| `Adafruit MPU6050` | Accelerometer (real sensor) |
| `TinyGPS++` | GPS parsing (real sensor) |
| `WiFi` | Built-in for ESP32 |
| `HTTPClient` | Built-in for ESP32 |

---

## Google Sheets Format

The app automatically creates a worksheet named **PotholeData** in your spreadsheet with these columns:

| Device_ID | Latitude | Longitude | Speed | Vibration | Timestamp |
|-----------|----------|-----------|-------|-----------|-----------|
| ESP32-001 | 12.9716 | 77.5946 | 35.5 | 450.0 | 2026-03-08T16:34:56 |

---

## Vibration Filtering

The system has **two filtering stages**:

| Stage | Location | Threshold |
|-------|----------|-----------|
| **ESP32 local** | Arduino firmware (`LOCAL_VIB_THRESHOLD`) | Saves bandwidth |
| **Server-side** | Django API (`VIBRATION_THRESHOLD` in `.env`) | Guards Google Sheets |
| **Dashboard UI** | Slider in browser | Visual exploration only |

---

## Security Notes for Production

- Set `DEBUG=False` in `.env`
- Add your server's IP/domain to `ALLOWED_HOSTS`
- Add API key authentication to `PotholeDataView` (e.g. check a shared secret header)
- Never commit `credentials.json` or `.env` to version control (add to `.gitignore`)
