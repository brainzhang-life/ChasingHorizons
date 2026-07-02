import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLEMAP_API_KEY")

def main():
    context = "北京市"
    loc_names = ["北京市", "延庆区", "百里山水画廊", "延庆世界地质公园", "朝阳寺", "硅化木国家地质公园", "乌龙峡谷", "龙王庙", "滴水壶景区"]
    
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "routes.distanceMeters,routes.polyline.encodedPolyline,routes.legs.startLocation,routes.legs.endLocation,routes.legs.distanceMeters"
    }
    
    addrs = []
    for l in loc_names:
        addr = f"{l}, {context}" if context not in l else l
        addrs.append(addr)
        
    origin = {"address": addrs[0]}
    destination = {"address": addrs[-1]}
    intermediates = [{"address": addr} for addr in addrs[1:-1]]
    
    body = {
        "origin": origin,
        "destination": destination,
        "intermediates": intermediates,
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_UNAWARE"
    }
    
    r = requests.post(url, headers=headers, json=body)
    print("Routes API status code:", r.status_code)
    if r.status_code == 200:
        data = r.json()
        routes = data.get("routes", [])
        if routes:
            route = routes[0]
            polyline_str = route.get("polyline", {}).get("encodedPolyline", "")
            print("Polyline length:", len(polyline_str))
            
            # Print a snippet of the polyline
            print("Polyline snippet:", polyline_str[:100] + "..." if len(polyline_str) > 100 else polyline_str)
            
            # Check size of static map URL
            path_param = f"color:0x3B82F6ff|weight:6|enc:{polyline_str}"
            print("Path parameter length:", len(path_param))
            
            # Try calling Static Map API with different variations
            static_url = "https://maps.googleapis.com/maps/api/staticmap"
            
            # Attempt 1: Full polyline
            params = {
                "center": "40.0,116.0",
                "zoom": "10",
                "size": "800x500",
                "scale": "2",
                "path": path_param,
                "language": "zh-CN",
                "key": API_KEY
            }
            r_static = requests.get(static_url, params=params)
            print("Static Map with full polyline status:", r_static.status_code)
            if r_static.status_code != 200:
                print("Static Map response:", r_static.text[:500])
                
                # Attempt 2: No polyline
                params_no_path = {
                    "center": "40.0,116.0",
                    "zoom": "10",
                    "size": "800x500",
                    "scale": "2",
                    "language": "zh-CN",
                    "key": API_KEY
                }
                r_static_no_path = requests.get(static_url, params=params_no_path)
                print("Static Map WITHOUT polyline status:", r_static_no_path.status_code)
                if r_static_no_path.status_code != 200:
                    print("Static Map WITHOUT polyline response:", r_static_no_path.text[:500])
        else:
            print("No routes found in response.")
    else:
        print("Routes API error:", r.text)

if __name__ == "__main__":
    main()
