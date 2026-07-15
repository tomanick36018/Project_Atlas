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

    # Haal de handmatige input op die via de GitHub Action is meegegeven
    sport_preference = os.environ.get("SPORT_PREFERENCE", "Geen voorkeur (Auto)")
    athlete_notes = os.environ.get("ATHLETE_NOTES", "")

    # Garmin data & Post-Workout schakelaar (nieuwe fallbacks)
    garmin_data = coach_input.get("garmin_data", {})
    sleep_score = os.environ.get("SLEEP_SCORE", "") or str(garmin_data.get("sleep_score", ""))
    hrv_status = os.environ.get("HRV_STATUS", "") or str(garmin_data.get("hrv_status", ""))
    is_post_workout = os.environ.get("IS_POST_WORKOUT", "false").lower() == "true"

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY niet ingesteld.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Haal gegevens veilig en dynamisch uit uw echte profiel-configuratie
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
        CRITICAL MODE: POST-WORKOUT EVALUATION.
        The athlete has just finished a training session. Your primary task is to evaluate their execution and provide a precise recovery protocol.
        
        INSTRUCTIONS FOR THIS MODE:
        1. Look at the last completed activity in the training data (under recent_training_summary or activities). Assess if they hit their targets, if the intensity was correct, and evaluate their effort.
        2. Set "coach_verdict" to a detailed performance feedback of this specific workout.
        3. Since they are done training today, you will NOT recommend future sessions in "today_options". Instead, repurpose the "today_options" keys as follows:
           - "cycling_option": Set "session_title" to "Nutrition & Hydration". Set "workout_details" to exactly what they should eat and drink right now (e.g., carbs, protein in grams, water, electrolytes) based on the intensity/calories of the session they just completed.
           - "running_option": Set "session_title" to "Muscle Recovery & Mobility". Set "workout_details" to specific stretches, foam rolling, or active recovery movements tailored to the sport they just did.
           - "recovery_option": Set "session_title" to "Sleep & Tomorrow's Outlook". Set "workout_details" to how they should optimize sleep tonight and a brief preview of what kind of training load they can expect tomorrow.
        """
    else:
        mode_instruction = f"""
        CRITICAL MODE: PRE-WORKOUT PLANNING.
        Your task is to provide the athlete with three distinct training options for today (Cycling, Running, Recovery) so they can choose.
        - "cycling_option": Targets FTP (20-min power) or VO2max (5-min power).
        - "running_option": Targets 5km running performance.
        - "recovery_option": Active recovery or rest.
        Set "coach_verdict" to your direct recommendation of which option they should prioritize today based on their current CTL/ATL and notes.
        """

    prompt = f"""
    You are an expert, data-driven sports coach. Your athlete wants to optimize their rising fitness trend (CTL) safely and effectively.

    Evaluate the athlete's progress through three distinct time horizons:
    1. DAILY HORIZON (Per dag): Analyze immediate training stress, daily load, and today's recovery state.
    2. 3-WEEK HORIZON (Actuele status / 21 days): Evaluate recent block volume, fatigue accumulation (ATL), and adaptation rate.
    3. 6-MONTH HORIZON (Sporttrend / 180 days): Evaluate long-term sport trend, CTL ramp rate, and progress.

    ATHLETE GOALS:
    - Running: 5km performance.
    - Cycling: 5-minute power (VO2max) and 20-minute power (FTP).

    TODAY'S SUBJECTIVE INPUTS:
    - Preferred Sport (if pre-workout): {sport_preference}
    - Athlete Notes: "{athlete_notes if athlete_notes else 'No notes provided today.'}"
    - Garmin Sleep Score (last night): "{sleep_score if sleep_score else 'Not provided'}"
    - Garmin HRV Status: "{hrv_status if hrv_status else 'Not provided'}"

    ATHLETE TRAINING DATA:
    {json.dumps(coach_input, indent=2)}

    {mode_instruction}

    COACH INSTRUCTIONS:
    - You must return a JSON object containing exactly the following keys:
      "daily_load_assessment" (string)
      "acute_status_assessment_3_weeks" (string)
      "sport_trend_assessment_6_months" (string)
      "coach_verdict" (string)
      "today_options" (object containing: "cycling_option", "running_option", and "recovery_option")

    - Each of the three options ("cycling_option", "running_option", "recovery_option") must be an object with:
      "session_title" (string)
      "intensity" (string)
      "workout_details" (string)
      "reason" (string)

    Specifics to include:
    - Coach Style: {coach_style}, challenge level: {challenge_level}.
    - Athlete Goal: {goal}
    - Heart Rate Max: {max_hr} bpm.
    - FTP: {ftp} W.
    """

    print("Gegevens worden naar Gemini gestuurd voor snelle JSON analyse...")
    
    # We vragen om JSON-output, maar laten de zware schema-validatie achterwege voor maximale snelheid
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

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
        "today_options": ai_result.get("today_options", {})
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

    # Haal de opties veilig op uit het resultaat
    options = ai_result.get("today_options", {})
    cycling = options.get("cycling_option", {})
    running = options.get("running_option", {})
    recovery = options.get("recovery_option", {})

    # Dynamische README genereren op basis van Pre- of Post-Workout
    if is_post_workout:
        readme_content = f"""# 🧘‍♂️ Mijn AI Sportcoach - Post-Workout Herstel Rapport

