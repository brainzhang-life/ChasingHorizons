import requests
from io import BytesIO
from PIL import Image

def main():
    # Google Maps tile server URL
    # z=11, x=1682, y=774 (corresponds to Beijing area)
    url = "https://mt1.google.com/vt/lyrs=m&hl=zh-CN&x=1682&y=774&z=11"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    r = requests.get(url, headers=headers)
    print("Tile request status:", r.status_code)
    if r.status_code == 200:
        img = Image.open(BytesIO(r.content))
        img.save("test_tile.png")
        print("Successfully saved test_tile.png, size:", img.size)
    else:
        print("Failed to download tile:", r.text)

if __name__ == "__main__":
    main()
