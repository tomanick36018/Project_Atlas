import json
from datetime import datetime, timedelta


# Data laden
with open("data/activities.json", "r") as f:
    activities = json.load(f)

with open("config/athlete_profile.json", "r") as f:
    profile = json.load(f)


now = datetime.now()
days_21_ago = now - timedelta(days=21)


# Alleen laatste 21 dagen
last_21 = []

for activity in activities:
    date = datetime.fromisoformat(
        activity["start_date_local"]
    )

    if date >= days_21_ago:
        last_21.append(activity)


# Sportherkenning

running = []
ebike = []
cycling = []

for activity in last_21:

    activity_type = activity.get(
        "type",
        ""
    ).lower()

    if "run" in activity_type:
        running.append(activity)

    elif "ebike" in activity_type:
        ebike.append(activity)

    elif (
        "ride" in activity_type
        or "bike" in activity_type
        or "cycling" in activity_type
    ):
        cycling.append(activity)



def total_hours(items):
    return round(
        sum(
            x.get("moving_time",0)
            for x in items
        ) / 3600,
        1
    )


def total_load(items):
    return round(
        sum(
            x.get("icu_training_load",0)
            for x in items
        ),
        1
    )


def total_distance(items):
    return round(
        sum(
            x.get("distance",0)
            for x in items
        ) / 1000,
        1
    )


def average_hr(items):

    values = [
        x.get("average_heartrate")
        for x in items
        if x.get("average_heartrate")
    ]

    if not values:
        return None

    return round(
        sum(values) / len(values),
        0
    )


# Kwaliteitssessies
# Hoog intensief = HR boven ongeveer 85% max HR

quality_sessions = []

for activity in last_21:

    hr = activity.get(
        "average_heartrate"
    )

    if hr and hr >= 165:
        quality_sessions.append(activity)


summary = {

    "generated": str(now),

    "athlete": profile["athlete"],


    "training_block_21_days": {

        "total": {
            "sessions": len(last_21),
            "hours": total_hours(last_21),
            "training_load": total_load(last_21)
        },


        "running": {
            "sessions": len(running),
            "hours": total_hours(running),
            "distance_km": total_distance(running),
            "average_hr": average_hr(running)
        },


        "cycling_performance": {
            "sessions": len(cycling),
            "hours": total_hours(cycling),
            "distance_km": total_distance(cycling),
            "training_load": total_load(cycling),
            "average_hr": average_hr(cycling)
        },


        "cycling_commute": {
            "sessions": len(ebike),
            "hours": total_hours(ebike),
            "distance_km": total_distance(ebike),
            "training_load": total_load(ebike),
            "average_hr": average_hr(ebike)
        },


        "quality_sessions": {
            "count": len(quality_sessions)
        }

    },


    "current_state": {

        "CTL": activities[0].get(
            "icu_ctl"
        ),

        "ATL": activities[0].get(
            "icu_atl"
        ),

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


print("Fitness summary updated")
