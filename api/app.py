import os
import json
import re
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime, timedelta
from typing import Optional, List

# --- 1. Initialization and Setup ---
app = FastAPI(
    title="Space Weather & Environmental Monitoring API",
    description="Comprehensive monitoring: Space Weather, Air Quality, UV, Weather, Natural Events, Floods",
    version="5.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. Configuration ---
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
HF_MODEL = os.getenv("HF_MODEL", "HuggingFaceH4/zephyr-7b-beta")
HF_INFERENCE_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
HF_API_KEY = os.getenv("HF_API_KEY") or os.getenv("APERTUS_API_KEY")

DEFAULT_LAT = 47.3769
DEFAULT_LON = 8.5417

# --- 3. Data Source URLs ---

NOAA_URLS = {
    "kp_index": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
    "solar_wind_plasma": "https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json",
    "solar_wind_mag": "https://services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json",
    "xray_flux": "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json",
    "proton_flux": "https://services.swpc.noaa.gov/json/goes/primary/integral-protons-6-hour.json",
    "xray_flares": "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json",
    "alerts": "https://services.swpc.noaa.gov/products/alerts.json",
}

NASA_URLS = {
    "eonet_events": "https://eonet.gsfc.nasa.gov/api/v3/events",
    "eonet_categories": "https://eonet.gsfc.nasa.gov/api/v3/categories",
    "donki_gst": "https://api.nasa.gov/DONKI/GST",
    "donki_cme": "https://api.nasa.gov/DONKI/CME",
    "donki_flr": "https://api.nasa.gov/DONKI/FLR",
}

OPEN_METEO_URLS = {
    "air_quality": "https://air-quality-api.open-meteo.com/v1/air-quality",
    "weather": "https://api.open-meteo.com/v1/forecast",
    "flood": "https://flood-api.open-meteo.com/v1/flood",
    "marine": "https://marine-api.open-meteo.com/v1/marine",
}


# --- 4. Root Endpoint ---
@app.get("/")
def read_root():
    return {
        "status": "online",
        "version": "5.0.0 - Complete Environmental Suite",
        "capabilities": [
            "Space Weather (Kp, Solar Wind, X-Ray, Protons)",
            "Air Quality (PM2.5, PM10, NO2, O3, SO2, CO)",
            "UV Index with health recommendations",
            "Pollen forecast (Europe)",
            "Current weather conditions",
            "Natural disaster events (NASA EONET)",
            "Flood/River discharge forecasts",
            "Marine conditions (waves, sea temp)",
        ],
        "endpoints": {
            "combined_alert": "/alert/?lat=47.37&lon=8.54&profile=General%20Public",
            "space_weather": "/space-weather/",
            "environment": "/environment/?lat=47.37&lon=8.54",
            "natural_events": "/natural-events/",
            "floods": "/floods/?lat=47.37&lon=8.54",
            "marine": "/marine/?lat=47.37&lon=8.54",
            "all_data": "/all/?lat=47.37&lon=8.54",
        }
    }


# --- 5. Utility Functions ---

def safe_fetch(url: str, params: dict = None, timeout: int = 10) -> Optional[dict | list]:
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Fetch error for {url}: {e}")
        return None


# --- 6. Space Weather Functions ---

def fetch_kp_index() -> dict:
    data = safe_fetch(NOAA_URLS["kp_index"])
    if data and isinstance(data, list) and len(data) > 1:
        latest = data[-1]
        return {"value": float(latest[1]) if latest[1] else None, "time": latest[0], "status": "ok"}
    return {"value": None, "status": "error"}


def fetch_solar_wind() -> dict:
    plasma = safe_fetch(NOAA_URLS["solar_wind_plasma"])
    mag = safe_fetch(NOAA_URLS["solar_wind_mag"])
    result = {"speed": None, "density": None, "bz": None, "bt": None, "status": "error"}
    
    if plasma and isinstance(plasma, list) and len(plasma) > 1:
        latest = plasma[-1]
        if len(latest) >= 4:
            result["speed"] = float(latest[2]) if latest[2] else None
            result["density"] = float(latest[1]) if latest[1] else None
            result["temperature"] = float(latest[3]) if latest[3] else None
            result["status"] = "ok"
    
    if mag and isinstance(mag, list) and len(mag) > 1:
        latest = mag[-1]
        if len(latest) >= 5:
            result["bz"] = float(latest[3]) if latest[3] else None
            result["bt"] = float(latest[4]) if latest[4] else None
    return result


def fetch_xray_flux() -> dict:
    data = safe_fetch(NOAA_URLS["xray_flux"])
    if data:
        for entry in reversed(data):
            if isinstance(entry, dict) and entry.get("flux"):
                flux = float(entry["flux"])
                if flux >= 1e-4: level = f"X{int(flux / 1e-4)}"
                elif flux >= 1e-5: level = f"M{int(flux / 1e-5)}"
                elif flux >= 1e-6: level = f"C{int(flux / 1e-6)}"
                else: level = "B"
                return {"flux": flux, "level": level, "time": entry.get("time_tag"), "status": "ok"}
    return {"flux": None, "level": None, "status": "error"}


def fetch_proton_flux() -> dict:
    data = safe_fetch(NOAA_URLS["proton_flux"])
    if data:
        for entry in reversed(data):
            if isinstance(entry, dict) and entry.get("energy") == ">=10 MeV":
                flux = float(entry.get("flux", 0))
                if flux >= 100000: level = "S5-Extreme"
                elif flux >= 10000: level = "S4-Severe"
                elif flux >= 1000: level = "S3-Strong"
                elif flux >= 100: level = "S2-Moderate"
                elif flux >= 10: level = "S1-Minor"
                else: level = "S0-None"
                return {"flux": flux, "level": level, "status": "ok"}
    return {"flux": None, "level": "S0-None", "status": "error"}


def fetch_recent_flares() -> dict:
    data = safe_fetch(NOAA_URLS["xray_flares"])
    if data and isinstance(data, list):
        flares = [{"class": f.get("classtype"), "time": f.get("maxtime"), "region": f.get("region")} 
                  for f in data[-10:] if isinstance(f, dict)]
        return {"count": len(flares), "recent": flares[-5:], "status": "ok"}
    return {"count": 0, "recent": [], "status": "error"}


# --- 7. Environmental Functions ---

def fetch_air_quality(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat, "longitude": lon,
        "current": "european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,dust,uv_index",
        "timezone": "auto"
    }
    data = safe_fetch(OPEN_METEO_URLS["air_quality"], params=params, timeout=15)
    if not data: return {"status": "error"}
    
    current = data.get("current", {})
    eu_aqi = current.get("european_aqi", 0)
    us_aqi = current.get("us_aqi", 0)
    
    eu_cat = "Good" if eu_aqi <= 20 else "Fair" if eu_aqi <= 40 else "Moderate" if eu_aqi <= 60 else "Poor" if eu_aqi <= 80 else "Very Poor" if eu_aqi <= 100 else "Hazardous"
    us_cat = "Good" if us_aqi <= 50 else "Moderate" if us_aqi <= 100 else "Unhealthy-Sensitive" if us_aqi <= 150 else "Unhealthy" if us_aqi <= 200 else "Very Unhealthy" if us_aqi <= 300 else "Hazardous"
    
    return {
        "status": "ok",
        "european_aqi": {"value": eu_aqi, "category": eu_cat},
        "us_aqi": {"value": us_aqi, "category": us_cat},
        "pollutants": {
            "pm2_5": current.get("pm2_5"),
            "pm10": current.get("pm10"),
            "no2": current.get("nitrogen_dioxide"),
            "o3": current.get("ozone"),
            "so2": current.get("sulphur_dioxide"),
            "co": current.get("carbon_monoxide"),
        },
        "dust": current.get("dust"),
        "time": current.get("time")
    }


def fetch_uv_index(lat: float, lon: float) -> dict:
    params = {"latitude": lat, "longitude": lon, "current": "uv_index,uv_index_clear_sky", "timezone": "auto"}
    data = safe_fetch(OPEN_METEO_URLS["air_quality"], params=params)
    if not data: return {"status": "error"}
    
    current = data.get("current", {})
    uv = current.get("uv_index", 0) or 0
    
    if uv <= 2: cat, rec = "Low", "No protection needed"
    elif uv <= 5: cat, rec = "Moderate", "Wear sunglasses, SPF 30+"
    elif uv <= 7: cat, rec = "High", "Reduce sun exposure, hat & sunscreen"
    elif uv <= 10: cat, rec = "Very High", "Minimize outdoor time, seek shade"
    else: cat, rec = "Extreme", "Avoid sun, stay indoors if possible"
    
    return {"status": "ok", "uv_index": round(uv, 1), "category": cat, "recommendation": rec, "time": current.get("time")}


def fetch_pollen(lat: float, lon: float) -> dict:
    params = {"latitude": lat, "longitude": lon, "current": "alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen", "timezone": "auto"}
    data = safe_fetch(OPEN_METEO_URLS["air_quality"], params=params)
    if not data: return {"status": "error", "note": "Europe only"}
    
    current = data.get("current", {})
    def level(v): return "Low" if v is None or v < 10 else "Moderate" if v < 50 else "High" if v < 100 else "Very High"
    
    return {
        "status": "ok",
        "pollen": {
            "grass": {"value": current.get("grass_pollen"), "level": level(current.get("grass_pollen"))},
            "birch": {"value": current.get("birch_pollen"), "level": level(current.get("birch_pollen"))},
            "alder": {"value": current.get("alder_pollen"), "level": level(current.get("alder_pollen"))},
            "ragweed": {"value": current.get("ragweed_pollen"), "level": level(current.get("ragweed_pollen"))},
        },
        "note": "Europe only, seasonal"
    }


def fetch_weather(lat: float, lon: float) -> dict:
    params = {"latitude": lat, "longitude": lon, "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,pressure_msl", "timezone": "auto"}
    data = safe_fetch(OPEN_METEO_URLS["weather"], params=params)
    if not data: return {"status": "error"}
    
    current = data.get("current", {})
    codes = {0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 51: "Light drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Rain showers", 95: "Thunderstorm"}
    
    return {
        "status": "ok",
        "temperature": {"value": current.get("temperature_2m"), "feels_like": current.get("apparent_temperature"), "unit": "°C"},
        "humidity": current.get("relative_humidity_2m"),
        "precipitation": current.get("precipitation"),
        "weather": codes.get(current.get("weather_code", 0), "Unknown"),
        "cloud_cover": current.get("cloud_cover"),
        "wind": {"speed": current.get("wind_speed_10m"), "direction": current.get("wind_direction_10m")},
        "pressure": current.get("pressure_msl"),
        "time": current.get("time")
    }


# --- 8. Natural Events (NASA EONET) ---

def fetch_natural_events(limit: int = 20, category: str = None) -> dict:
    params = {"status": "open", "limit": limit}
    if category:
        params["category"] = category
    
    data = safe_fetch(NASA_URLS["eonet_events"], params=params, timeout=15)
    if not data: return {"status": "error", "events": []}
    
    events = []
    for event in data.get("events", [])[:limit]:
        geometry = event.get("geometry", [{}])[-1] if event.get("geometry") else {}
        events.append({
            "id": event.get("id"),
            "title": event.get("title"),
            "category": event.get("categories", [{}])[0].get("title") if event.get("categories") else None,
            "date": geometry.get("date"),
            "coordinates": geometry.get("coordinates"),
            "sources": [s.get("url") for s in event.get("sources", [])][:2]
        })
    
    # Count by category
    categories = {}
    for e in events:
        cat = e.get("category", "Other")
        categories[cat] = categories.get(cat, 0) + 1
    
    return {
        "status": "ok",
        "total": len(events),
        "by_category": categories,
        "events": events
    }


def fetch_nearby_events(lat: float, lon: float, radius_km: float = 500) -> dict:
    """Find natural events near a location"""
    all_events = fetch_natural_events(limit=50)
    if all_events.get("status") != "ok":
        return all_events
    
    nearby = []
    for event in all_events.get("events", []):
        coords = event.get("coordinates")
        if coords and len(coords) >= 2:
            # Simple distance calculation (approximate)
            event_lon, event_lat = coords[0], coords[1]
            dist = ((lat - event_lat) ** 2 + (lon - event_lon) ** 2) ** 0.5 * 111  # rough km
            if dist <= radius_km:
                event["distance_km"] = round(dist, 1)
                nearby.append(event)
    
    nearby.sort(key=lambda x: x.get("distance_km", 9999))
    
    return {
        "status": "ok",
        "location": {"lat": lat, "lon": lon},
        "radius_km": radius_km,
        "count": len(nearby),
        "events": nearby[:10]
    }


# --- 9. Flood Data ---

def fetch_flood_data(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat, "longitude": lon,
        "daily": "river_discharge,river_discharge_mean,river_discharge_max",
        "forecast_days": 7
    }
    data = safe_fetch(OPEN_METEO_URLS["flood"], params=params, timeout=15)
    if not data: return {"status": "error", "note": "No river data for this location"}
    
    daily = data.get("daily", {})
    discharge = daily.get("river_discharge", [])
    times = daily.get("time", [])
    
    if not discharge or all(d is None for d in discharge):
        return {"status": "no_data", "note": "No major river at this location"}
    
    # Find peak
    max_discharge = max((d for d in discharge if d), default=0)
    avg_discharge = sum((d for d in discharge if d), 0) / max(len([d for d in discharge if d]), 1)
    
    # Simple flood risk assessment
    if max_discharge > avg_discharge * 3:
        risk = "High"
    elif max_discharge > avg_discharge * 2:
        risk = "Moderate"
    elif max_discharge > avg_discharge * 1.5:
        risk = "Low"
    else:
        risk = "None"
    
    forecast = [{"date": t, "discharge": d} for t, d in zip(times, discharge) if d]
    
    return {
        "status": "ok",
        "river_discharge": {
            "current": discharge[0] if discharge else None,
            "max_forecast": max_discharge,
            "average": round(avg_discharge, 1),
            "unit": "m³/s"
        },
        "flood_risk": risk,
        "forecast_days": forecast[:7]
    }


# --- 10. Marine Data ---

def fetch_marine_data(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat, "longitude": lon,
        "current": "wave_height,wave_direction,wave_period,swell_wave_height,sea_level_pressure_msl",
        "hourly": "wave_height",
        "forecast_days": 2
    }
    data = safe_fetch(OPEN_METEO_URLS["marine"], params=params, timeout=15)
    if not data: return {"status": "error", "note": "No marine data (location not near coast)"}
    
    current = data.get("current", {})
    
    wave_height = current.get("wave_height")
    if wave_height is None:
        return {"status": "no_data", "note": "Location not near coast"}
    
    # Wave danger assessment
    if wave_height > 4: danger = "Dangerous"
    elif wave_height > 2.5: danger = "Rough"
    elif wave_height > 1: danger = "Moderate"
    else: danger = "Calm"
    
    return {
        "status": "ok",
        "waves": {
            "height": wave_height,
            "direction": current.get("wave_direction"),
            "period": current.get("wave_period"),
            "unit": "m"
        },
        "swell_height": current.get("swell_wave_height"),
        "sea_conditions": danger,
        "time": current.get("time")
    }


# --- 11. API Endpoints ---

@app.get("/space-weather/")
def get_space_weather():
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "kp_index": fetch_kp_index(),
        "solar_wind": fetch_solar_wind(),
        "xray": fetch_xray_flux(),
        "protons": fetch_proton_flux(),
        "recent_flares": fetch_recent_flares()
    }


