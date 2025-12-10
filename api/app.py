"""
Space Weather & Environmental Monitoring API v6.0
Complete Edition - All Available Data Sources

Data Sources:
- NOAA SWPC: Space Weather (Kp, Solar Wind, X-Ray, Protons, Aurora)
- NASA EONET: Natural Events (Wildfires, Volcanoes, Storms)
- NASA DONKI: Space Weather Events (CME, Flares, GST)
- USGS: Earthquakes worldwide
- NWS: US Weather Alerts (Tornados, Hurricanes, etc.)
- Open-Meteo: Weather, Air Quality, UV, Pollen, Floods, Marine

License Notes:
- US Government APIs (NOAA, NASA, USGS, NWS): Public Domain, commercial use OK
- Open-Meteo: CC BY 4.0, requires paid subscription for commercial use
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
    description="Complete environmental monitoring with 15+ data sources",
    version="6.0.0"
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
HF_API_KEY = os.getenv("HF_API_KEY") or os.getenv("APERTUS_API_KEY")
OPEN_METEO_API_KEY = os.getenv("OPEN_METEO_API_KEY")  # For commercial use

DEFAULT_LAT = 47.3769  # Zurich
DEFAULT_LON = 8.5417

# === 3. API ENDPOINTS ===

# NOAA Space Weather Prediction Center
NOAA_URLS = {
    "kp_index": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
    "solar_wind_plasma": "https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json",
    "solar_wind_mag": "https://services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json",
    "xray_flux": "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json",
    "proton_flux": "https://services.swpc.noaa.gov/json/goes/primary/integral-protons-6-hour.json",
    "electron_flux": "https://services.swpc.noaa.gov/json/goes/primary/integral-electrons-6-hour.json",
    "xray_flares": "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json",
    "aurora": "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json",
    "alerts": "https://services.swpc.noaa.gov/products/alerts.json",
    "solar_wind_speed": "https://services.swpc.noaa.gov/products/summary/solar-wind-speed.json",
    "geomag_storm": "https://services.swpc.noaa.gov/products/noaa-scales.json",
}

# NASA APIs
NASA_URLS = {
    "eonet_events": "https://eonet.gsfc.nasa.gov/api/v3/events",
    "donki_gst": "https://api.nasa.gov/DONKI/GST",
    "donki_cme": "https://api.nasa.gov/DONKI/CME", 
    "donki_flr": "https://api.nasa.gov/DONKI/FLR",
    "donki_sep": "https://api.nasa.gov/DONKI/SEP",
}

# USGS Earthquake
USGS_URLS = {
    "earthquakes_hour": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
    "earthquakes_day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    "earthquakes_significant": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson",
    "earthquakes_4.5_day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson",
    "earthquakes_2.5_day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
}

# NWS (National Weather Service) - US Only
NWS_BASE = "https://api.weather.gov"

# Open-Meteo (requires commercial license for commercial use)
OPEN_METEO_URLS = {
    "weather": "https://api.open-meteo.com/v1/forecast",
    "air_quality": "https://air-quality-api.open-meteo.com/v1/air-quality",
    "flood": "https://flood-api.open-meteo.com/v1/flood",
    "marine": "https://marine-api.open-meteo.com/v1/marine",
}


# === 4. UTILITY FUNCTIONS ===

def safe_fetch(url: str, params: dict = None, timeout: int = 10, headers: dict = None) -> Optional[dict | list]:
    """Safely fetch JSON from URL with error handling"""
    try:
        h = headers or {}
        h.setdefault("User-Agent", "SpaceWeatherAPI/6.0 (contact@example.com)")
        response = requests.get(url, params=params, timeout=timeout, headers=h)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Fetch error for {url}: {e}")
        return None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate approximate distance in km between two points"""
    from math import radians, sin, cos, sqrt, atan2
    R = 6371  # Earth's radius in km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


# === 5. NOAA SPACE WEATHER FUNCTIONS ===

def fetch_kp_index() -> dict:
    """Fetch current Kp index (geomagnetic activity)"""
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
    """Fetch solar wind plasma and magnetic field data"""
    plasma = safe_fetch(NOAA_URLS["solar_wind_plasma"])
    mag = safe_fetch(NOAA_URLS["solar_wind_mag"])
    
    result = {
        "speed": None, "density": None, "temperature": None,
        "bz": None, "bt": None, "status": "error"
    }
    
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
    
    # Add interpretation
    if result["speed"]:
        if result["speed"] > 700: result["wind_level"] = "Extreme"
        elif result["speed"] > 500: result["wind_level"] = "High"
        elif result["speed"] > 400: result["wind_level"] = "Elevated"
        else: result["wind_level"] = "Normal"
    
    return result


def fetch_xray_flux() -> dict:
    """Fetch X-ray flux (solar flare indicator)"""
    data = safe_fetch(NOAA_URLS["xray_flux"])
    if data:
        for entry in reversed(data):
            if isinstance(entry, dict) and entry.get("flux"):
                flux = float(entry["flux"])
                
                if flux >= 1e-4: level = f"X{int(flux / 1e-4)}"
                elif flux >= 1e-5: level = f"M{int(flux / 1e-5)}"
                elif flux >= 1e-6: level = f"C{int(flux / 1e-6)}"
                elif flux >= 1e-7: level = f"B{int(flux / 1e-7)}"
                else: level = "A"
                
                return {
                    "flux": flux, "level": level, 
                    "time": entry.get("time_tag"), "status": "ok"
                }
    return {"flux": None, "level": None, "status": "error"}


