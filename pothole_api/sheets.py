"""
Google Sheets integration using gspread and a service account.

Required configuration (via .env / settings.py):
    GOOGLE_CREDENTIALS_FILE       : Path to the service account credentials.json
    GOOGLE_SHEETS_SPREADSHEET_ID  : The spreadsheet ID from the Google Sheets URL

Sheet layout (row 1 must contain these headers):
    Device_ID | Latitude | Longitude | Speed | Vibration | Timestamp
"""

import sqlite3
import gspread
from google.oauth2.service_account import Credentials
from django.conf import settings
import logging
import os

logger = logging.getLogger(__name__)

# ── Local SQLite Fallback (for testing without Google keys) ─────
DB_PATH = os.path.join(settings.BASE_DIR, 'db.sqlite3')

def init_local_db():
    """Create the pothole table in SQLite if it doesn't exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pothole_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT,
                latitude REAL,
                longitude REAL,
                speed REAL,
                vibration REAL,
                timestamp TEXT
            )
        ''')

def _is_google_configured():
    """Check if Google Sheets credentials and ID are provided."""
    creds_exist = os.path.exists(settings.GOOGLE_CREDENTIALS_FILE)
    id_exists = bool(settings.GOOGLE_SHEETS_SPREADSHEET_ID)
    return creds_exist and id_exists

# Scopes required for read/write access to Google Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

# The worksheet name (tab) where data is stored
WORKSHEET_NAME = 'PotholeData'

# Expected header row — created automatically if worksheet is new
HEADERS = ['Device_ID', 'Latitude', 'Longitude', 'Speed', 'Vibration', 'Timestamp']


def _get_client() -> gspread.Client:
    """Authenticate with Google Sheets API using service account credentials."""
    creds = Credentials.from_service_account_file(
        settings.GOOGLE_CREDENTIALS_FILE,
        scopes=SCOPES
    )
    return gspread.authorize(creds)


def get_sheet() -> gspread.Worksheet:
    """
    Return the PotholeData worksheet, creating it with headers if it
    doesn't exist yet.
    """
    client = _get_client()
    spreadsheet = client.open_by_key(settings.GOOGLE_SHEETS_SPREADSHEET_ID)

    # Try to open existing worksheet; create it if missing
    try:
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=WORKSHEET_NAME,
            rows=1000,
            cols=len(HEADERS)
        )
        worksheet.append_row(HEADERS)
        logger.info("Created new worksheet '%s' with headers.", WORKSHEET_NAME)

    return worksheet


def append_pothole_row(data: dict) -> None:
    """
    Append a new pothole detection record to Google Sheets or local SQLite.
    """
    if _is_google_configured():
        try:
            worksheet = get_sheet()
            row = [data['device_id'], data['latitude'], data['longitude'], 
                   data['vehicle_speed'], data['vibration_value'], data['timestamp']]
            worksheet.append_row(row, value_input_option='USER_ENTERED')
            logger.info("Stored in Google Sheets: %s", data['device_id'])
            return
        except Exception as e:
            logger.error("Google Sheets failed, falling back to local: %s", e)

    # Fallback/Default: Local SQLite
    try:
        init_local_db()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                INSERT INTO pothole_records (device_id, latitude, longitude, speed, vibration, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (data['device_id'], data['latitude'], data['longitude'], 
                  data.get('vehicle_speed', 0), data.get('vibration_value', 0), data['timestamp']))
        logger.info("Stored in local DB: %s", data['device_id'])
    except Exception as e:
        logger.error("Local SQLite write failed: %s", e)


def get_all_potholes() -> list[dict]:
    """
    Fetch all pothole records from Google Sheets and local SQLite.
    """
    all_records = []

    # 1. Try Google Sheets
    if _is_google_configured():
        try:
            worksheet = get_sheet()
            records = worksheet.get_all_records(expected_headers=HEADERS)
            for r in records:
                all_records.append({
                    'device_id': r.get('Device_ID', ''),
                    'latitude':  r.get('Latitude', 0),
                    'longitude': r.get('Longitude', 0),
                    'speed':     r.get('Speed', 0),
                    'vibration': r.get('Vibration', 0),
                    'timestamp': r.get('Timestamp', ''),
                })
        except Exception as e:
            logger.error("Failed to fetch from Google Sheets: %s", e)

    # 2. Add Local SQLite records
    init_local_db()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM pothole_records ORDER BY id DESC')
            for row in cursor:
                # Merge logic: Avoid duplicates if possible, or just append
                all_records.append({
                    'device_id': row['device_id'],
                    'latitude':  row['latitude'],
                    'longitude': row['longitude'],
                    'speed':     row['speed'],
                    'vibration': row['vibration'],
                    'timestamp': row['timestamp'],
                })
    except Exception as e:
        logger.error("Failed to fetch from local DB: %s", e)

    return all_records
