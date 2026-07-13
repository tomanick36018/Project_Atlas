import json
import os
import sys
from datetime import datetime
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# 1. Definieer de structuur van de output
class SessionOption(BaseModel):
    session_title: str = Field(description="Short title, e.g., 'Sweet Spot Intervals' or 'Easy Aerobic Run'")
    intensity: str = Field(description="Target intensity level or zone (e.g., 'Zone 3 (Sweet Spot)', 'Zone 1-2 (Endurance)', 'VO2max')")
    workout_details: str = Field(description="Specific detailed session, e.g., 'Cycling: 3x10min at 220-230W (Zone 3) with 5min recovery' or 'Running: 5x1000m @ 5km pace with 2min walking recovery'")
    reason: str = Field(description="Physiological justification focusing on the specific target (5km run, 5min power, or 20min power) and how it fits the current training status.")

class TodayOptions(BaseModel):
    cycling_option: SessionOption = Field(description="Recommended session if the athlete chooses Cycling today")
    running_option: SessionOption = Field(description="Recommended session if the athlete chooses Running today")
    recovery_option: SessionOption = Field(description="Recommended session if the athlete chooses Rest or Recovery today")

class CoachAssessmentSchema(BaseModel):
    daily_load_assessment: str = Field(description="Analysis of immediate, daily training stress and recovery status based on recent workouts.")
    acute_status_assessment_3_weeks: str = Field(description="Evaluation of the 3-week (21 days) acute training status, block volume, and recent fatigue accumulation.")
    sport_trend_assessment_6_months: str = Field(description="Analysis of the long-term (6 months / 180 days) fitness trend, CTL ramp rate, and progression towards primary goals.")
    coach_verdict: str = Field(description="Direct coach feedback addressing the athlete's qualitative notes (e.g., HRV, fatigue, sleep) and recommending which option to prioritize today.")
    today_options: TodayOptions

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

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY niet ingesteld.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # De prompt is specifiek ingericht op de drie vensters: 1 dag, 3 weken en 6 maanden
    prompt = f"""
    You are an expert, data-driven sports coach. Your athlete wants to optimize their rising fitness trend (CTL) safely and effectively.

    You must analyze and evaluate the athlete's progress through three distinct time horizons:
    1. DAILY HORIZON (Per dag): Analyze immediate training stress, daily load, and today's recovery state to guide immediate session design.
    2. 3-WEEK HORIZON (Actuele status / 21 days): Treat this as the acute training status. Evaluate recent block volume, fatigue accumulation (ATL), and adaptation rate over the last 3 weeks.
    3. 6-MONTH HORIZON (Sporttrend / 180 days): Treat this as the long-term sport trend. Evaluate macro progression, CTL ramp rate (fitness build), and seasonal progress.

    ATHLETE GOALS:
    - Running: 5km performance (pace, VO2max, interval quality).
    - Cycling: 5-minute power (VO2max capacity) and 20-minute power (FTP/threshold endurance).

    TODAY'S ATHLETE INPUT:
    - Preferred Sport: {sport_preference}
    - Athlete Notes (HRV, sleep, soreness, feeling): "{athlete_notes if athlete_notes else 'No notes provided today. Focus purely on training data.'}"

    ATHLETE TRAINING DATA (Intervals.icu):
    {json.dumps(coach_input, indent=2)}

    COACH INSTRUCTIONS:
    - Strictly evaluate each of the three time horizons (Daily, 3-Week, 6-Month) in your assessment.
    - Directly address the athlete's subjective notes (HRV, soreness, etc.) in your verdict.
    - Generate THREE distinct options for today (Cycling, Running, and Recovery/Rest) so the athlete can choose.
    - Ensure the Cycling option targets FTP (20-min power) or VO2max (5-min power), the Running option targets 5km performance, and the Recovery option supports active recovery.
    - Be direct, strict, and precise. Give specific power targets (Watts) or heart rate zones (BPM) based on the athlete's FTP and Max HR.
    """

    print("Gegevens worden naar Gemini gestuurd voor gerichte 1-dag / 3-weken / 6-maanden analyse...")
    
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CoachAssessmentSchema,
        ),
    )

    ai_result = json.loads(response.text)

    # Laad de fitness state in die we via create_coach_input hebben toegevoegd
    fitness_state = coach_input.get("fitness_state", {})
    ctl = fitness_state.get("CTL", 0)
    atl = fitness_state.get("ATL", 0)

    analysis = {
        "generated": str(datetime.now()),
        "athlete_inputs": {
            "sport_preference": sport_preference,
            "athlete_notes": athlete_notes
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

    # 1. Sla JSON op voor eventueel dashboardgebruik
    with open("data/coach_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)

    # 2. Genereer een overzichtelijke README.md homepage
    tsb = round(ctl - atl, 1)
    # Bepaal visuele weergave van de TSB-status (kleur)
    if tsb < -30:
         tsb_status = "⚠️ Hoog Risico (TSB onder -30)"
    elif tsb <= -3.2: # op basis van -10% tot -30% van CTL (31.8)
         tsb_status = "🟢 Optimaal Trainingsvenster"
    else:
         tsb_status = "🔵 Fris / Herstel"

    readme_content = f"""# 🏃‍♂️ Mijn AI Sportcoach Dashboard

*Laatst bijgewerkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📊 Actuele Trainingsstatus (Lopend Gemiddelde)
* **Fitheid (CTL - 42 dagen):** `{round(ctl, 1)}`
* **Vermoeidheid (ATL - 7 dagen):** `{round(atl, 1)}`
* **Vorm / Balans (TSB):** `{tsb}`
* **Status:** **{tsb_status}**

---

## 📋 Coach Verdict & Advies voor Vandaag
> **Gevoel / Input van vandaag:** *"{athlete_notes if athlete_notes else 'Geen opmerkingen ingevoerd.'}"*
> 
> {analysis['coach_verdict']}

---

## 🎯 Trainingskeuzes voor Vandaag
*Kies zelf waar je vandaag zin in hebt of wat fysiek het beste voelt:*

### 🚴‍♂️ Optie 1: Fietsen (Doel: 5min / 20min vermogen)
* **Training:** **{analysis['today_options']['cycling_option']['session_title']}**
* **Intensiteit:** `{analysis['today_options']['cycling_option']['intensity']}`
* **Workout details:** {analysis['today_options']['cycling_option']['workout_details']}
* **Waarom:** *{analysis['today_options']['cycling_option']['reason']}*

### 🏃‍♂️ Optie 2: Hardlopen (Doel: 5km snelheid)
* **Training:** **{analysis['today_options']['running_option']['session_title']}**
* **Intensiteit:** `{analysis['today_options']['running_option']['intensity']}`
* **Workout details:** {analysis['today_options']['running_option']['workout_details']}
* **Waarom:** *{analysis['today_options']['running_option']['reason']}*

### 🧘‍♂️ Optie 3: Actief herstel / Rust
* **Training:** **{analysis['today_options']['recovery_option']['session_title']}**
* **Intensiteit:** `{analysis['today_options']['recovery_option']['intensity']}`
* **Workout details:** {analysis['today_options']['recovery_option']['workout_details']}
* **Waarom:** *{analysis['today_options']['recovery_option']['reason']}*

---

## 🔍 Diepgaande Trainingsanalyses

### 📅 Dagelijkse Belasting (1-Dag)
{analysis['daily_load_assessment']}

### 📈 Actuele Trainingsstatus (3-Weken)
{analysis['acute_status_assessment_3_weeks']}

### 📊 Algemene Sporttrend (6-Maanden)
{analysis['sport_trend_assessment_6_months']}
"""

    with open("README.md", "w") as f:
        f.write(readme_content)

    print("Gemini coach-analyse met 1D/3W/6M-structuur en README succesvol aangemaakt.")

if __name__ == "__main__":
    main()