@app.get("/environment/")
def get_environment(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON)):
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "location": {"lat": lat, "lon": lon},
        "air_quality": fetch_air_quality(lat, lon),
        "uv_index": fetch_uv_index(lat, lon),
        "pollen": fetch_pollen(lat, lon),
        "weather": fetch_weather(lat, lon)
    }


@app.get("/natural-events/")
def get_natural_events(limit: int = Query(20), category: str = Query(None)):
    """Get active natural events worldwide. Categories: wildfires, severeStorms, volcanoes, seaLakeIce"""
    return fetch_natural_events(limit=limit, category=category)


@app.get("/natural-events/nearby/")
def get_nearby_events(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON), radius: float = Query(500)):
    """Get natural events near a location"""
    return fetch_nearby_events(lat, lon, radius)


@app.get("/floods/")
def get_floods(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON)):
    """Get river discharge and flood forecast"""
    return fetch_flood_data(lat, lon)


@app.get("/marine/")
def get_marine(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON)):
    """Get marine/ocean conditions (coastal locations only)"""
    return fetch_marine_data(lat, lon)


@app.get("/all/")
def get_all_data(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON)):
    """Get ALL available data for a location"""
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "location": {"lat": lat, "lon": lon},
        "space_weather": {
            "kp_index": fetch_kp_index(),
            "solar_wind": fetch_solar_wind(),
            "xray": fetch_xray_flux(),
            "protons": fetch_proton_flux()
        },
        "environment": {
            "air_quality": fetch_air_quality(lat, lon),
            "uv_index": fetch_uv_index(lat, lon),
            "pollen": fetch_pollen(lat, lon),
            "weather": fetch_weather(lat, lon)
        },
        "hazards": {
            "nearby_events": fetch_nearby_events(lat, lon, 1000),
            "flood_risk": fetch_flood_data(lat, lon),
            "marine": fetch_marine_data(lat, lon)
        }
    }


