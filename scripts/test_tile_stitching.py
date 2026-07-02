import requests
import math
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

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

def main():
    # Coords for Beijing route
    loc_coords = [
        (39.905428, 116.395863), # 天安门
        (39.91511, 116.40169),   # 故宫
        (39.93709, 116.40316),   # 南锣鼓巷
        (39.941527, 116.38224),  # 什刹海
        (40.00247, 116.27504)    # 颐和园
    ]
    
    lats = [c[0] for c in loc_coords]
    lngs = [c[1] for c in loc_coords]
    clat = (min(lats) + max(lats)) / 2.0
    clng = (min(lngs) + max(lngs)) / 2.0
    zoom = 12
    
    cx, cy = latlng_to_tile(clat, clng, zoom)
    tx, ty = int(cx), int(cy)
    
    # Stitch 7x7 grid
    tile_size = 256
    grid_size = 7
    half_grid = grid_size // 2
    
    canvas = Image.new("RGBA", (grid_size * tile_size, grid_size * tile_size), (243, 244, 246, 255))
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print("Downloading tiles...")
    for dx in range(-half_grid, half_grid + 1):
        for dy in range(-half_grid, half_grid + 1):
            x = tx + dx
            y = ty + dy
            url = f"https://mt1.google.com/vt/lyrs=m&hl=zh-CN&x={x}&y={y}&z={zoom}"
            try:
                r = requests.get(url, headers=headers, timeout=5)
                if r.status_code == 200:
                    tile = Image.open(BytesIO(r.content))
                    paste_x = (dx + half_grid) * tile_size
                    paste_y = (dy + half_grid) * tile_size
                    canvas.paste(tile, (paste_x, paste_y))
            except Exception as e:
                print(f"Error downloading tile {x}, {y}: {e}")
                
    # Center crop to 1600x1000
    cx_px = (cx - (tx - half_grid)) * tile_size
    cy_px = (cy - (ty - half_grid)) * tile_size
    left = int(cx_px - 800)
    top = int(cy_px - 500)
    
    img = canvas.crop((left, top, left + 1600, top + 1000))
    draw = ImageDraw.Draw(img)
    
    # Draw path line
    path_pts = []
    for lat, lng in loc_coords:
        px, py = latlng_to_pixel(lat, lng, clat, clng, zoom, 1600, 1000, scale=1)
        path_pts.append((px, py))
    draw.line(path_pts, fill=(59, 130, 246, 255), width=6)
    
    # Draw markers
    for idx, (lat, lng) in enumerate(loc_coords):
        px, py = latlng_to_pixel(lat, lng, clat, clng, zoom, 1600, 1000, scale=1)
        
        if idx == 0:
            fill_color = (16, 185, 129, 255)
        elif idx == len(loc_coords) - 1:
            fill_color = (239, 68, 68, 255)
        else:
            fill_color = (59, 130, 246, 255)
            
        r_circle = 22
        draw.ellipse([px - r_circle - 2, py - r_circle - 2, px + r_circle + 2, py + r_circle + 2], fill=(100, 100, 100, 100))
        draw.ellipse([px - r_circle, py - r_circle, px + r_circle, py + r_circle], fill=(255, 255, 255, 255))
        draw.ellipse([px - r_circle + 3, py - r_circle + 3, px + r_circle - 3, py + r_circle - 3], fill=fill_color)
        
        # Label text
        label_str = str(idx + 1)
        draw.text((px - 5, py - 10), label_str, fill=(255, 255, 255, 255))
        
    output_path = "test_stitched_google_map.png"
    img.save(output_path, "PNG")
    print(f"Successfully saved stitched Google Map image to {output_path}")

if __name__ == "__main__":
    main()
