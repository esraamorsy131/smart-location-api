import os
import json
from flask import Flask, request, jsonify
from math import radians, sin, cos, sqrt, atan2

try:
    import googlemaps
except:
    googlemaps = None

app = Flask(__name__)

# --- Google Maps API ---
GMAPS_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=GMAPS_KEY) if googlemaps and GMAPS_KEY else None

# --- Helpers ---
def safe_get(d, *keys):
    for k in keys:
        for v in [k, k.lower(), k.upper()]:
            if isinstance(d, dict) and v in d and d[v] is not None:
                return d[v]
    return None

def geocode_address(address):
    if not gmaps or not address:
        return {"formatted_address": address}
    try:
        res = gmaps.geocode(address)
        if not res:
            return {"formatted_address": address}
        r = res[0]
        loc = r["geometry"]["location"]
        comps = {c["types"][0]: c["long_name"] for c in r["address_components"]}
        return {
            "formatted_address": r.get("formatted_address"),
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
            "city": comps.get("locality") or comps.get("administrative_area_level_2"),
            "district": comps.get("sublocality") or comps.get("neighborhood"),
        }
    except:
        return {"formatted_address": address}

def haversine(lat1, lon1, lat2, lon2):
    if not all([lat1, lon1, lat2, lon2]):
        return None
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return round(R * 2 * atan2(sqrt(a), sqrt(1 - a)), 2)

def translate_duration(dur):
    mapping = {
        "day": "يوم",
        "days": "أيام",
        "week": "أسبوع",
        "weeks": "أسابيع",
        "two weeks": "أسبوعين",
        "month": "شهر",
        "months": "شهور"
    }
    return mapping.get(dur, dur)

def translate_direction(dir):
    mapping = {"going": "ذهاب", "return": "عودة"}
    return mapping.get(dir, dir)

# --- normalize pickup/dropoff ---
def normalize_point(point):
    if isinstance(point, dict):
        lat = safe_get(point, "lat", "latitude")
        lng = safe_get(point, "lng", "longitude")
        address = safe_get(point, "address", "formattedAddress", "formatted_address")
        if lat and lng:
            return {"lat": float(lat), "lng": float(lng), "formatted_address": address}
        elif address:
            return geocode_address(address)
    elif isinstance(point, str):
        return geocode_address(point)
    return None

# --- extract duration/direction from columns ---
def extract_duration_direction(duration, direction):
    return {
        "duration_en": duration,
        "direction_en": direction,
        "duration_ar": translate_duration(duration),
        "direction_ar": translate_direction(direction)
    }

# --- Flask route ---
@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json(force=True)
    
    pickup = safe_get(data, "pickup", "origin", "from")
    dropoff = safe_get(data, "dropoff", "destination", "to")
    duration = safe_get(data, "duration")
    direction = safe_get(data, "direction")
    
    pickup_info = normalize_point(pickup)
    dropoff_info = normalize_point(dropoff)
    distance_km = haversine(pickup_info.get("lat"), pickup_info.get("lng"),
                            dropoff_info.get("lat"), dropoff_info.get("lng")) if pickup_info and dropoff_info else None

    dur_dir = extract_duration_direction(duration, direction)
    
    result = {
        "pickup": pickup_info,
        "dropoff": dropoff_info,
        "distance_km": distance_km,
        **dur_dir
    }
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
