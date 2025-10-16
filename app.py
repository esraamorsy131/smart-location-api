from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Union
import googlemaps
from math import radians, cos, sin, asin, sqrt
import json
from diskcache import Cache

API_KEY = 'YOUR_GOOGLE_MAPS_API_KEY'
gmaps = googlemaps.Client(key=API_KEY)

cache = Cache('location_cache')  # cache للـGoogle Maps

app = FastAPI()

class Trip(BaseModel):
    PickUp: Union[str, dict]
    DropOff: Union[str, dict]

class TripsBatch(BaseModel):
    trips: List[Trip]

# --- دالة extract مع cache و fallback ---
def extract_location_data(address):
    try:
        # لو العنوان JSON بدل نص
        if isinstance(address, dict):
            address = address.get('address', '')  

        if not address:
            return None, None, None, None

        # check cache
        if address in cache:
            return cache[address]

        geocode_result = gmaps.geocode(address)
        if not geocode_result:
            return None, None, None, None
        result = geocode_result[0]

        lat = result['geometry']['location']['lat']
        lng = result['geometry']['location']['lng']

        city = None
        district = None
        for comp in result['address_components']:
            if 'locality' in comp['types']:
                city = comp['long_name']
            if 'sublocality' in comp['types'] or 'neighborhood' in comp['types']:
                district = comp['long_name']
        if not district:
            district = city

        cache[address] = (city, district, lat, lng)  # حفظ في cache
        return city, district, lat, lng
    except:
        return None, None, None, None

# --- دالة حساب المسافة ---
def haversine(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371
    return c * r

# --- API endpoint batch ---
@app.post("/process_trips_batch/")
def process_trips_batch(batch: TripsBatch):
    results = []
    for trip in batch.trips:
        pickup_city, pickup_district, pickup_lat, pickup_lng = extract_location_data(trip.PickUp)
        drop_city, drop_district, drop_lat, drop_lng = extract_location_data(trip.DropOff)
        
        distance = None
        if pickup_lat and drop_lat:
            distance = haversine(pickup_lat, pickup_lng, drop_lat, drop_lng)
        
        results.append({
            "PickUp_City": pickup_city,
            "PickUp_District": pickup_district,
            "PickUp_Lat": pickup_lat,
            "PickUp_Lng": pickup_lng,
            "DropOff_City": drop_city,
            "DropOff_District": drop_district,
            "DropOff_Lat": drop_lat,
            "DropOff_Lng": drop_lng,
            "Distance_km": distance
        })
    return {"results": results}
