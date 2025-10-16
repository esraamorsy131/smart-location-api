import os
import re
import json
from flask import Flask, request, jsonify
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

# --- Helper: Safe get ---
def safe_get(d, *keys):
    for k in keys:
        for variant in [k, k.lower(), k.upper()]:
            if isinstance(d, dict) and variant in d and d[variant]:
                return d[variant]
    return None

# --- Helper: Duration / Direction extraction ---
def extract_duration_direction(text):
    if not text:
        return {"duration": None, "direction": None}
    t = text.lower()
    duration_match = re.search(r"(month|week|two weeks|day|days|months|weeks)", t)
    direction = None
    if any(x in t for x in ["going", "depart", "one way"]):
        direction = "going"
    elif any(x in t for x in ["return", "back", "round"]):
        direction = "return"
    return {"duration": duration_match.group(0) if duration_match else None, "direction": direction}

# --- Helper: Simple Haversine distance ---
def haversine(lat1, lon1, lat2, lon2):
    if not all([lat1, lon1, lat2, lon2]):
        return None
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

@app.route("/")
def home():
    return jsonify({"message": "✅ Smart Location API Lite is running", "usage": "POST /extract with a 'data' JSON object"})

@app.route("/extract", methods=["POST"])
def extract():
    payload = request.get_json(force=True)
    data = payload.get("data", payload)

    pickup = safe_get(data, "pickup", "origin", "from")
    dropoff = safe_get(data, "dropoff", "destination", "to")
    trip_info = safe_get(data, "trip_info", "details", "info")

    duration_info = extract_duration_direction(json.dumps(trip_info or data))

    def normalize_point(point):
        if isinstance(point, dict):
            lat = safe_get(point, "lat", "latitude")
            lng = safe_get(point, "lng", "longitude")
            address = safe_get(point, "address", "formattedAddress", "formatted_address")
            return {
                "lat": float(lat) if lat else None,
                "lng": float(lng) if lng else None,
                "formatted_address": address
            }
        elif isinstance(point, str):
            return {"formatted_address": point}
        return None

    pickup_info = normalize_point(pickup)
    dropoff_info = normalize_point(dropoff)

    distance_km = None
    if pickup_info and dropoff_info and pickup_info["lat"] and dropoff_info["lat"]:
        distance_km = round(haversine(pickup_info["lat"], pickup_info["lng"],
                                      dropoff_info["lat"], dropoff_info["lng"]), 2)

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
