import os
import re
import json
import requests
from flask import Flask, request, jsonify
from geopy.distance import geodesic

# Try import googlemaps safely
try:
    import googlemaps
except ImportError:
    googlemaps = None

app = Flask(__name__)

# -----------------------------
# 🔑 Environment setup
# -----------------------------
GMAPS_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=GMAPS_KEY) if googlemaps and GMAPS_KEY else None


# -----------------------------
# 🧩 Helper: Safe key extraction
# -----------------------------
def safe_get(d, *keys):
    if not isinstance(d, dict):
        return None
    for k in keys:
        for variant in [k, k.lower(), k.upper()]:
            if variant in d and d[variant] not in [None, ""]:
                return d[variant]
    return None


# -----------------------------
# 🕓 Extract duration & direction
# -----------------------------
def extract_duration_direction(text):
    if not text:
        return {"duration": None, "direction": None}

    t = text.lower()
    duration_match = re.search(r"(month|week|two weeks|day|days|months|weeks)", t)

    direction = None
    if any(word in t for word in ["going", "depart", "one way", "ذهاب"]):
        direction = "going"
    elif any(word in t for word in ["return", "back", "round", "عودة"]):
        direction = "return"

    return {
        "duration": duration_match.group(0) if duration_match else None,
        "direction": direction
    }


# -----------------------------
# 📍 Geocode address
# -----------------------------
def geocode_address(address):
    if not address:
        return {"formatted_address": None}

    # If Google API is not configured
    if not gmaps:
        return {"formatted_address": address, "note": "Google Maps API not configured"}

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

    except Exception as e:
        return {"formatted_address": address, "error": str(e)}


# -----------------------------
# 📏 Compute distance
# -----------------------------
def compute_distance(p1, p2):
    try:
        if not (p1 and p2 and p1.get("lat") and p2.get("lat")):
            return None
        return round(geodesic((p1["lat"], p1["lng"]), (p2["lat"], p2["lng"])).kilometers, 3)
    except Exception:
        return None


# -----------------------------
# 🚀 Main Endpoint
# -----------------------------
@app.route("/extract", methods=["POST"])
def extract():
    try:
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
                    return geocode_address(address)
            elif isinstance(point, str):
                return geocode_address(point)
            return None

        pickup_info = normalize_point(pickup)
        dropoff_info = normalize_point(dropoff)
        distance_km = compute_distance(pickup_info, dropoff_info)

        result = {
            "pickup": pickup_info or {},
            "dropoff": dropoff_info or {},
            "distance_km": distance_km,
            "duration": duration_info.get("duration"),
            "direction": duration_info.get("direction"),
            "status": "success"
        }

        # Add a note if Google API not configured
        if not GMAPS_KEY:
            result["note"] = "⚠️ Google Maps API key not configured – geocoding skipped."

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e), "status": "failed"}), 500


# -----------------------------
# 🌐 Root Endpoint
# -----------------------------
@app.route("/")
def home():
    return jsonify({
        "message": "✅ Smart Location API v2 is running",
        "usage": "Send POST request to /extract with a 'data' JSON object."
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