# --- 12. Main Alert Endpoint ---

def calculate_risk(space: dict, env: dict, hazards: dict) -> tuple[str, list]:
    risks = []
    score = 0
    
    # Space weather
    kp = space.get("kp_index", {}).get("value") or 0
    if kp >= 7: score += 3; risks.append(f"Severe geomagnetic storm (Kp={kp})")
    elif kp >= 5: score += 2; risks.append(f"Geomagnetic storm (Kp={kp})")
    
    xray = space.get("xray", {}).get("level", "")
    if xray.startswith("X"): score += 3; risks.append(f"X-class solar flare ({xray})")
    elif xray.startswith("M"): score += 2; risks.append(f"M-class solar flare ({xray})")
    
    # Environment
    aqi = env.get("air_quality", {}).get("european_aqi", {}).get("value") or 0
    if aqi > 80: score += 2; risks.append(f"Poor air quality (AQI {aqi})")
    elif aqi > 60: score += 1; risks.append(f"Moderate air quality (AQI {aqi})")
    
    uv = env.get("uv_index", {}).get("uv_index") or 0
    if uv >= 8: score += 2; risks.append(f"Very high UV ({uv})")
    elif uv >= 6: score += 1; risks.append(f"High UV ({uv})")
    
    # Hazards
    flood = hazards.get("flood_risk", {}).get("flood_risk", "None")
    if flood in ["High", "Moderate"]: score += 2; risks.append(f"Flood risk: {flood}")
    
    nearby = hazards.get("nearby_events", {}).get("count", 0)
    if nearby > 0: 
        events = hazards.get("nearby_events", {}).get("events", [])
        for e in events[:2]:
            risks.append(f"Nearby: {e.get('title', 'Event')}")
        score += nearby
    
    level = "High" if score >= 5 else "Medium" if score >= 3 else "Low-Medium" if score >= 1 else "Low"
    return level, risks