def fetch_proton_flux() -> dict:
    """Fetch proton flux (radiation storm indicator)"""
    data = safe_fetch(NOAA_URLS["proton_flux"])
    if data:
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


def fetch_aurora_forecast(lat: float = None, lon: float = None) -> dict:
    """Fetch aurora forecast from OVATION model"""
    data = safe_fetch(NOAA_URLS["aurora"], timeout=15)
    if not data:
        return {"status": "error", "probability": None}
    
    result = {
        "status": "ok",
        "forecast_time": data.get("Forecast Time"),
        "observation_time": data.get("Observation Time"),
    }
    
    # If coordinates provided, find probability for that location
    if lat is not None and lon is not None and "coordinates" in data:
        coords = data["coordinates"]
        
        # Find closest grid point
        best_prob = 0
        min_dist = float('inf')
        
        # Aurora data is [lon, lat, probability]
        for point in coords:
            if len(point) >= 3:
                p_lon, p_lat, prob = point[0], point[1], point[2]
                
                # Normalize longitude
                if lon < 0: lon_check = lon + 360
                else: lon_check = lon
                
                dist = abs(p_lat - lat) + abs(p_lon - lon_check)
                if dist < min_dist:
                    min_dist = dist
                    best_prob = prob
        
        result["probability"] = best_prob
        result["location"] = {"lat": lat, "lon": lon}
        
        # Interpretation
        if best_prob >= 50: result["visibility"] = "Excellent - Aurora likely visible!"
        elif best_prob >= 30: result["visibility"] = "Good - Aurora possible"
        elif best_prob >= 10: result["visibility"] = "Fair - Aurora might be visible on horizon"
        else: result["visibility"] = "Low - Aurora unlikely"
    else:
        result["note"] = "Provide lat/lon for location-specific probability"
    
    return result


def fetch_space_weather_alerts() -> dict:
    """Fetch active space weather alerts, watches, and warnings"""
    data = safe_fetch(NOAA_URLS["alerts"])
    if not data:
        return {"status": "error", "alerts": []}
    
    alerts = []
    for alert in data[:20]:  # Last 20 alerts
        if isinstance(alert, dict):
            alerts.append({
                "message": alert.get("message", "")[:500],
                "issue_time": alert.get("issue_datetime"),
            })
        elif isinstance(alert, list) and len(alert) >= 2:
            alerts.append({
                "message": str(alert[1])[:500] if len(alert) > 1 else "",
                "issue_time": alert[0] if alert else None,
            })
    
    return {"status": "ok", "count": len(alerts), "alerts": alerts}


def fetch_recent_flares() -> dict:
    """Fetch recent solar flares"""
    data = safe_fetch(NOAA_URLS["xray_flares"])
    if data and isinstance(data, list):
        flares = []
        for f in data[-20:]:
            if isinstance(f, dict):
                flares.append({
                    "class": f.get("classtype"),
                    "start": f.get("begintime"),
                    "peak": f.get("maxtime"),
                    "end": f.get("endtime"),
                    "region": f.get("region"),
                })
        
        # Count by class
        x_class = sum(1 for f in flares if f.get("class", "").startswith("X"))
        m_class = sum(1 for f in flares if f.get("class", "").startswith("M"))
        c_class = sum(1 for f in flares if f.get("class", "").startswith("C"))
        
        return {
            "status": "ok",
            "total": len(flares),
            "by_class": {"X": x_class, "M": m_class, "C": c_class},
            "recent": flares[-5:]
        }
    return {"status": "error", "total": 0, "recent": []}


# === 6. USGS EARTHQUAKE FUNCTIONS ===

def fetch_earthquakes(min_magnitude: float = 2.5, hours: int = 24) -> dict:
    """Fetch recent earthquakes from USGS"""
    
    # Select appropriate feed based on criteria
    if min_magnitude >= 4.5:
        url = USGS_URLS["earthquakes_4.5_day"]
    elif hours <= 1:
        url = USGS_URLS["earthquakes_hour"]
    else:
        url = USGS_URLS["earthquakes_2.5_day"]
    
    data = safe_fetch(url, timeout=15)
    if not data:
        return {"status": "error", "earthquakes": []}
    
    earthquakes = []
    features = data.get("features", [])
    
    for eq in features:
        props = eq.get("properties", {})
        geom = eq.get("geometry", {})
        coords = geom.get("coordinates", [0, 0, 0])
        
        mag = props.get("mag", 0)
        if mag and mag >= min_magnitude:
            earthquakes.append({
                "magnitude": mag,
                "location": props.get("place"),
                "time": props.get("time"),
                "time_human": datetime.fromtimestamp(props.get("time", 0)/1000).isoformat() if props.get("time") else None,
                "depth_km": coords[2] if len(coords) > 2 else None,
                "coordinates": {"lon": coords[0], "lat": coords[1]},
                "tsunami_warning": props.get("tsunami", 0) == 1,
                "felt_reports": props.get("felt"),
                "alert_level": props.get("alert"),
                "url": props.get("url"),
            })
    
    # Sort by magnitude descending
    earthquakes.sort(key=lambda x: x.get("magnitude", 0), reverse=True)
    
    # Statistics
    magnitudes = [eq["magnitude"] for eq in earthquakes if eq.get("magnitude")]
    
    return {
        "status": "ok",
        "count": len(earthquakes),
        "statistics": {
            "max_magnitude": max(magnitudes) if magnitudes else None,
            "avg_magnitude": round(sum(magnitudes)/len(magnitudes), 2) if magnitudes else None,
            "with_tsunami_warning": sum(1 for eq in earthquakes if eq.get("tsunami_warning")),
        },
        "earthquakes": earthquakes[:50]  # Limit to 50
    }


