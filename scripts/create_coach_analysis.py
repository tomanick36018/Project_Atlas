import json
from datetime import datetime


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


coach_input = load_json("data/coach_input.json")


block = coach_input.get("current_training_block", {})
performance = coach_input.get("performance", {})
athlete = coach_input.get("athlete", {})


ctl = block.get("CTL", 0)
atl = block.get("ATL", 0)
training_load = block.get("training_load", 0)


analysis = {

    "generated": str(datetime.now()),

    "athlete": athlete,

    "current_state": {

        "training_load_21_days": training_load,

        "CTL": ctl,

        "ATL": atl

    },

    "coach_assessment": "",

    "today_recommendation": {

        "type": "",

        "session": "",

        "reason": ""

    }

}


# eenvoudige eerste coachregels

if atl > ctl * 1.4:

    analysis["coach_assessment"] = (
        "High fatigue detected. Avoid hard intensity."
    )

    analysis["today_recommendation"] = {
        "type": "recovery",
        "session": "Zone 1-2 easy endurance",
        "reason": "Recent load is high compared with fitness."
    }


elif training_load < 300:

    analysis["coach_assessment"] = (
        "Training stimulus is too low."
    )

    analysis["today_recommendation"] = {
        "type": "quality",
        "session": "Interval training",
        "reason": "Increase training stimulus."
    }


else:

    analysis["coach_assessment"] = (
        "Good training window."
    )

    analysis["today_recommendation"] = {
        "type": "quality",
        "session": "Choose running or cycling intervals",
        "reason": "Current load supports productive intensity."
    }


with open(
    "data/coach_analysis.json",
    "w"
) as f:

    json.dump(
        analysis,
        f,
        indent=2
    )


print("Coach analysis created")
