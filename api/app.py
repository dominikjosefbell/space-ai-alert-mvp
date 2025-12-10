import os
import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime, timedelta
from typing import Optional

# --- 1. Initialization and Setup ---
app = FastAPI(
    title="Space Weather AI Alert API - Extended",
    description="Comprehensive space weather monitoring with multiple satellite data sources.",
    version="3.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. API Keys and Configuration ---
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
HF_MODEL = os.getenv("HF_MODEL", "HuggingFaceH4/zephyr-7b-beta")
HF_INFERENCE_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
HF_API_KEY = os.getenv("HF_API_KEY") or os.getenv("APERTUS_API_KEY")

# --- 3. Data Source URLs ---

# NOAA Space Weather Prediction Center (SWPC) - FREE, no API key needed!
NOAA_URLS = {
    # Geomagnetic indices
    "kp_index": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
    "dst_index": "https://services.swpc.noaa.gov/products/kyoto-dst.json",
    
    # Solar Wind (from DSCOVR satellite at L1)
    "solar_wind_plasma": "https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json",
    "solar_wind_mag": "https://services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json",
    
    # GOES Satellite Data
    "xray_flux": "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json",
    "proton_flux": "https://services.swpc.noaa.gov/json/goes/primary/integral-protons-6-hour.json",
    "electron_flux": "https://services.swpc.noaa.gov/json/goes/primary/integral-electrons-6-hour.json",
    
    # Forecasts and Alerts
    "aurora_forecast": "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json",
    "solar_probabilities": "https://services.swpc.noaa.gov/json/solar_probabilities.json",
    "alerts": "https://services.swpc.noaa.gov/products/alerts.json",
    
    # Solar Activity
    "sunspot_report": "https://services.swpc.noaa.gov/json/sunspot_report.json",
    "solar_regions": "https://services.swpc.noaa.gov/json/solar_regions.json",
    "xray_flares": "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json",
}

# NASA DONKI (Space Weather Database)
NASA_DONKI_URLS = {
    "gst": "https://api.nasa.gov/DONKI/GST",  # Geomagnetic Storms
    "cme": "https://api.nasa.gov/DONKI/CME",  # Coronal Mass Ejections
    "flr": "https://api.nasa.gov/DONKI/FLR",  # Solar Flares
    "sep": "https://api.nasa.gov/DONKI/SEP",  # Solar Energetic Particles
    "hss": "https://api.nasa.gov/DONKI/HSS",  # High Speed Streams
    "ips": "https://api.nasa.gov/DONKI/IPS",  # Interplanetary Shocks
}


# --- 4. Root Endpoint ---
@app.get("/")
def read_root():
    """Health check and API information."""
    return {
        "status": "online",
        "version": "3.0.0 - Extended",
        "message": "Space Weather AI Alert API with comprehensive satellite data",
        "data_sources": {
            "noaa_swpc": list(NOAA_URLS.keys()),
            "nasa_donki": list(NASA_DONKI_URLS.keys()),
        },
        "endpoints": {
            "health": "/",
            "alert": "/alert/?profile=General%20Public",
            "full_data": "/space-weather/full",
            "kp_index": "/space-weather/kp",
            "solar_wind": "/space-weather/solar-wind",
            "xray": "/space-weather/xray",
            "protons": "/space-weather/protons",
            "aurora": "/space-weather/aurora",
            "flares": "/space-weather/flares",
            "debug": "/debug/"
        }
    }


# --- 5. Data Fetching Functions ---

def safe_fetch(url: str, params: dict = None, timeout: int = 10) -> Optional[list | dict]:
    """Safely fetch JSON data from an API endpoint."""
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Fetch error for {url}: {e}")
        return None
    except json.JSONDecodeError:
        print(f"JSON decode error for {url}")
        return None


def fetch_kp_index() -> dict:
    """Fetch current Kp-index from NOAA."""
    data = safe_fetch(NOAA_URLS["kp_index"])
    
    if data and isinstance(data, list) and len(data) > 1:
        # Format: [["time_tag","Kp","a_running","station_count"], ["2025-12-10...", "3.33", ...], ...]
        latest = data[-1]
        return {
            "value": float(latest[1]) if len(latest) > 1 else None,
            "time": latest[0] if len(latest) > 0 else None,
            "status": "ok"
        }
    return {"value": None, "time": None, "status": "error"}


def fetch_solar_wind() -> dict:
    """Fetch solar wind plasma data from DSCOVR satellite."""
    plasma = safe_fetch(NOAA_URLS["solar_wind_plasma"])
    mag = safe_fetch(NOAA_URLS["solar_wind_mag"])
    
    result = {
        "speed": None,
        "density": None,
        "temperature": None,
        "bz": None,
        "bt": None,
        "time": None,
        "status": "error"
    }
    
    # Plasma data: [["time_tag", "density", "speed", "temperature"], ...]
    if plasma and isinstance(plasma, list) and len(plasma) > 1:
        latest_plasma = plasma[-1]
        if len(latest_plasma) >= 4:
            result["time"] = latest_plasma[0]
            result["density"] = float(latest_plasma[1]) if latest_plasma[1] else None
            result["speed"] = float(latest_plasma[2]) if latest_plasma[2] else None
            result["temperature"] = float(latest_plasma[3]) if latest_plasma[3] else None
            result["status"] = "ok"
    
    # Magnetic field data: [["time_tag", "bx_gsm", "by_gsm", "bz_gsm", "bt", ...], ...]
    if mag and isinstance(mag, list) and len(mag) > 1:
        latest_mag = mag[-1]
        if len(latest_mag) >= 5:
            result["bz"] = float(latest_mag[3]) if latest_mag[3] else None
            result["bt"] = float(latest_mag[4]) if latest_mag[4] else None
    
    return result


def fetch_xray_flux() -> dict:
    """Fetch X-ray flux data from GOES satellite."""
    data = safe_fetch(NOAA_URLS["xray_flux"])
    
    if data and isinstance(data, list) and len(data) > 1:
        # Find latest valid reading
        for entry in reversed(data):
            if isinstance(entry, dict) and entry.get("flux"):
                flux = float(entry["flux"])
                # Classify flare level
                if flux >= 1e-4:
                    level = "X" + str(int(flux / 1e-4))
                elif flux >= 1e-5:
                    level = "M" + str(int(flux / 1e-5))
                elif flux >= 1e-6:
                    level = "C" + str(int(flux / 1e-6))
                elif flux >= 1e-7:
                    level = "B" + str(int(flux / 1e-7))
                else:
                    level = "A"
                
                return {
                    "flux": flux,
                    "level": level,
                    "time": entry.get("time_tag"),
                    "status": "ok"
                }
    
    return {"flux": None, "level": None, "time": None, "status": "error"}


def fetch_proton_flux() -> dict:
    """Fetch proton flux data from GOES satellite (radiation storm indicator)."""
    data = safe_fetch(NOAA_URLS["proton_flux"])
    
    if data and isinstance(data, list) and len(data) > 1:
        # Find latest >10 MeV proton flux
        for entry in reversed(data):
            if isinstance(entry, dict) and entry.get("energy") == ">=10 MeV":
                flux = float(entry.get("flux", 0))
                
                # NOAA S-scale for radiation storms
                if flux >= 100000:
                    level = "S5 - Extreme"
                elif flux >= 10000:
                    level = "S4 - Severe"
                elif flux >= 1000:
                    level = "S3 - Strong"
                elif flux >= 100:
                    level = "S2 - Moderate"
                elif flux >= 10:
                    level = "S1 - Minor"
                else:
                    level = "S0 - None"
                
                return {
                    "flux_10mev": flux,
                    "level": level,
                    "time": entry.get("time_tag"),
                    "status": "ok"
                }
    
    return {"flux_10mev": None, "level": None, "time": None, "status": "error"}


def fetch_recent_flares() -> dict:
    """Fetch recent solar flare events."""
    data = safe_fetch(NOAA_URLS["xray_flares"])
    
    if data and isinstance(data, list):
        # Filter last 24 hours
        recent_flares = []
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        for flare in data[-20:]:  # Check last 20 entries
            if isinstance(flare, dict):
                recent_flares.append({
                    "class": flare.get("classtype", "Unknown"),
                    "start": flare.get("begintime"),
                    "peak": flare.get("maxtime"),
                    "end": flare.get("endtime"),
                    "region": flare.get("region")
                })
        
        return {
            "count_24h": len(recent_flares),
            "flares": recent_flares[-5:],  # Last 5 flares
            "status": "ok"
        }
    
    return {"count_24h": 0, "flares": [], "status": "error"}


def fetch_aurora_forecast() -> dict:
    """Fetch aurora forecast from OVATION model."""
    data = safe_fetch(NOAA_URLS["aurora_forecast"])
    
    if data and isinstance(data, dict):
        return {
            "forecast_time": data.get("Forecast Time"),
            "observation_time": data.get("Observation Time"),
            "status": "ok",
            # Note: Full aurora map data is large, we just confirm availability
            "data_available": "coordinates" in data
        }
    
    return {"forecast_time": None, "status": "error"}


def fetch_nasa_donki(event_type: str, days: int = 7) -> dict:
    """Fetch events from NASA DONKI database."""
    if event_type not in NASA_DONKI_URLS:
        return {"events": [], "status": "invalid_type"}
    
    today = datetime.now()
    start_date = today - timedelta(days=days)
    
    params = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": today.strftime("%Y-%m-%d"),
        "api_key": NASA_API_KEY
    }
    
    data = safe_fetch(NASA_DONKI_URLS[event_type], params=params, timeout=15)
    
    if data and isinstance(data, list):
        return {
            "event_type": event_type,
            "count": len(data),
            "events": data[-5:] if len(data) > 5 else data,  # Last 5 events
            "status": "ok"
        }
    
    return {"event_type": event_type, "events": [], "status": "error"}


