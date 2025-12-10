"""
Space Weather & Environmental Monitoring API v7.1
With Apertus AI Chat Interface & Full Multilingual Support

Features:
- Chat interface for conversational AI recommendations
- Full multilingual support (DE, EN, FR, IT)
- Improved fallback recommendations
- Profile-specific advice
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
    title="Environmental Monitor API",
    description="AI-powered environmental monitoring with chat interface",
    version="7.1.0"
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
HF_API_KEY = os.getenv("HF_API_KEY") or os.getenv("APERTUS_API_KEY")

DEFAULT_LAT = 47.3769
DEFAULT_LON = 8.5417

# === 3. TRANSLATIONS ===

TRANSLATIONS = {
    "de": {
        "good_morning": "Guten Morgen",
        "good_day": "Guten Tag", 
        "good_evening": "Guten Abend",
        "weather": "Wetter",
        "temperature": "Temperatur",
        "feels_like": "gefühlt",
        "humidity": "Luftfeuchtigkeit",
        "wind": "Wind",
        "air_quality": "Luftqualität",
        "excellent": "Ausgezeichnet",
        "good": "Gut",
        "moderate": "Mässig",
        "poor": "Schlecht",
        "very_poor": "Sehr schlecht",
        "hazardous": "Gefährlich",
        "uv_index": "UV-Index",
        "low": "Niedrig",
        "high": "Hoch",
        "very_high": "Sehr hoch",
        "extreme": "Extrem",
        "sunscreen_needed": "Sonnencreme empfohlen",
        "sunscreen_required": "Sonnencreme erforderlich (SPF 30+)",
        "avoid_sun": "Mittagssonne meiden, SPF 50+",
        "stay_inside": "Draussen-Aktivitäten einschränken",
        "perfect_outdoor": "Perfekt für Outdoor-Aktivitäten",
        "good_outdoor": "Gut für Outdoor-Aktivitäten",
        "limit_outdoor": "Intensive Aktivitäten einschränken",
        "avoid_outdoor": "Outdoor-Sport vermeiden",
        "warm_clothes": "Warme Kleidung empfohlen",
        "light_jacket": "Leichte Jacke reicht",
        "light_clothes": "Leichte Kleidung, viel trinken",
        "stay_hydrated": "Viel trinken!",
        "pollen_high": "Hohe Pollenbelastung",
        "take_inhaler": "Inhalator mitnehmen",
        "take_antihistamine": "Antihistaminikum empfohlen",
        "earthquake_warning": "Erdbeben in der Nähe",
        "flood_risk": "Hochwasser-Risiko",
        "aurora_possible": "Nordlichter möglich",
        "aurora_unlikely": "Nordlichter unwahrscheinlich",
        "hf_radio_disruption": "HF-Funk möglicherweise gestört",
        "gps_issues": "GPS-Genauigkeit reduziert",
        "rough_sea": "Rauer Seegang",
        "calm_sea": "Ruhige See",
        "no_concerns": "Keine besonderen Hinweise",
        "enjoy_day": "Geniessen Sie den Tag!",
        "have_fun": "Viel Spass!",
        "stay_safe": "Passen Sie auf sich auf!",
        "overcast": "Bewölkt",
        "clear": "Klar",
        "rain": "Regen",
        "snow": "Schnee",
        "fog": "Nebel",
        "thunderstorm": "Gewitter",
    },
    "en": {
        "good_morning": "Good morning",
        "good_day": "Hello",
        "good_evening": "Good evening",
        "weather": "Weather",
        "temperature": "Temperature",
        "feels_like": "feels like",
        "humidity": "Humidity",
        "wind": "Wind",
        "air_quality": "Air quality",
        "excellent": "Excellent",
        "good": "Good",
        "moderate": "Moderate",
        "poor": "Poor",
        "very_poor": "Very poor",
        "hazardous": "Hazardous",
        "uv_index": "UV index",
        "low": "Low",
        "high": "High",
        "very_high": "Very high",
        "extreme": "Extreme",
        "sunscreen_needed": "Sunscreen recommended",
        "sunscreen_required": "Sunscreen required (SPF 30+)",
        "avoid_sun": "Avoid midday sun, use SPF 50+",
        "stay_inside": "Limit outdoor activities",
        "perfect_outdoor": "Perfect for outdoor activities",
        "good_outdoor": "Good for outdoor activities",
        "limit_outdoor": "Limit intense activities",
        "avoid_outdoor": "Avoid outdoor sports",
        "warm_clothes": "Warm clothes recommended",
        "light_jacket": "Light jacket is enough",
        "light_clothes": "Light clothes, stay hydrated",
        "stay_hydrated": "Stay hydrated!",
        "pollen_high": "High pollen levels",
        "take_inhaler": "Bring your inhaler",
        "take_antihistamine": "Antihistamine recommended",
        "earthquake_warning": "Earthquake nearby",
        "flood_risk": "Flood risk",
        "aurora_possible": "Aurora possible",
        "aurora_unlikely": "Aurora unlikely",
        "hf_radio_disruption": "HF radio may be disrupted",
        "gps_issues": "GPS accuracy reduced",
        "rough_sea": "Rough sea conditions",
        "calm_sea": "Calm sea",
        "no_concerns": "No special concerns",
        "enjoy_day": "Enjoy your day!",
        "have_fun": "Have fun!",
        "stay_safe": "Stay safe!",
        "overcast": "Overcast",
        "clear": "Clear",
        "rain": "Rain",
        "snow": "Snow",
        "fog": "Fog",
        "thunderstorm": "Thunderstorm",
    },
    "fr": {
        "good_morning": "Bonjour",
        "good_day": "Bonjour",
        "good_evening": "Bonsoir",
        "weather": "Météo",
        "temperature": "Température",
        "feels_like": "ressenti",
        "humidity": "Humidité",
        "wind": "Vent",
        "air_quality": "Qualité de l'air",
        "excellent": "Excellente",
        "good": "Bonne",
        "moderate": "Modérée",
        "poor": "Mauvaise",
        "very_poor": "Très mauvaise",
        "hazardous": "Dangereuse",
        "uv_index": "Indice UV",
        "low": "Faible",
        "high": "Élevé",
        "very_high": "Très élevé",
        "extreme": "Extrême",
        "sunscreen_needed": "Crème solaire recommandée",
        "sunscreen_required": "Crème solaire nécessaire (SPF 30+)",
        "avoid_sun": "Évitez le soleil de midi, SPF 50+",
        "stay_inside": "Limitez les activités extérieures",
        "perfect_outdoor": "Parfait pour les activités extérieures",
        "good_outdoor": "Bon pour les activités extérieures",
        "limit_outdoor": "Limitez les activités intenses",
        "avoid_outdoor": "Évitez le sport en extérieur",
        "warm_clothes": "Vêtements chauds recommandés",
        "light_jacket": "Une veste légère suffit",
        "light_clothes": "Vêtements légers, buvez beaucoup",
        "stay_hydrated": "Restez hydraté!",
        "pollen_high": "Taux de pollen élevé",
        "take_inhaler": "Prenez votre inhalateur",
        "take_antihistamine": "Antihistaminique recommandé",
        "earthquake_warning": "Séisme à proximité",
        "flood_risk": "Risque d'inondation",
        "aurora_possible": "Aurores possibles",
        "aurora_unlikely": "Aurores improbables",
        "hf_radio_disruption": "Radio HF peut être perturbée",
        "gps_issues": "Précision GPS réduite",
        "rough_sea": "Mer agitée",
        "calm_sea": "Mer calme",
        "no_concerns": "Pas de préoccupations particulières",
        "enjoy_day": "Profitez de votre journée!",
        "have_fun": "Amusez-vous bien!",
        "stay_safe": "Prenez soin de vous!",
        "overcast": "Nuageux",
        "clear": "Dégagé",
        "rain": "Pluie",
        "snow": "Neige",
        "fog": "Brouillard",
        "thunderstorm": "Orage",
    },
    "it": {
        "good_morning": "Buongiorno",
        "good_day": "Buongiorno",
        "good_evening": "Buonasera",
        "weather": "Meteo",
        "temperature": "Temperatura",
        "feels_like": "percepita",
        "humidity": "Umidità",
        "wind": "Vento",
        "air_quality": "Qualità dell'aria",
        "excellent": "Eccellente",
        "good": "Buona",
        "moderate": "Moderata",
        "poor": "Scarsa",
        "very_poor": "Molto scarsa",
        "hazardous": "Pericolosa",
        "uv_index": "Indice UV",
        "low": "Basso",
        "high": "Alto",
        "very_high": "Molto alto",
        "extreme": "Estremo",
        "sunscreen_needed": "Crema solare consigliata",
        "sunscreen_required": "Crema solare necessaria (SPF 30+)",
        "avoid_sun": "Evitare il sole di mezzogiorno, SPF 50+",
        "stay_inside": "Limitare le attività all'aperto",
        "perfect_outdoor": "Perfetto per attività all'aperto",
        "good_outdoor": "Buono per attività all'aperto",
        "limit_outdoor": "Limitare attività intense",
        "avoid_outdoor": "Evitare sport all'aperto",
        "warm_clothes": "Vestiti caldi consigliati",
        "light_jacket": "Una giacca leggera è sufficiente",
        "light_clothes": "Vestiti leggeri, bere molto",
        "stay_hydrated": "Rimanere idratati!",
        "pollen_high": "Livelli di polline alti",
        "take_inhaler": "Portare l'inalatore",
        "take_antihistamine": "Antistaminico consigliato",
        "earthquake_warning": "Terremoto nelle vicinanze",
        "flood_risk": "Rischio alluvione",
        "aurora_possible": "Aurora possibile",
        "aurora_unlikely": "Aurora improbabile",
        "hf_radio_disruption": "Radio HF potrebbe essere disturbata",
        "gps_issues": "Precisione GPS ridotta",
        "rough_sea": "Mare mosso",
        "calm_sea": "Mare calmo",
        "no_concerns": "Nessuna preoccupazione particolare",
        "enjoy_day": "Buona giornata!",
        "have_fun": "Buon divertimento!",
        "stay_safe": "Stai attento!",
        "overcast": "Nuvoloso",
        "clear": "Sereno",
        "rain": "Pioggia",
        "snow": "Neve",
        "fog": "Nebbia",
        "thunderstorm": "Temporale",
    }
}

def t(key: str, lang: str = "de") -> str:
    """Get translation"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["de"]).get(key, TRANSLATIONS["de"].get(key, key))


