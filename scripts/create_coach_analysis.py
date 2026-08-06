import json
import os
import sys
import time
from datetime import datetime
from google import genai
from google.genai import types

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def main():
    try:
        coach_input = load_json("data/coach_input.json")
    except FileNotFoundError:
        print("Error: data/coach_input.json niet gevonden.")
        sys.exit(1)

    # Haal de invoer op
    sport_preference = os.environ.get("SPORT_PREFERENCE", "Geen voorkeur (Auto)")
    athlete_notes = os.environ.get("ATHLETE_NOTES", "")

    # Garmin data & Post-Workout schakelaar
    garmin_data = coach_input.get("garmin_data", {})
    sleep_score = os.environ.get("SLEEP_SCORE", "") or str(garmin_data.get("sleep_score", ""))
    hrv_status = os.environ.get("HRV_STATUS", "") or str(garmin_data.get("hrv_status", ""))
    hrv_value = str(garmin_data.get("hrv_value", ""))
    is_post_workout = os.environ.get("IS_POST_WORKOUT", "false").lower() == "true"

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY niet ingesteld.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Profielgegevens uitlezen
    profile_config = coach_input.get("profile_config", {})
    athlete = profile_config.get("athlete", {})
    coach_settings = profile_config.get("coach_settings", {})
    heart_rate = profile_config.get("heart_rate", {})
    performance_config = profile_config.get("performance", {})

    goal = athlete.get("goal", "Improve endurance performance with focus on 5km running and cycling power")
    max_hr = heart_rate.get("max_hr", 194)
    ftp = performance_config.get("cycling", {}).get("ftp_watts", 250)
    coach_style = coach_settings.get("style", "strict")
    challenge_level = coach_settings.get("challenge_level", "high")
    priorities = coach_settings.get("priority", [])

    # Schakel tussen Pre-Workout en Post-Workout modus in de prompt
    if is_post_workout:
        mode_instruction = f"""
        CRITICAL MODE: POST-WORKOUT RECOVERY COACH.
        The athlete has just finished a training session. Do NOT recommend future training sessions. Focus entirely on evaluation, recovery, nutrition, and preparation for a potential workout tomorrow.
        
        INSTRUCTIONS:
        1. Evaluate the last completed workout from 'recent_training_summary' or 'activities'. Provide detailed performance feedback in "coach_verdict".
        2. Set the "post_workout_recovery" object with these exact keys:
           - "workout_evaluation": A detailed breakdown of their execution, intensity, and compliance with their zones.
           - "hydration_nutrition": Specific advice on post-workout recovery meals and drinks (carbohydrates, protein ratio, hydration, electrolytes) tailored to the workout intensity and calorie expenditure.
           - "stretching_mobility": Specific recovery exercises, foam rolling, or stretching tailored to the sport they just did.
           - "tomorrow_outlook": Sleep hygiene tips and a brief fysiologische vooruitblik on whether they can expect a hard, moderate, or easy training load tomorrow with the goal of being ready to train if possible.
        """
    else:
        mode_instruction = f"""
        CRITICAL MODE: PRE-WORKOUT PLANNING.
        Recommend exactly THREE ranked training choices for today, ordered by priority (from highest recommended to lowest).
        You have full autonomy to suggest ANY sport/training type (Running, Cycling, Strength, or Recovery/Rest) for each priority. For example, you may suggest 2 different running options and 1 strength option, or 1 cycling, 1 running, and 1 rest option, depending on what the data suggests.
        
        INSTRUCTIONS:
        1. Set the "today_options" object with these exact keys:
           - "priority_1": Object representing the highest recommended option.
           - "priority_2": Object representing the second recommended option.
           - "priority_3": Object representing the third recommended option.
        Each priority object must contain:
           - "session_title" (string, e.g., 'VO2max Cycling Intervals' or 'Upper Body Aesthetics Strength')
           - "sport_type" (string, e.g., 'Running', 'Cycling', 'Strength', 'Recovery')
           - "intensity" (string, e.g., 'Zone 4', 'RPE 8/10', 'Heavy Strength')
           - "workout_details" (string, detailed set/rep/interval scheme)
           - "reason" (string, justification for this option and rank)
        2. Set "coach_verdict" to a direct recommendation of which priority they should focus on and why.
        """

    prompt = f"""
    You are an expert, data-driven elite sports coach. Your athlete wants to optimize their rising fitness trend (CTL) safely and effectively.

    PYRAMIDAL TRAINING DISTRIBUTION (70/30 Rule):
    - Apply a Pyramidal training distribution (70/30 split). This is highly justifiable for this athlete due to their specific short-duration goals (5km speed, 5-min power, 20-min power) and their massive low-intensity aerobic baseline from consistent e-bike commuting.
    - You are allowed to prescribe up to 2 to 3 high-intensity quality sessions per week (Zone 4, Zone 5, Sweet Spot, or hard intervals), but ONLY if their current Form/TSB, last night's sleep score, and HRV status are favorable.
    - If they have recently executed a hard session, or if Garmin data/notes indicate fatigue, the top priorities must revert to Zone 2 Aerobic Endurance or Strength.
    - 70% of the training focus should still remain on building and maintaining their aerobic engine (Zone 2)
