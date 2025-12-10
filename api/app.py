import os
import json
import re
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime, timedelta
from typing import Optional

# --- 1. Initialization and Setup ---
app = FastAPI(
    title="Space Weather & Environment API - Full Suite",
    description="Comprehensive space weather, air quality, UV index, and environmental monitoring.",
    version="4.0.0"
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

# Default location (Zürich, Switzerland - can be overridden)
DEFAULT_LAT = 47.3769
DEFAULT_LON = 8.5417

# --- 3. Data Source URLs ---

# NOAA Space Weather Prediction Center
NOAA_URLS = {
    "kp_index": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
    "solar_wind_plasma": "https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json",
    "solar_wind_mag": "https://services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json",
    "xray_flux": "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json",
    "proton_flux": "https://services.swpc.noaa.gov/json/goes/primary/integral-protons-6-hour.json",
    "xray_flares": "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json",
}

# NASA DONKI
NASA_DONKI_URLS = {
    "gst": "https://api.nasa.gov/DONKI/GST",
    "cme": "https://api.nasa.gov/DONKI/CME",
    "flr": "https://api.nasa.gov/DONKI/FLR",
    "sep": "https://api.nasa.gov/DONKI/SEP",
}

# Open-Meteo APIs (FREE, no key required!)
OPEN_METEO_URLS = {
    "air_quality": "https://air-quality-api.open-meteo.com/v1/air-quality",
    "weather": "https://api.open-meteo.com/v1/forecast",
    "uv": "https://air-quality-api.open-meteo.com/v1/air-quality",  # UV is in air quality API
}


# --- 4. Root Endpoint ---
@app.get("/")
def read_root():
    """Health check and API overview."""
    return {
        "status": "online",
        "version": "4.0.0 - Full Environmental Suite",
        "message": "Space Weather + Air Quality + UV Index + Weather API",
        "data_sources": {
            "space_weather": ["NOAA SWPC", "NASA DONKI", "GOES Satellites", "DSCOVR"],
            "environment": ["Open-Meteo Air Quality", "Copernicus CAMS", "Open-Meteo Weather"],
        },
        "capabilities": [
            "Real-time Kp-index & geomagnetic activity",
            "Solar wind speed, density, magnetic field",
            "X-ray flux & solar flare detection",
            "Proton flux & radiation storms",
            "Air Quality Index (EU & US standards)",
            "PM2.5, PM10, NO2, O3, SO2, CO",
            "UV Index with health recommendations",
            "Pollen forecast (Europe)",
            "Weather conditions",
        ],
        "endpoints": {
            "alert": "/alert/?profile=General%20Public",
            "environment": "/environment/?lat=47.37&lon=8.54",
            "space_weather": "/space-weather/full",
            "air_quality": "/air-quality/?lat=47.37&lon=8.54",
            "uv_index": "/uv/?lat=47.37&lon=8.54",
            "weather": "/weather/?lat=47.37&lon=8.54",
            "combined": "/combined/?lat=47.37&lon=8.54&profile=General%20Public",
        }
    }


# --- 5. Utility Functions ---

def safe_fetch(url: str, params: dict = None, timeout: int = 10) -> Optional[dict | list]:
    """Safely fetch JSON data from an API endpoint."""
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Fetch error for {url}: {e}")
        return None


# --- 6. Space Weather Functions (from Phase 1) ---

def fetch_kp_index() -> dict:
    """Fetch current Kp-index from NOAA."""
    data = safe_fetch(NOAA_URLS["kp_index"])
    if data and isinstance(data, list) and len(data) > 1:
        latest = data[-1]
        return {
            "value": float(latest[1]) if len(latest) > 1 else None,
            "time": latest[0] if len(latest) > 0 else None,
            "status": "ok"
        }
    return {"value": None, "status": "error"}


def fetch_solar_wind() -> dict:
    """Fetch solar wind plasma data from DSCOVR."""
    plasma = safe_fetch(NOAA_URLS["solar_wind_plasma"])
    mag = safe_fetch(NOAA_URLS["solar_wind_mag"])
    
    result = {"speed": None, "density": None, "bz": None, "status": "error"}
    
    if plasma and isinstance(plasma, list) and len(plasma) > 1:
        latest = plasma[-1]
        if len(latest) >= 4:
            result["speed"] = float(latest[2]) if latest[2] else None
            result["density"] = float(latest[1]) if latest[1] else None
            result["status"] = "ok"
    
    if mag and isinstance(mag, list) and len(mag) > 1:
        latest = mag[-1]
        if len(latest) >= 5:
            result["bz"] = float(latest[3]) if latest[3] else None
    
    return result


def fetch_xray_flux() -> dict:
    """Fetch X-ray flux from GOES."""
    data = safe_fetch(NOAA_URLS["xray_flux"])
    if data and isinstance(data, list):
        for entry in reversed(data):
            if isinstance(entry, dict) and entry.get("flux"):
                flux = float(entry["flux"])
                if flux >= 1e-4:
                    level = f"X{int(flux / 1e-4)}"
                elif flux >= 1e-5:
                    level = f"M{int(flux / 1e-5)}"
                elif flux >= 1e-6:
                    level = f"C{int(flux / 1e-6)}"
                else:
                    level = "B"
                return {"flux": flux, "level": level, "status": "ok"}
    return {"flux": None, "level": None, "status": "error"}


def fetch_proton_flux() -> dict:
    """Fetch proton flux from GOES."""
    data = safe_fetch(NOAA_URLS["proton_flux"])
    if data and isinstance(data, list):
        for entry in reversed(data):
            if isinstance(entry, dict) and entry.get("energy") == ">=10 MeV":
                flux = float(entry.get("flux", 0))
                if flux >= 100000: level = "S5 - Extreme"
                elif flux >= 10000: level = "S4 - Severe"
                elif flux >= 1000: level = "S3 - Strong"
                elif flux >= 100: level = "S2 - Moderate"
                elif flux >= 10: level = "S1 - Minor"
                else: level = "S0 - None"
                return {"flux": flux, "level": level, "status": "ok"}
    return {"flux": None, "level": "S0 - None", "status": "error"}


# --- 7. NEW: Air Quality Functions ---

def fetch_air_quality(lat: float, lon: float) -> dict:
    """Fetch air quality data from Open-Meteo (Copernicus CAMS data)."""
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,dust,uv_index",
        "hourly": "pm2_5,pm10,nitrogen_dioxide,ozone",
        "forecast_days": 1,
        "timezone": "auto"
    }
    
    data = safe_fetch(OPEN_METEO_URLS["air_quality"], params=params, timeout=15)
    
    if not data:
        return {"status": "error", "message": "Failed to fetch air quality data"}
    
    current = data.get("current", {})
    
    # Interpret EU AQI
    eu_aqi = current.get("european_aqi", 0)
    if eu_aqi <= 20: eu_category = "Good"
    elif eu_aqi <= 40: eu_category = "Fair"
    elif eu_aqi <= 60: eu_category = "Moderate"
    elif eu_aqi <= 80: eu_category = "Poor"
    elif eu_aqi <= 100: eu_category = "Very Poor"
    else: eu_category = "Extremely Poor"
    
    # Interpret US AQI
    us_aqi = current.get("us_aqi", 0)
    if us_aqi <= 50: us_category = "Good"
    elif us_aqi <= 100: us_category = "Moderate"
    elif us_aqi <= 150: us_category = "Unhealthy for Sensitive Groups"
    elif us_aqi <= 200: us_category = "Unhealthy"
    elif us_aqi <= 300: us_category = "Very Unhealthy"
    else: us_category = "Hazardous"
    
    return {
        "status": "ok",
        "location": {"latitude": lat, "longitude": lon},
        "european_aqi": {
            "value": eu_aqi,
            "category": eu_category
        },
        "us_aqi": {
            "value": us_aqi,
            "category": us_category
        },
        "pollutants": {
            "pm2_5": {"value": current.get("pm2_5"), "unit": "μg/m³"},
            "pm10": {"value": current.get("pm10"), "unit": "μg/m³"},
            "no2": {"value": current.get("nitrogen_dioxide"), "unit": "μg/m³"},
            "o3": {"value": current.get("ozone"), "unit": "μg/m³"},
            "so2": {"value": current.get("sulphur_dioxide"), "unit": "μg/m³"},
            "co": {"value": current.get("carbon_monoxide"), "unit": "μg/m³"},
        },
        "dust": current.get("dust"),
        "time": current.get("time"),
        "data_source": "Copernicus CAMS via Open-Meteo"
    }


