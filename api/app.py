"""
Space Weather & Environmental Monitoring API v7.2
Complete Edition with ALL Data Sources

NEW in v7.2:
- NASA FIRMS: Real-time wildfire detection (VIIRS/MODIS satellites)
- Smithsonian GVP: Active volcanoes worldwide
- GDACS: UN Global Disaster Alerts
- Improved AI recommendations

Data Sources:
- NOAA SWPC: Space Weather (Kp, Solar Wind, X-Ray, Aurora)
- NASA EONET: Natural Events
- NASA FIRMS: Wildfires (requires MAP_KEY)
- USGS: Earthquakes
- Open-Meteo: Weather, Air Quality, UV, Pollen, Floods, Marine
- Smithsonian GVP: Volcanoes
- GDACS: Disaster Alerts
"""

import os
import json
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime, timedelta
from typing import Optional, List
import math

# === 1. INITIALIZATION ===

app = FastAPI(
    title="Environmental Monitor API",
    description="Complete environmental monitoring with 10+ satellite data sources",
    version="7.2.0"
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
FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY")
OPEN_METEO_API_KEY = os.getenv("OPEN_METEO_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY") or os.getenv("APERTUS_API_KEY")
CDS_API_KEY = os.getenv("CDS_API_KEY")

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
        "wildfire_warning": "Waldbrände in der Nähe",
        "volcano_warning": "Vulkanaktivität in der Nähe",
        "disaster_warning": "Katastrophenwarnung",
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
        "wildfire_warning": "Wildfires nearby",
        "volcano_warning": "Volcanic activity nearby",
        "disaster_warning": "Disaster warning",
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
        "perfect_outdoor": "Parfait pour les activités extérieures",
        "wildfire_warning": "Incendies à proximité",
        "volcano_warning": "Activité volcanique à proximité",
        "disaster_warning": "Alerte catastrophe",
        "no_concerns": "Pas de préoccupations particulières",
        "enjoy_day": "Profitez de votre journée!",
    },
    "it": {
        "good_morning": "Buongiorno",
        "good_day": "Buongiorno",
        "good_evening": "Buonasera",
        "weather": "Meteo",
        "temperature": "Temperatura",
        "perfect_outdoor": "Perfetto per attività all'aperto",
        "wildfire_warning": "Incendi nelle vicinanze",
        "volcano_warning": "Attività vulcanica nelle vicinanze",
        "disaster_warning": "Allarme catastrofe",
        "no_concerns": "Nessuna preoccupazione particolare",
        "enjoy_day": "Buona giornata!",
    }
}

def t(key: str, lang: str = "de") -> str:
    """Get translation with fallback"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["de"]).get(key, 
           TRANSLATIONS["de"].get(key, key))


# === 4. UTILITY FUNCTIONS ===

def safe_fetch(url: str, params: dict = None, timeout: int = 10, headers: dict = None) -> Optional[dict | list]:
    """Safely fetch JSON from URL"""
    try:
        h = headers or {}
        h.setdefault("User-Agent", "EnvironmentalMonitor/7.2")
        response = requests.get(url, params=params, timeout=timeout, headers=h)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Fetch error for {url}: {e}")
        return None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km using Haversine formula"""
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


# === 5. NOAA SPACE WEATHER ===

NOAA_URLS = {
    "kp_index": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
    "solar_wind_plasma": "https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json",
    "solar_wind_mag": "https://services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json",
    "xray_flux": "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json",
    "aurora": "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json",
}

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


# === 6. USGS EARTHQUAKES ===

def fetch_earthquakes_nearby(lat: float, lon: float, radius_km: float = 500) -> dict:
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
    data = safe_fetch(url, timeout=15)
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


# === 7. NASA FIRMS - WILDFIRES ===