# === 4. API ENDPOINTS ===

NOAA_URLS = {
    "kp_index": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
    "solar_wind_plasma": "https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json",
    "solar_wind_mag": "https://services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json",
    "xray_flux": "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json",
    "proton_flux": "https://services.swpc.noaa.gov/json/goes/primary/integral-protons-6-hour.json",
    "aurora": "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json",
}

USGS_URLS = {
    "earthquakes_day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
}

OPEN_METEO_URLS = {
    "weather": "https://api.open-meteo.com/v1/forecast",
    "air_quality": "https://air-quality-api.open-meteo.com/v1/air-quality",
    "flood": "https://flood-api.open-meteo.com/v1/flood",
    "marine": "https://marine-api.open-meteo.com/v1/marine",
}


# === 5. UTILITY FUNCTIONS ===

def safe_fetch(url: str, params: dict = None, timeout: int = 10) -> Optional[dict | list]:
    try:
        response = requests.get(url, params=params, timeout=timeout, 
                               headers={"User-Agent": "EnvironmentalMonitor/7.1"})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Fetch error: {e}")
        return None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import radians, sin, cos, sqrt, atan2
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))


# === 6. DATA FETCHING ===

def fetch_kp_index() -> dict:
    data = safe_fetch(NOAA_URLS["kp_index"])
    if data and len(data) > 1:
        latest = data[-1]
        kp = float(latest[1]) if latest[1] else None
        levels = {8: "Extreme Storm", 7: "Severe Storm", 6: "Strong Storm", 
                  5: "Moderate Storm", 4: "Active", 0: "Quiet"}
        level = next((v for k, v in sorted(levels.items(), reverse=True) if kp and kp >= k), "Quiet")
        return {"value": kp, "level": level, "status": "ok"}
    return {"value": None, "level": "Unknown", "status": "error"}