def fetch_uv_index(lat: float, lon: float) -> dict:
    """Fetch UV index data."""
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "uv_index,uv_index_clear_sky",
        "hourly": "uv_index",
        "forecast_days": 1,
        "timezone": "auto"
    }
    
    data = safe_fetch(OPEN_METEO_URLS["uv"], params=params, timeout=10)
    
    if not data:
        return {"status": "error"}
    
    current = data.get("current", {})
    uv = current.get("uv_index", 0)
    
    # UV Index categories (WHO standard)
    if uv <= 2:
        category = "Low"
        recommendation = "No protection required. Safe to be outside."
    elif uv <= 5:
        category = "Moderate"
        recommendation = "Wear sunglasses. Use SPF 30+ sunscreen if outside for 30+ minutes."
    elif uv <= 7:
        category = "High"
        recommendation = "Reduce sun exposure 10am-4pm. Wear hat, sunglasses, SPF 30+ sunscreen."
    elif uv <= 10:
        category = "Very High"
        recommendation = "Minimize sun exposure. Seek shade. Protective clothing essential."
    else:
        category = "Extreme"
        recommendation = "Avoid sun exposure. Stay indoors if possible. Maximum protection required."
    
    return {
        "status": "ok",
        "uv_index": round(uv, 1),
        "uv_index_clear_sky": round(current.get("uv_index_clear_sky", 0), 1),
        "category": category,
        "recommendation": recommendation,
        "time": current.get("time"),
        "location": {"latitude": lat, "longitude": lon}
    }