def fetch_wildfires_nearby(lat: float, lon: float, radius_km: float = 100) -> dict:
    """Fetch active fires from NASA FIRMS VIIRS satellite"""
    if not FIRMS_MAP_KEY:
        return {"status": "no_api_key", "count": 0, "fires": [], "message": "FIRMS_MAP_KEY not configured"}
    
    # Calculate bounding box (approximate)
    delta = radius_km / 111  # ~111km per degree
    west = lon - delta
    east = lon + delta
    south = lat - delta
    north = lat + delta
    
    # FIRMS API - get last 24h of VIIRS data for area
    # Format: /area/csv/MAP_KEY/VIIRS_SNPP_NRT/bbox/days
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_MAP_KEY}/VIIRS_NOAA20_NRT/{west},{south},{east},{north}/1"
    
    try:
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            return {"status": "error", "count": 0, "fires": [], "error": f"HTTP {response.status_code}"}
        
        # Parse CSV response
        lines = response.text.strip().split('\n')
        if len(lines) <= 1:
            return {"status": "ok", "count": 0, "fires": [], "message": "No fires detected"}
        
        # CSV header: latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight
        fires = []
        header = lines[0].split(',')
        
        for line in lines[1:]:
            values = line.split(',')
            if len(values) >= 10:
                try:
                    fire_lat = float(values[0])
                    fire_lon = float(values[1])
                    dist = calculate_distance(lat, lon, fire_lat, fire_lon)
                    
                    if dist <= radius_km:
                        fires.append({
                            "latitude": fire_lat,
                            "longitude": fire_lon,
                            "brightness": float(values[2]) if values[2] else None,
                            "confidence": values[8],
                            "satellite": values[7],
                            "acq_date": values[5],
                            "acq_time": values[6],
                            "frp": float(values[11]) if len(values) > 11 and values[11] else None,  # Fire Radiative Power
                            "distance_km": round(dist, 1)
                        })
                except (ValueError, IndexError):
                    continue
        
        fires.sort(key=lambda x: x.get("distance_km", 9999))
        
        return {
            "status": "ok",
            "count": len(fires),
            "fires": fires[:20],  # Limit to 20 closest
            "source": "NASA FIRMS VIIRS",
            "coverage": "Global"
        }
        
    except Exception as e:
        return {"status": "error", "count": 0, "fires": [], "error": str(e)}


# === 8. SMITHSONIAN - VOLCANOES ===

def fetch_volcanoes_nearby(lat: float, lon: float, radius_km: float = 500) -> dict:
    """Fetch active volcanoes from Smithsonian GVP"""
    # GVP provides a weekly report feed
    url = "https://volcano.si.edu/news/WeeklyVolcanoRSS.xml"
    
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "EnvironmentalMonitor/7.2"})
        
        if response.status_code != 200:
            # Fallback: Use hardcoded list of major active volcanoes
            return fetch_volcanoes_fallback(lat, lon, radius_km)
        
        # Parse RSS/XML for recent activity
        # This is simplified - in production would use proper XML parser
        content = response.text
        
        # Extract volcano names from titles
        import re
        titles = re.findall(r'<title>([^<]+)</title>', content)
        
        # For now, return the recent activity info
        recent_activity = [t for t in titles if t and 'Weekly' not in t and 'Smithsonian' not in t]
        
        return {
            "status": "ok",
            "recent_activity": recent_activity[:10],
            "count": len(recent_activity),
            "source": "Smithsonian GVP",
            "note": "Shows globally active volcanoes this week"
        }
        
    except Exception as e:
        return fetch_volcanoes_fallback(lat, lon, radius_km)


def fetch_volcanoes_fallback(lat: float, lon: float, radius_km: float = 500) -> dict:
    """Fallback list of notable active volcanoes"""
    # Major active volcanoes with approximate coordinates
    volcanoes = [
        {"name": "Etna", "lat": 37.75, "lon": 14.99, "country": "Italy"},
        {"name": "Stromboli", "lat": 38.79, "lon": 15.21, "country": "Italy"},
        {"name": "Kilauea", "lat": 19.41, "lon": -155.29, "country": "USA"},
        {"name": "Fuego", "lat": 14.47, "lon": -90.88, "country": "Guatemala"},
        {"name": "Popocatépetl", "lat": 19.02, "lon": -98.62, "country": "Mexico"},
        {"name": "Sakurajima", "lat": 31.58, "lon": 130.66, "country": "Japan"},
        {"name": "Semeru", "lat": -8.11, "lon": 112.92, "country": "Indonesia"},
        {"name": "Merapi", "lat": -7.54, "lon": 110.44, "country": "Indonesia"},
        {"name": "Piton de la Fournaise", "lat": -21.23, "lon": 55.71, "country": "Réunion"},
        {"name": "Fagradalsfjall", "lat": 63.89, "lon": -22.27, "country": "Iceland"},
    ]
    
    nearby = []
    for v in volcanoes:
        dist = calculate_distance(lat, lon, v["lat"], v["lon"])
        if dist <= radius_km:
            nearby.append({**v, "distance_km": round(dist, 1)})
    
    nearby.sort(key=lambda x: x["distance_km"])
    
    return {
        "status": "ok",
        "count": len(nearby),
        "volcanoes": nearby,
        "source": "Static database",
        "note": "Major active volcanoes"
    }


