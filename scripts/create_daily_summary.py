import json
from collections import defaultdict


def safe(value):
    """
    Zet lege waarden (null) om naar 0.
    """
    return 0 if value is None else value


# -----------------------------
# Data laden
# -----------------------------

with open("data/activities.json", "r") as f:
    activities = json.load(f)


# -----------------------------
# Dagstructuur
# -----------------------------

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


# -----------------------------
# Activiteiten verwerken
# -----------------------------

for activity in activities:

    date = activity.get("start_date_local", "")[:10]

    if not date:
        continue

    day = days[date]

    distance = safe(activity.get("distance"))

    load = safe(activity.get("icu_training_load"))

    moving_time = safe(activity.get("moving_time"))


    day["sessions"] += 1
    day["training_load"] += load
    day["hours"] += moving_time / 3600
    day["distance_km"] += distance / 1000


    activity_type = activity.get("type", "").lower()


    # -------------------------
    # Sporttype
    # -------------------------

    if "run" in activity_type:

        day["running"]["sessions"] += 1
        day["running"]["distance_km"] += distance / 1000


    elif "ebike" in activity_type:

        day["cycling_commute"]["sessions"] += 1
        day["cycling_commute"]["distance_km"] += distance / 1000


    elif "ride" in activity_type or "bike" in activity_type:

        day["cycling_performance"]["sessions"] += 1
        day["cycling_performance"]["distance_km"] += distance / 1000


    # -------------------------
    # Kwaliteitssessie
    # -------------------------

    if load >= 60:
        day["quality"] = True



# -----------------------------
# Afronden
# -----------------------------

for day in days.values():

    day["training_load"] = round(day["training_load"], 1)
    day["hours"] = round(day["hours"], 2)
    day["distance_km"] = round(day["distance_km"], 1)

    day["running"]["distance_km"] = round(
        day["running"]["distance_km"], 1
    )

    day["cycling_performance"]["distance_km"] = round(
        day["cycling_performance"]["distance_km"], 1
    )

    day["cycling_commute"]["distance_km"] = round(
        day["cycling_commute"]["distance_km"], 1
    )


# -----------------------------
# Opslaan
# -----------------------------

output = dict(sorted(days.items()))


with open("data/daily_summary.json", "w") as f:
    json.dump(output, f, indent=2)


print("Daily summary updated successfully")