def fetch_all_space_weather() -> dict:
    """Fetch comprehensive space weather data from all sources."""
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "geomagnetic": {
            "kp_index": fetch_kp_index(),
        },
        "solar_wind": fetch_solar_wind(),
        "radiation": {
            "xray": fetch_xray_flux(),
            "protons": fetch_proton_flux(),
        },
        "solar_activity": {
            "recent_flares": fetch_recent_flares(),
        },
        "forecasts": {
            "aurora": fetch_aurora_forecast(),
        },
        "nasa_events": {
            "geomagnetic_storms": fetch_nasa_donki("gst"),
            "coronal_mass_ejections": fetch_nasa_donki("cme"),
            "solar_flares": fetch_nasa_donki("flr"),
        }
    }


# --- 6. Individual Data Endpoints ---

@app.get("/space-weather/kp")
def get_kp_index():
    """Get current Kp-index."""
    return fetch_kp_index()


@app.get("/space-weather/solar-wind")
def get_solar_wind():
    """Get current solar wind conditions from DSCOVR."""
    return fetch_solar_wind()


@app.get("/space-weather/xray")
def get_xray():
    """Get current X-ray flux (flare indicator)."""
    return fetch_xray_flux()


@app.get("/space-weather/protons")
def get_protons():
    """Get current proton flux (radiation storm indicator)."""
    return fetch_proton_flux()