def fetch_nearby_earthquakes(lat: float, lon: float, radius_km: float = 500, hours: int = 24) -> dict:
    """Fetch earthquakes near a specific location"""
    all_eq = fetch_earthquakes(min_magnitude=1.0, hours=hours)
    
    if all_eq.get("status") != "ok":
        return all_eq
    
    nearby = []
    for eq in all_eq.get("earthquakes", []):
        coords = eq.get("coordinates", {})
        eq_lat = coords.get("lat", 0)
        eq_lon = coords.get("lon", 0)
        
        dist = calculate_distance(lat, lon, eq_lat, eq_lon)
        
        if dist <= radius_km:
            eq["distance_km"] = round(dist, 1)
            nearby.append(eq)
    
    nearby.sort(key=lambda x: x.get("distance_km", 9999))
    
    return {
        "status": "ok",
        "location": {"lat": lat, "lon": lon},
        "radius_km": radius_km,
        "count": len(nearby),
        "earthquakes": nearby[:20]
    }


def fetch_significant_earthquakes() -> dict:
    """Fetch significant earthquakes from past month"""
    data = safe_fetch(USGS_URLS["earthquakes_significant"], timeout=15)
    if not data:
        return {"status": "error", "earthquakes": []}
    
    earthquakes = []
    for eq in data.get("features", [])[:20]:
        props = eq.get("properties", {})
        geom = eq.get("geometry", {})
        coords = geom.get("coordinates", [0, 0, 0])
        
        earthquakes.append({
            "magnitude": props.get("mag"),
            "location": props.get("place"),
            "time": props.get("time"),
            "time_human": datetime.fromtimestamp(props.get("time", 0)/1000).isoformat() if props.get("time") else None,
            "depth_km": coords[2] if len(coords) > 2 else None,
            "coordinates": {"lon": coords[0], "lat": coords[1]},
            "tsunami_warning": props.get("tsunami", 0) == 1,
            "deaths": props.get("deaths"),
            "alert_level": props.get("alert"),
            "title": props.get("title"),
        })
    
    return {
        "status": "ok",
        "count": len(earthquakes),
        "earthquakes": earthquakes
    }


# === 7. NWS WEATHER ALERTS (US ONLY) ===

def fetch_nws_alerts(state: str = None, lat: float = None, lon: float = None) -> dict:
    """Fetch active weather alerts from NWS (US only)"""
    
    headers = {"User-Agent": "SpaceWeatherAPI/6.0 (contact@example.com)"}
    
    if lat and lon:
        # Get alerts for a point
        url = f"{NWS_BASE}/alerts/active"
        params = {"point": f"{lat},{lon}"}
    elif state:
        # Get alerts for a state
        url = f"{NWS_BASE}/alerts/active"
        params = {"area": state.upper()}
    else:
        # Get all active alerts
        url = f"{NWS_BASE}/alerts/active"
        params = {"status": "actual", "limit": 50}
    
    data = safe_fetch(url, params=params, timeout=15, headers=headers)
    if not data:
        return {"status": "error", "note": "NWS API unavailable or location outside US", "alerts": []}
    
    alerts = []
    for feature in data.get("features", [])[:30]:
        props = feature.get("properties", {})
        
        alerts.append({
            "event": props.get("event"),
            "headline": props.get("headline"),
            "severity": props.get("severity"),
            "urgency": props.get("urgency"),
            "certainty": props.get("certainty"),
            "areas": props.get("areaDesc"),
            "onset": props.get("onset"),
            "expires": props.get("expires"),
            "description": props.get("description", "")[:500],
            "instruction": props.get("instruction", "")[:300],
            "sender": props.get("senderName"),
        })
    
    # Group by severity
    by_severity = {}
    for alert in alerts:
        sev = alert.get("severity", "Unknown")
        by_severity[sev] = by_severity.get(sev, 0) + 1
    
    return {
        "status": "ok",
        "count": len(alerts),
        "by_severity": by_severity,
        "alerts": alerts,
        "note": "US locations only"
    }


# === 8. NASA EONET - NATURAL EVENTS ===

