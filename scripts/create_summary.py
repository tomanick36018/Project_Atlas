import json
from datetime import datetime, timedelta


# activiteiten laden
with open("data/activities.json", "r") as f:
    activities = json.load(f)


now = datetime.now()
week_ago = now - timedelta(days=7)


last_week = []

for activity in activities:
    date = datetime.fromisoformat(
        activity["start_date_local"]
    )

    if date >= week_ago:
        last_week.append(activity)


summary = {
    "generated": str(now),
    "activities_last_7_days": len(last_week),
    "training_hours_last_7_days": round(
        sum(a["moving_time"] for a in last_week) / 3600,
        2
    ),
    "training_load_last_7_days": round(
        sum(a.get("icu_training_load",0) for a in last_week),
        1
    ),
    "latest_ctl": activities[0].get("icu_ctl"),
    "latest_atl": activities[0].get("icu_atl"),
    "latest_resting_hr": activities[0].get("icu_resting_hr"),
    "latest_weight": activities[0].get("icu_weight")
}


with open("data/fitness_summary.json", "w") as f:
    json.dump(summary, f, indent=2)


print(summary)