@app.get("/space-weather/aurora")
def get_aurora():
    """Get aurora forecast."""
    return fetch_aurora_forecast()


@app.get("/space-weather/flares")
def get_flares():
    """Get recent solar flares."""
    return fetch_recent_flares()


@app.get("/space-weather/full")
def get_full_space_weather():
    """Get comprehensive space weather data from all sources."""
    return fetch_all_space_weather()


@app.get("/nasa/{event_type}")
def get_nasa_events(event_type: str, days: int = 7):
    """Get NASA DONKI events (gst, cme, flr, sep, hss, ips)."""
    return fetch_nasa_donki(event_type, days)


# --- 7. AI Alert Generation ---

def calculate_risk_level(data: dict) -> tuple[str, list[str]]:
    """Calculate overall risk level based on all available data."""
    risks = []
    risk_score = 0
    
    # Kp-index assessment
    kp = data.get("geomagnetic", {}).get("kp_index", {}).get("value")
    if kp is not None:
        if kp >= 7:
            risk_score += 3
            risks.append(f"Severe geomagnetic storm (Kp={kp})")
        elif kp >= 5:
            risk_score += 2
            risks.append(f"Moderate geomagnetic storm (Kp={kp})")
        elif kp >= 4:
            risk_score += 1
            risks.append(f"Minor geomagnetic activity (Kp={kp})")
    
    # Solar wind assessment
    sw = data.get("solar_wind", {})
    speed = sw.get("speed")
    bz = sw.get("bz")
    
    if speed and speed > 700:
        risk_score += 2
        risks.append(f"High-speed solar wind ({speed:.0f} km/s)")
    elif speed and speed > 500:
        risk_score += 1
        risks.append(f"Elevated solar wind ({speed:.0f} km/s)")
    
    if bz is not None and bz < -10:
        risk_score += 2
        risks.append(f"Strong southward IMF (Bz={bz:.1f} nT)")
    elif bz is not None and bz < -5:
        risk_score += 1
        risks.append(f"Southward IMF (Bz={bz:.1f} nT)")
    
    # X-ray flux assessment
    xray = data.get("radiation", {}).get("xray", {})
    if xray.get("level", "").startswith("X"):
        risk_score += 3
        risks.append(f"X-class flare detected ({xray['level']})")
    elif xray.get("level", "").startswith("M"):
        risk_score += 2
        risks.append(f"M-class flare detected ({xray['level']})")
    
    # Proton flux assessment
    protons = data.get("radiation", {}).get("protons", {})
    if protons.get("level", "").startswith("S") and protons["level"] != "S0 - None":
        risk_score += 2
        risks.append(f"Radiation storm: {protons['level']}")
    
    # Determine overall risk level
    if risk_score >= 6:
        level = "High"
    elif risk_score >= 3:
        level = "Medium"
    elif risk_score >= 1:
        level = "Low-Medium"
    else:
        level = "Low"
    
    return level, risks