def fetch_natural_events(limit: int = 20, category: str = None, days: int = 30) -> dict:
    """Fetch natural events from NASA EONET"""
    params = {"status": "open", "limit": limit}
    if category:
        params["category"] = category
    
    data = safe_fetch(NASA_URLS["eonet_events"], params=params, timeout=15)
    if not data:
        return {"status": "error", "events": []}
    
    events = []
    for event in data.get("events", [])[:limit]:
        geometry = event.get("geometry", [{}])[-1] if event.get("geometry") else {}
        
        events.append({
            "id": event.get("id"),
            "title": event.get("title"),
            "category": event.get("categories", [{}])[0].get("title") if event.get("categories") else None,
            "date": geometry.get("date"),
            "coordinates": geometry.get("coordinates"),
            "sources": [s.get("url") for s in event.get("sources", [])][:2],
            "closed": event.get("closed"),
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


def fetch_nearby_natural_events(lat: float, lon: float, radius_km: float = 1000) -> dict:
    """Find natural events near a location"""
    all_events = fetch_natural_events(limit=100)
    if all_events.get("status") != "ok":
        return all_events
    
    nearby = []
    for event in all_events.get("events", []):
        coords = event.get("coordinates")
        if coords and len(coords) >= 2:
            event_lon, event_lat = coords[0], coords[1]
            dist = calculate_distance(lat, lon, event_lat, event_lon)
            
            if dist <= radius_km:
                event["distance_km"] = round(dist, 1)
                nearby.append(event)
    
    nearby.sort(key=lambda x: x.get("distance_km", 9999))
    
    return {
        "status": "ok",
        "location": {"lat": lat, "lon": lon},
        "radius_km": radius_km,
        "count": len(nearby),
        "events": nearby[:20]
    }


# === 9. OPEN-METEO FUNCTIONS ===

def fetch_weather(lat: float, lon: float) -> dict:
    """Fetch current weather conditions"""
    params = {
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,wind_gusts_10m,pressure_msl,visibility",
        "timezone": "auto"
    }
    
    if OPEN_METEO_API_KEY:
        params["apikey"] = OPEN_METEO_API_KEY
    
    data = safe_fetch(OPEN_METEO_URLS["weather"], params=params)
    if not data:
        return {"status": "error"}
    
    current = data.get("current", {})
    
    # Weather code interpretation
    codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers",
        82: "Violent rain showers", 85: "Slight snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }
    
    return {
        "status": "ok",
        "temperature": {
            "actual": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "unit": "°C"
        },
        "humidity": current.get("relative_humidity_2m"),
        "precipitation": current.get("precipitation"),
        "weather": codes.get(current.get("weather_code", 0), "Unknown"),
        "weather_code": current.get("weather_code"),
        "cloud_cover": current.get("cloud_cover"),
        "visibility": current.get("visibility"),
        "wind": {
            "speed": current.get("wind_speed_10m"),
            "gusts": current.get("wind_gusts_10m"),
            "direction": current.get("wind_direction_10m"),
            "unit": "km/h"
        },
        "pressure": current.get("pressure_msl"),
        "time": current.get("time")
    }


def fetch_air_quality(lat: float, lon: float) -> dict:
    """Fetch air quality data"""
    params = {
        "latitude": lat, "longitude": lon,
        "current": "european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,dust,uv_index,uv_index_clear_sky",
        "timezone": "auto"
    }
    
    if OPEN_METEO_API_KEY:
        params["apikey"] = OPEN_METEO_API_KEY
    
    data = safe_fetch(OPEN_METEO_URLS["air_quality"], params=params, timeout=15)
    if not data:
        return {"status": "error"}
    
    current = data.get("current", {})
    eu_aqi = current.get("european_aqi", 0) or 0
    us_aqi = current.get("us_aqi", 0) or 0
    
    # EU AQI categories
    if eu_aqi <= 20: eu_cat = "Good"
    elif eu_aqi <= 40: eu_cat = "Fair"
    elif eu_aqi <= 60: eu_cat = "Moderate"
    elif eu_aqi <= 80: eu_cat = "Poor"
    elif eu_aqi <= 100: eu_cat = "Very Poor"
    else: eu_cat = "Hazardous"
    
    # US AQI categories
    if us_aqi <= 50: us_cat = "Good"
    elif us_aqi <= 100: us_cat = "Moderate"
    elif us_aqi <= 150: us_cat = "Unhealthy for Sensitive Groups"
    elif us_aqi <= 200: us_cat = "Unhealthy"
    elif us_aqi <= 300: us_cat = "Very Unhealthy"
    else: us_cat = "Hazardous"
    
    return {
        "status": "ok",
        "european_aqi": {"value": eu_aqi, "category": eu_cat},
        "us_aqi": {"value": us_aqi, "category": us_cat},
        "pollutants": {
            "pm2_5": {"value": current.get("pm2_5"), "unit": "μg/m³"},
            "pm10": {"value": current.get("pm10"), "unit": "μg/m³"},
            "no2": {"value": current.get("nitrogen_dioxide"), "unit": "μg/m³"},
            "o3": {"value": current.get("ozone"), "unit": "μg/m³"},
            "so2": {"value": current.get("sulphur_dioxide"), "unit": "μg/m³"},
            "co": {"value": current.get("carbon_monoxide"), "unit": "μg/m³"},
        },
        "dust": current.get("dust"),
        "uv_index": current.get("uv_index"),
        "time": current.get("time")
    }


def fetch_uv_index(lat: float, lon: float) -> dict:
    """Fetch UV index with recommendations"""
    params = {
        "latitude": lat, "longitude": lon,
        "current": "uv_index,uv_index_clear_sky",
        "timezone": "auto"
    }
    
    if OPEN_METEO_API_KEY:
        params["apikey"] = OPEN_METEO_API_KEY
    
    data = safe_fetch(OPEN_METEO_URLS["air_quality"], params=params)
    if not data:
        return {"status": "error"}
    
    current = data.get("current", {})
    uv = current.get("uv_index", 0) or 0
    
    if uv <= 2:
        category, recommendation = "Low", "No protection needed"
    elif uv <= 5:
        category, recommendation = "Moderate", "Wear sunglasses, use SPF 30+"
    elif uv <= 7:
        category, recommendation = "High", "Reduce sun exposure 10am-4pm, wear hat & sunscreen"
    elif uv <= 10:
        category, recommendation = "Very High", "Minimize outdoor time, seek shade, SPF 50+"
    else:
        category, recommendation = "Extreme", "Avoid sun exposure, stay indoors if possible"
    
    return {
        "status": "ok",
        "uv_index": round(uv, 1),
        "uv_index_clear_sky": current.get("uv_index_clear_sky"),
        "category": category,
        "recommendation": recommendation,
        "time": current.get("time")
    }


def fetch_pollen(lat: float, lon: float) -> dict:
    """Fetch pollen forecast (Europe only)"""
    params = {
        "latitude": lat, "longitude": lon,
        "current": "alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen",
        "timezone": "auto"
    }
    
    if OPEN_METEO_API_KEY:
        params["apikey"] = OPEN_METEO_API_KEY
    
    data = safe_fetch(OPEN_METEO_URLS["air_quality"], params=params)
    if not data:
        return {"status": "error", "note": "Europe only"}
    
    current = data.get("current", {})
    
    def level(v):
        if v is None or v < 10: return "Low"
        elif v < 50: return "Moderate"
        elif v < 100: return "High"
        else: return "Very High"
    
    pollen_types = {
        "grass": current.get("grass_pollen"),
        "birch": current.get("birch_pollen"),
        "alder": current.get("alder_pollen"),
        "mugwort": current.get("mugwort_pollen"),
        "olive": current.get("olive_pollen"),
        "ragweed": current.get("ragweed_pollen"),
    }
    
    pollen_data = {}
    high_pollen = []
    for name, value in pollen_types.items():
        lvl = level(value)
        pollen_data[name] = {"value": value, "level": lvl, "unit": "grains/m³"}
        if lvl in ["High", "Very High"]:
            high_pollen.append(name)
    
    return {
        "status": "ok",
        "pollen": pollen_data,
        "high_pollen_alert": high_pollen if high_pollen else None,
        "note": "Europe only, seasonal availability"
    }


def fetch_flood_data(lat: float, lon: float) -> dict:
    """Fetch river discharge and flood forecast"""
    params = {
        "latitude": lat, "longitude": lon,
        "daily": "river_discharge,river_discharge_mean,river_discharge_max",
        "forecast_days": 7
    }
    
    if OPEN_METEO_API_KEY:
        params["apikey"] = OPEN_METEO_API_KEY
    
    data = safe_fetch(OPEN_METEO_URLS["flood"], params=params, timeout=15)
    if not data:
        return {"status": "error", "note": "No river data for this location"}
    
    daily = data.get("daily", {})
    discharge = daily.get("river_discharge", [])
    times = daily.get("time", [])
    
    if not discharge or all(d is None for d in discharge):
        return {"status": "no_data", "note": "No major river at this location"}
    
    valid_discharge = [d for d in discharge if d is not None]
    if not valid_discharge:
        return {"status": "no_data", "note": "No discharge data available"}
    
    max_discharge = max(valid_discharge)
    avg_discharge = sum(valid_discharge) / len(valid_discharge)
    current_discharge = valid_discharge[0] if valid_discharge else None
    
    # Flood risk assessment
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
            "current": current_discharge,
            "max_forecast": max_discharge,
            "average": round(avg_discharge, 1),
            "unit": "m³/s"
        },
        "flood_risk": risk,
        "forecast": forecast[:7]
    }


