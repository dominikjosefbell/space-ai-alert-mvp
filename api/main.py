import os
import json
from fastapi import FastAPI, HTTPException
from urllib.parse import urlencode
import requests
from datetime import datetime, timedelta

# --- 1. Initialization and Setup ---
app = FastAPI(
    title="Space Weather AI Alert API",
    description="Backend for the AI Solar Storm Alert App (App 4)."
)

# --- 2. Data Source URLs and Keys ---
NASA_API_KEY = os.getenv("NASA_API_KEY")

# Verifizierte NOAA/NASA Data Endpoints
NOAA_KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json" # Real-time Kp index
NASA_GST_URL = "https://api.nasa.gov/DONKI/GST" # Geomagnetic Storm (GST) Alerts
NASA_CME_URL = "https://api.nasa.gov/DONKI/CME" # Coronal Mass Ejection (CME) Alerts

# Apertus Inference Endpoint (Placeholder - Must be corrected)
APERTUS_INFERENCE_URL = os.getenv("APERTUS_INFERENCE_URL", "https://api-inference.huggingface.co/models/swiss-ai/Apertus-8B-Instruct-2509")
APERTUS_API_KEY = os.getenv("APERTUS_API_KEY")


# --- 3. Data Fetching Functions ---

def fetch_space_weather_data():
    """Fetches key indices and alerts from NOAA and NASA."""
    
    # Kp-Index (NOAA)
    try:
        kp_response = requests.get(NOAA_KP_URL, timeout=5)
        kp_response.raise_for_status()
        kp_data = kp_response.json()
        
        # KORREKTUR: Wir stellen sicher, dass kp_data eine nicht leere Liste ist und nehmen das letzte Element.
        if kp_data and isinstance(kp_data, list):
            # Wir verwenden .get() für sicheren Zugriff
            latest_kp = kp_data[-1].get('kp', 'N/A')
        else:
            latest_kp = "N/A (Data empty)"
            
    except requests.exceptions.RequestException:
        latest_kp = "N/A (Fetch Error)"
    
    
    # GST Alerts (NASA DONKI)
    # ... (Rest des GST-Codes bleibt gleich)
    today = datetime.now()
    seven_days_ago = today - timedelta(days=7)
    
    gst_params = {
        "startDate": seven_days_ago.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
        "api_key": NASA_API_KEY
    }
    
    try:
        gst_response = requests.get(NASA_GST_URL, params=gst_params, timeout=5)
        gst_response.raise_for_status()
        gst_alerts = gst_response.json()
        
        # Summarize alerts for the LLM prompt
        alert_summary = "No recent GST alerts."
        if gst_alerts:
            # Get the highest Kp observed in the last 7 days (NASA verwendet hier 'kpIndex')
            latest_gst = max(gst_alerts, key=lambda x: x.get('kpIndex', 0))
            alert_summary = f"Geomagnetic Storm (GST) Alert. Max Kp observed: {latest_gst.get('kpIndex', 'N/A')}"
            
    except requests.exceptions.RequestException:
        alert_summary = "Alert data unavailable."

    # KORREKTUR: Der Key "" wurde durch "kp_index" ersetzt (wichtig für den Aufruf in get_ai_alert)
    return {
        "kp_index": latest_kp,
        "alert_summary": alert_summary,
    }

# --- 4. Main API Endpoint (The Brain) ---

@app.get("/alert/")
def get_ai_alert(profile: str):
    """
    Retrieves space weather data and asks Apertus to generate a tailored alert.
    """
    
    # 4.1. Key and URL validation
    if not APERTUS_API_KEY:
        raise HTTPException(
            status_code=503, 
            detail="Apertus API Key not set. Check Render Environment Variables."
        )

    try:
        # 4.2. Fetch raw data
        raw_data = fetch_space_weather_data()
        
        # KORREKTUR: Zugriff auf den korrigierten Key "kp_index"
        kp = raw_data['kp_index']
        alerts = raw_data['alert_summary']
        
        # 4.3. Construct the Apertus Prompt (The Instruction)
        llm_prompt = (
            f"You are the 'AI Solar Storm Alert & Protection App'. Your goal is to translate "
            f"complex space weather data into simple, actionable advice tailored to a specific user profile. "
            f"Current Space Weather Data: Kp-index is {kp}. Active Alerts: {alerts}. "
            f"User Profile: {profile}. "
            f"Task: "
            f"1. Generate a **Risk Level** (Low, Medium, or High) for the user's activities. "
            f"2. Provide a **Specific Recommendation** (1-2 sentences) relevant to their profile. "
            f"3. Output ONLY a clean JSON object with keys 'risk' and 'advice'."
            f"Example for Drone Pilot (Risk: Medium, Advice: 'GPS accuracy may be degraded. Avoid flying over water or out of sight.')"
        )
        
        # 4.4. Call Apertus API
        headers = {
            "Authorization": f"Bearer {APERTUS_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": llm_prompt,
            "max_tokens": 200,
        }
        
        apertus_response = requests.post(
            APERTUS_INFERENCE_URL, 
            json=payload, 
            headers=headers,
            timeout=10
        )
        apertus_response.raise_for_status() 
        
        # 4.5. Process and Return the AI Response
        # LLM inference APIs usually return an array of results where the output is text.
        
        # Beispielverarbeitung für Hugging Face API:
        # response_data = apertus_response.json()
        # raw_text = response_data[0]['generated_text'] 
        
        # Für diesen Code nehmen wir an, dass die Antwort den JSON-Text direkt im Feld 'generated_text' enthält.
        # WICHTIG: Die Verarbeitung des LLM-Outputs ist der letzte potenziell fehlerhafte Schritt.
        
        # Wir senden die Rohdaten und die AI-Antwort zurück
        
        # HINWEIS: Sie müssen den tatsächlichen LLM-Output des Providers hier parsen (z.B. den JSON-String extrahieren)
        # Zur Vereinfachung senden wir die Rohdaten und die Apertus-Antwort zurück:
        return {"raw_data": raw_data, "ai_output_raw": apertus_response.json()}
        
    except requests.exceptions.RequestException as e:
        # Handle failures connecting to NOAA/NASA or Apertus
        raise HTTPException(status_code=500, detail=f"External data source error: {e}")
    except Exception as e:
        # Handle general errors (z.B. JSON parsing failure)
        raise HTTPException(status_code=500, detail=f"Internal processing error: {e}")


# --- 5. Debugging/Testing Entry Point ---
if __name__ == "__main__":
    import uvicorn
    # Get port from environment or default to 8000
    port = int(os.environ.get("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)