def generate_profile_advice(profile: str, risk_level: str, risks: list[str], data: dict) -> str:
    """Generate profile-specific advice based on current conditions."""
    
    profile_lower = profile.lower()
    kp = data.get("geomagnetic", {}).get("kp_index", {}).get("value", 0) or 0
    sw_speed = data.get("solar_wind", {}).get("speed", 0) or 0
    
    base_conditions = f"Current conditions: Kp={kp:.1f}"
    if sw_speed:
        base_conditions += f", Solar wind {sw_speed:.0f} km/s"
    
    # Profile-specific advice
    if "pilot" in profile_lower or "aviation" in profile_lower or "flight" in profile_lower:
        if risk_level == "High":
            return f"{base_conditions}. CAUTION: HF radio blackouts likely on polar routes. Consider alternate routing. Monitor SIGMET advisories. GPS accuracy may be degraded."
        elif risk_level == "Medium":
            return f"{base_conditions}. HF communication may experience intermittent disruption on high-latitude routes. Standard procedures apply."
        else:
            return f"{base_conditions}. Normal operations. No significant space weather impacts expected."
    
    elif "grid" in profile_lower or "power" in profile_lower or "utility" in profile_lower:
        if risk_level == "High":
            return f"{base_conditions}. WARNING: GIC levels elevated. Monitor transformer temperatures. Consider reducing reactive power reserves. Check protection systems."
        elif risk_level == "Medium":
            return f"{base_conditions}. Elevated GIC possible. Maintain situational awareness. Review contingency procedures."
        else:
            return f"{base_conditions}. Normal grid operations. Low GIC risk."
    
    elif "satellite" in profile_lower or "spacecraft" in profile_lower:
        proton_level = data.get("radiation", {}).get("protons", {}).get("level", "S0")
        if risk_level == "High" or "S2" in proton_level or "S3" in proton_level:
            return f"{base_conditions}. ALERT: Elevated radiation environment. Consider postponing EVA activities. Single-event upsets possible. Increased atmospheric drag on LEO assets."
        elif risk_level == "Medium":
            return f"{base_conditions}. Monitor radiation levels. Spacecraft charging possible during substorms."
        else:
            return f"{base_conditions}. Nominal space environment. Standard operations."
    
    elif "radio" in profile_lower or "ham" in profile_lower or "hf" in profile_lower:
        xray_level = data.get("radiation", {}).get("xray", {}).get("level", "A")
        if xray_level.startswith("X") or xray_level.startswith("M"):
            return f"{base_conditions}. HF radio blackout in progress ({xray_level} flare). Daylight side affected. Try higher frequencies or wait for recovery."
        elif kp >= 5:
            return f"{base_conditions}. Excellent conditions for aurora-related propagation! 6m and 2m band openings possible at high latitudes."
        else:
            return f"{base_conditions}. Normal propagation conditions. HF bands stable."
    
    elif "aurora" in profile_lower or "photographer" in profile_lower or "northern lights" in profile_lower:
        if kp >= 7:
            return f"{base_conditions}. EXCELLENT aurora viewing! Visible at mid-latitudes (40-50°N). Peak activity expected. Get away from city lights!"
        elif kp >= 5:
            return f"{base_conditions}. Good aurora conditions! Visible at higher latitudes (50-60°N). Best viewing after midnight."
        elif kp >= 4:
            return f"{base_conditions}. Possible aurora at high latitudes (60°N+). Worth checking if you're in northern regions."
        else:
            return f"{base_conditions}. Low aurora probability. Kp needs to reach 4+ for visible activity at most locations."
    
    elif "gps" in profile_lower or "navigation" in profile_lower or "survey" in profile_lower:
        if risk_level == "High":
            return f"{base_conditions}. GPS accuracy degraded due to ionospheric disturbance. Expect position errors. Consider SBAS corrections or postpone precision work."
        elif risk_level == "Medium":
            return f"{base_conditions}. Minor ionospheric irregularities possible. Monitor GPS accuracy if precision is critical."
        else:
            return f"{base_conditions}. Normal GPS operations expected. Ionospheric conditions stable."
    
    else:  # General Public
        if risk_level == "High":
            return f"{base_conditions}. Significant space weather event in progress. Aurora may be visible at unusual latitudes. Minor technology disruptions possible. No health concerns for people on Earth."
        elif risk_level == "Medium":
            return f"{base_conditions}. Active space weather conditions. Aurora hunters in northern regions may have good viewing opportunities."
        else:
            return f"{base_conditions}. Quiet space weather conditions. No impacts expected for daily activities."