def fetch_marine_data(lat: float, lon: float) -> dict:
    """Fetch marine/ocean conditions"""
    params = {
        "latitude": lat, "longitude": lon,
        "current": "wave_height,wave_direction,wave_period,swell_wave_height,swell_wave_direction,swell_wave_period",
        "timezone": "auto"
    }
    
    if OPEN_METEO_API_KEY:
        params["apikey"] = OPEN_METEO_API_KEY
    
    data = safe_fetch(OPEN_METEO_URLS["marine"], params=params, timeout=15)
    if not data:
        return {"status": "error", "note": "No marine data (location not near coast)"}
    
    current = data.get("current", {})
    wave_height = current.get("wave_height")
    
    if wave_height is None:
        return {"status": "no_data", "note": "Location not near coast"}
    
    # Sea conditions assessment
    if wave_height > 6: danger = "Very Rough - Dangerous"
    elif wave_height > 4: danger = "Rough"
    elif wave_height > 2.5: danger = "Moderate to Rough"
    elif wave_height > 1: danger = "Slight to Moderate"
    else: danger = "Calm"
    
    return {
        "status": "ok",
        "waves": {
            "height": wave_height,
            "direction": current.get("wave_direction"),
            "period": current.get("wave_period"),
            "unit": "m"
        },
        "swell": {
            "height": current.get("swell_wave_height"),
            "direction": current.get("swell_wave_direction"),
            "period": current.get("swell_wave_period"),
        },
        "sea_conditions": danger,
        "time": current.get("time")
    }


# === 10. API ENDPOINTS ===

