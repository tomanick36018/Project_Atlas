import json
from datetime import datetime, timedelta


# -----------------------------
# Data laden
# -----------------------------

with open("data/daily_summary.json", "r") as f:
    daily = json.load(f)


# -----------------------------
# Laatste 21 dagen bepalen
# -----------------------------

dates = [
    datetime.strptime(date, "%Y-%m-%d")
    for date in daily.keys()
]

latest_date = max(dates)

start_date = latest_date - timedelta(days=20)


# -----------------------------
# Variabelen
# -----------------------------

block = {
    "period_days": 21,
    "start": start_date.strftime("%Y-%m-%d"),
    "end": latest_date.strftime("%Y-%m-%d"),

    "sessions": 0,
    "hours": 0,
    "training_load": 0,

    "running_sessions": 0,
    "cycling_sessions": 0,
    "ebike_sessions": 0,

    "quality_sessions": 0
}


# -----------------------------
# Data verzamelen
# -----------------------------

for date, data in daily.items():

    current = datetime.strptime(date, "%Y-%m-%d")

    if start_date <= current <= latest_date:

        block["sessions"] += data["sessions"]
        block["hours"] += data["hours"]
        block["training_load"] += data["training_load"]

        block["running_sessions"] += data["running"]["sessions"]

        block["cycling_sessions"] += (
            data["cycling_performance"]["sessions"]
        )

        block["ebike_sessions"] += (
            data["cycling_commute"]["sessions"]
        )

        if data["quality"]:
            block["quality_sessions"] += 1


# -----------------------------
# Afronden
# -----------------------------

block["hours"] = round(block["hours"], 2)


# -----------------------------
# Opslaan
# -----------------------------

output = {
    "current_block": block
}


with open("data/training_blocks.json", "w") as f:
    json.dump(output, f, indent=2)


print("Training block updated successfully")
