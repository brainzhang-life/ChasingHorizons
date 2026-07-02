import os
import re
import math
import requests
import json
import sys
import time
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# Load env variables
load_dotenv()
API_KEY = os.getenv("GOOGLEMAP_API_KEY")

# Create directories
os.makedirs("docs/images/maps", exist_ok=True)
os.makedirs("scripts", exist_ok=True)

# Geocoding cache setup
CACHE_PATH = "scripts/geocode_cache.json"
geocode_cache = {}

PROVINCE_BBOXES = {
    "北京市": {"lat": (39.4, 41.1), "lng": (115.4, 117.6)},
    "天津市": {"lat": (38.5, 40.3), "lng": (116.7, 118.1)},
    "上海市": {"lat": (30.5, 32.0), "lng": (120.8, 122.3)},
    "重庆市": {"lat": (28.1, 32.4), "lng": (105.1, 110.3)},
    "黑龙江省": {"lat": (43.4, 53.6), "lng": (121.1, 135.1)},
    "吉林省": {"lat": (40.8, 46.3), "lng": (121.6, 131.3)},
    "辽宁省": {"lat": (38.7, 43.5), "lng": (118.8, 125.8)},
    "内蒙古自治区": {"lat": (37.4, 53.4), "lng": (97.1, 126.1)},
    "宁夏回族自治区": {"lat": (35.2, 39.5), "lng": (104.2, 107.7)},
    "甘肃省": {"lat": (32.5, 42.8), "lng": (92.3, 108.8)},
    "青海省": {"lat": (31.5, 39.4), "lng": (89.4, 103.1)},
    "新疆维吾尔自治区": {"lat": (34.3, 49.2), "lng": (73.5, 96.4)},
    "西藏自治区": {"lat": (26.8, 36.5), "lng": (78.4, 99.2)},
    "四川省": {"lat": (25.9, 34.4), "lng": (97.3, 108.6)},
    "云南省": {"lat": (21.1, 29.3), "lng": (97.5, 106.2)},
    "贵州省": {"lat": (24.5, 29.3), "lng": (103.5, 109.6)},
    "陕西省": {"lat": (31.6, 39.6), "lng": (105.4, 111.3)},
    "山西省": {"lat": (34.5, 40.8), "lng": (110.1, 114.6)},
    "河北省": {"lat": (36.0, 42.7), "lng": (113.4, 120.0)},
    "河南省": {"lat": (31.3, 36.4), "lng": (110.3, 116.7)},
    "山东省": {"lat": (34.3, 38.5), "lng": (114.7, 122.8)},
    "安徽省": {"lat": (29.3, 34.7), "lng": (114.8, 119.7)},
    "湖北省": {"lat": (29.0, 33.3), "lng": (108.3, 116.2)},
    "湖南省": {"lat": (24.6, 30.2), "lng": (108.7, 114.3)},
    "江西省": {"lat": (24.4, 30.1), "lng": (113.5, 118.5)},
    "江苏省": {"lat": (30.7, 35.2), "lng": (116.3, 122.0)},
    "浙江省": {"lat": (27.0, 31.3), "lng": (118.0, 123.0)},
    "福建省": {"lat": (23.5, 28.4), "lng": (115.8, 120.8)},
    "广东省": {"lat": (20.2, 25.6), "lng": (109.6, 117.3)},
    "广西壮族自治区": {"lat": (20.9, 26.4), "lng": (104.4, 112.1)},
    "海南省": {"lat": (3.0, 20.5), "lng": (108.0, 112.0)},
    "香港": {"lat": (22.1, 22.6), "lng": (113.8, 114.4)},
    "澳门": {"lat": (22.0, 22.3), "lng": (113.5, 113.6)},
    "台湾": {"lat": (21.8, 25.4), "lng": (119.9, 122.1)}
}

def is_in_province_bbox(lat, lng, context):
    if not context or context not in PROVINCE_BBOXES:
        return True
    bbox = PROVINCE_BBOXES[context]
    lat_min, lat_max = bbox["lat"]
    lng_min, lng_max = bbox["lng"]
    return lat_min <= lat <= lat_max and lng_min <= lng <= lng_max

