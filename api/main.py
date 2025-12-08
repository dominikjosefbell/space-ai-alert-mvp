import os
from fastapi import FastAPI, HTTPException
from urllib.parse import urlencode
import requests
from datetime import datetime, timedelta

# --- 1. Initialization and Setup ---
app = FastAPI(
    title="Space Weather AI Alert API",
    description="Backend for the AI Solar Storm Alert App (App 4)."
)

# NOTE: The PORT is handled by the Render 'gunicorn' Start Command.
# The app is designed to run in the Render environment.

# --- 2. Data Source URLs and Keys ---
# NOAA/NASA data is free for commercial use, but requires a NASA API key.
# Get your own key at api.nasa.gov.
NASA_API_KEY = os.getenv("NASA_API_KEY")

# Verified NOAA/NASA Data Endpoints (Free and Commercially Available)
NOAA_KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json" # Real-time Kp index
NASA_GST_URL = "https://api.nasa.gov/DONKI/GST" # Geomagnetic Storm (GST) Alerts
NASA_CME_URL = "https://api.nasa.gov/DONKI/CME" # Coronal Mass Ejection (CME) Alerts

# Apertus Inference Endpoint (Placeholder - You must replace this!)
# NOTE: Apertus is open-source, but you need an *inference provider's* endpoint (e.g., Swisscom/Public AI/your own deployed instance).
APERTUS_INFERENCE_URL = "https://api-inference.huggingface.co/models/swiss-ai/Apertus-8B-Instruct-2509"
APERTUS_API_KEY = os.getenv("APERTUS_API_KEY")


# --- 3. Data Fetching Functions ---

def fetch_space_weather_data():
    """Fetches key indices and alerts from NOAA and NASA."""
    
    # Kp-Index (NOAA)
    # Fetches a list, we take the last (most recent) entry.
    kp_response = requests.get(NOAA_KP_URL, timeout=5)
    kp_response.raise_for_status() 
    kp_data = kp_response.json()
    latest_kp = kp_data[-1]['kp'] if kp_data else "N/A"
    
    # GST Alerts (NASA DONKI)
    # Query for the last 7 days of alerts.
    today = datetime.now()
    seven_days_ago = today - timedelta(days=7)
    
    gst_params = {
        "startDate": seven_days_ago.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
        "api_key": NASA_API_KEY
    }
    
    gst_response = requests.get(NASA_GST_URL, params=gst_params, timeout=5)
    gst_response.raise_for_status()
    gst_alerts = gst_response.json()
    
    # Summarize alerts for the LLM prompt
    alert_summary = "No recent GST alerts."
    if gst_alerts:
        # Get the highest G-scale alert in the last 7 days
        latest_gst = max(gst_alerts, key=lambda x: x.get('kpIndex', 0))
        alert_summary = f"Geomagnetic Storm (GST) Alert. Max Kp observed: {latest_gst.get('kpIndex', 'N/A')}"

    return {
        "kp_index": latest_kp,
        "alert_summary": alert_summary,
    }

# --- 4. Main API Endpoint (The Brain) ---

@app.get("/alert/")
def get_ai_alert(profile: str):
    """
    Retrieves space weather data and asks Apertus to generate a tailored alert.
    
    :param profile: The user's activity profile (e.g., "Drone Pilot", "Aurora Hunter").
    """
    
    # 4.1. Key and URL validation
    if not APERTUS_API_KEY or APERTUS_INFERENCE_URL.startswith("YOUR_"):
        # This will happen if you forget to set the API Key in Render's Environment Variables
        raise HTTPException(
            status_code=503, 
            detail="Apertus service configuration error. Check API Key and URL."
        )

    try:
        # 4.2. Fetch raw data
        raw_data = fetch_space_weather_data()
        kp = raw_data['kp_index']
        alerts = raw_data['alert_summary']
        
        # 4.3. Construct the Apertus Prompt (The Instruction)
        # This is the most important part! Be very clear and ask for JSON output.
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
        
        # NOTE: The exact JSON body depends on your Apertus provider, but typically includes 'prompt'
        payload = {
            "prompt": llm_prompt,
            "max_tokens": 200,
            # Add any other required parameters (e.g., 'model_name')
        }
        
        apertus_response = requests.post(
            APERTUS_INFERENCE_URL, 
            json=payload, 
            headers=headers,
            timeout=10 # Set a timeout so the app doesn't hang
        )
        apertus_response.raise_for_status() 
        
        # 4.5. Process and Return the AI Response
        # This step depends on how your Apertus provider wraps the JSON response.
        # You may need to extract the text and then parse the inner JSON string.
        # For simplicity, we assume the response text is the JSON object requested in the prompt.
        
        # *** You will likely need to adjust this section based on the real API response! ***
        
        # If the API returns the JSON directly:
        ai_output = apertus_response.json()
        return {"data_source": raw_data, "ai_result": ai_output}
        
    except requests.exceptions.RequestException as e:
        # Handle failures connecting to NOAA/NASA or Apertus
        raise HTTPException(status_code=500, detail=f"External data source error: {e}")
    except Exception as e:
        # Handle general errors (e.g., JSON parsing failure if the LLM output is messy)
        raise HTTPException(status_code=500, detail=f"Internal processing error: {e}")


# --- 5. Debugging/Testing Entry Point (Render uses gunicorn, but helpful for local testing) ---
# This is usually not needed when using gunicorn on Render, but keeps the code complete.
if __name__ == "__main__":
    # Get port from environment or default to 8000
    port = int(os.environ.get("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)