@app.get("/")
def read_root():
    """API root - list all available endpoints"""
    return {
        "status": "online",
        "version": "6.0.0 - Complete Environmental Suite",
        "data_sources": {
            "space_weather": "NOAA SWPC (Public Domain)",
            "earthquakes": "USGS (Public Domain)",
            "us_weather_alerts": "NWS (Public Domain)",
            "natural_events": "NASA EONET (Public Domain)",
            "weather_environment": "Open-Meteo (CC BY 4.0 - Commercial license required)"
        },
        "endpoints": {
            "main": {
                "/alert/": "Complete environmental alert for location",
                "/all/": "All data combined for location",
            },
            "space_weather": {
                "/space-weather/": "All space weather data",
                "/space-weather/kp/": "Kp index only",
                "/aurora/": "Aurora forecast with location probability",
                "/space-weather/alerts/": "Space weather alerts/warnings",
            },
            "earthquakes": {
                "/earthquakes/": "Recent earthquakes worldwide",
                "/earthquakes/nearby/": "Earthquakes near location",
                "/earthquakes/significant/": "Significant earthquakes (month)",
            },
            "us_alerts": {
                "/nws-alerts/": "US weather alerts (NWS)",
            },
            "natural_events": {
                "/natural-events/": "Active natural events (EONET)",
                "/natural-events/nearby/": "Events near location",
            },
            "environment": {
                "/weather/": "Current weather",
                "/air-quality/": "Air quality & pollutants",
                "/uv/": "UV index",
                "/pollen/": "Pollen forecast (Europe)",
                "/floods/": "Flood/river forecast",
                "/marine/": "Marine conditions",
            }
        }
    }


# --- Space Weather Endpoints ---

@app.get("/space-weather/")
def get_space_weather():
    """Get comprehensive space weather data"""
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "NOAA SWPC (Public Domain)",
        "kp_index": fetch_kp_index(),
        "solar_wind": fetch_solar_wind(),
        "xray": fetch_xray_flux(),
        "protons": fetch_proton_flux(),
        "recent_flares": fetch_recent_flares(),
    }


@app.get("/space-weather/kp/")
def get_kp_index():
    """Get current Kp index"""
    return fetch_kp_index()


@app.get("/aurora/")
def get_aurora(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON)):
    """Get aurora forecast with probability for location"""
    return fetch_aurora_forecast(lat, lon)


@app.get("/space-weather/alerts/")
def get_space_weather_alerts():
    """Get active space weather alerts"""
    return fetch_space_weather_alerts()


# --- Earthquake Endpoints ---

@app.get("/earthquakes/")
def get_earthquakes(min_magnitude: float = Query(2.5), hours: int = Query(24)):
    """Get recent earthquakes worldwide"""
    return fetch_earthquakes(min_magnitude, hours)


@app.get("/earthquakes/nearby/")
def get_nearby_earthquakes(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    radius: float = Query(500),
    hours: int = Query(24)
):
    """Get earthquakes near a location"""
    return fetch_nearby_earthquakes(lat, lon, radius, hours)


@app.get("/earthquakes/significant/")
def get_significant_earthquakes():
    """Get significant earthquakes from past month"""
    return fetch_significant_earthquakes()


# --- NWS Alerts Endpoint (US Only) ---

@app.get("/nws-alerts/")
def get_nws_alerts(
    state: str = Query(None, description="US state code (e.g., CA, TX, NY)"),
    lat: float = Query(None),
    lon: float = Query(None)
):
    """Get US weather alerts from National Weather Service"""
    return fetch_nws_alerts(state, lat, lon)


# --- Natural Events Endpoints ---

@app.get("/natural-events/")
def get_natural_events(
    limit: int = Query(20),
    category: str = Query(None, description="wildfires, severeStorms, volcanoes, seaLakeIce, earthquakes")
):
    """Get active natural events worldwide"""
    return fetch_natural_events(limit, category)


@app.get("/natural-events/nearby/")
def get_nearby_natural_events(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    radius: float = Query(1000)
):
    """Get natural events near a location"""
    return fetch_nearby_natural_events(lat, lon, radius)


# --- Environment Endpoints ---

@app.get("/weather/")
def get_weather(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON)):
    """Get current weather conditions"""
    return fetch_weather(lat, lon)


@app.get("/air-quality/")
def get_air_quality(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON)):
    """Get air quality data"""
    return fetch_air_quality(lat, lon)


@app.get("/uv/")
def get_uv(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON)):
    """Get UV index with recommendations"""
    return fetch_uv_index(lat, lon)


@app.get("/pollen/")
def get_pollen(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON)):
    """Get pollen forecast (Europe only)"""
    return fetch_pollen(lat, lon)


@app.get("/floods/")
def get_floods(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON)):
    """Get flood/river discharge forecast"""
    return fetch_flood_data(lat, lon)


@app.get("/marine/")
def get_marine(lat: float = Query(DEFAULT_LAT), lon: float = Query(DEFAULT_LON)):
    """Get marine conditions (coastal locations)"""
    return fetch_marine_data(lat, lon)


# --- Combined Endpoints ---

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
            "protons": fetch_proton_flux(),
            "aurora": fetch_aurora_forecast(lat, lon),
        },
        "earthquakes": fetch_nearby_earthquakes(lat, lon, 1000),
        "natural_events": fetch_nearby_natural_events(lat, lon, 1000),
        "environment": {
            "weather": fetch_weather(lat, lon),
            "air_quality": fetch_air_quality(lat, lon),
            "uv": fetch_uv_index(lat, lon),
            "pollen": fetch_pollen(lat, lon),
        },
        "hazards": {
            "floods": fetch_flood_data(lat, lon),
            "marine": fetch_marine_data(lat, lon),
        }
    }


# === 11. MAIN ALERT ENDPOINT ===