*Gegenereerd na de training op: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📊 Trainingsstatus & Garmin Statistieken
* **Fitheid (CTL):** `{round(ctl, 1)}` | **Vermoeidheid (ATL):** `{round(atl, 1)}` | **Vorm (TSB):** `{tsb}`
* **Slaapscore gisteravond:** `{sleep_score if sleep_score else 'Niet opgegeven'}`
* **Garmin HRV-status:** `{hrv_status if hrv_status else 'Niet opgegeven'}`

---

## 📋 Beoordeling van de Training (Coach Feedback)
> **Mijn gevoel na de training:** *"{athlete_notes if athlete_notes else 'Geen specifieke opmerkingen.'}"*
> 
> {ai_result.get('coach_verdict', '')}

---

## 🥗 Jouw Herstelprotocol voor Vandaag
*Volg deze stappen nauwkeurig op om je herstel te maximaliseren en blessures te voorkomen:*

### 🥛 Stap 1: Voeding & Hydratatie (Eten & Drinken)
* **Protocol:** **{cycling.get('session_title', 'Herstelvoeding')}**
* **Doel:** `{cycling.get('intensity', '-')}`
* **Details:** {cycling.get('workout_details', '-')}
* **Waarom:** *{cycling.get('reason', '-')}*

### 🧘‍♂️ Stap 2: Spieren & Mobiliteit (Stretching & Mobiliteit)
* **Protocol:** **{running.get('session_title', 'Mobiliteit en herstel')}**
* **Doel:** `{running.get('intensity', '-')}`
* **Details:** {running.get('workout_details', '-')}
* **Waarom:** *{running.get('reason', '-')}*

### 🛌 Stap 3: Slaap & Volgende Stap (Vooruitblik)
* **Protocol:** **{recovery.get('session_title', 'Vooruitblik')}**
* **Doel:** `{recovery.get('intensity', '-')}`
* **Details:** {recovery.get('workout_details', '-')}
* **Waarom:** *{recovery.get('reason', '-')}*

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
        # Standaard Pre-Workout README
        readme_content = f"""# 🏃‍♂️ Mijn AI Sportcoach Dashboard

*Laatst bijgewerkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📊 Actuele Trainingsstatus (Lopend Gemiddelde)
* **Fitheid (CTL):** `{round(ctl, 1)}` | **Vermoeidheid (ATL):** `{round(atl, 1)}` | **Vorm (TSB):** `{tsb}`
* **Status:** **{tsb_status}**
* **Slaapscore gisteravond:** `{sleep_score if sleep_score else 'Niet opgegeven'}` | **HRV-status:** `{hrv_status if hrv_status else 'Niet opgegeven'}`

---

## 📋 Coach Verdict & Advies voor Vandaag
> **Mijn gevoel vanochtend:** *"{athlete_notes if athlete_notes else 'Geen opmerkingen ingevoerd.'}"*
> 
> {ai_result.get('coach_verdict', '')}

---

## 🎯 Trainingskeuzes voor Vandaag
*Kies zelf waar je vandaag zin in hebt of wat fysiek het beste voelt:*

### 🚴‍♂️ Optie 1: Fietsen (Doel: 5min / 20min vermogen)
* **Training:** **{cycling.get('session_title', 'Geen training beschikbaar')}**
* **Intensiteit:** `{cycling.get('intensity', '-')}`
* **Workout details:** {cycling.get('workout_details', '-')}
* **Waarom:** *{cycling.get('reason', '-')}*

### 🏃‍♂️ Optie 2: Hardlopen (Doel: 5km snelheid)
* **Training:** **{running.get('session_title', 'Geen training beschikbaar')}**
* **Intensiteit:** `{running.get('intensity', '-')}`
* **Workout details:** {running.get('workout_details', '-')}
* **Waarom:** *{running.get('reason', '-')}*

### 🧘‍♂️ Optie 3: Actief herstel / Rust
* **Training:** **{recovery.get('session_title', 'Geen training beschikbaar')}**
* **Intensiteit:** `{recovery.get('intensity', '-')}`
* **Workout details:** {recovery.get('workout_details', '-')}
* **Waarom:** *{recovery.get('reason', '-')}*

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
