import os
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
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")

# NOAA/NASA Data Endpoints
NOAA_KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
NASA_GST_URL = "https://api.nasa.gov/DONKI/GST"

# Hugging Face - FUNKTIONIERENDES kostenloses Modell
# Optionen: "google/gemma-2-2b-it", "mistralai/Mistral-7B-Instruct-v0.3", "HuggingFaceH4/zephyr-7b-beta"
HF_MODEL = os.getenv("HF_MODEL", "HuggingFaceH4/zephyr-7b-beta")
HF_INFERENCE_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
HF_API_KEY = os.getenv("HF_API_KEY") or os.getenv("APERTUS_API_KEY")  # Beide Namen akzeptieren


# --- 3. Root Endpoint (Health Check) ---
@app.get("/")
def read_root():
    """Health check endpoint - zeigt dass die API läuft."""
    return {
        "status": "online",
        "message": "Space Weather AI Alert API is running!",
        "model": HF_MODEL,
        "endpoints": {
            "health": "/",
            "alert": "/alert/?profile=General%20Public",
            "debug": "/debug/"
        }
    }


# --- 4. Data Fetching Functions ---

def fetch_space_weather_data():
    """Fetches key indices and alerts from NOAA and NASA."""
    
    # Kp-Index (NOAA)
    latest_kp = "N/A"
    try:
        kp_response = requests.get(NOAA_KP_URL, timeout=10)
        kp_response.raise_for_status()
        kp_data = kp_response.json()
        
        # NOAA gibt eine Liste von Listen zurück!
        # Format: [["time_tag","Kp",...], ["2025-12-09...", "1.33", ...], ...]
        if kp_data and isinstance(kp_data, list) and len(kp_data) > 1:
            latest_row = kp_data[-1]
            latest_kp = latest_row[1] if len(latest_row) > 1 else "N/A"
            
    except requests.exceptions.RequestException as e:
        latest_kp = f"N/A (Error)"
    except (IndexError, TypeError):
        latest_kp = "N/A (Parse Error)"
    
    
    # GST Alerts (NASA DONKI)
    alert_summary = "No recent GST alerts."
    try:
        today = datetime.now()
        seven_days_ago = today - timedelta(days=7)
        
        gst_params = {
            "startDate": seven_days_ago.strftime("%Y-%m-%d"),
            "endDate": today.strftime("%Y-%m-%d"),
            "api_key": NASA_API_KEY
        }
        
        gst_response = requests.get(NASA_GST_URL, params=gst_params, timeout=10)
        gst_response.raise_for_status()
        gst_alerts = gst_response.json()
        
        if gst_alerts and isinstance(gst_alerts, list) and len(gst_alerts) > 0:
            latest_gst = max(gst_alerts, key=lambda x: x.get('kpIndex', 0) if isinstance(x, dict) else 0)
            if isinstance(latest_gst, dict):
                alert_summary = f"GST Alert - Max Kp: {latest_gst.get('kpIndex', 'N/A')}"
            
    except requests.exceptions.RequestException:
        alert_summary = "Alert data unavailable."
    except Exception:
        alert_summary = "Alert parse error."

    return {
        "kp_index": latest_kp,
        "alert_summary": alert_summary,
    }