def calculate_overall_risk(data: dict) -> tuple[str, list]:
    """Calculate overall risk level from all data sources"""
    risks = []
    score = 0
    
    # Space Weather
    kp = data.get("space", {}).get("kp_index", {}).get("value") or 0
    if kp >= 8: score += 4; risks.append(f"🌞 Extreme geomagnetic storm (Kp={kp})")
    elif kp >= 7: score += 3; risks.append(f"🌞 Severe geomagnetic storm (Kp={kp})")
    elif kp >= 5: score += 2; risks.append(f"🌞 Geomagnetic storm (Kp={kp})")
    
    xray = data.get("space", {}).get("xray", {}).get("level", "")
    if xray.startswith("X"): score += 3; risks.append(f"☀️ X-class solar flare ({xray})")
    elif xray.startswith("M"): score += 2; risks.append(f"☀️ M-class solar flare ({xray})")
    
    # Earthquakes
    eq_nearby = data.get("earthquakes", {}).get("count", 0)
    if eq_nearby > 0:
        max_mag = data.get("earthquakes", {}).get("earthquakes", [{}])[0].get("magnitude", 0)
        if max_mag >= 6: score += 4; risks.append(f"🌍 Major earthquake nearby (M{max_mag})")
        elif max_mag >= 5: score += 3; risks.append(f"🌍 Significant earthquake nearby (M{max_mag})")
        elif max_mag >= 4: score += 2; risks.append(f"🌍 Moderate earthquake nearby (M{max_mag})")
    
    # Natural Events
    events_nearby = data.get("natural_events", {}).get("count", 0)
    if events_nearby > 0:
        for event in data.get("natural_events", {}).get("events", [])[:3]:
            risks.append(f"⚠️ {event.get('category', 'Event')}: {event.get('title', 'Unknown')}")
            score += 2
    
    # Air Quality
    aqi = data.get("environment", {}).get("air_quality", {}).get("european_aqi", {}).get("value") or 0
    if aqi > 100: score += 3; risks.append(f"💨 Hazardous air quality (AQI {aqi})")
    elif aqi > 80: score += 2; risks.append(f"💨 Very poor air quality (AQI {aqi})")
    elif aqi > 60: score += 1; risks.append(f"💨 Poor air quality (AQI {aqi})")
    
    # UV
    uv = data.get("environment", {}).get("uv", {}).get("uv_index") or 0
    if uv >= 11: score += 2; risks.append(f"☀️ Extreme UV ({uv})")
    elif uv >= 8: score += 1; risks.append(f"☀️ Very high UV ({uv})")
    
    # Floods
    flood_risk = data.get("hazards", {}).get("floods", {}).get("flood_risk", "None")
    if flood_risk == "High": score += 3; risks.append("🌊 High flood risk")
    elif flood_risk == "Moderate": score += 2; risks.append("🌊 Moderate flood risk")
    
    # Determine level
    if score >= 8: level = "Critical"
    elif score >= 5: level = "High"
    elif score >= 3: level = "Medium"
    elif score >= 1: level = "Low-Medium"
    else: level = "Low"
    
    return level, risks


def generate_comprehensive_advice(profile: str, data: dict, risk_level: str) -> str:
    """Generate advice based on profile and all data"""
    profile_lower = profile.lower()
    
    weather = data.get("environment", {}).get("weather", {})
    temp = weather.get("temperature", {}).get("actual", "N/A")
    conditions = weather.get("weather", "Unknown")
    
    kp = data.get("space", {}).get("kp_index", {}).get("value", 0) or 0
    aqi = data.get("environment", {}).get("air_quality", {}).get("european_aqi", {}).get("value", 0) or 0
    uv = data.get("environment", {}).get("uv", {}).get("uv_index", 0) or 0
    
    eq_count = data.get("earthquakes", {}).get("count", 0)
    events_count = data.get("natural_events", {}).get("count", 0)
    
    base = f"Weather: {temp}°C, {conditions}. "
    
    if "pilot" in profile_lower or "aviation" in profile_lower:
        advice = f"🛩️ Aviation Advisory: {base}"
        if kp >= 5: advice += f"CAUTION: Geomagnetic storm (Kp={kp}) - HF radio degradation likely. "
        xray = data.get("space", {}).get("xray", {}).get("level", "")
        if xray.startswith(("X", "M")): advice += f"Solar flare {xray} - possible radio blackouts. "
        if eq_count > 0: advice += f"Seismic activity reported in region. "
        return advice
    
    elif "aurora" in profile_lower or "northern lights" in profile_lower:
        aurora = data.get("space", {}).get("aurora", {})
        prob = aurora.get("probability", 0)
        if kp >= 7: return f"🌌 EXCELLENT! Kp={kp}, {prob}% probability - Aurora visible at mid-latitudes! Get away from city lights!"
        elif kp >= 5: return f"🌌 Good conditions: Kp={kp}, {prob}% probability. Best viewing after midnight, away from light pollution."
        elif kp >= 4: return f"🌌 Possible aurora at high latitudes: Kp={kp}, {prob}% probability."
        return f"🌌 Low aurora activity: Kp={kp}, {prob}% probability. Need Kp 4+ for visible aurora."
    
    elif "asthma" in profile_lower or "respiratory" in profile_lower or "allergy" in profile_lower:
        aqi_cat = data.get("environment", {}).get("air_quality", {}).get("european_aqi", {}).get("category", "N/A")
        pm25 = data.get("environment", {}).get("air_quality", {}).get("pollutants", {}).get("pm2_5", {}).get("value")
        advice = f"🫁 Air Quality: {aqi_cat} (AQI {aqi}). "
        if pm25: advice += f"PM2.5: {pm25} μg/m³. "
        if aqi > 60: advice += "Consider limiting outdoor activity. "
        
        pollen = data.get("environment", {}).get("pollen", {}).get("high_pollen_alert")
        if pollen: advice += f"⚠️ High pollen: {', '.join(pollen)}. "
        return advice
    
    elif "outdoor" in profile_lower or "sport" in profile_lower or "hiking" in profile_lower:
        advice = f"🏃 Outdoor Advisory: {base}"
        if uv >= 6: advice += f"UV {uv} - sun protection essential. "
        if aqi > 60: advice += f"Moderate air quality - reduce intense exercise. "
        
        flood_risk = data.get("hazards", {}).get("floods", {}).get("flood_risk")
        if flood_risk in ["High", "Moderate"]: advice += f"⚠️ Flood risk: {flood_risk}. "
        
        if eq_count > 0: advice += f"Seismic activity in area ({eq_count} recent earthquakes). "
        if events_count > 0: advice += f"⚠️ {events_count} natural events in region. "
        return advice
    
    elif "marine" in profile_lower or "sailing" in profile_lower or "boat" in profile_lower:
        marine = data.get("hazards", {}).get("marine", {})
        sea_cond = marine.get("sea_conditions", "Unknown")
        wave_h = marine.get("waves", {}).get("height")
        advice = f"⛵ Marine Advisory: Sea conditions: {sea_cond}. "
        if wave_h: advice += f"Wave height: {wave_h}m. "
        if kp >= 5: advice += f"GPS accuracy may be affected (Kp={kp}). "
        return advice
    
    else:  # General Public
        advice = base
        
        # Add most relevant warnings
        if risk_level in ["Critical", "High"]:
            advice += "⚠️ ELEVATED RISK - Check specific warnings. "
        
        if aqi > 60: advice += f"Air quality: {data.get('environment', {}).get('air_quality', {}).get('european_aqi', {}).get('category', 'N/A')}. "
        if uv >= 6: advice += f"UV: {uv} ({data.get('environment', {}).get('uv', {}).get('category', 'High')}). "
        if eq_count > 0: advice += f"Seismic activity nearby. "
        if events_count > 0: 
            event = data.get("natural_events", {}).get("events", [{}])[0]
            advice += f"Active event: {event.get('title', 'Unknown')}. "
        if kp >= 5: advice += f"Space weather active. "
        
        return advice


