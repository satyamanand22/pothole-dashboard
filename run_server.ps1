# ── PotholeTrack Server Startup Script ───────────────────────────
# Run this instead of `python manage.py runserver` so the ESP32
# (on the same WiFi) can reach the server from your PC.
#
# Usage:
#   .\run_server.ps1
# ─────────────────────────────────────────────────────────────────

$PYTHON = "C:\Users\satya\AppData\Local\Programs\Python\Python313\python.exe"
$PORT   = 8000

# Get the PC's local WiFi IP automatically
$IP = (Get-NetIPAddress -AddressFamily IPv4 |
       Where-Object { $_.IPAddress -notmatch '^127\.' -and
                      $_.IPAddress -notmatch '^169\.' } |
       Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  PotholeTrack — Starting Dev Server" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Dashboard  : http://127.0.0.1:$PORT/dashboard/" -ForegroundColor Green
Write-Host "  API        : http://127.0.0.1:$PORT/api/pothole-data/" -ForegroundColor Green
Write-Host ""
Write-Host "  ESP32 URL  : http://$IP:$PORT/api/pothole-data/" -ForegroundColor Yellow
Write-Host "  (Copy this into pothole_detector.ino as SERVER_URL)" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Press Ctrl+C to stop the server" -ForegroundColor DarkGray
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Update ALLOWED_HOSTS in .env to include the local IP
$envFile = ".\.env"
$envContent = Get-Content $envFile -Raw

if ($envContent -notmatch [regex]::Escape($IP)) {
    $envContent = $envContent -replace "ALLOWED_HOSTS=.*", "ALLOWED_HOSTS=127.0.0.1,localhost,$IP"
    Set-Content $envFile $envContent
    Write-Host "[.env] Added $IP to ALLOWED_HOSTS automatically" -ForegroundColor DarkGreen
}

# Start server on all interfaces so ESP32 can reach it
& $PYTHON manage.py runserver 0.0.0.0:$PORT
