import json
from datetime import datetime


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


profile = load_json("data/athlete_profile.json")
summary = load_json("data/daily_summary.json")
blocks = load_json("data/training_blocks.json")
performance = load_json("data/performance_trends.json")


coach_input = {

    "generated": str(datetime.now()),

    "athlete": profile["athlete"],

    "goals": profile["performance_goals"],

    "preferences": profile["training_preferences"],

    "current_training_block": blocks.get(
        "current_block",
        {}
    ),

    "recent_training_summary": summary,

    "performance": performance

}


with open(
    "data/coach_input.json",
    "w"
) as f:

    json.dump(
        coach_input,
        f,
        indent=2
    )


print("Coach input created")
