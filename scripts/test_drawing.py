import os
import requests
import math
import sys
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLEMAP_API_KEY")

def latlng_to_world_coords(lat, lng):
    x = 256.0 * (lng + 180.0) / 360.0
    lat_rad = math.radians(lat)
    lat_rad = max(min(lat_rad, 1.48), -1.48)
    y = 128.0 * (1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi)
    return x, y

def latlng_to_pixel(lat, lng, clat, clng, zoom, width, height, scale=2):
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

def calculate_optimal_bounds_and_zoom(coords, width=800, height=500, margin=60):
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

def main():
    if not API_KEY:
        print("API_KEY not found in env.")
        return

    # Use the coordinates from the previous test response
    loc_coords = [
        (39.905427599999996, 116.39586279999999), # 天安门广场
        (39.91511, 116.40169),                    # 北京故宫
        (39.93709, 116.40316000000001),           # 南锣鼓巷
        (39.941527, 116.3822404),                 # 什刹海
        (40.002469999999995, 116.27504)           # 颐和园
    ]
    leg_distances = [3.6, 3.9, 3.1, 16.0] # In km

    # Let's get directions polyline using Routes API
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "routes.polyline.encodedPolyline"
    }
    body = {
        "origin": {"address": "天安门广场, 北京市"},
        "destination": {"address": "颐和园, 北京市"},
        "intermediates": [
            {"address": "北京故宫, 北京市"},
            {"address": "南锣鼓巷, 北京市"},
            {"address": "什刹海, 北京市"}
        ],
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_UNAWARE"
    }
    
    r = requests.post(url, headers=headers, json=body)
    if r.status_code != 200:
        print("Routes API failed:", r.text)
        return
    
    data = r.json()
    encoded_polyline = data["routes"][0]["polyline"]["encodedPolyline"]

    clat, clng, zoom = calculate_optimal_bounds_and_zoom(loc_coords, 800, 500, 60)
    print(f"Optimal bounds: center=({clat}, {clng}), zoom={zoom}")

    # Fetch Static Map
    static_url = "https://maps.googleapis.com/maps/api/staticmap"
    params = {
        "center": f"{clat},{clng}",
        "zoom": str(zoom),
        "size": "800x500",
        "scale": "2",
        "path": f"color:0x3B82F6ff|weight:6|enc:{encoded_polyline}",
        "language": "zh-CN",
        "key": API_KEY
    }
    
    sr = requests.get(static_url, params=params)
    if sr.status_code != 200:
        print("Static map failed:", sr.status_code, sr.text)
        return
        
    img = Image.open(BytesIO(sr.content))
    draw = ImageDraw.Draw(img)

    # Try loading font
    font_loaded = False
    for font_path in [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc"
    ]:
        try:
            font = ImageFont.truetype(font_path, 20)
            bold_font = ImageFont.truetype(font_path, 22)
            font_loaded = True
            print(f"Loaded font: {font_path}")
            break
        except Exception:
            continue
    if not font_loaded:
        font = ImageFont.load_default()
        bold_font = ImageFont.load_default()
        print("Loaded default font")

    # 1. Draw location markers (1 to N)
    for idx, coord in enumerate(loc_coords):
        px, py = latlng_to_pixel(coord[0], coord[1], clat, clng, zoom, 800, 500, scale=2)
        print(f"Location {idx+1} pixel coordinates: ({px}, {py})")
        
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

    # 2. Draw distance labels
    for idx in range(len(loc_coords) - 1):
        coord1 = loc_coords[idx]
        coord2 = loc_coords[idx+1]
        dist = leg_distances[idx]
        
        px1, py1 = latlng_to_pixel(coord1[0], coord1[1], clat, clng, zoom, 800, 500, scale=2)
        px2, py2 = latlng_to_pixel(coord2[0], coord2[1], clat, clng, zoom, 800, 500, scale=2)
        
        mx = (px1 + px2) // 2
        my = (py1 + py2) // 2
        
        dist_text = f"{dist:.1f} km"
        bbox = draw.textbbox((0, 0), dist_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        
        pad_x, pad_y = 10, 6
        bx1 = mx - tw/2 - pad_x
        by1 = my - th/2 - pad_y
        bx2 = mx + tw/2 + pad_x
        by2 = my + th/2 + pad_y
        
        draw.rounded_rectangle([bx1 - 1, by1 - 1, bx2 + 1, by2 + 1], radius=8, fill=(100, 100, 100, 80))
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=8, fill=(255, 255, 255, 255), outline=(59, 130, 246, 255), width=2)
        draw.text((mx - tw/2, my - th/2 - 2), dist_text, fill=(31, 41, 55, 255), font=font)
        print(f"Leg {idx+1} midpoint pixel coordinates: ({mx}, {my})")

    output_path = "/Users/brainzhang/work/brainzhang/ChasingHorizons/test_stitched_map.png"
    img.save(output_path, "PNG")
    print(f"Saved test output map to {output_path}")

if __name__ == "__main__":
    main()