def fetch_solar_wind() -> dict:
    plasma = safe_fetch(NOAA_URLS["solar_wind_plasma"])
    mag = safe_fetch(NOAA_URLS["solar_wind_mag"])
    result = {"speed": None, "density": None, "bz": None, "status": "ok"}
    
    if plasma and len(plasma) > 1:
        latest = plasma[-1]
        result["speed"] = float(latest[2]) if len(latest) > 2 and latest[2] else None
        result["density"] = float(latest[1]) if len(latest) > 1 and latest[1] else None
    
    if mag and len(mag) > 1:
        latest = mag[-1]
        result["bz"] = float(latest[3]) if len(latest) > 3 and latest[3] else None
    
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


def fetch_aurora_forecast(lat: float, lon: float) -> dict:
    data = safe_fetch(NOAA_URLS["aurora"], timeout=15)
    if not data or "coordinates" not in data:
        return {"status": "error", "probability": 0}
    
    coords = data["coordinates"]
    lon_check = lon + 360 if lon < 0 else lon
    min_dist, prob = float('inf'), 0
    
    for point in coords:
        if len(point) >= 3:
            dist = abs(point[1] - lat) + abs(point[0] - lon_check)
            if dist < min_dist:
                min_dist = dist
                prob = point[2]
    
    visibility = "Excellent" if prob >= 50 else "Good" if prob >= 30 else "Fair" if prob >= 10 else "Low"
    return {"status": "ok", "probability": prob, "visibility": visibility}


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
            })
    
    nearby.sort(key=lambda x: x.get("distance_km", 9999))
    max_mag = max((eq["magnitude"] for eq in nearby if eq.get("magnitude")), default=None)
    
    return {"status": "ok", "count": len(nearby), "max_magnitude": max_mag, "earthquakes": nearby[:5]}