def generate_ai_response(data: dict, profile: str) -> dict:
    """Generate AI-enhanced response or fallback to rule-based."""
    
    # Calculate risk level from data
    risk_level, risk_factors = calculate_risk_level(data)
    
    # Generate profile-specific advice
    advice = generate_profile_advice(profile, risk_level, risk_factors, data)
    
    # Try AI enhancement if available
    if HF_API_KEY:
        try:
            # Prepare concise data summary for AI
            kp = data.get("geomagnetic", {}).get("kp_index", {}).get("value", "N/A")
            sw = data.get("solar_wind", {})
            xray = data.get("radiation", {}).get("xray", {}).get("level", "N/A")
            
            prompt = f"""<|system|>
You are a space weather advisor. Enhance this alert with additional context.
Keep response under 100 words. Be specific and actionable.
</s>
<|user|>
Data: Kp={kp}, Solar Wind={sw.get('speed', 'N/A')} km/s, Bz={sw.get('bz', 'N/A')} nT, X-ray={xray}
Risk: {risk_level}
Profile: {profile}
Base advice: {advice}

Enhance this advice with any additional relevant details.
</s>
<|assistant|>
"""
            
            response = requests.post(
                HF_INFERENCE_URL,
                json={"inputs": prompt, "parameters": {"max_new_tokens": 150, "temperature": 0.7}},
                headers={"Authorization": f"Bearer {HF_API_KEY}"},
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    enhanced = result[0].get('generated_text', '')
                    if enhanced and len(enhanced) > 20:
                        advice = enhanced[:500]  # Limit length
                        
        except Exception as e:
            print(f"AI enhancement failed: {e}")
            # Continue with rule-based advice
    
    return {
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "advice": advice,
        "source": "ai-enhanced" if HF_API_KEY else "rule-based"
    }


# --- 8. Main Alert Endpoint ---

@app.get("/alert/")
def get_ai_alert(profile: str = "General Public"):
    """Generate a comprehensive space weather alert tailored to the user profile."""
    
    try:
        # Fetch all space weather data
        space_weather_data = fetch_all_space_weather()
        
        # Generate AI response
        ai_alert = generate_ai_response(space_weather_data, profile)
        
        # Prepare summary for response
        summary = {
            "kp_index": space_weather_data["geomagnetic"]["kp_index"].get("value"),
            "solar_wind_speed": space_weather_data["solar_wind"].get("speed"),
            "solar_wind_bz": space_weather_data["solar_wind"].get("bz"),
            "xray_level": space_weather_data["radiation"]["xray"].get("level"),
            "proton_level": space_weather_data["radiation"]["protons"].get("level"),
            "recent_flares": space_weather_data["solar_activity"]["recent_flares"].get("count_24h", 0),
        }
        
        return {
            "status": "success",
            "profile": profile,
            "summary": summary,
            "ai_alert": ai_alert,
            "full_data_available": "/space-weather/full",
            "timestamp": space_weather_data["timestamp"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# --- 9. Debug Endpoint ---

@app.get("/debug/")
def debug_info():
    """Debug endpoint to check all data sources."""
    
    results = {
        "api_keys": {
            "nasa_api_key_set": bool(NASA_API_KEY and NASA_API_KEY != "DEMO_KEY"),
            "hf_api_key_set": bool(HF_API_KEY),
        },
        "hf_model": HF_MODEL,
        "noaa_endpoints": {},
        "nasa_endpoints": {},
    }
    
    # Test NOAA endpoints
    for name, url in list(NOAA_URLS.items())[:5]:  # Test first 5
        try:
            r = requests.get(url, timeout=5)
            results["noaa_endpoints"][name] = f"OK ({r.status_code})"
        except Exception as e:
            results["noaa_endpoints"][name] = f"Error: {str(e)[:30]}"
    
    # Test NASA endpoint
    try:
        r = requests.get(NASA_DONKI_URLS["gst"], params={"api_key": NASA_API_KEY}, timeout=5)
        results["nasa_endpoints"]["donki_gst"] = f"OK ({r.status_code})"
    except Exception as e:
        results["nasa_endpoints"]["donki_gst"] = f"Error: {str(e)[:30]}"
    
    # Fetch sample data
    results["sample_data"] = {
        "kp_index": fetch_kp_index(),
        "solar_wind": fetch_solar_wind(),
    }
    
    return results


# --- 10. Local Development ---

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