# === 9. GDACS - DISASTER ALERTS ===

def fetch_gdacs_alerts(lat: float, lon: float, radius_km: float = 1000) -> dict:
    """Fetch disaster alerts from UN GDACS"""
    url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
    
    params = {
        "eventlist": "EQ,TC,FL,VO,DR,WF",  # Earthquake, Tropical Cyclone, Flood, Volcano, Drought, Wildfire
        "maxresults": 50,
        "orderby": "alertscore",
        "country": "",  # All countries
    }
    
    try:
        data = safe_fetch(url, params=params, timeout=15)
        
        if not data or "features" not in data:
            return {"status": "error", "count": 0, "alerts": []}
        
        nearby = []
        for event in data.get("features", []):
            props = event.get("properties", {})
            geom = event.get("geometry", {})
            coords = geom.get("coordinates", [0, 0])
            
            # GDACS coordinates are [lon, lat]
            event_lon, event_lat = coords[0], coords[1] if len(coords) > 1 else 0
            dist = calculate_distance(lat, lon, event_lat, event_lon)
            
            if dist <= radius_km:
                nearby.append({
                    "name": props.get("name", "Unknown"),
                    "type": props.get("eventtype"),
                    "alert_level": props.get("alertlevel"),  # Green, Orange, Red
                    "severity": props.get("severity", {}).get("severity"),
                    "country": props.get("country"),
                    "date": props.get("fromdate"),
                    "distance_km": round(dist, 1),
                    "url": props.get("url"),
                })
        
        nearby.sort(key=lambda x: (
            {"Red": 0, "Orange": 1, "Green": 2}.get(x.get("alert_level"), 3),
            x.get("distance_km", 9999)
        ))
        
        return {
            "status": "ok",
            "count": len(nearby),
            "alerts": nearby[:10],
            "source": "UN GDACS"
        }
        
    except Exception as e:
        return {"status": "error", "count": 0, "alerts": [], "error": str(e)}


# === 10. OPEN-METEO WEATHER & ENVIRONMENT ===

OPEN_METEO_URLS = {
    "weather": "https://api.open-meteo.com/v1/forecast",
    "air_quality": "https://air-quality-api.open-meteo.com/v1/air-quality",
    "flood": "https://flood-api.open-meteo.com/v1/flood",
    "marine": "https://marine-api.open-meteo.com/v1/marine",
}

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


# === 11. AI INTEGRATION ===

def build_ai_prompt(data: dict, profile: str, language: str, user_question: str = None) -> str:
    """Build prompt for AI with all data sources"""
    
    lang_names = {"de": "German", "en": "English", "fr": "French", "it": "Italian"}
    lang_name = lang_names.get(language, "German")
    
    weather = data.get("weather", {})
    air = data.get("air_quality", {})
    space = data.get("space", {})
    eq = data.get("earthquakes", {})
    pollen = data.get("pollen", {})
    fires = data.get("wildfires", {})
    volcanoes = data.get("volcanoes", {})
    gdacs = data.get("gdacs", {})
    
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

Pollen: High levels: {', '.join(pollen.get('high_pollen', [])) or 'None'}

Space Weather:
- Kp Index: {space.get('kp', {}).get('value', 'N/A')} ({space.get('kp', {}).get('level', 'N/A')})
- Aurora probability: {space.get('aurora', {}).get('probability', 0)}%

