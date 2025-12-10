"""
Space Weather & Environmental Monitoring API v7.0
With Apertus AI Integration for Personalized Recommendations

Data Sources:
- NOAA SWPC: Space Weather (Kp, Solar Wind, X-Ray, Protons, Aurora)
- NASA EONET: Natural Events (Wildfires, Volcanoes, Storms)
- USGS: Earthquakes worldwide
- NWS: US Weather Alerts
- Open-Meteo: Weather, Air Quality, UV, Pollen, Floods, Marine

AI Integration:
- Swiss AI Apertus (via Hugging Face / Public AI) for personalized recommendations
- Multilingual support (DE, EN, FR, IT)
- Profile-specific advice generation
"""

import os
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime, timedelta
from typing import Optional, List

# === 1. INITIALIZATION ===

app = FastAPI(
    title="Space Weather & Environmental Monitoring API",
    description="Complete environmental monitoring with AI-powered recommendations",
    version="7.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 2. CONFIGURATION ===

NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
OPEN_METEO_API_KEY = os.getenv("OPEN_METEO_API_KEY")

# Apertus AI Configuration
HF_API_KEY = os.getenv("HF_API_KEY") or os.getenv("APERTUS_API_KEY")
APERTUS_MODEL = "swiss-ai/Apertus-8B-Instruct-2509"
HF_INFERENCE_URL = "https://router.huggingface.co/hf-inference/models"

# Fallback model if Apertus unavailable
FALLBACK_MODEL = "HuggingFaceH4/zephyr-7b-beta"

DEFAULT_LAT = 47.3769  # Zurich
DEFAULT_LON = 8.5417

# === 3. API ENDPOINTS ===

NOAA_URLS = {
    "kp_index": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
    "solar_wind_plasma": "https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json",
    "solar_wind_mag": "https://services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json",
    "xray_flux": "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json",
    "proton_flux": "https://services.swpc.noaa.gov/json/goes/primary/integral-protons-6-hour.json",
    "xray_flares": "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json",
    "aurora": "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json",
}

NASA_URLS = {
    "eonet_events": "https://eonet.gsfc.nasa.gov/api/v3/events",
}

USGS_URLS = {
    "earthquakes_day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
    "earthquakes_significant": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson",
}

OPEN_METEO_URLS = {
    "weather": "https://api.open-meteo.com/v1/forecast",
    "air_quality": "https://air-quality-api.open-meteo.com/v1/air-quality",
    "flood": "https://flood-api.open-meteo.com/v1/flood",
    "marine": "https://marine-api.open-meteo.com/v1/marine",
}


# === 4. UTILITY FUNCTIONS ===

def safe_fetch(url: str, params: dict = None, timeout: int = 10, headers: dict = None) -> Optional[dict | list]:
    """Safely fetch JSON from URL"""
    try:
        h = headers or {}
        h.setdefault("User-Agent", "EnvironmentalMonitor/7.0")
        response = requests.get(url, params=params, timeout=timeout, headers=h)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Fetch error for {url}: {e}")
        return None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two points"""
    from math import radians, sin, cos, sqrt, atan2
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))


# === 5. DATA FETCHING FUNCTIONS ===

def fetch_kp_index() -> dict:
    data = safe_fetch(NOAA_URLS["kp_index"])
    if data and isinstance(data, list) and len(data) > 1:
        latest = data[-1]
        kp = float(latest[1]) if latest[1] else None
        if kp is not None:
            if kp >= 8: level = "Extreme Storm (G4-G5)"
            elif kp >= 7: level = "Severe Storm (G3)"
            elif kp >= 6: level = "Strong Storm (G2)"
            elif kp >= 5: level = "Moderate Storm (G1)"
            elif kp >= 4: level = "Active"
            else: level = "Quiet"
        else:
            level = "Unknown"
        return {"value": kp, "level": level, "time": latest[0], "status": "ok"}
    return {"value": None, "level": "Unknown", "status": "error"}


def fetch_solar_wind() -> dict:
    plasma = safe_fetch(NOAA_URLS["solar_wind_plasma"])
    mag = safe_fetch(NOAA_URLS["solar_wind_mag"])
    result = {"speed": None, "density": None, "bz": None, "bt": None, "status": "error"}
    
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
                return {"flux": flux, "level": level, "status": "ok"}
    return {"flux": None, "level": None, "status": "error"}


def fetch_proton_flux() -> dict:
    data = safe_fetch(NOAA_URLS["proton_flux"])
    if data:
        for entry in reversed(data):
            if isinstance(entry, dict) and entry.get("energy") == ">=10 MeV":
                flux = float(entry.get("flux", 0))
                if flux >= 10000: level = "S4-Severe"
                elif flux >= 1000: level = "S3-Strong"
                elif flux >= 100: level = "S2-Moderate"
                elif flux >= 10: level = "S1-Minor"
                else: level = "S0-None"
                return {"flux": flux, "level": level, "status": "ok"}
    return {"flux": None, "level": "S0-None", "status": "error"}


def fetch_aurora_forecast(lat: float, lon: float) -> dict:
    data = safe_fetch(NOAA_URLS["aurora"], timeout=15)
    if not data:
        return {"status": "error", "probability": 0}
    
    result = {"status": "ok", "probability": 0, "forecast_time": data.get("Forecast Time")}
    
    if "coordinates" in data:
        coords = data["coordinates"]
        min_dist = float('inf')
        lon_check = lon + 360 if lon < 0 else lon
        
        for point in coords:
            if len(point) >= 3:
                dist = abs(point[1] - lat) + abs(point[0] - lon_check)
                if dist < min_dist:
                    min_dist = dist
                    result["probability"] = point[2]
        
        if result["probability"] >= 50: result["visibility"] = "Excellent"
        elif result["probability"] >= 30: result["visibility"] = "Good"
        elif result["probability"] >= 10: result["visibility"] = "Fair"
        else: result["visibility"] = "Low"
    
    return result


def fetch_earthquakes_nearby(lat: float, lon: float, radius_km: float = 500) -> dict:
    data = safe_fetch(USGS_URLS["earthquakes_day"], timeout=15)
    if not data:
        return {"status": "error", "count": 0, "earthquakes": []}
    
    nearby = []
    for eq in data.get("features", []):
        props = eq.get("properties", {})
        coords = eq.get("geometry", {}).get("coordinates", [0, 0, 0])
        
        dist = calculate_distance(lat, lon, coords[1], coords[0])
        if dist <= radius_km:
            nearby.append({
                "magnitude": props.get("mag"),
                "location": props.get("place"),
                "depth_km": coords[2],
                "distance_km": round(dist, 1),
                "time": props.get("time"),
                "tsunami": props.get("tsunami", 0) == 1
            })
    
    nearby.sort(key=lambda x: x.get("distance_km", 9999))
    max_mag = max((eq["magnitude"] for eq in nearby if eq.get("magnitude")), default=None)
    
    return {
        "status": "ok",
        "count": len(nearby),
        "max_magnitude": max_mag,
        "earthquakes": nearby[:10]
    }


def fetch_natural_events_nearby(lat: float, lon: float, radius_km: float = 500) -> dict:
    data = safe_fetch(NASA_URLS["eonet_events"], params={"status": "open", "limit": 50}, timeout=15)
    if not data:
        return {"status": "error", "count": 0, "events": []}
    
    nearby = []
    for event in data.get("events", []):
        geometry = event.get("geometry", [{}])[-1] if event.get("geometry") else {}
        coords = geometry.get("coordinates")
        
        if coords and len(coords) >= 2:
            dist = calculate_distance(lat, lon, coords[1], coords[0])
            if dist <= radius_km:
                nearby.append({
                    "title": event.get("title"),
                    "category": event.get("categories", [{}])[0].get("title") if event.get("categories") else None,
                    "distance_km": round(dist, 1),
                    "date": geometry.get("date")
                })
    
    nearby.sort(key=lambda x: x.get("distance_km", 9999))
    return {"status": "ok", "count": len(nearby), "events": nearby[:10]}


def fetch_weather(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,cloud_cover,wind_speed_10m,wind_gusts_10m",
        "timezone": "auto"
    }
    if OPEN_METEO_API_KEY:
        params["apikey"] = OPEN_METEO_API_KEY
    
    data = safe_fetch(OPEN_METEO_URLS["weather"], params=params)
    if not data:
        return {"status": "error"}
    
    current = data.get("current", {})
    codes = {0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog",
             51: "Light drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
             71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Rain showers", 95: "Thunderstorm"}
    
    return {
        "status": "ok",
        "temperature": current.get("temperature_2m"),
        "feels_like": current.get("apparent_temperature"),
        "humidity": current.get("relative_humidity_2m"),
        "precipitation": current.get("precipitation"),
        "weather": codes.get(current.get("weather_code", 0), "Unknown"),
        "weather_code": current.get("weather_code"),
        "cloud_cover": current.get("cloud_cover"),
        "wind_speed": current.get("wind_speed_10m"),
        "wind_gusts": current.get("wind_gusts_10m"),
    }


def fetch_air_quality(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat, "longitude": lon,
        "current": "european_aqi,us_aqi,pm10,pm2_5,nitrogen_dioxide,ozone,uv_index",
        "timezone": "auto"
    }
    if OPEN_METEO_API_KEY:
        params["apikey"] = OPEN_METEO_API_KEY
    
    data = safe_fetch(OPEN_METEO_URLS["air_quality"], params=params, timeout=15)
    if not data:
        return {"status": "error"}
    
    current = data.get("current", {})
    eu_aqi = current.get("european_aqi", 0) or 0
    
    if eu_aqi <= 20: category = "Excellent"
    elif eu_aqi <= 40: category = "Good"
    elif eu_aqi <= 60: category = "Moderate"
    elif eu_aqi <= 80: category = "Poor"
    elif eu_aqi <= 100: category = "Very Poor"
    else: category = "Hazardous"
    
    return {
        "status": "ok",
        "eu_aqi": eu_aqi,
        "us_aqi": current.get("us_aqi"),
        "category": category,
        "pm2_5": current.get("pm2_5"),
        "pm10": current.get("pm10"),
        "no2": current.get("nitrogen_dioxide"),
        "ozone": current.get("ozone"),
        "uv_index": current.get("uv_index"),
    }


def fetch_pollen(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat, "longitude": lon,
        "current": "grass_pollen,birch_pollen,alder_pollen,ragweed_pollen",
        "timezone": "auto"
    }
    if OPEN_METEO_API_KEY:
        params["apikey"] = OPEN_METEO_API_KEY
    
    data = safe_fetch(OPEN_METEO_URLS["air_quality"], params=params)
    if not data:
        return {"status": "error"}
    
    current = data.get("current", {})
    
    def level(v):
        if v is None or v < 10: return "Low"
        elif v < 50: return "Moderate"
        elif v < 100: return "High"
        return "Very High"
    
    pollen = {
        "grass": {"value": current.get("grass_pollen"), "level": level(current.get("grass_pollen"))},
        "birch": {"value": current.get("birch_pollen"), "level": level(current.get("birch_pollen"))},
        "alder": {"value": current.get("alder_pollen"), "level": level(current.get("alder_pollen"))},
        "ragweed": {"value": current.get("ragweed_pollen"), "level": level(current.get("ragweed_pollen"))},
    }
    
    high_pollen = [k for k, v in pollen.items() if v["level"] in ["High", "Very High"]]
    
    return {"status": "ok", "pollen": pollen, "high_pollen": high_pollen}


def fetch_flood_risk(lat: float, lon: float) -> dict:
    params = {"latitude": lat, "longitude": lon, "daily": "river_discharge", "forecast_days": 7}
    if OPEN_METEO_API_KEY:
        params["apikey"] = OPEN_METEO_API_KEY
    
    data = safe_fetch(OPEN_METEO_URLS["flood"], params=params, timeout=15)
    if not data:
        return {"status": "error", "risk": "Unknown"}
    
    discharge = data.get("daily", {}).get("river_discharge", [])
    valid = [d for d in discharge if d is not None]
    
    if not valid:
        return {"status": "no_river", "risk": "N/A"}
    
    max_d, avg_d = max(valid), sum(valid) / len(valid)
    
    if max_d > avg_d * 3: risk = "High"
    elif max_d > avg_d * 2: risk = "Moderate"
    elif max_d > avg_d * 1.5: risk = "Low"
    else: risk = "None"
    
    return {"status": "ok", "risk": risk, "current_discharge": valid[0] if valid else None}


def fetch_marine(lat: float, lon: float) -> dict:
    params = {"latitude": lat, "longitude": lon, "current": "wave_height,wave_period,swell_wave_height"}
    if OPEN_METEO_API_KEY:
        params["apikey"] = OPEN_METEO_API_KEY
    
    data = safe_fetch(OPEN_METEO_URLS["marine"], params=params, timeout=15)
    if not data or not data.get("current", {}).get("wave_height"):
        return {"status": "no_coast", "conditions": "N/A"}
    
    current = data.get("current", {})
    wave_h = current.get("wave_height", 0)
    
    if wave_h > 4: cond = "Dangerous"
    elif wave_h > 2.5: cond = "Rough"
    elif wave_h > 1: cond = "Moderate"
    else: cond = "Calm"
    
    return {"status": "ok", "wave_height": wave_h, "conditions": cond}


# === 6. APERTUS AI INTEGRATION ===

def build_ai_prompt(data: dict, profile: str, language: str = "de") -> str:
    """Build a prompt for Apertus to generate personalized recommendations"""
    
    # Language-specific instructions
    lang_instructions = {
        "de": "Antworte auf Deutsch. Sei freundlich und gib konkrete, praktische Empfehlungen.",
        "en": "Answer in English. Be friendly and give concrete, practical recommendations.",
        "fr": "Réponds en français. Sois amical et donne des recommandations concrètes et pratiques.",
        "it": "Rispondi in italiano. Sii amichevole e dai raccomandazioni concrete e pratiche."
    }
    
    # Profile-specific context
    profile_context = {
        "General Public": "für eine normale Person im Alltag",
        "Outdoor/Sports": "für jemanden der heute draussen Sport treiben möchte (Joggen, Wandern, Radfahren)",
        "Asthma/Respiratory": "für jemanden mit Asthma oder Atemwegserkrankungen (achte besonders auf Luftqualität und Pollen)",
        "Pilot/Aviation": "für einen Piloten (achte auf Weltraumwetter, GPS-Störungen, Funkstörungen)",
        "Aurora Hunter": "für jemanden der Nordlichter beobachten möchte",
        "Marine/Sailing": "für jemanden der segeln oder Boot fahren möchte",
        "Allergy": "für jemanden mit Pollenallergie",
    }
    
    context = profile_context.get(profile, profile_context["General Public"])
    
    # Build data summary
    weather = data.get("weather", {})
    air = data.get("air_quality", {})
    space = data.get("space", {})
    eq = data.get("earthquakes", {})
    events = data.get("natural_events", {})
    pollen = data.get("pollen", {})
    flood = data.get("flood", {})
    marine = data.get("marine", {})
    
    data_summary = f"""
AKTUELLE UMWELTDATEN:

Wetter:
- Temperatur: {weather.get('temperature', 'N/A')}°C (gefühlt {weather.get('feels_like', 'N/A')}°C)
- Bedingungen: {weather.get('weather', 'N/A')}
- Luftfeuchtigkeit: {weather.get('humidity', 'N/A')}%
- Wind: {weather.get('wind_speed', 'N/A')} km/h (Böen: {weather.get('wind_gusts', 'N/A')} km/h)

Luftqualität:
- EU AQI: {air.get('eu_aqi', 'N/A')} ({air.get('category', 'N/A')})
- PM2.5: {air.get('pm2_5', 'N/A')} μg/m³
- UV-Index: {air.get('uv_index', 'N/A')}

Pollen:
- Gräser: {pollen.get('pollen', {}).get('grass', {}).get('level', 'N/A')}
- Birke: {pollen.get('pollen', {}).get('birch', {}).get('level', 'N/A')}
- Hohe Pollenbelastung: {', '.join(pollen.get('high_pollen', [])) or 'Keine'}

Weltraumwetter:
- Kp-Index: {space.get('kp', {}).get('value', 'N/A')} ({space.get('kp', {}).get('level', 'N/A')})
- Aurora-Wahrscheinlichkeit: {space.get('aurora', {}).get('probability', 0)}%
- Sonnenaktivität (X-Ray): {space.get('xray', {}).get('level', 'N/A')}

Gefahren:
- Erdbeben in der Nähe (500km): {eq.get('count', 0)} (Max Magnitude: {eq.get('max_magnitude', 'N/A')})
- Naturereignisse in der Nähe: {events.get('count', 0)}
- Hochwasser-Risiko: {flood.get('risk', 'N/A')}
- Seebedingungen: {marine.get('conditions', 'N/A')}
"""

    prompt = f"""Du bist ein freundlicher Umwelt-Assistent. Basierend auf den aktuellen Umweltdaten, gib eine kurze, praktische Empfehlung {context}.

{data_summary}

{lang_instructions.get(language, lang_instructions['de'])}

Wichtig:
- Maximal 3-4 Sätze
- Konkrete Handlungsempfehlungen (z.B. "Nimm Sonnencreme mit", "Ideal zum Joggen", "Bleib heute lieber drinnen")
- Verwende passende Emojis
- Erwähne nur relevante Informationen für das Profil
- Bei Gefahren (Erdbeben, schlechte Luft, Sturm) warne deutlich

Deine Empfehlung:"""

    return prompt


def call_apertus_api(prompt: str) -> Optional[str]:
    """Call Apertus via Hugging Face Inference API"""
    if not HF_API_KEY:
        return None
    
    # Try Apertus first, then fallback
    models_to_try = [
        ("swiss-ai/Apertus-8B-Instruct-2509", "https://router.huggingface.co/hf-inference/models/swiss-ai/Apertus-8B-Instruct-2509/v1/chat/completions"),
        ("HuggingFaceH4/zephyr-7b-beta", "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"),
    ]
    
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }
    
    for model_name, url in models_to_try:
        try:
            if "chat/completions" in url:
                # OpenAI-compatible format for Apertus
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 300,
                    "temperature": 0.7
                }
            else:
                # Standard HF Inference format
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 300,
                        "temperature": 0.7,
                        "do_sample": True
                    }
                }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Parse response based on format
                if "choices" in result:
                    # OpenAI format
                    text = result["choices"][0]["message"]["content"]
                elif isinstance(result, list) and len(result) > 0:
                    # HF format
                    text = result[0].get("generated_text", "")
                    # Remove the prompt from response
                    if prompt in text:
                        text = text.split(prompt)[-1]
                else:
                    continue
                
                # Clean up
                text = text.strip()
                if text:
                    return text
                    
        except Exception as e:
            print(f"AI API error ({model_name}): {e}")
            continue
    
    return None


def generate_fallback_recommendation(data: dict, profile: str, language: str = "de") -> str:
    """Generate rule-based recommendations when AI is unavailable"""
    
    weather = data.get("weather", {})
    air = data.get("air_quality", {})
    space = data.get("space", {})
    eq = data.get("earthquakes", {})
    pollen = data.get("pollen", {})
    
    recommendations = []
    warnings = []
    
    temp = weather.get("temperature")
    uv = air.get("uv_index", 0) or 0
    aqi = air.get("eu_aqi", 0) or 0
    kp = space.get("kp", {}).get("value", 0) or 0
    eq_count = eq.get("count", 0)
    high_pollen = pollen.get("high_pollen", [])
    
    # Temperature-based
    if temp is not None:
        if temp < 5:
            recommendations.append("🧥 Warme Kleidung empfohlen")
        elif temp > 25:
            recommendations.append("💧 Viel trinken, leichte Kleidung")
    
    # UV-based
    if uv >= 8:
        warnings.append(f"☀️ Sehr hoher UV-Index ({uv}) - Sonnencreme SPF50+ und Schatten suchen!")
    elif uv >= 6:
        recommendations.append(f"🧴 Sonnencreme empfohlen (UV {uv})")
    elif uv >= 3:
        recommendations.append("☀️ Leichter Sonnenschutz sinnvoll")
    
    # Air quality
    if aqi > 80:
        warnings.append(f"😷 Schlechte Luftqualität (AQI {aqi}) - Outdoor-Aktivitäten reduzieren!")
    elif aqi > 60:
        recommendations.append(f"💨 Mäßige Luftqualität (AQI {aqi})")
    else:
        recommendations.append("✅ Gute Luftqualität")
    
    # Profile-specific
    if "Asthma" in profile or "Allergy" in profile:
        if high_pollen:
            warnings.append(f"🌸 Hohe Pollenbelastung: {', '.join(high_pollen)}")
        if aqi > 40:
            recommendations.append("Inhalator mitnehmen empfohlen")
    
    if "Aurora" in profile:
        aurora_prob = space.get("aurora", {}).get("probability", 0)
        if kp >= 5:
            recommendations.append(f"🌌 Gute Chancen auf Nordlichter! Kp={kp}, {aurora_prob}% Wahrscheinlichkeit")
        else:
            recommendations.append(f"Aurora unwahrscheinlich heute (Kp={kp})")
    
    if "Pilot" in profile or "Aviation" in profile:
        if kp >= 5:
            warnings.append(f"⚠️ Geomagnetischer Sturm (Kp={kp}) - HF-Funk möglicherweise gestört")
        xray = space.get("xray", {}).get("level", "")
        if xray.startswith("M") or xray.startswith("X"):
            warnings.append(f"☀️ Sonneneruption ({xray}) - mögliche Funkstörungen")
    
    if "Marine" in profile or "Sailing" in profile:
        marine_cond = data.get("marine", {}).get("conditions", "")
        if marine_cond in ["Dangerous", "Rough"]:
            warnings.append(f"🌊 {marine_cond} - Seegang nicht empfohlen!")
    
    # Earthquakes
    if eq_count > 0:
        max_mag = eq.get("max_magnitude")
        if max_mag and max_mag >= 5:
            warnings.append(f"🌍 Signifikante seismische Aktivität (M{max_mag}) in der Region")
    
    # Combine
    weather_desc = f"{weather.get('weather', 'Unbekannt')}, {temp}°C" if temp else weather.get('weather', '')
    
    result = f"🌤️ {weather_desc}. "
    
    if warnings:
        result += " ".join(warnings) + " "
    
    if recommendations:
        result += " ".join(recommendations[:3])
    
    if not warnings and not recommendations:
        result += "Gute Bedingungen für Outdoor-Aktivitäten! ✅"
    
    return result


# === 7. MAIN API ENDPOINTS ===

@app.get("/")
def root():
    return {
        "status": "online",
        "version": "7.0.0 - AI-Powered Environmental Monitor",
        "ai_model": "Swiss AI Apertus-8B",
        "features": [
            "Real-time environmental data from 6+ sources",
            "AI-powered personalized recommendations",
            "Multilingual support (DE, EN, FR, IT)",
            "Profile-specific advice"
        ],
        "endpoints": {
            "/alert/": "Get AI-powered environmental alert",
            "/data/": "Get raw environmental data",
            "/health/": "API health check"
        }
    }


@app.get("/health/")
def health():
    return {
        "status": "healthy",
        "ai_available": bool(HF_API_KEY),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/data/")
def get_data(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON)):
    """Get raw environmental data without AI recommendations"""
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "location": {"lat": lat, "lon": lon},
        "weather": fetch_weather(lat, lon),
        "air_quality": fetch_air_quality(lat, lon),
        "pollen": fetch_pollen(lat, lon),
        "space": {
            "kp": fetch_kp_index(),
            "solar_wind": fetch_solar_wind(),
            "xray": fetch_xray_flux(),
            "aurora": fetch_aurora_forecast(lat, lon),
        },
        "earthquakes": fetch_earthquakes_nearby(lat, lon),
        "natural_events": fetch_natural_events_nearby(lat, lon),
        "flood": fetch_flood_risk(lat, lon),
        "marine": fetch_marine(lat, lon),
    }


@app.get("/alert/")
def get_alert(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    profile: str = Query("General Public"),
    language: str = Query("de", description="de, en, fr, it")
):
    """Get AI-powered environmental alert with personalized recommendations"""
    
    # Fetch all data
    data = {
        "weather": fetch_weather(lat, lon),
        "air_quality": fetch_air_quality(lat, lon),
        "pollen": fetch_pollen(lat, lon),
        "space": {
            "kp": fetch_kp_index(),
            "solar_wind": fetch_solar_wind(),
            "xray": fetch_xray_flux(),
            "protons": fetch_proton_flux(),
            "aurora": fetch_aurora_forecast(lat, lon),
        },
        "earthquakes": fetch_earthquakes_nearby(lat, lon),
        "natural_events": fetch_natural_events_nearby(lat, lon),
        "flood": fetch_flood_risk(lat, lon),
        "marine": fetch_marine(lat, lon),
    }
    
    # Generate AI recommendation
    ai_source = "none"
    
    if HF_API_KEY:
        prompt = build_ai_prompt(data, profile, language)
        ai_recommendation = call_apertus_api(prompt)
        
        if ai_recommendation:
            ai_source = "apertus"
            recommendation = ai_recommendation
        else:
            ai_source = "fallback"
            recommendation = generate_fallback_recommendation(data, profile, language)
    else:
        ai_source = "fallback"
        recommendation = generate_fallback_recommendation(data, profile, language)
    
    # Calculate risk level
    risk_score = 0
    risk_factors = []
    
    kp = data["space"]["kp"].get("value", 0) or 0
    if kp >= 7: risk_score += 3; risk_factors.append(f"Severe geomagnetic storm (Kp={kp})")
    elif kp >= 5: risk_score += 2; risk_factors.append(f"Geomagnetic storm (Kp={kp})")
    
    aqi = data["air_quality"].get("eu_aqi", 0) or 0
    if aqi > 80: risk_score += 2; risk_factors.append(f"Poor air quality (AQI {aqi})")
    elif aqi > 60: risk_score += 1; risk_factors.append(f"Moderate air quality (AQI {aqi})")
    
    uv = data["air_quality"].get("uv_index", 0) or 0
    if uv >= 8: risk_score += 2; risk_factors.append(f"Very high UV ({uv})")
    elif uv >= 6: risk_score += 1; risk_factors.append(f"High UV ({uv})")
    
    eq_count = data["earthquakes"].get("count", 0)
    if eq_count > 0:
        max_mag = data["earthquakes"].get("max_magnitude")
        if max_mag and max_mag >= 5:
            risk_score += 3; risk_factors.append(f"Earthquake M{max_mag} nearby")
    
    if data["flood"].get("risk") == "High":
        risk_score += 2; risk_factors.append("High flood risk")
    
    if risk_score >= 5: risk_level = "High"
    elif risk_score >= 3: risk_level = "Medium"
    elif risk_score >= 1: risk_level = "Low-Medium"
    else: risk_level = "Low"
    
    # Build summary
    summary = {
        "temperature": data["weather"].get("temperature"),
        "weather": data["weather"].get("weather"),
        "air_quality": aqi,
        "uv_index": uv,
        "kp_index": kp,
        "aurora_probability": data["space"]["aurora"].get("probability", 0),
        "earthquakes_nearby": eq_count,
        "flood_risk": data["flood"].get("risk"),
    }
    
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "location": {"lat": lat, "lon": lon},
        "profile": profile,
        "language": language,
        "recommendation": recommendation,
        "ai_source": ai_source,
        "risk": {
            "level": risk_level,
            "factors": risk_factors
        },
        "summary": summary,
        "data": data
    }


# === 8. MAIN ===

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
