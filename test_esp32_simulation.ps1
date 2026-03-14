# ── PotholeTrack — Simulate ESP32 POST (no hardware needed) ──────
# Run this script to test the full Django → Google Sheets pipeline
# from your Windows PC, before connecting real ESP32 hardware.
#
# Usage:
#   .\test_esp32_simulation.ps1
#
# What it does:
#   1. Sends a VALID pothole (vibration=450) → should be stored
#   2. Sends a LOW vibration event (vibration=80) → should be ignored
#   3. Sends an INVALID payload (missing fields) → should return error
# ─────────────────────────────────────────────────────────────────

$API = "http://127.0.0.1:8000/api/pothole-data/"
$HEADERS = @{ "Content-Type" = "application/json" }

function Post-Pothole($label, $body) {
    Write-Host ""
    Write-Host "── Test: $label ──" -ForegroundColor Cyan
    Write-Host "Sending: $body" -ForegroundColor DarkGray
    try {
        $response = Invoke-WebRequest -Uri $API -Method POST `
                        -Headers $HEADERS -Body $body -ErrorAction Stop
        $json = $response.Content | ConvertFrom-Json
        $color = if ($json.status -eq "success") { "Green" } `
                 elseif ($json.status -eq "ignored") { "Yellow" } else { "Red" }
        Write-Host "Response [$($response.StatusCode)]: status=$($json.status)" -ForegroundColor $color
        Write-Host "          message=$($json.message)" -ForegroundColor $color
    } catch {
        $errBody = $_.ErrorDetails.Message
        Write-Host "Response [ERROR]: $errBody" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║   PotholeTrack — ESP32 Simulation Test   ║" -ForegroundColor Magenta
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Magenta

# ── Test 1: Valid high-vibration pothole (should be STORED) ─────
Post-Pothole "Valid Pothole (vibration=450)" `
    '{"device_id":"ESP32-001","latitude":12.9716,"longitude":77.5946,"vehicle_speed":35.5,"vibration_value":450.0,"timestamp":"2026-03-08T17:14:59"}'

# ── Test 2: Low vibration — false positive (should be IGNORED) ──
Post-Pothole "Low Vibration / False Positive (vibration=80)" `
    '{"device_id":"ESP32-001","latitude":12.9810,"longitude":77.6050,"vehicle_speed":28.0,"vibration_value":80.0,"timestamp":"2026-03-08T17:15:05"}'

# ── Test 3: Missing required fields (should return ERROR) ────────
Post-Pothole "Invalid Payload (missing latitude/longitude)" `
    '{"device_id":"ESP32-001","vehicle_speed":30.0,"vibration_value":400.0,"timestamp":"2026-03-08T17:15:10"}'

# ── Test 4: Second device, different location ────────────────────
Post-Pothole "Second Device (ESP32-002, different location)" `
    '{"device_id":"ESP32-002","latitude":12.9620,"longitude":77.5800,"vehicle_speed":42.0,"vibration_value":620.0,"timestamp":"2026-03-08T17:15:15"}'

Write-Host ""
Write-Host "Done! Now refresh your dashboard to see new markers:" -ForegroundColor Green
Write-Host "  http://127.0.0.1:8000/dashboard/" -ForegroundColor Green
Write-Host ""