Natural Hazards:
- Earthquakes nearby (500km): {eq.get('count', 0)}, Max: M{eq.get('max_magnitude', 'N/A')}
- Active fires nearby (100km): {fires.get('count', 0)}
- Volcanoes: {volcanoes.get('count', 0)} active nearby
- GDACS Disaster Alerts: {gdacs.get('count', 0)}
"""

    if user_question:
        instruction = f"""You are a helpful environmental advisor. Answer the user's question based on the data.

User question: {user_question}

{data_summary}

Answer in {lang_name}. Be concise (2-4 sentences), practical, use emojis.
"""
    else:
        profile_context = {
            "General Public": "a regular person",
            "Outdoor/Sports": "someone exercising outdoors",
            "Asthma/Respiratory": "someone with respiratory conditions",
            "Allergy": "someone with pollen allergies",
            "Pilot/Aviation": "a pilot",
            "Aurora Hunter": "someone wanting to see northern lights",
            "Marine/Sailing": "someone sailing or boating",
        }
        
        instruction = f"""You are a helpful environmental advisor giving a recommendation for {profile_context.get(profile, 'a person')}.

{data_summary}

Give a brief recommendation in {lang_name}:
- Maximum 3-4 sentences
- Concrete, actionable advice
- Use emojis
- Warn about any hazards (fires, earthquakes, poor air quality)
- End positively if conditions are good
"""

    return instruction


def call_ai_api(prompt: str) -> tuple[Optional[str], dict]:
    """Call AI API with debug info"""
    debug_info = {"api_key_set": bool(HF_API_KEY), "attempts": []}
    
    if not HF_API_KEY:
        return None, debug_info
    
    endpoints = [
        {"name": "Apertus", "url": "https://router.huggingface.co/hf-inference/models/swiss-ai/Apertus-8B-Instruct-2509/v1/chat/completions", "format": "openai"},
        {"name": "Zephyr", "url": "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta", "format": "hf"},
    ]
    
    headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}
    
    for endpoint in endpoints:
        attempt = {"name": endpoint["name"]}
        try:
            if endpoint["format"] == "openai":
                payload = {"model": "swiss-ai/Apertus-8B-Instruct-2509", "messages": [{"role": "user", "content": prompt}], "max_tokens": 300, "temperature": 0.7}
            else:
                payload = {"inputs": prompt, "parameters": {"max_new_tokens": 300, "temperature": 0.7, "do_sample": True}}
            
            response = requests.post(endpoint["url"], headers=headers, json=payload, timeout=30)
            attempt["status"] = response.status_code
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result:
                    text = result["choices"][0]["message"]["content"]
                elif isinstance(result, list) and result:
                    text = result[0].get("generated_text", "")
                    if prompt in text:
                        text = text.split(prompt)[-1]
                else:
                    continue
                
                text = text.strip()
                if text and len(text) > 20:
                    debug_info["success"] = endpoint["name"]
                    debug_info["attempts"].append(attempt)
                    return text, debug_info
                    
        except Exception as e:
            attempt["error"] = str(e)
        
        debug_info["attempts"].append(attempt)
    
    return None, debug_info


def generate_recommendation(data: dict, profile: str, language: str) -> str:
    """Generate rule-based recommendation"""
    
    weather = data.get("weather", {})
    air = data.get("air_quality", {})
    space = data.get("space", {})
    eq = data.get("earthquakes", {})
    pollen = data.get("pollen", {})
    fires = data.get("wildfires", {})
    
    tips = []
    warnings = []
    
    temp = weather.get("temperature")
    uv = air.get("uv_index", 0) or 0
    aqi = air.get("eu_aqi", 0) or 0
    kp = space.get("kp", {}).get("value", 0) or 0
    high_pollen = pollen.get("high_pollen", [])
    fire_count = fires.get("count", 0)
    eq_count = eq.get("count", 0)
    
    # Wildfires - HIGH PRIORITY
    if fire_count > 0:
        warnings.append(f"🔥 {t('wildfire_warning', language)} ({fire_count})")
    
    # Earthquakes
    if eq_count > 0:
        max_mag = eq.get("max_magnitude")
        if max_mag and max_mag >= 4:
            warnings.append(f"🌍 {t('earthquake_warning', language)} (M{max_mag})")
    
    # Air quality
    if aqi > 80:
        warnings.append(f"😷 {t('air_quality', language)}: {t('poor', language)}")
    elif aqi <= 40:
        tips.append(f"✅ {t('air_quality', language)}: {t('good', language)}")
    
    # UV
    if uv >= 8:
        warnings.append(f"☀️ {t('avoid_sun', language)}")
    elif uv >= 3:
        tips.append(f"🧴 {t('sunscreen_needed', language)}")
    
    # Temperature
    if temp is not None:
        if temp < 5:
            tips.append(f"🧥 {t('warm_clothes', language)}")
        elif temp > 28:
            tips.append(f"💧 {t('stay_hydrated', language)}")
    
    # Profile-specific
    if "Allergy" in profile and high_pollen:
        warnings.append(f"🌸 {t('pollen_high', language)}: {', '.join(high_pollen)}")
    
    if "Aurora" in profile:
        aurora_prob = space.get("aurora", {}).get("probability", 0)
        if kp >= 5:
            tips.append(f"🌌 {t('aurora_possible', language)}! Kp={kp}")
        else:
            tips.append(f"🌌 {t('aurora_unlikely', language)} (Kp={kp})")
    
    # Build response
    weather_desc = f"{weather.get('weather', '')}, {temp}°C" if temp else weather.get('weather', '')
    
    parts = [f"🌤️ {t('good_day', language)}! {weather_desc}."]
    parts.extend(warnings)
    parts.extend(tips[:3])
    
    if not warnings:
        parts.append(t('enjoy_day', language))
    
    return " ".join(parts)


# === 12. API ENDPOINTS ===

@app.get("/")
def root():
    return {
        "status": "online",
        "version": "7.2.0 - Complete Environmental Monitor",
        "data_sources": {
            "space_weather": "NOAA SWPC (GOES, DSCOVR satellites)",
            "earthquakes": "USGS",
            "wildfires": f"NASA FIRMS {'✅' if FIRMS_MAP_KEY else '❌ (no key)'}",
            "volcanoes": "Smithsonian GVP",
            "disasters": "UN GDACS",
            "weather": "Open-Meteo (ECMWF, GFS)",
            "air_quality": "Copernicus CAMS",
        },
        "ai_enabled": bool(HF_API_KEY),
    }


@app.get("/debug/")
def debug():
    return {
        "api_keys": {
            "HF_API_KEY": bool(HF_API_KEY),
            "FIRMS_MAP_KEY": bool(FIRMS_MAP_KEY),
            "OPEN_METEO_API_KEY": bool(OPEN_METEO_API_KEY),
            "CDS_API_KEY": bool(CDS_API_KEY),
        },
        "firms_key_prefix": FIRMS_MAP_KEY[:8] + "..." if FIRMS_MAP_KEY else None,
    }


@app.get("/data/")
def get_data(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON)):
    """Get all environmental data"""
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
        "wildfires": fetch_wildfires_nearby(lat, lon),
        "volcanoes": fetch_volcanoes_nearby(lat, lon),
        "gdacs": fetch_gdacs_alerts(lat, lon),
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
        "wildfires": fetch_wildfires_nearby(lat, lon),
        "volcanoes": fetch_volcanoes_nearby(lat, lon),
        "gdacs": fetch_gdacs_alerts(lat, lon),
        "flood": fetch_flood_risk(lat, lon),
        "marine": fetch_marine(lat, lon),
    }
    
    # Try AI
    ai_source = "rule-based"
    if HF_API_KEY:
        prompt = build_ai_prompt(data, profile, language)
        ai_response, _ = call_ai_api(prompt)
        if ai_response:
            ai_source = "apertus"
            recommendation = ai_response
        else:
            recommendation = generate_recommendation(data, profile, language)
    else:
        recommendation = generate_recommendation(data, profile, language)
    
    # Calculate risk
    risk_score = 0
    risk_factors = []
    
    # Wildfires - HIGH RISK
    fire_count = data["wildfires"].get("count", 0)
    if fire_count > 5:
        risk_score += 4
        risk_factors.append(f"🔥 {fire_count} fires nearby")
    elif fire_count > 0:
        risk_score += 2
        risk_factors.append(f"🔥 {fire_count} fires nearby")
    
    # Earthquakes
    eq_max = data["earthquakes"].get("max_magnitude")
    if eq_max and eq_max >= 5:
        risk_score += 3
        risk_factors.append(f"🌍 Earthquake M{eq_max}")
    elif eq_max and eq_max >= 4:
        risk_score += 1
        risk_factors.append(f"🌍 Earthquake M{eq_max}")
    
    # GDACS alerts
    gdacs_count = data["gdacs"].get("count", 0)
    if gdacs_count > 0:
        risk_score += 2
        risk_factors.append(f"⚠️ {gdacs_count} disaster alerts")
    
    # Air quality
    aqi = data["air_quality"].get("eu_aqi", 0) or 0
    if aqi > 80:
        risk_score += 2
        risk_factors.append(f"😷 Poor air (AQI {aqi})")
    
    # UV
    uv = data["air_quality"].get("uv_index", 0) or 0
    if uv >= 8:
        risk_score += 1
        risk_factors.append(f"☀️ High UV ({uv})")
    
    # Space weather
    kp = data["space"]["kp"].get("value", 0) or 0
    if kp >= 7:
        risk_score += 2
        risk_factors.append(f"🌞 Severe storm (Kp={kp})")
    
    risk_level = "Critical" if risk_score >= 6 else "High" if risk_score >= 4 else "Medium" if risk_score >= 2 else "Low"
    
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "location": {"lat": lat, "lon": lon},
        "profile": profile,
        "language": language,
        "recommendation": recommendation,
        "ai_source": ai_source,
        "risk": {"level": risk_level, "score": risk_score, "factors": risk_factors},
        "summary": {
            "temperature": data["weather"].get("temperature"),
            "weather": data["weather"].get("weather"),
            "air_quality": aqi,
            "uv_index": uv,
            "kp_index": kp,
            "earthquakes_nearby": data["earthquakes"].get("count", 0),
            "wildfires_nearby": fire_count,
            "disaster_alerts": gdacs_count,
        },
        "data": data
    }


@app.get("/wildfires/")
def get_wildfires(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    radius_km: float = Query(100)
):
    """Get nearby wildfires from NASA FIRMS"""
    return fetch_wildfires_nearby(lat, lon, radius_km)


@app.get("/volcanoes/")
def get_volcanoes(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    radius_km: float = Query(500)
):
    """Get nearby volcanoes"""
    return fetch_volcanoes_nearby(lat, lon, radius_km)


@app.get("/disasters/")
def get_disasters(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    radius_km: float = Query(1000)
):
    """Get GDACS disaster alerts"""
    return fetch_gdacs_alerts(lat, lon, radius_km)


@app.post("/chat/")
def chat(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    profile: str = Query("General Public"),
    language: str = Query("de"),
    question: str = Query(...)
):
    """Chat with AI about conditions"""
    
    data = {
        "weather": fetch_weather(lat, lon),
        "air_quality": fetch_air_quality(lat, lon),
        "pollen": fetch_pollen(lat, lon),
        "space": {"kp": fetch_kp_index(), "aurora": fetch_aurora_forecast(lat, lon)},
        "earthquakes": fetch_earthquakes_nearby(lat, lon),
        "wildfires": fetch_wildfires_nearby(lat, lon),
        "volcanoes": fetch_volcanoes_nearby(lat, lon),
        "gdacs": fetch_gdacs_alerts(lat, lon),
    }
    
    if HF_API_KEY:
        prompt = build_ai_prompt(data, profile, language, user_question=question)
        ai_response, _ = call_ai_api(prompt)
        if ai_response:
            return {"status": "success", "answer": ai_response, "ai_source": "apertus"}
    
    return {"status": "success", "answer": generate_recommendation(data, profile, language), "ai_source": "rule-based"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
