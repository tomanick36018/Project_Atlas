import json
from datetime import datetime, timedelta


with open("data/activities.json","r") as f:
    activities = json.load(f)


now = datetime.now()
days_180 = now - timedelta(days=180)


rides = []

for a in activities:

    date = datetime.fromisoformat(
        a["start_date_local"]
    )

    if date >= days_180 and a.get("type") == "Ride":
        rides.append(a)



def maximum(values):
    values = [
        v for v in values
        if v is not None
    ]

    if not values:
        return None

    return max(values)



performance = {

    "generated": str(now),

    "cycling": {

        "rides_last_180_days": len(rides),

        "best_ftp": maximum([
            r.get("icu_ftp")
            for r in rides
        ]),

        "best_5min_power": None,
        ]),

        "best_wprime": maximum([
            r.get("icu_pm_w_prime")
            for r in rides
        ]),

        "best_peak_power": maximum([
            r.get("icu_pm_p_max")
            for r in rides
        ])

    }
}


with open(
    "data/performance_trends.json",
    "w"
) as f:

    json.dump(
        performance,
        f,
        indent=2
    )


print(performance)
