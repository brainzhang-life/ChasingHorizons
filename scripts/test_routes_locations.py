import os
import requests
import json
from dotenv import load_dotenv

# Load env variables
load_dotenv()
API_KEY = os.getenv("GOOGLEMAP_API_KEY")

url = "https://routes.googleapis.com/directions/v2:computeRoutes"
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": API_KEY,
    "X-Goog-FieldMask": "routes.distanceMeters,routes.polyline.encodedPolyline,routes.legs.startLocation,routes.legs.endLocation,routes.legs.distanceMeters"
}

body = {
    "origin": {
        "address": "天安门广场, 北京市"
    },
    "destination": {
        "address": "颐和园, 北京市"
    },
    "intermediates": [
        {"address": "北京故宫, 北京市"},
        {"address": "南锣鼓巷, 北京市"},
        {"address": "什刹海, 北京市"}
    ],
    "travelMode": "DRIVE",
    "routingPreference": "TRAFFIC_UNAWARE"
}

r = requests.post(url, headers=headers, json=body)
print("Status Code:", r.status_code)
if r.status_code == 200:
    data = r.json()
    routes = data.get("routes", [])
    if routes:
        route = routes[0]
        legs = route.get("legs", [])
        print(f"Total distance meters: {route.get('distanceMeters')}")
        print(f"Number of legs: {len(legs)}")
        for idx, leg in enumerate(legs):
            start_loc = leg.get("startLocation", {}).get("latLng")
            end_loc = leg.get("endLocation", {}).get("latLng")
            print(f"  Leg {idx+1}:")
            print(f"    Start coordinate: {start_loc}")
            print(f"    End coordinate: {end_loc}")
            print(f"    Distance: {leg.get('distanceMeters')} meters")
    else:
        print("No routes found:", data)
else:
    print("Error:", r.json())