def fetch_pollen(lat: float, lon: float) -> dict:
    """Fetch pollen data (Europe only)."""
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen",
        "timezone": "auto"
    }
    
    data = safe_fetch(OPEN_METEO_URLS["air_quality"], params=params, timeout=10)
    
    if not data:
        return {"status": "error", "message": "Pollen data not available (Europe only)"}
    
    current = data.get("current", {})
    
    def pollen_level(value):
        if value is None: return {"value": None, "level": "N/A"}
        if value < 10: return {"value": value, "level": "Low"}
        if value < 50: return {"value": value, "level": "Moderate"}
        if value < 100: return {"value": value, "level": "High"}
        return {"value": value, "level": "Very High"}
    
    return {
        "status": "ok",
        "pollen": {
            "grass": pollen_level(current.get("grass_pollen")),
            "birch": pollen_level(current.get("birch_pollen")),
            "alder": pollen_level(current.get("alder_pollen")),
            "mugwort": pollen_level(current.get("mugwort_pollen")),
            "olive": pollen_level(current.get("olive_pollen")),
            "ragweed": pollen_level(current.get("ragweed_pollen")),
        },
        "unit": "grains/m³",
        "note": "Pollen data available for Europe only",
        "time": current.get("time")
    }


def fetch_weather(lat: float, lon: float) -> dict:
    """Fetch current weather conditions."""
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m",
        "timezone": "auto"
    }
    
    data = safe_fetch(OPEN_METEO_URLS["weather"], params=params, timeout=10)
    
    if not data:
        return {"status": "error"}
    
    current = data.get("current", {})
    
    # Weather code interpretation (WMO codes)
    weather_codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }
    
    code = current.get("weather_code", 0)
    
    return {
        "status": "ok",
        "temperature": {
            "actual": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "unit": "°C"
        },
        "humidity": current.get("relative_humidity_2m"),
        "precipitation": current.get("precipitation"),
        "weather": {
            "code": code,
            "description": weather_codes.get(code, "Unknown")
        },
        "cloud_cover": current.get("cloud_cover"),
        "wind": {
            "speed": current.get("wind_speed_10m"),
            "direction": current.get("wind_direction_10m"),
            "unit": "km/h"
        },
        "time": current.get("time"),
        "location": {"latitude": lat, "longitude": lon}
    }


# --- 8. API Endpoints ---

@app.get("/space-weather/full")
def get_space_weather():
    """Get comprehensive space weather data."""
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "geomagnetic": {"kp_index": fetch_kp_index()},
        "solar_wind": fetch_solar_wind(),
        "radiation": {
            "xray": fetch_xray_flux(),
            "protons": fetch_proton_flux()
        }
    }