def fetch_weather(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_gusts_10m",
        "timezone": "auto"
    }
    if OPEN_METEO_API_KEY:
        params["apikey"] = OPEN_METEO_API_KEY
    
    data = safe_fetch(OPEN_METEO_URLS["weather"], params=params)
    if not data:
        return {"status": "error"}
    
    current = data.get("current", {})
    codes = {0: "Clear", 1: "Clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog",
             51: "Drizzle", 61: "Rain", 63: "Rain", 65: "Heavy rain",
             71: "Snow", 73: "Snow", 75: "Heavy snow", 80: "Showers", 95: "Thunderstorm"}
    
    return {
        "status": "ok",
        "temperature": current.get("temperature_2m"),
        "feels_like": current.get("apparent_temperature"),
        "humidity": current.get("relative_humidity_2m"),
        "precipitation": current.get("precipitation"),
        "weather": codes.get(current.get("weather_code", 0), "Unknown"),
        "weather_code": current.get("weather_code"),
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
    
    categories = [(20, "excellent"), (40, "good"), (60, "moderate"), 
                  (80, "poor"), (100, "very_poor")]
    category = next((c for th, c in categories if eu_aqi <= th), "hazardous")
    
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
        return {"status": "error", "pollen": {}, "high_pollen": []}
    
    current = data.get("current", {})
    
    def level(v):
        if v is None or v < 10: return "low"
        elif v < 50: return "moderate"
        elif v < 100: return "high"
        return "very_high"
    
    pollen = {
        "grass": {"value": current.get("grass_pollen"), "level": level(current.get("grass_pollen"))},
        "birch": {"value": current.get("birch_pollen"), "level": level(current.get("birch_pollen"))},
        "alder": {"value": current.get("alder_pollen"), "level": level(current.get("alder_pollen"))},
        "ragweed": {"value": current.get("ragweed_pollen"), "level": level(current.get("ragweed_pollen"))},
    }
    
    high_pollen = [k for k, v in pollen.items() if v["level"] in ["high", "very_high"]]
    
    return {"status": "ok", "pollen": pollen, "high_pollen": high_pollen}


def fetch_flood_risk(lat: float, lon: float) -> dict:
    params = {"latitude": lat, "longitude": lon, "daily": "river_discharge", "forecast_days": 7}
    if OPEN_METEO_API_KEY:
        params["apikey"] = OPEN_METEO_API_KEY
    
    data = safe_fetch(OPEN_METEO_URLS["flood"], params=params, timeout=15)
    if not data:
        return {"status": "error", "risk": "unknown"}
    
    discharge = data.get("daily", {}).get("river_discharge", [])
    valid = [d for d in discharge if d is not None]
    
    if not valid:
        return {"status": "no_river", "risk": "none"}
    
    max_d, avg_d = max(valid), sum(valid) / len(valid)
    
    if max_d > avg_d * 3: risk = "high"
    elif max_d > avg_d * 2: risk = "moderate"
    elif max_d > avg_d * 1.5: risk = "low"
    else: risk = "none"
    
    return {"status": "ok", "risk": risk}


def fetch_marine(lat: float, lon: float) -> dict:
    params = {"latitude": lat, "longitude": lon, "current": "wave_height,wave_period"}
    if OPEN_METEO_API_KEY:
        params["apikey"] = OPEN_METEO_API_KEY
    
    data = safe_fetch(OPEN_METEO_URLS["marine"], params=params, timeout=15)
    if not data or not data.get("current", {}).get("wave_height"):
        return {"status": "no_coast", "conditions": "none"}
    
    wave_h = data.get("current", {}).get("wave_height", 0)
    
    if wave_h > 4: cond = "dangerous"
    elif wave_h > 2.5: cond = "rough"
    elif wave_h > 1: cond = "moderate"
    else: cond = "calm"
    
    return {"status": "ok", "wave_height": wave_h, "conditions": cond}


# === 7. AI INTEGRATION ===

def build_ai_prompt(data: dict, profile: str, language: str, user_question: str = None) -> str:
    """Build prompt for AI"""
    
    lang_names = {"de": "German", "en": "English", "fr": "French", "it": "Italian"}
    lang_name = lang_names.get(language, "German")
    
    profile_descriptions = {
        "de": {
            "General Public": "eine normale Person im Alltag",
            "Outdoor/Sports": "jemanden der draussen Sport treiben möchte (Joggen, Wandern, Radfahren)",
            "Asthma/Respiratory": "jemanden mit Asthma oder Atemwegserkrankungen",
            "Allergy": "jemanden mit Pollenallergie",
            "Pilot/Aviation": "einen Piloten (Fokus auf Funkstörungen, GPS)",
            "Aurora Hunter": "jemanden der Nordlichter beobachten möchte",
            "Marine/Sailing": "jemanden der segeln oder Boot fahren möchte",
        },
        "en": {
            "General Public": "a regular person going about their day",
            "Outdoor/Sports": "someone who wants to exercise outdoors (jogging, hiking, cycling)",
            "Asthma/Respiratory": "someone with asthma or respiratory conditions",
            "Allergy": "someone with pollen allergies",
            "Pilot/Aviation": "a pilot (focus on radio disruptions, GPS)",
            "Aurora Hunter": "someone who wants to see the northern lights",
            "Marine/Sailing": "someone who wants to sail or go boating",
        }
    }
    
    profile_desc = profile_descriptions.get(language, profile_descriptions["de"]).get(profile, profile)
    
    weather = data.get("weather", {})
    air = data.get("air_quality", {})
    space = data.get("space", {})
    eq = data.get("earthquakes", {})
    pollen = data.get("pollen", {})
    
    data_summary = f"""
CURRENT ENVIRONMENTAL DATA:

Weather:
- Temperature: {weather.get('temperature', 'N/A')}°C (feels like {weather.get('feels_like', 'N/A')}°C)
- Conditions: {weather.get('weather', 'N/A')}
- Humidity: {weather.get('humidity', 'N/A')}%
- Wind: {weather.get('wind_speed', 'N/A')} km/h

Air Quality:
- EU AQI: {air.get('eu_aqi', 'N/A')} ({air.get('category', 'N/A')})
- PM2.5: {air.get('pm2_5', 'N/A')} μg/m³
- UV Index: {air.get('uv_index', 'N/A')}

Pollen: High levels of: {', '.join(pollen.get('high_pollen', [])) or 'None'}

Space Weather:
- Kp Index: {space.get('kp', {}).get('value', 'N/A')}
- Aurora probability: {space.get('aurora', {}).get('probability', 0)}%

Hazards:
- Earthquakes nearby (500km): {eq.get('count', 0)}
- Max magnitude: {eq.get('max_magnitude', 'N/A')}
"""

    if user_question:
        instruction = f"""You are a friendly environmental advisor. Answer the user's question based on the current data.

User profile: {profile_desc}
User's question: {user_question}

{data_summary}

IMPORTANT: 
- Answer in {lang_name} only
- Be concise (2-4 sentences)
- Give practical, actionable advice
- Use appropriate emojis
- If the question is unrelated to weather/environment, politely redirect

Your answer:"""
    else:
        instruction = f"""You are a friendly environmental advisor. Give a brief, personalized recommendation for {profile_desc}.

{data_summary}

IMPORTANT:
- Answer in {lang_name} only
- Maximum 3-4 sentences
- Give concrete recommendations (e.g., "bring sunscreen", "perfect for jogging", "stay indoors")
- Use appropriate emojis
- Only mention what's relevant for this profile
- Warn clearly about any hazards

Your recommendation:"""

    return instruction


def call_ai_api(prompt: str, debug: bool = False) -> tuple[Optional[str], dict]:
    """Call Apertus or fallback AI. Returns (response, debug_info)"""
    debug_info = {"api_key_set": bool(HF_API_KEY), "api_key_prefix": HF_API_KEY[:10] + "..." if HF_API_KEY else None, "attempts": []}
    
    if not HF_API_KEY:
        debug_info["error"] = "No API key found (checked HF_API_KEY and APERTUS_API_KEY)"
        return None, debug_info
    
    # Try multiple endpoints
    endpoints = [
        # Apertus via HF Inference (Public AI)
        {
            "name": "Apertus-PublicAI",
            "url": "https://router.huggingface.co/hf-inference/models/swiss-ai/Apertus-8B-Instruct-2509/v1/chat/completions",
            "format": "openai"
        },
        # Standard HF Inference API for Apertus
        {
            "name": "Apertus-HF-Direct",
            "url": "https://api-inference.huggingface.co/models/swiss-ai/Apertus-8B-Instruct-2509",
            "format": "hf"
        },
        # Fallback: Zephyr (reliable)
        {
            "name": "Zephyr-Fallback",
            "url": "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta",
            "format": "hf"
        },
        # Fallback: Mistral
        {
            "name": "Mistral-Fallback",
            "url": "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2",
            "format": "hf"
        }
    ]
    
    headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}
    
    for endpoint in endpoints:
        attempt = {"name": endpoint["name"], "url": endpoint["url"]}
        try:
            if endpoint["format"] == "openai":
                payload = {
                    "model": "swiss-ai/Apertus-8B-Instruct-2509",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.7
                }
            else:
                payload = {
                    "inputs": prompt,
                    "parameters": {"max_new_tokens": 300, "temperature": 0.7, "do_sample": True}
                }
            
            response = requests.post(endpoint["url"], headers=headers, json=payload, timeout=30)
            attempt["status_code"] = response.status_code
            
            if response.status_code == 200:
                result = response.json()
                attempt["response_keys"] = list(result.keys()) if isinstance(result, dict) else f"list[{len(result)}]"
                
                if "choices" in result:
                    text = result["choices"][0]["message"]["content"]
                elif isinstance(result, list) and result:
                    text = result[0].get("generated_text", "")
                    if prompt in text:
                        text = text.split(prompt)[-1]
                else:
                    attempt["error"] = "Unknown response format"
                    debug_info["attempts"].append(attempt)
                    continue
                
                text = text.strip()
                if text and len(text) > 20:
                    attempt["success"] = True
                    attempt["response_length"] = len(text)
                    debug_info["attempts"].append(attempt)
                    debug_info["success_model"] = endpoint["name"]
                    return text, debug_info
                else:
                    attempt["error"] = f"Response too short ({len(text)} chars)"
            else:
                attempt["error"] = f"HTTP {response.status_code}"
                try:
                    attempt["error_detail"] = response.json()
                except:
                    attempt["error_detail"] = response.text[:200]
                    
        except Exception as e:
            attempt["error"] = str(e)
        
        debug_info["attempts"].append(attempt)
    
    return None, debug_info