def generate_ai_response(kp: str, alerts: str, profile: str) -> dict:
    """Generiert AI-Antwort mit Hugging Face oder Fallback."""
    
    # Fallback wenn kein API Key
    if not HF_API_KEY:
        return generate_fallback_response(kp, alerts, profile)
    
    # Prompt für das Modell
    prompt = f"""<|system|>
You are a space weather advisor. Analyze the data and provide a risk assessment.
Respond ONLY with valid JSON: {{"risk": "Low/Medium/High", "advice": "your advice"}}
</s>
<|user|>
Space Weather Data:
- Kp-index: {kp}
- Alerts: {alerts}
- User Profile: {profile}

Provide risk level and specific advice for this user profile.
</s>
<|assistant|>
"""

    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 150,
            "temperature": 0.7,
            "return_full_text": False,
            "do_sample": True
        }
    }
    
    try:
        response = requests.post(
            HF_INFERENCE_URL, 
            json=payload, 
            headers=headers,
            timeout=30
        )
        
        # Model loading - retry after wait
        if response.status_code == 503:
            return {
                "risk": "Unknown",
                "advice": "AI model is loading. Please try again in 20-30 seconds.",
                "status": "model_loading"
            }
        
        response.raise_for_status()
        result = response.json()
        
        # Parse die Antwort
        if isinstance(result, list) and len(result) > 0:
            generated_text = result[0].get('generated_text', '')
        else:
            generated_text = str(result)
        
        # Versuche JSON zu extrahieren
        import json
        import re
        
        # Finde JSON im Text
        json_match = re.search(r'\{[^{}]*"risk"[^{}]*"advice"[^{}]*\}', generated_text, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                return parsed
            except json.JSONDecodeError:
                pass
        
        # Fallback: Gib rohen Text zurück
        return {
            "risk": "Medium",
            "advice": generated_text[:200] if generated_text else "Unable to parse AI response.",
            "raw": generated_text[:500]
        }
        
    except requests.exceptions.RequestException as e:
        # Bei API-Fehler: Intelligenter Fallback
        return generate_fallback_response(kp, alerts, profile)


def generate_fallback_response(kp: str, alerts: str, profile: str) -> dict:
    """Generiert eine regelbasierte Antwort ohne AI."""
    
    # Parse Kp-Index
    try:
        kp_value = float(kp) if kp not in ["N/A", "N/A (Error)", "N/A (Parse Error)"] else 2.0
    except (ValueError, TypeError):
        kp_value = 2.0
    
    # Regelbasierte Risikobewertung
    if kp_value >= 7:
        risk = "High"
        base_advice = "Strong geomagnetic storm in progress. "
    elif kp_value >= 5:
        risk = "Medium"
        base_advice = "Moderate geomagnetic activity. "
    elif kp_value >= 4:
        risk = "Low-Medium"
        base_advice = "Minor geomagnetic activity. "
    else:
        risk = "Low"
        base_advice = "Geomagnetic conditions are quiet. "
    
    # Profilspezifische Empfehlungen
    profile_lower = profile.lower()
    
    if "pilot" in profile_lower or "aviation" in profile_lower:
        advice = base_advice + "HF radio communication may be affected on polar routes. Check NOTAMs for updates."
    elif "grid" in profile_lower or "power" in profile_lower or "utility" in profile_lower:
        advice = base_advice + "Monitor transformer temperatures. GIC levels may increase."
    elif "satellite" in profile_lower or "space" in profile_lower:
        advice = base_advice + "Increased drag on LEO satellites possible. Monitor orbital parameters."
    elif "radio" in profile_lower or "ham" in profile_lower:
        advice = base_advice + ("Great conditions for aurora-related propagation!" if kp_value >= 5 else "Normal propagation expected.")
    elif "aurora" in profile_lower or "photographer" in profile_lower:
        advice = base_advice + (f"Aurora possible at mid-latitudes! Kp {kp_value} suggests good viewing." if kp_value >= 4 else "Aurora viewing unlikely at mid-latitudes.")
    else:
        advice = base_advice + "No significant impacts expected for general public activities."
    
    return {
        "risk": risk,
        "advice": advice,
        "source": "rule-based-fallback"
    }


# --- 5. Main API Endpoint ---

@app.get("/alert/")
def get_ai_alert(profile: str = "General Public"):
    """
    Retrieves space weather data and generates a tailored alert.
    """
    
    try:
        # Fetch raw data
        raw_data = fetch_space_weather_data()
        
        kp = raw_data['kp_index']
        alerts = raw_data['alert_summary']
        
        # Generate AI response (with fallback)
        ai_response = generate_ai_response(kp, alerts, profile)
        
        return {
            "status": "success",
            "profile": profile,
            "space_weather": raw_data,
            "ai_alert": ai_response,
            "model_used": HF_MODEL if HF_API_KEY else "rule-based-fallback"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing request: {str(e)}"
        )


# --- 6. Debug Endpoint ---
@app.get("/debug/")
def debug_info():
    """Debug endpoint to check configuration and test data sources."""
    
    # Test NOAA
    noaa_status = "unknown"
    try:
        r = requests.get(NOAA_KP_URL, timeout=5)
        noaa_status = f"OK ({r.status_code})"
    except Exception as e:
        noaa_status = f"Error: {str(e)[:50]}"
    
    # Test HF
    hf_status = "unknown"
    if HF_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {HF_API_KEY}"}
            r = requests.get(
                f"https://api-inference.huggingface.co/models/{HF_MODEL}",
                headers=headers,
                timeout=5
            )
            hf_status = f"OK ({r.status_code})"
        except Exception as e:
            hf_status = f"Error: {str(e)[:50]}"
    else:
        hf_status = "No API key set"
    
    return {
        "nasa_api_key_set": bool(NASA_API_KEY and NASA_API_KEY != "DEMO_KEY"),
        "hf_api_key_set": bool(HF_API_KEY),
        "hf_model": HF_MODEL,
        "noaa_url": NOAA_KP_URL,
        "noaa_status": noaa_status,
        "hf_status": hf_status,
        "test_data": fetch_space_weather_data()
    }


# --- 7. Local Development Entry Point ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)
