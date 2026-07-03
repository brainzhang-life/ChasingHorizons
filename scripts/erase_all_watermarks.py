import pytesseract
from PIL import Image, ImageDraw
import os
import re

pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

def get_horizontal_median_color(img, box):
    x1, y1, x2, y2 = box
    w, h = img.size
    pixels = []
    
    # Sample pixels just above and below the horizontal band
    for x in range(x1, x2):
        if y1 - 5 >= 0:
            pixels.append(img.getpixel((x, y1 - 5)))
        if y2 + 5 < h:
            pixels.append(img.getpixel((x, y2 + 5)))
            
    if not pixels:
        return (255, 255, 255)
        
    first_pixel = pixels[0]
    if isinstance(first_pixel, int):
        pixels.sort()
        return pixels[len(pixels) // 2]
    else:
        num_channels = len(first_pixel)
        medians = []
        for c in range(num_channels):
            vals = [p[c] for p in pixels]
            vals.sort()
            medians.append(vals[len(vals) // 2])
        return tuple(medians)

def process_image(img_path):
    try:
        img = Image.open(img_path)
        w, h = img.size
        
        # Define bottom-left and bottom-right crops
        crop_h = 150
        crop_top = h - crop_h
        
        crops = [
            ("left", img.crop((0, crop_top, 750, h)), 0),
            ("right", img.crop((w - 900, crop_top, w, h)), w - 900)
        ]
        
        draw = ImageDraw.Draw(img)
        watermark_y_by_side = {"left": [], "right": []}
        detected_texts = []
        
        keywords = ["审", "图", "号", "GS", "gs", "3", "23", "3023", "SESS", "SHED", "SES", "wags", "2017", "2019", "2020", "2021", "2023", "ales", "4ie"]
        
        for side, cropped, x_offset in crops:
            # Scale up 2x
            large = cropped.resize((cropped.width * 2, cropped.height * 2), Image.Resampling.LANCZOS).convert('L')
            
            # Run OCR with PSM 6
            data = pytesseract.image_to_data(large, lang="chi_sim+eng", config="--psm 6", output_type=pytesseract.Output.DICT)
            
            n_boxes = len(data['level'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                if not text:
                    continue
                    
                is_watermark = False
                
                # Check keywords
                for kw in keywords:
                    if kw in text:
                        is_watermark = True
                        break
                        
                # Check digits
                if not is_watermark:
                    if re.search(r'\d+', text):
                        is_watermark = True
                        
                if is_watermark:
                    # Convert coords back to original image space
                    y_orig = crop_top + int(data['top'][i] / 2)
                    box_h = int(data['height'][i] / 2)
                    
                    watermark_y_by_side[side].append((y_orig, y_orig + box_h))
                    detected_texts.append(text)
                    
        erased_count = 0
        
        # Process left side erasure if any watermark was detected on the left
        if watermark_y_by_side["left"]:
            min_y = min([b[0] for b in watermark_y_by_side["left"]])
            max_y = max([b[1] for b in watermark_y_by_side["left"]])
            
            # Expand y range slightly
            y1 = max(0, min_y - 12)
            y2 = min(h, max_y + 12)
            
            # Erase the entire left horizontal margin band (x=30 to x=750)
            x1, x2 = 30, 750
            median_color = get_horizontal_median_color(img, (x1, y1, x2, y2))
            draw.rectangle([x1, y1, x2, y2], fill=median_color)
            erased_count += 1
            
        # Process right side erasure if any watermark was detected on the right
        if watermark_y_by_side["right"]:
            min_y = min([b[0] for b in watermark_y_by_side["right"]])
            max_y = max([b[1] for b in watermark_y_by_side["right"]])
            
            y1 = max(0, min_y - 12)
            y2 = min(h, max_y + 12)
            
            # Erase the entire right horizontal margin band (x=w-950 to x=w-30)
            x1, x2 = max(0, w - 950), min(w, w - 30)
            median_color = get_horizontal_median_color(img, (x1, y1, x2, y2))
            draw.rectangle([x1, y1, x2, y2], fill=median_color)
            erased_count += 1
            
        if erased_count > 0:
            img.save(img_path)
            print(f"Processed {os.path.basename(img_path)}:")
            print(f"  - Detected texts: {detected_texts}")
            print(f"  - Erased {erased_count} full-width margin bands.")
            return True
        return False
    except Exception as e:
        print(f"Error processing {img_path}: {e}")
        return False

def main():
    images_dir = "/Users/brainzhang/work/brainzhang/ChasingHorizons/docs/images"
    jpg_files = []
    for root, dirs, files in os.walk(images_dir):
        if "maps" in root: # skip route maps
            continue
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg')):
                jpg_files.append(os.path.join(root, f))
                
    print(f"Starting high-precision watermark erasure v4 on {len(jpg_files)} JPG maps...")
    modified_count = 0
    for path in sorted(jpg_files):
        if process_image(path):
            modified_count += 1
            
    print(f"\nCompleted. Cleanly erased watermarks in {modified_count} files.")

if __name__ == "__main__":
    main()
