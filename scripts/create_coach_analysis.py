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
        mode_instruction = """
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
        mode_instruction = """
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

    # We gebruiken een veilige template-string met placeholders om f-string fouten in Python 3.10 te voorkomen
    prompt_template = """
    You are an expert, data-driven elite sports coach. Your athlete wants to optimize their rising fitness trend (CTL) safely and effectively.

    PYRAMIDAL TRAINING DISTRIBUTION (70/30 Rule):
    - Apply a Pyramidal training distribution (70/30 split). This is highly justifiable for this athlete due to their specific short-duration goals (5km speed, 5-min power, 20-min power) and their massive low-intensity aerobic baseline from consistent e-bike commuting.
    - You are allowed to prescribe up to 2 to 3 high-intensity quality sessions per week (Zone 4, Zone 5, Sweet Spot, or hard intervals), but ONLY if their current Form/TSB, last night's sleep score, and HRV status are favorable.
    - If they have recently executed a hard session, or if Garmin data/notes indicate fatigue, the top priorities must revert to Zone 2 Aerobic Endurance or Strength.
    - 70% of the training focus should still remain on building and maintaining their aerobic engine (Zone 2) and sport-specific strength to justify the overall training load and ensure safe progression.

    Evaluate the athlete's progress through three distinct time horizons:
    1. DAILY HORIZON (Per dag): Analyze immediate training stress, daily load, and today's recovery status.
    2. 3-WEEK HORIZON (Actuele status / 21 days): Treat this as the acute training status. Evaluate recent block volume, fatigue accumulation (ATL), and adaptation rate.
    3. 6-MONTH HORIZON (Sporttrend / 180 days): Treat this as the long-term sport trend. Evaluate macro progression, CTL ramp rate, and seasonal progress.

    ATHLETE GOALS:
    - Running: 5km performance (pace, VO2max, interval quality).
    - Cycling: 5-minute power (VO2max capacity) and 20-minute power (FTP/threshold endurance).

    STRENGTH TRAINING PARAMETERS (Gym equipment available):
    - Equipment: Powerrack (Squat, Deadlift, Bench Press, Overhead Press), Barbell with up to 120kg weight plates, Heavy Sandbag (70kg), Kettlebell (20kg), Bodyweight.
    - Goals: Strength to support cycling torque and running power, core stability, and upper body aesthetics (chest, shoulders, biceps, abs).
    - Note: Strength training is NOT the main priority, but can be integrated as a full training option (Main workout) or extra work (Supplementary/recovery) when appropriate.

    TODAY'S SUBJECTIVE INPUTS:
    - Preferred Sport (if pre-workout): __SPORT_PREFERENCE__
    - Athlete Notes: "__ATHLETE_NOTES__"
    - Garmin Sleep Score (last night): "__SLEEP_SCORE__"
    - Garmin HRV Status: "__HRV_STATUS__ (__HRV_VALUE__ ms)"

    ATHLETE TRAINING DATA:
    __ATHLETE_DATA__

    __MODE_INSTRUCTION__

    COACH INSTRUCTIONS FOR OUTPUT:
    - If is_post_workout is False:
      You must return a JSON object containing exactly the following keys:
      "daily_load_assessment" (string)
      "acute_status_assessment_3_weeks" (string)
      "sport_trend_assessment_6_months" (string)
      "coach_verdict" (string)
      "today_options" (object containing: "priority_1", "priority_2", "priority_3")
    - If is_post_workout is True:
      You must return a JSON object containing exactly the following keys:
      "daily_load_assessment" (string)
      "acute_status_assessment_3_weeks" (string)
      "sport_trend_assessment_6_months" (string)
      "coach_verdict" (string)
      "post_workout_recovery" (object containing: "workout_evaluation", "hydration_nutrition", "stretching_mobility", "tomorrow_outlook")

    Specifics:
    - Coach Style: __COACH_STYLE__, challenge level: __CHALLENGE_LEVEL__.
    - Heart Rate Max: __MAX_HR__ bpm.
    - FTP: __FTP__ W.
    - Athlete Goal: __ATHLETE_GOAL__
    """

    # Vervang de placeholders veilig door de variabelen
    prompt = (prompt_template
              .replace("__SPORT_PREFERENCE__", sport_preference)
              .replace("__ATHLETE_NOTES__", athlete_notes if athlete_notes else "No notes provided today.")
              .replace("__SLEEP_SCORE__", sleep_score)
              .replace("__HRV_STATUS__", hrv_status)
              .replace("__HRV_VALUE__", hrv_value)
              .replace("__ATHLETE_DATA__", json.dumps(coach_input, indent=2))
              .replace("__MODE_INSTRUCTION__", mode_instruction)
              .replace("__COACH_STYLE__", coach_style)
              .replace("__CHALLENGE_LEVEL__", challenge_level)
              .replace("__MAX_HR__", str(max_hr))
              .replace("__FTP__", str(ftp))
              .replace("__ATHLETE_GOAL__", goal))

    print("Gegevens worden naar Gemini gestuurd voor gerichte analyse...")
    
    response = None
    # We proberen de drie meest geschikte modellen na elkaar bij drukte
    models_to_try = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]

    for model_name in models_to_try:
        print(f"Poging met model: {model_name}...")
        for attempt in range(3):  # Maximaal 3 pogingen per model met korte pauze
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
                break  # Gelukt! Breek uit de pogingen-loop
            except Exception as e:
                print(f"Waarschuwing: Fout bij poging {attempt+1} met {model_name}: {e}")
                if attempt < 2:
                    time.sleep(5)  # Wacht 5 seconden voor de volgende poging
                else:
                    print(f"Model {model_name} is niet gelukt na 3 pogingen.")
        
        if response:
            print(f"✅ Analyse succesvol gegenereerd met model: {model_name}")
            break  # Stop de modellen-loop zodra we een succesvol antwoord hebben

    if not response:
        print("❌ Fout: Kon geen verbinding maken met de Gemini API vanwege aanhoudende serverdrukte bij Google.")
        sys.exit(1)

    # Parse de resulterende JSON-tekst
    ai_result = json.loads(response.text)

    fitness_state = coach_input.get("fitness_state", {})
    ctl = fitness_state.get("CTL", 0)
    atl = fitness_state.get("ATL", 0)

    analysis = {
        "generated": str(datetime.now()),
        "athlete_inputs": {
            "sport_preference": sport_preference,
            "athlete_notes": athlete_notes,
            "sleep_score": sleep_score,
            "hrv_status": hrv_status,
            "is_post_workout": is_post_workout
        },
        "current_state": {
            "CTL": round(ctl, 1),
            "ATL": round(atl, 1),
            "Form_TSB": round(ctl - atl, 1)
        },
        "daily_load_assessment": ai_result.get("daily_load_assessment", ""),
        "acute_status_assessment_3_weeks": ai_result.get("acute_status_assessment_3_weeks", ""),
        "sport_trend_assessment_6_months": ai_result.get("sport_trend_assessment_6_months", ""),
        "coach_verdict": ai_result.get("coach_verdict", ""),
        "today_options": ai_result.get("today_options", {}),
        "post_workout_recovery": ai_result.get("post_workout_recovery", {})
    }

    # 1. Sla JSON op
    with open("data/coach_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)

    # 2. Genereer README.md
    tsb = round(ctl - atl, 1)
    if tsb < -30:
         tsb_status = "⚠️ Hoog Risico (TSB onder -30)"
    elif tsb <= -3.2:
         tsb_status = "🟢 Optimaal Trainingsvenster"
    else:
         tsb_status = "🔵 Fris / Herstel"

    # Dynamische README genereren op basis van Pre- of Post-Workout
    if is_post_workout:
        recovery = ai_result.get("post_workout_recovery", {})
