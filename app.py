from flask import Flask, request, jsonify
import requests
import math
import json

app = Flask(__name__)

GOOGLE_API_KEY = "YAIzaSyCQPCCKyScLV1CUElhBH5a8is8KFBjuYeA"  # 🔹 حطي هنا الـ API Key بتاعتك

# ---- Helper: Haversine Formula لحساب المسافة ----
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # نصف قطر الأرض بالكيلومتر
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# ---- Helper: Smart Extract ----
def smart_extract_location(data_str):
    try:
        data = json.loads(data_str)
    except:
        return None

    lat, lng, city, district = None, None, None, None

    # لو موجود lat/lng صريح
    for k, v in data.items():
        if 'lat' in k.lower(): lat = v
        if 'lng' in k.lower() or 'lon' in k.lower(): lng = v

    # لو موجود formatted_address أو placeName
    address = data.get("formatted_address") or data.get("placeName") or ""
    if address:
        params = {"address": address, "key": GOOGLE_API_KEY}
        res = requests.get("https://maps.googleapis.com/maps/api/geocode/json", params=params).json()
        if res["status"] == "OK":
            result = res["results"][0]
            loc = result["geometry"]["location"]
            lat, lng = loc["lat"], loc["lng"]
            for comp in result["address_components"]:
                if "locality" in comp["types"]:
                    city = comp["long_name"]
                if "sublocality" in comp["types"] or "neighborhood" in comp["types"]:
                    district = comp["long_name"]

    if lat and lng and not city:
        # Reverse geocoding لو مفيش city
        params = {"latlng": f"{lat},{lng}", "key": GOOGLE_API_KEY}
        res = requests.get("https://maps.googleapis.com/maps/api/geocode/json", params=params).json()
        if res["status"] == "OK":
            result = res["results"][0]
            for comp in result["address_components"]:
                if "locality" in comp["types"]:
                    city = comp["long_name"]
                if "sublocality" in comp["types"] or "neighborhood" in comp["types"]:
                    district = comp["long_name"]

    return {"city": city, "district": district, "lat": lat, "lng": lng}

@app.route("/process", methods=["POST"])
def process_data():
    rows = request.get_json()
    output = []

    for row in rows:
        pickup_info = smart_extract_location(row.get("pickup", ""))
        dropoff_info = smart_extract_location(row.get("dropoff", ""))

        if pickup_info and dropoff_info:
            dist_km = calculate_distance(
                pickup_info["lat"], pickup_info["lng"],
                dropoff_info["lat"], dropoff_info["lng"]
            )
        else:
            dist_km = None

        output.append({
            **row,
            "pickup_city": pickup_info.get("city"),
            "pickup_district": pickup_info.get("district"),
            "pickup_lat": pickup_info.get("lat"),
            "pickup_lng": pickup_info.get("lng"),
            "dropoff_city": dropoff_info.get("city"),
            "dropoff_district": dropoff_info.get("district"),
            "dropoff_lat": dropoff_info.get("lat"),
            "dropoff_lng": dropoff_info.get("lng"),
            "distance_km": dist_km
        })

    return jsonify(output)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
