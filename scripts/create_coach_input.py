import json
from datetime import datetime

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

profile = load_json("data/athlete_profile.json")
summary = load_json("data/daily_summary.json")
blocks = load_json("data/training_blocks.json")
performance = load_json("data/performance_trends.json")
fitness = load_json("data/fitness_summary.json")
garmin = load_json("data/garmin_data.json")

coach_input = {
    "generated": str(datetime.now()),
    "profile_config": profile,
    "current_training_block": blocks.get("current_block", {}),
    "recent_training_summary": summary,
    "performance_trends": performance,
    "fitness_state": fitness.get("current_state", {}),
    "garmin_data": garmin
}

with open("data/coach_input.json", "w") as f:
    json.dump(coach_input, f, indent=2)

print("Coach input created successfully")