@app.get("/alert/")
def get_comprehensive_alert(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    profile: str = Query("General Public", description="Pilot, Aurora Hunter, Asthma, Outdoor/Sports, Marine, General Public")
):
    """Generate comprehensive environmental alert for location"""
    
    # Gather all data
    data = {
        "space": {
            "kp_index": fetch_kp_index(),
            "solar_wind": fetch_solar_wind(),
            "xray": fetch_xray_flux(),
            "protons": fetch_proton_flux(),
            "aurora": fetch_aurora_forecast(lat, lon),
        },
        "earthquakes": fetch_nearby_earthquakes(lat, lon, 500),
        "natural_events": fetch_nearby_natural_events(lat, lon, 500),
        "environment": {
            "weather": fetch_weather(lat, lon),
            "air_quality": fetch_air_quality(lat, lon),
            "uv": fetch_uv_index(lat, lon),
            "pollen": fetch_pollen(lat, lon),
        },
        "hazards": {
            "floods": fetch_flood_data(lat, lon),
            "marine": fetch_marine_data(lat, lon),
        }
    }
    
    # Calculate risk
    risk_level, risk_factors = calculate_overall_risk(data)
    
    # Generate advice
    advice = generate_comprehensive_advice(profile, data, risk_level)
    
    # Create summary
    summary = {
        "kp_index": data["space"]["kp_index"].get("value"),
        "solar_wind_speed": data["space"]["solar_wind"].get("speed"),
        "xray_level": data["space"]["xray"].get("level"),
        "aurora_probability": data["space"]["aurora"].get("probability"),
        "earthquakes_nearby": data["earthquakes"].get("count", 0),
        "natural_events_nearby": data["natural_events"].get("count", 0),
        "temperature": data["environment"]["weather"].get("temperature", {}).get("actual"),
        "weather": data["environment"]["weather"].get("weather"),
        "air_quality_aqi": data["environment"]["air_quality"].get("european_aqi", {}).get("value"),
        "uv_index": data["environment"]["uv"].get("uv_index"),
        "flood_risk": data["hazards"]["floods"].get("flood_risk"),
    }
    
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "location": {"lat": lat, "lon": lon},
        "profile": profile,
        "risk": {
            "level": risk_level,
            "factors": risk_factors
        },
        "advice": advice,
        "summary": summary,
        "data": data
    }


# === 12. DEBUG ENDPOINT ===

@app.get("/debug/")
def debug():
    """Debug endpoint to check API status"""
    return {
        "config": {
            "nasa_api_key": "configured" if NASA_API_KEY != "DEMO_KEY" else "using DEMO_KEY",
            "hf_api_key": "configured" if HF_API_KEY else "not set",
            "open_meteo_api_key": "configured (commercial)" if OPEN_METEO_API_KEY else "not set (free tier)",
        },
        "tests": {
            "noaa_kp": fetch_kp_index().get("status"),
            "usgs_earthquakes": fetch_earthquakes(4.5, 24).get("status"),
            "nasa_eonet": fetch_natural_events(3).get("status"),
            "open_meteo_weather": fetch_weather(DEFAULT_LAT, DEFAULT_LON).get("status"),
        }
    }


# === 13. MAIN ===

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
