import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime, timedelta

# --- 1. Initialization and Setup ---
app = FastAPI(
    title="Space Weather AI Alert API",
    description="Backend for the AI Solar Storm Alert App."
)

# CORS Middleware - wichtig für Frontend-Zugriff
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In Produktion einschränken
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. Data Source URLs and Keys ---
NASA_API_KEY = os.getenv("NASA_API_KEY")

# NOAA/NASA Data Endpoints
NOAA_KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
NASA_GST_URL = "https://api.nasa.gov/DONKI/GST"

# Apertus Inference Endpoint
APERTUS_INFERENCE_URL = os.getenv(
    "APERTUS_INFERENCE_URL", 
    "https://api-inference.huggingface.co/models/swiss-ai/Apertus-8B-Instruct-2509"
)
APERTUS_API_KEY = os.getenv("APERTUS_API_KEY")


# --- 3. Root Endpoint (Health Check) ---
@app.get("/")
def read_root():
    """Health check endpoint - zeigt dass die API läuft."""
    return {
        "status": "online",
        "message": "Space Weather AI Alert API is running!",
        "endpoints": {
            "health": "/",
            "alert": "/alert/?profile=General%20Public"
        }
    }


# --- 4. Data Fetching Functions ---

def fetch_space_weather_data():
    """Fetches key indices and alerts from NOAA and NASA."""
    
    # Kp-Index (NOAA)
    try:
        kp_response = requests.get(NOAA_KP_URL, timeout=10)
        kp_response.raise_for_status()
        kp_data = kp_response.json()
        
        # KORRIGIERTE LOGIK: NOAA gibt eine Liste von Listen zurück!
        # Format: [["time_tag","Kp","a_running","station_count"], ["2025-12-09...", "1.33", "5", "7"], ...]
        # Die erste Zeile ist der Header, die letzte Zeile sind die aktuellsten Daten
        # Index 1 ist der Kp-Wert
        
        if kp_data and isinstance(kp_data, list) and len(kp_data) > 1:
            # Letzte Datenzeile holen (nicht den Header)
            latest_row = kp_data[-1]
            # Index 1 ist der Kp-Wert
            latest_kp = latest_row[1] if len(latest_row) > 1 else "N/A"
        else:
            latest_kp = "N/A (Data empty)"
            
    except requests.exceptions.RequestException as e:
        latest_kp = f"N/A (Fetch Error: {str(e)[:50]})"
    except (IndexError, TypeError) as e:
        latest_kp = f"N/A (Parse Error: {str(e)[:50]})"
    
    
    # GST Alerts (NASA DONKI)
    today = datetime.now()
    seven_days_ago = today - timedelta(days=7)
    
    gst_params = {
        "startDate": seven_days_ago.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
        "api_key": NASA_API_KEY
    }
    
    try:
        gst_response = requests.get(NASA_GST_URL, params=gst_params, timeout=10)
        gst_response.raise_for_status()
        gst_alerts = gst_response.json()
        
        # Summarize alerts for the LLM prompt
        alert_summary = "No recent GST alerts."
        if gst_alerts and isinstance(gst_alerts, list) and len(gst_alerts) > 0:
            # Finde den Alert mit dem höchsten Kp-Index
            latest_gst = max(gst_alerts, key=lambda x: x.get('kpIndex', 0) if isinstance(x, dict) else 0)
            if isinstance(latest_gst, dict):
                alert_summary = f"Geomagnetic Storm (GST) Alert. Max Kp observed: {latest_gst.get('kpIndex', 'N/A')}"
            
    except requests.exceptions.RequestException:
        alert_summary = "Alert data unavailable."
    except Exception:
        alert_summary = "Alert data parse error."

    return {
        "kp_index": latest_kp,
        "alert_summary": alert_summary,
    }


# --- 5. Main API Endpoint (The Brain) ---

@app.get("/alert/")
def get_ai_alert(profile: str = "General Public"):
    """
    Retrieves space weather data and asks Apertus to generate a tailored alert.
    """
    
    # 5.1. Key validation
    if not APERTUS_API_KEY:
        raise HTTPException(
            status_code=503, 
            detail="Apertus API Key not set. Check Render Environment Variables."
        )

    try:
        # 5.2. Fetch raw data
        raw_data = fetch_space_weather_data()
        
        kp = raw_data['kp_index']
        alerts = raw_data['alert_summary']
        
        # 5.3. Construct the Apertus Prompt
        llm_prompt = (
            f"You are the 'AI Solar Storm Alert & Protection App'. Your goal is to translate "
            f"complex space weather data into simple, actionable advice tailored to a specific user profile. "
            f"Current Space Weather Data: Kp-index is {kp}. Active Alerts: {alerts}. "
            f"User Profile: {profile}. "
            f"Task: "
            f"1. Generate a **Risk Level** (Low, Medium, or High) for the user's activities. "
            f"2. Provide a **Specific Recommendation** (1-2 sentences) relevant to their profile. "
            f"3. Output ONLY a clean JSON object with keys 'risk' and 'advice'."
        )
        
        # 5.4. Call Apertus API
        headers = {
            "Authorization": f"Bearer {APERTUS_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Hugging Face Inference API Format
        payload = {
            "inputs": llm_prompt,  # HF verwendet "inputs", nicht "prompt"
            "parameters": {
                "max_new_tokens": 200,
                "return_full_text": False
            }
        }
        
        apertus_response = requests.post(
            APERTUS_INFERENCE_URL, 
            json=payload, 
            headers=headers,
            timeout=30
        )
        apertus_response.raise_for_status() 
        
        # 5.5. Process and Return the AI Response
        return {
            "status": "success",
            "raw_data": raw_data, 
            "ai_output": apertus_response.json()
        }
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500, 
            detail=f"External API error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Internal processing error: {str(e)}"
        )


# --- 6. Debug Endpoint ---
@app.get("/debug/")
def debug_info():
    """Debug endpoint to check configuration and data sources."""
    return {
        "nasa_api_key_set": bool(NASA_API_KEY),
        "apertus_api_key_set": bool(APERTUS_API_KEY),
        "noaa_url": NOAA_KP_URL,
        "test_data": fetch_space_weather_data()
    }


# --- 7. Local Development Entry Point ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)