def generate_advice(profile: str, space: dict, env: dict, hazards: dict, risk_level: str) -> str:
    profile_lower = profile.lower()
    weather = env.get("weather", {})
    temp = weather.get("temperature", {}).get("value", "N/A")
    conditions = weather.get("weather", "Unknown")
    aqi = env.get("air_quality", {}).get("european_aqi", {}).get("value", "N/A")
    uv = env.get("uv_index", {}).get("uv_index", 0)
    kp = space.get("kp_index", {}).get("value", 0)
    
    base = f"Current: {temp}°C, {conditions}. "
    
    if "pilot" in profile_lower or "aviation" in profile_lower:
        advice = base + f"Space weather Kp={kp}. "
        if kp >= 5: advice += "HF radio degradation on polar routes possible. "
        xray = space.get("xray", {}).get("level", "")
        if xray.startswith("M") or xray.startswith("X"): advice += f"Solar flare {xray} - monitor for radio blackouts. "
        return advice
    
    elif "asthma" in profile_lower or "respiratory" in profile_lower or "allergy" in profile_lower:
        advice = f"Air Quality: {env.get('air_quality', {}).get('european_aqi', {}).get('category', 'N/A')} (AQI {aqi}). "
        pm25 = env.get("air_quality", {}).get("pollutants", {}).get("pm2_5")
        if pm25: advice += f"PM2.5: {pm25} μg/m³. "
        if aqi and aqi > 60: advice += "Consider limiting outdoor activity. "
        pollen = env.get("pollen", {}).get("pollen", {})
        high = [k for k, v in pollen.items() if isinstance(v, dict) and v.get("level") in ["High", "Very High"]]
        if high: advice += f"High pollen: {', '.join(high)}. "
        return advice
    
    elif "outdoor" in profile_lower or "sport" in profile_lower or "hiking" in profile_lower:
        advice = base
        if uv >= 6: advice += f"UV {uv} ({env.get('uv_index', {}).get('category')}) - sun protection essential. "
        if aqi and aqi > 60: advice += f"Air quality moderate - reduce intense exercise. "
        flood = hazards.get("flood_risk", {}).get("flood_risk")
        if flood in ["High", "Moderate"]: advice += f"⚠️ Flood risk: {flood}. Check local conditions. "
        return advice
    
    elif "aurora" in profile_lower or "northern lights" in profile_lower:
        if kp >= 7: return f"🌌 EXCELLENT! Kp={kp} - Aurora visible at mid-latitudes! Get away from city lights!"
        elif kp >= 5: return f"🌌 Good aurora conditions (Kp={kp}). Best viewing after midnight at higher latitudes."
        elif kp >= 4: return f"Possible aurora at high latitudes (Kp={kp}). Worth checking if you're in northern regions."
        return f"Low aurora probability (Kp={kp}). Need Kp 4+ for visible activity."
    
    else:  # General Public
        advice = base
        advice += f"Air: {env.get('air_quality', {}).get('european_aqi', {}).get('category', 'N/A')}. "
        advice += f"UV: {uv} ({env.get('uv_index', {}).get('category', 'N/A')}). "
        if kp >= 5: advice += f"Space weather active (Kp={kp}). "
        nearby = hazards.get("nearby_events", {}).get("events", [])
        if nearby: advice += f"Active event nearby: {nearby[0].get('title', 'Natural event')}. "
        return advice