@app.get("/air-quality/")
def get_air_quality(
    lat: float = Query(DEFAULT_LAT, description="Latitude"),
    lon: float = Query(DEFAULT_LON, description="Longitude")
):
    """Get air quality data for a location."""
    return fetch_air_quality(lat, lon)


@app.get("/uv/")
def get_uv(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON)
):
    """Get UV index for a location."""
    return fetch_uv_index(lat, lon)


@app.get("/pollen/")
def get_pollen(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON)
):
    """Get pollen forecast (Europe only)."""
    return fetch_pollen(lat, lon)


@app.get("/weather/")
def get_weather(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON)
):
    """Get current weather conditions."""
    return fetch_weather(lat, lon)


@app.get("/environment/")
def get_environment(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON)
):
    """Get all environmental data for a location."""
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "location": {"latitude": lat, "longitude": lon},
        "air_quality": fetch_air_quality(lat, lon),
        "uv_index": fetch_uv_index(lat, lon),
        "pollen": fetch_pollen(lat, lon),
        "weather": fetch_weather(lat, lon)
    }


# --- 9. Combined Alert Endpoint ---

def calculate_combined_risk(space_data: dict, env_data: dict) -> tuple[str, list[str]]:
    """Calculate risk from both space weather and environmental data."""
    risks = []
    score = 0
    
    # Space weather risks
    kp = space_data.get("geomagnetic", {}).get("kp_index", {}).get("value")
    if kp and kp >= 5:
        score += 2
        risks.append(f"Geomagnetic storm (Kp={kp})")
    
    sw_speed = space_data.get("solar_wind", {}).get("speed")
    if sw_speed and sw_speed > 600:
        score += 1
        risks.append(f"High solar wind ({sw_speed:.0f} km/s)")
    
    xray = space_data.get("radiation", {}).get("xray", {}).get("level", "")
    if xray.startswith("M") or xray.startswith("X"):
        score += 2
        risks.append(f"Solar flare ({xray})")
    
    # Environmental risks
    aqi = env_data.get("air_quality", {}).get("european_aqi", {}).get("value", 0)
    if aqi and aqi > 80:
        score += 2
        risks.append(f"Poor air quality (AQI={aqi})")
    elif aqi and aqi > 60:
        score += 1
        risks.append(f"Moderate air quality (AQI={aqi})")
    
    uv = env_data.get("uv_index", {}).get("uv_index", 0)
    if uv and uv >= 8:
        score += 2
        risks.append(f"Very high UV ({uv})")
    elif uv and uv >= 6:
        score += 1
        risks.append(f"High UV ({uv})")
    
    # Determine level
    if score >= 5: level = "High"
    elif score >= 3: level = "Medium"
    elif score >= 1: level = "Low-Medium"
    else: level = "Low"
    
    return level, risks


