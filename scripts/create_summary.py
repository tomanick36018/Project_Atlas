import json
from datetime import datetime, timedelta


# Data laden
with open("data/activities.json", "r") as f:
    activities = json.load(f)

with open("config/athlete_profile.json", "r") as f:
    profile = json.load(f)


now = datetime.now()
days_21_ago = now - timedelta(days=21)
days_7_ago = now - timedelta(days=7)


last_21 = []
last_7 = []


for activity in activities:

    date = datetime.fromisoformat(
        activity["start_date_local"]
    )

    if date >= days_21_ago:
        last_21.append(activity)

    if date >= days_7_ago:
        last_7.append(activity)


def hours(items):
    return round(
        sum(x.get("moving_time",0) for x in items) / 3600,
        1
    )


def load(items):
    return round(
        sum(
            x.get("icu_training_load",0)
            for x in items
        ),
        1
    )


runs = [
    x for x in last_21
    if "run" in x.get("type","").lower()
]


rides = [
    x for x in last_21
    if any(
        word in x.get("type","").lower()
        for word in [
            "ride",
            "bike",
            "cycling",
            "virtual"
        ]
    )
]


summary = {

    "generated": str(now),

    "athlete": profile["athlete"],

    "training_block_21_days": {

        "sessions": len(last_21),

        "hours": hours(last_21),

        "training_load": load(last_21),

        "running": {
            "sessions": len(runs),
            "distance_km": round(
                sum(
                    x.get("distance",0)
                    for x in runs
                ) / 1000,
                1
            )
        },

        "cycling": {
            "sessions": len(rides),
            "distance_km": round(
                sum(
                    x.get("distance",0)
                    for x in rides
                ) / 1000,
                1
            )
        }
    },


    "current_state": {

        "CTL": activities[0].get("icu_ctl"),

        "ATL": activities[0].get("icu_atl"),

        "resting_hr": activities[0].get(
            "icu_resting_hr"
        ),

        "weight": activities[0].get(
            "icu_weight"
        )
    }
}


with open(
    "data/fitness_summary.json",
    "w"
) as f:

    json.dump(
        summary,
        f,
        indent=2
    )


print("Summary created")
print(summary)
