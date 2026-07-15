import os
import json
from datetime import date
from garminconnect import Garmin

# Haal inloggegevens op uit de GitHub Secrets
email = os.environ.get("GARMIN_EMAIL")
password = os.environ.get("GARMIN_PASSWORD")

if not email or not password:
    print("Garmin inloggegevens ontbreken in Secrets. We slaan deze stap over.")
    with open("data/garmin_data.json", "w") as f:
        json.dump({}, f)
    exit(0)

try:
    print("Inloggen bij Garmin Connect...")
    client = Garmin(email, password)
    client.login()
    
    today = date.today().isoformat()
    
    # 1. Haal slaapgegevens op
    print("Slaapgegevens ophalen...")
    sleep_data = client.get_sleep_data(today)
    sleep_score = sleep_data.get("dailySleepDTO", {}).get("sleepScore", "")
    
    # 2. Haal HRV-gegevens op
    print("HRV-gegevens ophalen...")
    hrv_data = client.get_hrv_data(today)
    hrv_summary = hrv_data.get("hrvSummary", {}) if hrv_data else {}
    last_night_avg = hrv_summary.get("lastNightAvg", "")
    hrv_status = hrv_summary.get("feedbackType", "") # Bijv: "BALANCED", "LOW"
    
    garmin_summary = {
        "sleep_score": sleep_score,
        "hrv_status": hrv_status,
        "hrv_value": last_night_avg
    }
    
    print(f"Succes! Garmin data: {garmin_summary}")
    
except Exception as e:
    print(f"Fout bij het ophalen van Garmin data: {e}")
    garmin_summary = {}

# Sla de gegevens op
with open("data/garmin_data.json", "w") as f:
    json.dump(garmin_summary, f, indent=2)