def generate_recommendation(data: dict, profile: str, language: str) -> str:
    """Generate rule-based recommendation in the correct language"""
    
    weather = data.get("weather", {})
    air = data.get("air_quality", {})
    space = data.get("space", {})
    eq = data.get("earthquakes", {})
    pollen = data.get("pollen", {})
    flood = data.get("flood", {})
    marine = data.get("marine", {})
    
    tips = []
    warnings = []
    
    temp = weather.get("temperature")
    uv = air.get("uv_index", 0) or 0
    aqi = air.get("eu_aqi", 0) or 0
    kp = space.get("kp", {}).get("value", 0) or 0
    high_pollen = pollen.get("high_pollen", [])
    
    # Weather conditions
    weather_desc = weather.get("weather", "")
    
    # Temperature advice
    if temp is not None:
        if temp < 5:
            tips.append(f"🧥 {t('warm_clothes', language)}")
        elif temp < 15:
            tips.append(f"🧥 {t('light_jacket', language)}")
        elif temp > 28:
            tips.append(f"💧 {t('light_clothes', language)}")
    
    # UV advice
    if uv >= 8:
        warnings.append(f"☀️ {t('avoid_sun', language)}")
    elif uv >= 6:
        tips.append(f"🧴 {t('sunscreen_required', language)}")
    elif uv >= 3:
        tips.append(f"🧴 {t('sunscreen_needed', language)}")
    
    # Air quality
    if aqi > 80:
        warnings.append(f"😷 {t('air_quality', language)}: {t('poor', language)} - {t('limit_outdoor', language)}")
    elif aqi > 60:
        tips.append(f"💨 {t('air_quality', language)}: {t('moderate', language)}")
    elif aqi <= 40:
        tips.append(f"✅ {t('air_quality', language)}: {t('good', language)}")
    
    # Profile-specific
    if "Asthma" in profile or "Respiratory" in profile:
        if high_pollen:
            warnings.append(f"🌸 {t('pollen_high', language)}: {', '.join(high_pollen)}")
        if aqi > 40:
            tips.append(f"💊 {t('take_inhaler', language)}")
    
    if "Allergy" in profile:
        if high_pollen:
            warnings.append(f"🌸 {t('pollen_high', language)}: {', '.join(high_pollen)}")
            tips.append(f"💊 {t('take_antihistamine', language)}")
    
    if "Aurora" in profile:
        aurora_prob = space.get("aurora", {}).get("probability", 0)
        if kp >= 5 or aurora_prob >= 20:
            tips.append(f"🌌 {t('aurora_possible', language)}! Kp={kp}, {aurora_prob}%")
        else:
            tips.append(f"🌌 {t('aurora_unlikely', language)} (Kp={kp})")
    
    if "Pilot" in profile or "Aviation" in profile:
        if kp >= 5:
            warnings.append(f"⚠️ {t('hf_radio_disruption', language)} (Kp={kp})")
        xray = space.get("xray", {}).get("level", "")
        if xray and (xray.startswith("M") or xray.startswith("X")):
            warnings.append(f"☀️ {t('gps_issues', language)}")
    
    if "Marine" in profile or "Sailing" in profile:
        cond = marine.get("conditions", "")
        if cond in ["dangerous", "rough"]:
            warnings.append(f"🌊 {t('rough_sea', language)}")
        elif cond == "calm":
            tips.append(f"🌊 {t('calm_sea', language)}")
    
    if "Outdoor" in profile or "Sports" in profile:
        if aqi <= 40 and uv < 8 and not warnings:
            tips.insert(0, f"🏃 {t('perfect_outdoor', language)}")
        elif aqi <= 60 and uv < 6:
            tips.insert(0, f"👍 {t('good_outdoor', language)}")
    
    # Earthquakes
    if eq.get("count", 0) > 0:
        max_mag = eq.get("max_magnitude")
        if max_mag and max_mag >= 4:
            warnings.append(f"🌍 {t('earthquake_warning', language)} (M{max_mag})")
    
    # Flood
    if flood.get("risk") in ["high", "moderate"]:
        warnings.append(f"🌊 {t('flood_risk', language)}: {flood.get('risk')}")
    
    # Build response
    greeting = t("good_day", language)
    weather_summary = f"{weather_desc}, {temp}°C" if temp else weather_desc
    
    response_parts = [f"🌤️ {greeting}! {weather_summary}."]
    
    if warnings:
        response_parts.extend(warnings)
    
    if tips:
        response_parts.extend(tips[:3])
    
    if not warnings and not tips:
        response_parts.append(f"{t('no_concerns', language)} {t('enjoy_day', language)}")
    elif not warnings:
        response_parts.append(f"{t('have_fun', language)}")
    
    return " ".join(response_parts)


