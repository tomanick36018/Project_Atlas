import json
import os
import requests


API_KEY = os.environ["INTERVALS_API_KEY"]

headers = {
    "User-Agent": "performance-dashboard"
}

auth = (
    "API_KEY",
    API_KEY
)


with open("data/activities.json", "r") as f:
    activities = json.load(f)


power_data = {}


for activity in activities:

    activity_id = activity.get("id")

    # alleen echte fietsritten met power
    if (
        activity.get("type") == "Ride"
        and "watts" in activity.get("stream_types", [])
    ):

        print(f"Ophalen power stream: {activity_id}")

        url = (
            f"https://intervals.icu/api/v1/activity/"
            f"{activity_id}/streams"
        )

        response = requests.get(
            url,
            headers=headers,
            auth=auth
        )

        if response.status_code == 200:
            power_data[activity_id] = response.json()

        else:
            print(
                f"Fout bij {activity_id}: {response.status_code}"
            )


with open("data/power_streams.json", "w") as f:
    json.dump(power_data, f, indent=2)


print("Power streams opgeslagen")