@app.get("/alert/")
def get_alert(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    profile: str = Query("General Public")
):
    """Generate comprehensive environmental alert"""
    
    space = {
        "kp_index": fetch_kp_index(),
        "solar_wind": fetch_solar_wind(),
        "xray": fetch_xray_flux(),
        "protons": fetch_proton_flux()
    }
    
    env = {
        "air_quality": fetch_air_quality(lat, lon),
        "uv_index": fetch_uv_index(lat, lon),
        "pollen": fetch_pollen(lat, lon),
        "weather": fetch_weather(lat, lon)
    }
    
    hazards = {
        "nearby_events": fetch_nearby_events(lat, lon, 500),
        "flood_risk": fetch_flood_data(lat, lon)
    }
    
    risk_level, risk_factors = calculate_risk(space, env, hazards)
    advice = generate_advice(profile, space, env, hazards, risk_level)
    
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "location": {"lat": lat, "lon": lon},
        "profile": profile,
        "risk": {"level": risk_level, "factors": risk_factors},
        "advice": advice,
        "summary": {
            "kp_index": space["kp_index"].get("value"),
            "solar_wind_speed": space["solar_wind"].get("speed"),
            "xray_level": space["xray"].get("level"),
            "air_quality": env["air_quality"].get("european_aqi", {}).get("value"),
            "uv_index": env["uv_index"].get("uv_index"),
            "temperature": env["weather"].get("temperature", {}).get("value"),
            "weather": env["weather"].get("weather"),
            "nearby_events": hazards["nearby_events"].get("count", 0),
            "flood_risk": hazards["flood_risk"].get("flood_risk")
        },
        "data": {"space": space, "environment": env, "hazards": hazards}
    }


# --- 13. Debug ---

@app.get("/debug/")
def debug():
    return {
        "apis": {"nasa": bool(NASA_API_KEY != "DEMO_KEY"), "hf": bool(HF_API_KEY)},
        "test_kp": fetch_kp_index(),
        "test_air": fetch_air_quality(DEFAULT_LAT, DEFAULT_LON),
        "test_events": fetch_natural_events(limit=3)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
