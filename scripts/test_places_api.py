import os
import requests
from dotenv import load_dotenv

# Load env variables
load_dotenv()
API_KEY = os.getenv("GOOGLEMAP_API_KEY")

print("API_KEY loaded:", API_KEY[:10] + "..." if API_KEY else "None")

# Test Places API (New) Text Search
url = "https://places.googleapis.com/v1/places:searchText"
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": API_KEY,
    "X-Goog-FieldMask": "places.location,places.displayName,places.formattedAddress"
}

body = {
    "textQuery": "天安门广场, 北京市",
    "languageCode": "zh-CN"
}

r = requests.post(url, headers=headers, json=body)
data = r.json()

print("Response Status Code:", r.status_code)
if r.status_code == 200:
    places = data.get("places", [])
    if places:
        place = places[0]
        print("Display Name:", place.get("displayName", {}).get("text"))
        print("Formatted Address:", place.get("formattedAddress"))
        print("Location:", place.get("location"))
    else:
        print("No places found in response:", data)
else:
    print("Error response:", data)
