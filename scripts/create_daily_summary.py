import json
from datetime import datetime
from collections import defaultdict

# Data laden
with open("data/activities.json", "r") as f:
    activities = json.load(f)

days = defaultdict(lambda: {
    "sessions": 0,
    "training_load": 0,
    "hours": 0,
    "distance_km": 0,
    "running": {
        "sessions": 0,
        "distance_km": 0
    },
    "cycling_performance": {
        "sessions": 0,
        "distance_km": 0
    },
    "cycling_commute": {
        "sessions": 0,
        "distance_km": 0
    },
    "quality": False
})

for activity in activities:

    date = activity["start_date_local"][:10]
    day = days[date]

    day["sessions"] += 1
    day["training_load"] += activity.get("icu_training_load", 0)
    day["hours"] += activity.get("moving_time", 0) / 3600
    day["distance_km"] += activity.get("distance", 0) / 1000

    activity_type = activity.get("type", "").lower()

    if "run" in activity_type:
        day["running"]["sessions"] += 1
        day["running"]["distance_km"] += activity.get("distance", 0) / 1000

    elif "ebike" in activity_type:
        day["cycling_commute"]["sessions"] += 1
        day["cycling_commute"]["distance_km"] += activity.get("distance", 0) / 1000

    elif "ride" in activity_type or "bike" in activity_type:
        day["cycling_performance"]["sessions"] += 1
        day["cycling_performance"]["distance_km"] += activity.get("distance", 0) / 1000

    # Eenvoudige definitie van een kwaliteitssessie
    if activity.get("icu_training_load", 0) >= 60:
        day["quality"] = True

# Afronden
for day in days.values():
    day["hours"] = round(day["hours"], 2)
    day["distance_km"] = round(day["distance_km"], 1)

    day["running"]["distance_km"] = round(day["running"]["distance_km"], 1)
    day["cycling_performance"]["distance_km"] = round(day["cycling_performance"]["distance_km"], 1)
    day["cycling_commute"]["distance_km"] = round(day["cycling_commute"]["distance_km"], 1)

# Chronologisch sorteren
output = dict(sorted(days.items()))

with open("data/daily_summary.json", "w") as f:
    json.dump(output, f, indent=2)

print("Daily summary updated")
