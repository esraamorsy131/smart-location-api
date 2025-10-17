from flask import Flask, request, jsonify
import json
import math
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


# --- Helper: Calculate distance between two coordinates (Haversine formula) ---
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (math.sin(d_phi / 2) ** 2) + math.cos(phi1) * math.cos(phi2) * (math.sin(d_lambda / 2) ** 2)
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


# --- Helper: Smart extraction from JSON string or dict ---
def smart_extract_location(raw_value):
    try:
        # If it's a string that looks like JSON
        if isinstance(raw_value, str):
            raw_value = json.loads(raw_value)
    except Exception:
        return {"city": None, "district": None, "lat": None, "lng": None}

    if not isinstance(raw_value, dict):
        return {"city": None, "district": None, "lat": None, "lng": None}

    formatted_address = raw_value.get("formattedAddress", "") or ""
    city, district = None, None

    # Smart detection: Arabic patterns
    if "حي" in formatted_address:
        parts = formatted_address.split("حي")
        if len(parts) > 1:
            district = "حي" + parts[1].split("،")[0].strip()

    # Try detecting city (last part before 'Saudi Arabia')
    if "Saudi Arabia" in formatted_address:
        city = formatted_address.split(",")[-2].strip()

    return {
        "city": city,
        "district": district,
        "lat": raw_value.get("latitude"),
        "lng": raw_value.get("longitude")
    }


@app.route("/process", methods=["POST"])
def process_data():
    data = request.get_json()

    # Handle malformed inputs
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return jsonify({"error": "Invalid JSON format"}), 400

    if isinstance(data, dict):
        data = [data]

    results = []

    for row in data:
        if not isinstance(row, dict):
            continue

        # Support different key names
        pickup_raw = row.get("pickup") or row.get("pick up") or ""
        dropoff_raw = row.get("dropoff") or row.get("drop off") or ""

        pickup_info = smart_extract_location(pickup_raw)
        dropoff_info = smart_extract_location(dropoff_raw)

        result = {
            "pickup_city": pickup_info.get("city"),
            "pickup_district": pickup_info.get("district"),
            "pickup_lat": pickup_info.get("lat"),
            "pickup_lng": pickup_info.get("lng"),
            "dropoff_city": dropoff_info.get("city"),
            "dropoff_district": dropoff_info.get("district"),
            "dropoff_lat": dropoff_info.get("lat"),
            "dropoff_lng": dropoff_info.get("lng"),
        }

        # Calculate distance if lat/lng available
        if pickup_info["lat"] and dropoff_info["lat"]:
            result["distance_km"] = haversine_distance(
                pickup_info["lat"], pickup_info["lng"],
                dropoff_info["lat"], dropoff_info["lng"]
            )
        else:
            result["distance_km"] = None

        results.append(result)

    return jsonify(results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
