import json
import os
import sys
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

    # Haal de invoer op van de GitHub Action
    sport_preference = os.environ.get("SPORT_PREFERENCE", "Geen voorkeur (Auto)")
    athlete_notes = os.environ.get("ATHLETE_NOTES", "")
    is_post_workout = os.environ.get("IS_POST_WORKOUT", "false").lower() == "true"

    # Haal Garmin-data automatisch op uit de input JSON (geen handmatige invoer meer nodig)
    garmin_data = coach_input.get("garmin_data", {})
    sleep_score = str(garmin_data.get("sleep_score", "Niet beschikbaar"))
    hrv_status = str(garmin_data.get("hrv_status", "Niet beschikbaar"))
    hrv_value = str(garmin_data.get("hrv_value", ""))

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

    # Bepaal de modus-specifieke instructie voor Gemini
    if is_post_workout:
        mode_instruction = f"""
        CRITICAL MODE: POST-WORKOUT RECOVERY COACH.
        The athlete has just completed a training session. Do NOT recommend future training sessions. Focus entirely on evaluation, recovery, nutrition, and preparation for a potential workout tomorrow.
        
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
    You are an expert, data-driven sports coach. Your athlete wants to optimize their rising fitness trend (CTL) safely and effectively.

    Evaluate the athlete's progress through three distinct time horizons:
    1. DAILY HORIZON (Per dag): Analyze immediate training stress, daily load, and today's recovery status.
    2. 3-WEEK HORIZON (Actuele status / 21 days): Evaluate recent block volume, fatigue accumulation (ATL), and adaptation rate.
    3. 6-MONTH HORIZON (Sporttrend / 180 days): Evaluate long-term sport trend, CTL ramp rate, and progress.

    ATHLETE GOALS:
    - Running: 5km performance (pace, VO2max, interval quality).
    - Cycling: 5-minute power (VO2max capacity) and 20-minute power (FTP/threshold endurance).

    STRENGTH TRAINING PARAMETERS (Gym equipment available):
    - Equipment: Powerrack (Squat, Deadlift, Bench Press, Overhead Press), Barbell with up to 120kg weight plates, Heavy Sandbag (70kg), Kettlebell (20kg), Bodyweight.
    - Goals: Strength to support cycling torque and running power, core stability, and upper body aesthetics (chest, shoulders, biceps, abs).
    - Note: Strength training is NOT the main priority, but can be integrated as a full training option (Main workout) or extra work (Supplementary/recovery) when appropriate. There are no exercises you need to avoid.

    TODAY'S SUBJECTIVE INPUTS:
    - Preferred Sport (if pre-workout): {sport_preference}
    - Athlete Notes: "{athlete_notes if athlete_notes else 'No notes provided today.'}"
    - Garmin Sleep Score (last night): "{sleep_score}"
    - Garmin HRV Status: "{hrv_status} ({hrv_value} ms)"

    ATHLETE TRAINING DATA:
    {json.dumps(coach_input, indent=2)}

    {mode_instruction}

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
    - Coach Style: {coach_style}, challenge level: {challenge_level}.
    - Heart Rate Max: {max_hr} bpm.
    - FTP: {ftp} W.
    """

    print("Gegevens worden naar Gemini gestuurd voor gerichte analyse...")
    
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

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
        readme_content = f"""# 🧘‍♂️ Mijn AI Sportcoach - Post-Workout Herstel Rapport

*Gegenereerd na de training op: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📊 Trainingsstatus & Garmin Statistieken
* **Fitheid (CTL):** `{round(ctl, 1)}` | **Vermoeidheid (ATL):** `{round(atl, 1)}` | **Vorm (TSB):** `{tsb}`
* **Slaapscore gisteravond:** `{sleep_score}` | **Garmin HRV-status:** `{hrv_status} ({hrv_value} ms)`

---

## 📋 Beoordeling van de Training (Coach Feedback)
> **Mijn gevoel na de training:** *"{athlete_notes if athlete_notes else 'Geen specifieke opmerkingen.'}"*
> 
> {ai_result.get('coach_verdict', '')}

---

## 🥗 Jouw Herstelprotocol voor Vandaag
*Volg deze stappen nauwkeurig op om je herstel te maximaliseren en blessures te voorkomen:*

### 📋 Stap 1: Beoordeling van de Training
{recovery.get('workout_evaluation', 'Geen beoordeling beschikbaar.')}

### 🥛 Stap 2: Voeding & Hydratatie (Eten & Drinken)
{recovery.get('hydration_nutrition', 'Geen voedingsadvies beschikbaar.')}

### 🧘‍♂️ Stap 3: Spieren & Mobiliteit (Stretching & Mobiliteit)
{recovery.get('stretching_mobility', 'Geen rekoefeningen beschikbaar.')}

### 🛌 Stap 4: Slaap & Vooruitblik naar Morgen
{recovery.get('tomorrow_outlook', 'Geen vooruitblik beschikbaar.')}

---

## 🔍 Diepgaande Trainingsanalyses

### 📅 Dagelijkse Belasting (1-Dag)
{ai_result.get('daily_load_assessment', '')}

### 📈 Actuele Trainingsstatus (3-Weken)
{ai_result.get('acute_status_assessment_3_weeks', '')}

### 📊 Algemene Sporttrend (6-Maanden)
{ai_result.get('sport_trend_assessment_6_months', '')}
"""
    else:
        # Standaard Pre-Workout README (Top 3 Prioriteiten)
        options = ai_result.get("today_options", {})
        p1 = options.get("priority_1", {})
        p2 = options.get("priority_2", {})
        p3 = options.get("priority_3", {})

        readme_content = f"""# 🏃‍♂️ Mijn AI Sportcoach Dashboard

*Laatst bijgewerkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📊 Actuele Trainingsstatus (Lopend Gemiddelde)
* **Fitheid (CTL):** `{round(ctl, 1)}` | **Vermoeidheid (ATL):** `{round(atl, 1)}` | **Vorm (TSB):** `{tsb}`
* **Status:** **{tsb_status}**
* **Slaapscore gisteravond:** `{sleep_score}` | **HRV-status:** `{hrv_status} ({hrv_value} ms)`

---

## 📋 Coach Verdict & Advies voor Vandaag
> **Mijn gevoel vanochtend:** *"{athlete_notes if athlete_notes else 'Geen opmerkingen ingevoerd.'}"*
> 
> {ai_result.get('coach_verdict', '')}

---

## 🎯 Trainingskeuzes voor Vandaag (Gerangschikt op Prioriteit)
*Kies zelf waar je vandaag zin in hebt of wat fysiek het beste voelt:*

### 🥇 Prioriteit 1: {p1.get('sport_type', 'Training')} - {p1.get('session_title', 'Geen training beschikbaar')}
* **Intensiteit:** `{p1.get('intensity', '-')}`
* **Workout details:** {p1.get('workout_details', '-')}
* **Waarom:** *{p1.get('reason', '-')}*

### 🥈 Prioriteit 2: {p2.get('sport_type', 'Training')} - {p2.get('session_title', 'Geen training beschikbaar')}
* **Intensiteit:** `{p2.get('intensity', '-')}`
* **Workout details:** {p2.get('workout_details', '-')}
* **Waarom:** *{p2.get('reason', '-')}*

### 🥉 Prioriteit 3: {p3.get('sport_type', 'Training')} - {p3.get('session_title', 'Geen training beschikbaar')}
* **Intensiteit:** `{p3.get('intensity', '-')}`
* **Workout details:** {p3.get('workout_details', '-')}
* **Waarom:** *{p3.get('reason', '-')}*

---

## 🔍 Diepgaande Trainingsanalyses

### 📅 Dagelijkse Belasting (1-Dag)
{ai_result.get('daily_load_assessment', '')}

### 📈 Actuele Trainingsstatus (3-Weken)
{ai_result.get('acute_status_assessment_3_weeks', '')}

### 📊 Algemene Sporttrend (6-Maanden)
{ai_result.get('sport_trend_assessment_6_months', '')}
"""

    with open("README.md", "w") as f:
        f.write(readme_content)

    print("Gemini coach-analyse met 1D/3W/6M-structuur en README succesvol aangemaakt.")

if __name__ == "__main__":
    main()