# === 8. API ENDPOINTS ===

@app.get("/")
def root():
    return {
        "status": "online",
        "version": "7.1.0",
        "ai_enabled": bool(HF_API_KEY),
        "ai_key_prefix": HF_API_KEY[:10] + "..." if HF_API_KEY else None,
        "endpoints": {
            "/alert/": "Get environmental alert with AI recommendation",
            "/chat/": "Chat with AI about environmental conditions",
            "/data/": "Get raw environmental data",
            "/debug/ai/": "Test AI connection",
        }
    }


@app.get("/debug/ai/")
def debug_ai():
    """Test AI API connection and see detailed error info"""
    test_prompt = "Say 'Hello, I am working!' in exactly those words."
    
    response, debug_info = call_ai_api(test_prompt, debug=True)
    
    return {
        "status": "success" if response else "failed",
        "ai_response": response,
        "debug_info": debug_info,
        "config": {
            "HF_API_KEY_set": bool(os.getenv("HF_API_KEY")),
            "APERTUS_API_KEY_set": bool(os.getenv("APERTUS_API_KEY")),
            "key_used_prefix": HF_API_KEY[:15] + "..." if HF_API_KEY else None,
        }
    }


@app.get("/data/")
def get_data(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON)):
    """Get raw environmental data"""
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
        "flood": fetch_flood_risk(lat, lon),
        "marine": fetch_marine(lat, lon),
    }