def get_province_short_name(province_name):
    if not province_name:
        return ""
    name = province_name
    for suffix in ["自治区", "省", "市"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    for specifier in ["回族", "维吾尔", "壮族"]:
        if name.endswith(specifier):
            name = name[:-len(specifier)]
    return name

def check_province_match(val, short_name):
    if not val or not short_name:
        return False
    val = val.strip()
    norm_map = {
        "澳门": ["澳门", "澳門"],
        "台湾": ["台湾", "台灣", "臺灣"],
        "香港": ["香港"],
    }
    targets = norm_map.get(short_name, [short_name])
    for target in targets:
        if target in val:
            return True
    return False

def verify_nominatim_result(result, context_name):
    try:
        lat = float(result["lat"])
        lon = float(result["lon"])
    except (KeyError, ValueError):
        return False
        
    if not is_in_province_bbox(lat, lon, context_name):
        return False
        
    address = result.get("address", {})
    short_name = get_province_short_name(context_name)
    
    if context_name in ["香港", "澳门", "台湾"]:
        check_fields = ["state", "province", "region", "city", "country"]
        for field in check_fields:
            val = address.get(field, "")
            if check_province_match(val, short_name):
                return True
        if context_name == "台湾" and address.get("country_code") == "tw":
            return True
        return check_province_match(result.get("display_name", ""), short_name)
    else:
        check_fields = ["state", "province", "municipality"]
        has_any_field = False
        for field in check_fields:
            if field in address:
                has_any_field = True
                if check_province_match(address[field], short_name):
                    return True
        if not has_any_field:
            return check_province_match(result.get("display_name", ""), short_name)
        return False

def verify_google_result(result, context_name):
    try:
        loc = result["geometry"]["location"]
        lat, lon = loc["lat"], loc["lng"]
    except (KeyError, TypeError):
        return False
        
    if not is_in_province_bbox(lat, lon, context_name):
        return False
        
    components = result.get("address_components", [])
    short_name = get_province_short_name(context_name)
    
    if context_name in ["香港", "澳门", "台湾"]:
        allowed_types = {"administrative_area_level_1", "country", "locality", "colloquial_area"}
        for comp in components:
            comp_types = set(comp.get("types", []))
            if comp_types.intersection(allowed_types):
                val = comp.get("long_name", "")
                if check_province_match(val, short_name):
                    return True
        return check_province_match(result.get("formatted_address", ""), short_name)
    else:
        allowed_types = {"administrative_area_level_1"}
        has_any_field = False
        for comp in components:
            comp_types = set(comp.get("types", []))
            if "administrative_area_level_1" in comp_types:
                has_any_field = True
                val = comp.get("long_name", "")
                if check_province_match(val, short_name):
                    return True
        if not has_any_field:
            return check_province_match(result.get("formatted_address", ""), short_name)
        return False

if os.path.exists(CACHE_PATH):
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            loaded_cache = json.load(f)
        cleaned_cache = {}
        removed_count = 0
        for key, val in loaded_cache.items():
            if not val:
                cleaned_cache[key] = val
                continue
            parts = key.split("_")
            if len(parts) >= 2:
                context = parts[-1]
                lat, lng = val
                if is_in_province_bbox(lat, lng, context):
                    cleaned_cache[key] = val
                else:
                    print(f"Removing invalid cached coordinate for {key}: {val}")
                    removed_count += 1
            else:
                cleaned_cache[key] = val
        if removed_count > 0:
            print(f"Removed {removed_count} invalid cache entries.")
        geocode_cache = cleaned_cache
    except Exception as e:
        print(f"Failed to load cache: {e}")

def save_cache():
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(geocode_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Failed to save cache: {e}")

# Geocoding context for each province number
contexts = {
    1: "北京市", 2: "天津市", 3: "上海市", 4: "重庆市",
    5: "黑龙江省", 6: "吉林省", 7: "辽宁省", 8: "内蒙古自治区",
    9: "宁夏回族自治区", 10: "甘肃省", 11: "青海省", 12: "新疆维吾尔自治区",
    13: "西藏自治区", 14: "四川省", 15: "云南省", 16: "贵州省",
    17: "陕西省", 18: "山西省", 19: "河北省", 20: "河南省",
    21: "山东省", 22: "安徽省", 23: "湖北省", 24: "湖南省",
    25: "江西省", 26: "江苏省", 27: "浙江省", 28: "福建省",
    29: "广东省", 30: "广西壮族自治区", 31: "海南省", 32: "香港", 33: "澳门", 34: "台湾"
}

# Location name cleaning and replacements
loc_replacements = {
    "主城区": "市中心",
    "市区": "市中心",
    "上海市区": "上海市中心",
    "北京市": "北京天安门",
    "天津市": "天津鼓楼",
    "重庆市区": "重庆市中心",
    "拉萨市": "拉萨布达拉宫",
    "成都市": "成都天府广场",
    "昆明市": "昆明翠湖公园",
    "贵阳市": "贵阳甲秀楼",
    "西安市": "西安钟楼",
    "太原市": "太原晋祠",
    "石家庄市": "石家庄市政府",
    "郑州市": "郑州二七广场",
    "济南市": "济南泉城广场",
    "合肥市": "合肥包公园",
    "武汉市": "武汉黄鹤楼",
    "长沙市": "长沙橘子洲",
    "南昌市": "南昌滕王阁",
    "南京市": "南京新街口",
    "杭州市": "杭州西湖",
    "福州市": "三坊七巷",
    "福州三坊七巷": "三坊七巷",
    "广州市": "广州天河体育中心",
    "南宁市": "南宁朝阳广场",
    "海口市": "海口骑楼老街",
    "东方明珠塔": "东方明珠电视塔",
    "分界洲岛": "分界洲",
    "日月湾": "礼纪镇",
    "五指山热带雨林": "五指山国家级自然保护区",
    "五指山热带雨林景区": "五指山国家级自然保护区",
    "槟榔谷黎苗景区": "槟榔谷",
    "槟榔谷黎苗文化旅游区": "槟榔谷",
    "威尼斯人度假城": "澳门威尼斯人",
    "港珠澳大桥珠海公路口岸": "港珠澳大桥",
    "呀诺达雨林文化景区": "呀诺达雨林"
}

def robust_request(method, url, max_retries=5, initial_backoff=1.0, **kwargs):
    backoff = initial_backoff
    for i in range(max_retries):
        try:
            r = requests.request(method, url, **kwargs)
            if r is not None:
                return r
        except Exception as e:
            if i == max_retries - 1:
                print(f"Request failed after {max_retries} attempts: {e}")
                return None
            time.sleep(backoff)
            backoff *= 2.0
    return None

def latlng_to_world_coords(lat, lng):
    x = 256.0 * (lng + 180.0) / 360.0
    lat_rad = math.radians(lat)
    lat_rad = max(min(lat_rad, 1.48), -1.48)
    y = 128.0 * (1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi)
    return x, y

def latlng_to_pixel(lat, lng, clat, clng, zoom, width, height, scale=1):
    n = 2.0 ** zoom
    x, y = latlng_to_world_coords(lat, lng)
    x_Z = x * n
    y_Z = y * n
    
    cx, cy = latlng_to_world_coords(clat, clng)
    cx_Z = cx * n
    cy_Z = cy * n
    
    px = (width * scale / 2.0) + (x_Z - cx_Z) * scale
    py = (height * scale / 2.0) + (y_Z - cy_Z) * scale
    return int(px), int(py)

def latlng_to_tile(lat, lng, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = (lng + 180.0) / 360.0 * n
    ytile = (1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * n
    return xtile, ytile

def calculate_optimal_bounds_and_zoom(coords, width=1600, height=1000, margin=120):
    if not coords:
        return 0.0, 0.0, 10
    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    clat = (min(lats) + max(lats)) / 2.0
    clng = (min(lngs) + max(lngs)) / 2.0
    
    optimal_zoom = 12
    for z in range(18, 1, -1):
        all_fit = True
        for lat, lng in coords:
            px, py = latlng_to_pixel(lat, lng, clat, clng, z, width, height, scale=1)
            if not (margin <= px <= width - margin and margin <= py <= height - margin):
                all_fit = False
                break
        if all_fit:
            optimal_zoom = z
            break
    return clat, clng, optimal_zoom

def decode_polyline(polyline_str):
    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {'latitude': 0, 'longitude': 0}
    while index < len(polyline_str):
        for unit in ['latitude', 'longitude']:
            shift, result = 0, 0
            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1f) << shift
                shift += 5
                if not byte >= 0x20:
                    break
            if (result & 1):
                changes[unit] = ~(result >> 1)
            else:
                changes[unit] = (result >> 1)
        lat += changes['latitude']
        lng += changes['longitude']
        coordinates.append((lat / 100000.0, lng / 100000.0))
    return coordinates

def encode_polyline(points):
    def encode_value(val):
        val = int(round(val * 1e5))
        val = ~(val << 1) if val < 0 else val << 1
        chunks = []
        while val >= 0x20:
            chunks.append(chr((0x20 | (val & 0x1f)) + 63))
            val >>= 5
        chunks.append(chr(val + 63))
        return "".join(chunks)

    last_lat = 0
    last_lng = 0
    result = []
    for lat, lng in points:
        result.append(encode_value(lat - last_lat))
        result.append(encode_value(lng - last_lng))
        last_lat = lat
        last_lng = lng
    return "".join(result)

def clean_location_name(name):
    # Remove text in parentheses
    name = re.sub(r'\(.*?\)|（.*?）', '', name)
    name = name.strip()
    if name.startswith("返回"):
        name = name[2:].strip()
    for k, v in loc_replacements.items():
        if name == k:
            name = v
            break
    return name

def geocode_location(name, context):
    name_clean = clean_location_name(name)
    if not name_clean:
        return None
        
    cache_key = f"{name_clean}_{context}"
    if cache_key in geocode_cache:
        val = geocode_cache[cache_key]
        if val:
            return tuple(val)
        return None
        
    # 1. Try Google Geocoding API first
    if API_KEY:
        google_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": f"{name_clean}, {context}" if context not in name_clean else name_clean,
            "key": API_KEY,
            "language": "zh-CN"
        }
        try:
            r = robust_request("GET", google_url, params=params, timeout=5)
            if r is not None and r.status_code == 200:
                data = r.json()
                if data.get("status") == "OK" and data.get("results"):
                    for result in data["results"]:
                        if verify_google_result(result, context):
                            loc = result["geometry"]["location"]
                            lat, lng = loc["lat"], loc["lng"]
                            geocode_cache[cache_key] = [lat, lng]
                            save_cache()
                            return lat, lng
                    print(f"  Google Geocoding found results for '{name_clean}', but none were in {context}")
                elif data.get("status") == "OVER_QUERY_LIMIT":
                    print(f"  Google Geocoding API query limit hit for '{name_clean}'.")
        except Exception as e:
            print(f"  Google Geocoding request failed: {e}")

    # 2. Fallback to Nominatim (OSM)
    time.sleep(1.0) # Compliance with OSM Nominatim usage policy (1 request/sec limit)
    nominatim_url = "https://nominatim.openstreetmap.org/search"
    headers = {
        "User-Agent": "ChasingHorizonsTravelGuideRouteMapGenerator/1.0 (contact: travel@chasinghorizons.org)"
    }
    
    # Try query with context first
    q_with_context = f"{name_clean}, {context}" if context not in name_clean else name_clean
    try:
        params = {
            "q": q_with_context,
            "format": "json",
            "limit": 5,
            "accept-language": "zh",
            "addressdetails": 1
        }
        r = robust_request("GET", nominatim_url, params=params, headers=headers, timeout=5)
        if r is not None and r.status_code == 200:
            results = r.json()
            if results:
                for result in results:
                    if verify_nominatim_result(result, context):
                        lat = float(result["lat"])
                        lon = float(result["lon"])
                        print(f"  OSM Nominatim geocoded '{name_clean}' (with context) to ({lat}, {lon}) in {context}")
                        geocode_cache[cache_key] = [lat, lon]
                        save_cache()
                        return lat, lon
                print(f"  OSM Nominatim found results with context for '{name_clean}', but none were in {context}")
            else:
                print(f"  OSM Nominatim found no results with context for '{name_clean}'")
    except Exception as e:
        print(f"  OSM Nominatim request with context failed: {e}")
        
    # Fallback: Try query with name_clean alone (it might be that appending context breaks OSM parser)
    if context in q_with_context:
        time.sleep(1.0)
        try:
            params = {
                "q": name_clean,
                "format": "json",
                "limit": 5,
                "accept-language": "zh",
                "addressdetails": 1
            }
            r = robust_request("GET", nominatim_url, params=params, headers=headers, timeout=5)
            if r is not None and r.status_code == 200:
                results = r.json()
                if results:
                    for result in results:
                        if verify_nominatim_result(result, context):
                            lat = float(result["lat"])
                            lon = float(result["lon"])
                            print(f"  OSM Nominatim geocoded '{name_clean}' (fallback alone) to ({lat}, {lon}) in {context}")
                            geocode_cache[cache_key] = [lat, lon]
                            save_cache()
                            return lat, lon
                    print(f"  OSM Nominatim found results for fallback '{name_clean}', but none were in {context}")
                else:
                    print(f"  OSM Nominatim found no results for fallback '{name_clean}'")
        except Exception as e:
            print(f"  OSM Nominatim fallback request failed: {e}")
        
    geocode_cache[cache_key] = None
    save_cache()
    return None

def get_route_data(loc_names, context):
    coords = []
    valid_names = []
    for name in loc_names:
        latlng = geocode_location(name, context)
        if latlng:
            coords.append(latlng)
            valid_names.append(name)
        else:
            print(f"  Warning: Could not geocode '{name}'")
            
    if len(coords) < 2:
        return None
        
    # Try Google Routes API first
    if API_KEY:
        google_url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": API_KEY,
            "X-Goog-FieldMask": "routes.distanceMeters,routes.polyline.encodedPolyline,routes.legs.startLocation,routes.legs.endLocation,routes.legs.distanceMeters"
        }
        origin = {"location": {"latLng": {"latitude": coords[0][0], "longitude": coords[0][1]}}}
        destination = {"location": {"latLng": {"latitude": coords[-1][0], "longitude": coords[-1][1]}}}
        intermediates = [{"location": {"latLng": {"latitude": c[0], "longitude": c[1]}}} for c in coords[1:-1]]
        
        body = {
            "origin": origin,
            "destination": destination,
            "intermediates": intermediates,
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_UNAWARE"
        }
        
        time.sleep(0.1)
        try:
            r = robust_request("POST", google_url, headers=headers, json=body, timeout=12)
            if r is not None and r.status_code == 200:
                data = r.json()
                routes = data.get("routes", [])
                if routes:
                    route = routes[0]
                    polyline_str = route.get("polyline", {}).get("encodedPolyline", "")
                    legs = route.get("legs", [])
                    if legs:
                        leg_distances = [leg.get("distanceMeters", 0) / 1000.0 for leg in legs]
                        total_dist = route.get("distanceMeters", 0) / 1000.0
                        path_coords = decode_polyline(polyline_str)
                        return {
                            "total_distance": total_dist,
                            "leg_distances": leg_distances,
                            "path": path_coords,
                            "loc_coords": coords,
                            "valid_names": valid_names,
                            "encoded_polyline": polyline_str
                        }
            elif r is not None and r.status_code == 429:
                print("  Google Routes API daily limit reached. Falling back to OSRM...")
        except Exception as e:
            print(f"  Google Routes API failed: {e}")

    # Fallback to OSRM routing
    print("  Using OSRM routing fallback...")
    coord_str = ";".join([f"{lng},{lat}" for lat, lng in coords])
    osrm_url = f"http://router.project-osrm.org/route/v1/driving/{coord_str}"
    params = {
        "overview": "full",
        "geometries": "polyline"
    }
    try:
        r = robust_request("GET", osrm_url, params=params, timeout=10)
        if r is not None and r.status_code == 200:
            data = r.json()
            routes = data.get("routes", [])
            if routes:
                route = routes[0]
                polyline_str = route.get("geometry", "")
                distance_meters = route.get("distance", 0)
                legs = route.get("legs", [])
                leg_distances = [leg.get("distance", 0) / 1000.0 for leg in legs]
                total_dist = distance_meters / 1000.0
                path_coords = decode_polyline(polyline_str)
                return {
                    "total_distance": total_dist,
                    "leg_distances": leg_distances,
                    "path": path_coords,
                    "loc_coords": coords,
                    "valid_names": valid_names,
                    "encoded_polyline": polyline_str
                }
    except Exception as e:
        print(f"  OSRM routing request failed: {e}")
        
    return None

def load_best_font(sizes=[20, 22]):
    font_paths = []
    if sys.platform == "darwin":
        font_paths = [
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    elif sys.platform.startswith("win"):
        font_paths = [
            "C:\\Windows\\Fonts\\msyh.ttc",
            "C:\\Windows\\Fonts\\simsun.ttc",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]
    else:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
        
    fonts = []
    for sz in sizes:
        font = None
        for fp in font_paths:
            try:
                font = ImageFont.truetype(fp, sz)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()
        fonts.append(font)
    return fonts

def generate_map_image(route_data, output_path):
    path = route_data["path"]
    loc_coords = route_data["loc_coords"]
    
    if not path or not loc_coords:
        return False
        
    # Use 1600x1000 crop sizing directly
    all_coords = path + loc_coords
    clat, clng, zoom = calculate_optimal_bounds_and_zoom(all_coords, 1600, 1000, 120)
    
    cx, cy = latlng_to_tile(clat, clng, zoom)
    tx, ty = int(cx), int(cy)
    
    # Stitch 7x7 grid of 256x256 tiles (Canvas size 1792x1792)
    tile_size = 256
    grid_size = 7
    half_grid = grid_size // 2
    
    canvas = Image.new("RGBA", (grid_size * tile_size, grid_size * tile_size), (243, 244, 246, 255))
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Download tiles in parallel
    from concurrent.futures import ThreadPoolExecutor
    
    tile_jobs = []
    for dx in range(-half_grid, half_grid + 1):
        for dy in range(-half_grid, half_grid + 1):
            x = tx + dx
            y = ty + dy
            url = f"https://mt1.google.com/vt/lyrs=m&hl=zh-CN&x={x}&y={y}&z={zoom}"
            tile_jobs.append((dx, dy, x, y, url))
            
    def fetch_tile(job):
        dx_val, dy_val, x_val, y_val, tile_url = job
        r = robust_request("GET", tile_url, headers=headers, timeout=5)
        if r is not None and r.status_code == 200:
            return dx_val, dy_val, r.content
        return dx_val, dy_val, None

    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(fetch_tile, tile_jobs))
        
    for dx_val, dy_val, content in results:
        if content:
            try:
                tile = Image.open(BytesIO(content))
                paste_x = (dx_val + half_grid) * tile_size
                paste_y = (dy_val + half_grid) * tile_size
                canvas.paste(tile, (paste_x, paste_y))
            except Exception as e:
                print(f"  Error loading tile at ({dx_val}, {dy_val}): {e}")
        else:
            print(f"  Warning: Could not download tile at ({dx_val}, {dy_val})")
                
    # Center crop to 1600x1000
    cx_px = (cx - (tx - half_grid)) * tile_size
    cy_px = (cy - (ty - half_grid)) * tile_size
    left = int(cx_px - 800)
    top = int(cy_px - 500)
    
    img = canvas.crop((left, top, left + 1600, top + 1000))
    draw = ImageDraw.Draw(img)
    
    # Draw path line
    path_pts = []
    for lat, lng in path:
        px, py = latlng_to_pixel(lat, lng, clat, clng, zoom, 1600, 1000, scale=1)
        path_pts.append((px, py))
        
    if len(path_pts) > 1:
        # Draw a beautiful thick semi-transparent blue route line
        draw.line(path_pts, fill=(59, 130, 246, 200), width=6)
        
    # Draw location markers (1 to N)
    fonts = load_best_font(sizes=[22])
    bold_font = fonts[0]
    
    for idx, coord in enumerate(loc_coords):
        px, py = latlng_to_pixel(coord[0], coord[1], clat, clng, zoom, 1600, 1000, scale=1)
        
        if idx == 0:
            fill_color = (16, 185, 129, 255) # Green
        elif idx == len(loc_coords) - 1:
            fill_color = (239, 68, 68, 255)  # Red
        else:
            fill_color = (59, 130, 246, 255) # Blue
            
        r_circle = 22
        # Shadow
        draw.ellipse([px - r_circle - 2, py - r_circle - 2, px + r_circle + 2, py + r_circle + 2], fill=(100, 100, 100, 100))
        # White border
        draw.ellipse([px - r_circle, py - r_circle, px + r_circle, py + r_circle], fill=(255, 255, 255, 255))
        # Color fill
        draw.ellipse([px - r_circle + 3, py - r_circle + 3, px + r_circle - 3, py + r_circle - 3], fill=fill_color)
        
        # Text label
        label_str = str(idx + 1)
        bbox = draw.textbbox((0, 0), label_str, font=bold_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((px - tw/2, py - th/2 - 2), label_str, fill=(255, 255, 255, 255), font=bold_font)
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    print(f"  Successfully saved stitched Google Map image to {output_path}")
    return True

def parse_and_update_file(file_path):
    filename = os.path.basename(file_path)
    prefix_match = re.match(r'^(\d+)_', filename)
    if not prefix_match:
        return
    num = int(prefix_match.group(1))
    context = contexts.get(num, "")
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    lines = content.split("\n")
    blocks = []
    current_block = None
    
    # Segment lines into route sections or raw lines
    for line in lines:
        m_bullet = re.match(r'^(\s*)\*\s*\*\*(.+?)\*\*\s*$', line)
        m_h4 = re.match(r'^####\s+(.*)$', line)
        m_h2_h3 = re.match(r'^##\s+(?!.*自驾旅行经典线路推荐|.*自驾线路推荐|.*自驾游与人文地图).*$', line) or re.match(r'^###\s+(?!.*自驾旅行经典线路推荐|.*自驾线路推荐|.*自驾游与人文地图).*$', line)
        
        # Check if it is a valid route start header (not one of the special sub-bullets)
        is_route_header = False
        indent = 0
        name = ""
        
        if m_bullet:
            name = m_bullet.group(2).strip()
            check_name = name.rstrip("：:")
            keywords = ["特点", "自驾线路", "自驾路线", "行车路线", "预算", "路线", "行车路", "线路打卡点推荐", "大致行程", "路线路段距离与地图"]
            if check_name not in keywords:
                is_route_header = True
                indent = len(m_bullet.group(1))
                
        if is_route_header:
            if current_block:
                blocks.append(current_block)
            current_block = {
                "type": "bullet",
                "name": name,
                "indent": indent,
                "header_line": line,
                "lines": []
            }
        elif m_h4:
            if current_block:
                blocks.append(current_block)
            current_block = {
                "type": "h4",
                "name": m_h4.group(1).strip(),
                "indent": 0,
                "header_line": line,
                "lines": []
            }
        elif m_h2_h3:
            if current_block:
                blocks.append(current_block)
                current_block = None
            blocks.append({"type": "raw", "lines": [line]})
        else:
            if current_block:
                current_block["lines"].append(line)
            else:
                blocks.append({"type": "raw", "lines": [line]})
                
    if current_block:
        blocks.append(current_block)
        
    new_blocks = []
    route_idx = 0
    
    for block in blocks:
        if block["type"] == "raw":
            new_blocks.append(block)
            continue
            
        route_name = block["name"]
        route_lines = block["lines"]
        
        # Look for the self-drive route definition line
        rl_idx = -1
        rl_line = ""
        for idx, line in enumerate(route_lines):
            if re.search(r'\*\*(自驾线路|行车路线|自驾路线|线路打卡点推荐|大致行程|自驾路)\*\*：', line):
                rl_idx = idx
                rl_line = line
                break
                
        if rl_idx == -1:
            new_blocks.append(block)
            continue
            
        prefix_match = re.search(r'^\s*\*?\s*\*\*(?:自驾线路|行车路线|自驾路线|线路打卡点推荐|大致行程|自驾路)\*\*：', rl_line)
        if not prefix_match:
            new_blocks.append(block)
            continue
            
        prefix = prefix_match.group(0)
        locs_part = rl_line[len(prefix):].strip()
        
        raw_loc_names = [l.strip() for l in re.split(r'→|->|->|-', locs_part) if l.strip()]
        raw_loc_names = [re.sub(r'[\.。]$', '', l).strip() for l in raw_loc_names]
        loc_names = [clean_location_name(l) for l in raw_loc_names if clean_location_name(l)]
        
        if len(loc_names) < 2:
            new_blocks.append(block)
            continue
            
        route_idx += 1
        print(f"[{filename}] Processing Route {route_idx} '{route_name}': {len(loc_names)} locations...")
        
        # Geocode and route using Google Routes API / OSRM fallbacks
        route_data = get_route_data(loc_names, context)
            
        if not route_data or len(route_data.get("loc_coords", [])) < 2:
            print(f"  Warning: Could not resolve coordinates or routing for '{route_name}'")
            new_blocks.append(block)
            continue
            
        filename_clean = re.sub(r'[^\w]', '', filename.replace(".md", ""))
        map_filename = f"{filename_clean}_{route_idx:02d}.png"
        map_path = f"docs/images/maps/{map_filename}"
        
        generate_map_image(route_data, map_path)
        
        # Clean up any existing old/duplicate tables and images from route lines
        cleaned_route_lines = []
        for line in route_lines:
            if "**路线路段距离与地图**" in line:
                continue
            if "![路线地图]" in line:
                continue
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                continue
            cleaned_route_lines.append(line)
            
        # Re-find the route line index in cleaned list
        new_rl_idx = -1
        for idx, line in enumerate(cleaned_route_lines):
            if re.search(r'\*\*(自驾线路|行车路线|自驾路线|线路打卡点推荐|大致行程|自驾路)\*\*：', line):
                new_rl_idx = idx
                break
                
        # Construct fresh markdown table and image
        indent = len(rl_line) - len(rl_line.lstrip())
        indent_str = " " * indent
        
        table_lines = [
            f"{indent_str}* **路线路段距离与地图**",
            f"{indent_str}  | 起点 | 终点 | 距离 |",
            f"{indent_str}  | :--- | :--- | :--- |"
        ]
        
        leg_dists = route_data["leg_distances"]
        v_names = route_data["valid_names"]
        for idx in range(len(v_names) - 1):
            dist = leg_dists[idx] if idx < len(leg_dists) else 0
            table_lines.append(f"{indent_str}  | ({idx+1}) {v_names[idx]} | ({idx+2}) {v_names[idx+1]} | {dist:.1f} 公里 |")
        table_lines.append(f"{indent_str}  | **总里程** | | **{route_data['total_distance']:.1f} 公里** |")
        table_lines.append(f"{indent_str}  ")
        table_lines.append(f"{indent_str}  ![路线地图](images/maps/{map_filename})")
        table_lines.append(f"{indent_str}  ")
        
        if new_rl_idx != -1:
            cleaned_route_lines = cleaned_route_lines[:new_rl_idx+1] + table_lines + cleaned_route_lines[new_rl_idx+1:]
        else:
            cleaned_route_lines.extend(table_lines)
            
        block["lines"] = cleaned_route_lines
        new_blocks.append(block)
        
    output_lines = []
    for block in new_blocks:
        if block["type"] == "raw":
            output_lines.extend(block["lines"])
        else:
            output_lines.append(block["header_line"])
            output_lines.extend(block["lines"])
            
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

def main():
    if len(sys.argv) > 1:
        # Run on specific file(s)
        for arg in sys.argv[1:]:
            if os.path.exists(arg):
                parse_and_update_file(arg)
            else:
                print(f"File not found: {arg}")
    else:
        # Run on all files in docs/
        docs_dir = "docs"
        files = sorted(os.listdir(docs_dir))
        for filename in files:
            if not filename.endswith(".md") or filename in ["SUMMARY.md", "README.md"]:
                continue
            file_path = os.path.join(docs_dir, filename)
            parse_and_update_file(file_path)

if __name__ == "__main__":
    main()