def generate_combined_advice(profile: str, space_data: dict, env_data: dict, risk_level: str) -> str:
    """Generate advice based on all data sources."""
    
    kp = space_data.get("geomagnetic", {}).get("kp_index", {}).get("value", 0) or 0
    aqi = env_data.get("air_quality", {}).get("european_aqi", {}).get("value", 0) or 0
    uv = env_data.get("uv_index", {}).get("uv_index", 0) or 0
    temp = env_data.get("weather", {}).get("temperature", {}).get("actual", "N/A")
    
    profile_lower = profile.lower()
    
    # Build advice based on profile
    if "outdoor" in profile_lower or "sport" in profile_lower or "exercise" in profile_lower:
        parts = [f"Current: {temp}°C, UV {uv}, AQI {aqi}."]
        if aqi > 60:
            parts.append("Consider reducing outdoor exercise intensity due to air quality.")
        if uv >= 6:
            parts.append(f"UV is {env_data.get('uv_index', {}).get('category', 'high')} - sun protection essential.")
        if kp >= 5:
            parts.append("Geomagnetic storm may affect GPS accuracy for fitness tracking.")
        return " ".join(parts)
    
    elif "asthma" in profile_lower or "respiratory" in profile_lower or "allergy" in profile_lower:
        pollen = env_data.get("pollen", {}).get("pollen", {})
        parts = [f"Air Quality Index: {aqi} ({env_data.get('air_quality', {}).get('european_aqi', {}).get('category', 'N/A')})."]
        pm25 = env_data.get("air_quality", {}).get("pollutants", {}).get("pm2_5", {}).get("value")
        if pm25:
            parts.append(f"PM2.5: {pm25} μg/m³.")
        if aqi > 60:
            parts.append("Consider staying indoors or wearing N95 mask outdoors.")
        
        # Check pollen levels
        high_pollen = [k for k, v in pollen.items() if v.get("level") in ["High", "Very High"]]
        if high_pollen:
            parts.append(f"High pollen: {', '.join(high_pollen)}.")
        return " ".join(parts)
    
    elif "pilot" in profile_lower or "aviation" in profile_lower:
        parts = [f"Space weather: Kp={kp}."]
        if kp >= 5:
            parts.append("HF radio degradation possible on polar routes.")
        xray = space_data.get("radiation", {}).get("xray", {}).get("level", "")
        if xray.startswith("M") or xray.startswith("X"):
            parts.append(f"Solar flare {xray} - radio blackouts possible.")
        parts.append(f"Surface conditions: {temp}°C, visibility may vary.")
        return " ".join(parts)
    
    else:  # General
        parts = []
        parts.append(f"Weather: {temp}°C, {env_data.get('weather', {}).get('weather', {}).get('description', 'N/A')}.")
        parts.append(f"Air Quality: {env_data.get('air_quality', {}).get('european_aqi', {}).get('category', 'N/A')}.")
        parts.append(f"UV Index: {uv} ({env_data.get('uv_index', {}).get('category', 'N/A')}).")
        if kp >= 4:
            parts.append(f"Space weather active (Kp={kp}) - aurora possible at high latitudes!")
        return " ".join(parts)


@app.get("/combined/")
def get_combined_alert(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    profile: str = Query("General Public")
):
    """Get combined space weather + environmental alert."""
    
    # Fetch all data
    space_data = {
        "geomagnetic": {"kp_index": fetch_kp_index()},
        "solar_wind": fetch_solar_wind(),
        "radiation": {"xray": fetch_xray_flux(), "protons": fetch_proton_flux()}
    }
    
    env_data = {
        "air_quality": fetch_air_quality(lat, lon),
        "uv_index": fetch_uv_index(lat, lon),
        "pollen": fetch_pollen(lat, lon),
        "weather": fetch_weather(lat, lon)
    }
    
    # Calculate risk
    risk_level, risk_factors = calculate_combined_risk(space_data, env_data)
    
    # Generate advice
    advice = generate_combined_advice(profile, space_data, env_data, risk_level)
    
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "location": {"latitude": lat, "longitude": lon},
        "profile": profile,
        "risk": {
            "level": risk_level,
            "factors": risk_factors
        },
        "advice": advice,
        "summary": {
            "kp_index": space_data["geomagnetic"]["kp_index"].get("value"),
            "solar_wind_speed": space_data["solar_wind"].get("speed"),
            "xray_level": space_data["radiation"]["xray"].get("level"),
            "air_quality_aqi": env_data["air_quality"].get("european_aqi", {}).get("value"),
            "uv_index": env_data["uv_index"].get("uv_index"),
            "temperature": env_data["weather"].get("temperature", {}).get("actual"),
        },
        "data": {
            "space_weather": space_data,
            "environment": env_data
        }
    }


@app.get("/alert/")
def get_alert(
    profile: str = Query("General Public"),
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON)
):
    """Legacy alert endpoint - now includes environmental data."""
    return get_combined_alert(lat=lat, lon=lon, profile=profile)


# --- 10. Debug Endpoint ---

@app.get("/debug/")
def debug_info():
    """Debug endpoint."""
    return {
        "api_keys": {
            "nasa": bool(NASA_API_KEY and NASA_API_KEY != "DEMO_KEY"),
            "huggingface": bool(HF_API_KEY)
        },
        "default_location": {"lat": DEFAULT_LAT, "lon": DEFAULT_LON},
        "test_space": fetch_kp_index(),
        "test_air": fetch_air_quality(DEFAULT_LAT, DEFAULT_LON),
        "test_uv": fetch_uv_index(DEFAULT_LAT, DEFAULT_LON)
    }


# --- 11. Local Development ---

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
