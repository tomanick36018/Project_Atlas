import json
import os
import sys
from datetime import datetime
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# 1. Definieer de structuur die we van Gemini terugverwachten
class TodayRecommendation(BaseModel):
    type: str = Field(description="The type of the suggested session, e.g., 'recovery', 'aerobic base', 'tempo', 'VO2max intervals', or 'rest'")
    session: str = Field(description="Detailed session instructions with specific intervals, zones (power or HR), or duration (e.g., 'Running: 5x1000m @ 5km pace with 2min rest' or 'Cycling: 2h Zone 2 easy endurance')")
    reason: str = Field(description="The physiological or tactical reason for this recommendation today, referencing metrics like ATL, CTL, fatigue levels, and goals")

class CoachAssessmentSchema(BaseModel):
    coach_assessment: str = Field(description="Strict and direct coach analysis of the current fitness trends, fatigue (ATL), fitness (CTL), and progress towards their endurance goals.")
    today_recommendation: TodayRecommendation

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def main():
    # Laad de samengestelde input data
    try:
        coach_input = load_json("data/coach_input.json")
    except FileNotFoundError:
        print("Error: data/coach_input.json niet gevonden. Voer eerst create_coach_input.py uit.")
        sys.exit(1)

    # Controleer of de API-sleutel aanwezig is
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: De omgevingsvariabele GEMINI_API_KEY is niet ingesteld.")
        sys.exit(1)

    # Initialiseer de Gemini-client
    client = genai.Client(api_key=api_key)

    # Stel de prompt op met alle data uit coach_input.json
    prompt = f"""
    You are an expert, data-driven elite sports coach. Your style, priority, and athlete parameters are defined in the input data.
    
    Review the following athlete data from Intervals.icu and other systems:
    {json.dumps(coach_input, indent=2)}

    Perform a professional coach evaluation of the athlete's state.
    Keep in mind:
    - Coach Style: strict, challenge level: high.
    - Priorities: quality intervals, aerobic base, progressive overload, recovery management.
    - Goal: {coach_input.get('goals', 'Improve performance')}
    - Heart Rate Max: {coach_input.get('athlete', {}).get('max_hr', 194)} bpm.
    - FTP: {coach_input.get('performance', {}).get('cycling', {}).get('ftp_watts', 250)} W.

    Please provide your expert coach assessment and today's recommendation in the requested JSON structure.
    """

    print("Gegevens worden naar Gemini gestuurd voor analyse...")
    
    # We gebruiken het stabiele en snelle gemini-2.5-flash model
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CoachAssessmentSchema,
        ),
    )

    # Parse het JSON-resultaat van de AI
    ai_result = json.loads(response.text)

    # Voeg de AI-analyse samen met de rest van de vereiste dashboardstructuur
    block = coach_input.get("current_training_block", {})
    analysis = {
        "generated": str(datetime.now()),
        "athlete": coach_input.get("athlete", {}),
        "current_state": {
            "training_load_21_days": block.get("training_load", 0),
            "CTL": block.get("CTL", 0),
            "ATL": block.get("ATL", 0)
        },
        "coach_assessment": ai_result.get("coach_assessment", ""),
        "today_recommendation": ai_result.get("today_recommendation", {
            "type": "",
            "session": "",
            "reason": ""
        })
    }

    # Sla het resultaat op
    with open("data/coach_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)

    print("Gemini coach-analyse succesvol aangemaakt en opgeslagen.")

if __name__ == "__main__":
    main()