@app.get("/alert/")
def get_alert(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    profile: str = Query("General Public"),
    language: str = Query("de")
):
    """Get AI-powered environmental alert"""
    
    # Validate language
    if language not in TRANSLATIONS:
        language = "de"
    
    # Fetch all data
    data = {
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
        "flood": fetch_flood_risk(lat, lon),
        "marine": fetch_marine(lat, lon),
    }
    
    # Try AI first
    ai_source = "rule-based"
    ai_debug = None
    
    if HF_API_KEY:
        prompt = build_ai_prompt(data, profile, language)
        ai_response, ai_debug = call_ai_api(prompt)
        
        if ai_response:
            ai_source = ai_debug.get("success_model", "apertus")
            recommendation = ai_response
        else:
            recommendation = generate_recommendation(data, profile, language)
    else:
        recommendation = generate_recommendation(data, profile, language)
    
    # Calculate risk
    risk_score = 0
    risk_factors = []
    
    kp = data["space"]["kp"].get("value", 0) or 0
    if kp >= 7: risk_score += 3; risk_factors.append(f"Severe storm (Kp={kp})")
    elif kp >= 5: risk_score += 2; risk_factors.append(f"Geomagnetic storm (Kp={kp})")
    
    aqi = data["air_quality"].get("eu_aqi", 0) or 0
    if aqi > 80: risk_score += 2; risk_factors.append(f"Poor air (AQI {aqi})")
    elif aqi > 60: risk_score += 1; risk_factors.append(f"Moderate air (AQI {aqi})")
    
    uv = data["air_quality"].get("uv_index", 0) or 0
    if uv >= 8: risk_score += 2; risk_factors.append(f"Very high UV ({uv})")
    elif uv >= 6: risk_score += 1; risk_factors.append(f"High UV ({uv})")
    
    eq_max = data["earthquakes"].get("max_magnitude")
    if eq_max and eq_max >= 5:
        risk_score += 3; risk_factors.append(f"Earthquake M{eq_max}")
    
    risk_level = "High" if risk_score >= 5 else "Medium" if risk_score >= 3 else "Low-Medium" if risk_score >= 1 else "Low"
    
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "location": {"lat": lat, "lon": lon},
        "profile": profile,
        "language": language,
        "recommendation": recommendation,
        "ai_source": ai_source,
        "risk": {"level": risk_level, "factors": risk_factors},
        "summary": {
            "temperature": data["weather"].get("temperature"),
            "weather": data["weather"].get("weather"),
            "air_quality": aqi,
            "uv_index": uv,
            "kp_index": kp,
            "aurora_probability": data["space"]["aurora"].get("probability", 0),
            "earthquakes_nearby": data["earthquakes"].get("count", 0),
            "flood_risk": data["flood"].get("risk"),
        },
        "data": data
    }


