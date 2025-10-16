import os
import re
import json
from flask import Flask, request, jsonify
from geopy.distance import geodesic

try:
    import googlemaps
except Exception:
    googlemaps = None

app = Flask(__name__)

GMAPS_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=GMAPS_KEY) if googlemaps and GMAPS_KEY else None

def safe_get(d, *keys):
    for k in keys:
        for variant in [k, k.lower(), k.upper()]:
            if isinstance(d, dict) and variant in d and d[variant]:
                return d[variant]
    return None

def extract_duration_direction(text):
    if not text:
        return {"duration": None, "direction": None}
    t = text.lower()
    duration_match = re.search(r"(month|week|two weeks|day|days|months|weeks)", t)
    direction = None
    if "going" in t or "depart" in t or "one way" in t:
        direction = "going"
    elif "return" in t or "back" in t or "round" in t:
        direction = "return"
    return {"duration": duration_match.group(0) if duration_match else None, "direction": direction}

def geocode_address(address):
    if not gmaps or not address:
        return {"formatted_address": address}
    try:
        res = gmaps.geocode(address)
        if not res:
            return {"formatted_address": address}
        r = res[0]
        loc = r["geometry"]["location"]
        components = {c["types"][0]: c["long_name"] for c in r["address_components"]}
        return {
            "formatted_address": r.get("formatted_address"),
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
            "city": components.get("locality") or components.get("administrative_area_level_2"),
            "district": components.get("sublocality") or components.get("neighborhood"),
        }
    except Exception:
        return {"formatted_address": address}

def compute_distance(p1, p2):
    try:
        return geodesic((p1["lat"], p1["lng"]), (p2["lat"], p2["lng"])).kilometers
    except Exception:
        return None

@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json(force=True)
    
    pickup = safe_get(data, "pickup", "pickup_location", "origin", "from")
    dropoff = safe_get(data, "dropoff", "dropoff_location", "destination", "to")
    duration_info = extract_duration_direction(json.dumps(data))

    def normalize_point(point):
        if isinstance(point, dict):
            lat = safe_get(point, "lat", "latitude")
            lng = safe_get(point, "lng", "longitude")
            address = safe_get(point, "address", "formattedAddress", "formatted_address")
            if lat and lng:
                return {"lat": float(lat), "lng": float(lng), "formatted_address": address}
            elif address:
                geo = geocode_address(address)
                return geo
        elif isinstance(point, str):
            geo = geocode_address(point)
            return geo
        return None

    pickup_info = normalize_point(pickup)
    dropoff_info = normalize_point(dropoff)
    distance_km = compute_distance(pickup_info, dropoff_info) if pickup_info and dropoff_info else None

    result = {
        "pickup": pickup_info,
        "dropoff": dropoff_info,
        "distance_km": distance_km,
        "duration": duration_info["duration"],
        "direction": duration_info["direction"]
    }
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