@app.post("/chat/")
def chat_with_ai(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    profile: str = Query("General Public"),
    language: str = Query("de"),
    question: str = Query(..., description="User's question")
):
    """Chat with AI about environmental conditions"""
    
    if language not in TRANSLATIONS:
        language = "de"
    
    # Fetch data
    data = {
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
        "flood": fetch_flood_risk(lat, lon),
        "marine": fetch_marine(lat, lon),
    }
    
    ai_source = "rule-based"
    ai_debug = None
    
    if HF_API_KEY:
        prompt = build_ai_prompt(data, profile, language, user_question=question)
        ai_response, ai_debug = call_ai_api(prompt)
        
        if ai_response:
            ai_source = ai_debug.get("success_model", "apertus")
            answer = ai_response
        else:
            # Fallback: Generate a simple response
            answer = generate_recommendation(data, profile, language)
    else:
        answer = generate_recommendation(data, profile, language)
    
    return {
        "status": "success",
        "question": question,
        "answer": answer,
        "ai_source": ai_source,
        "language": language,
        "data_summary": {
            "temperature": data["weather"].get("temperature"),
            "weather": data["weather"].get("weather"),
            "air_quality": data["air_quality"].get("eu_aqi"),
            "uv_index": data["air_quality"].get("uv_index"),
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
