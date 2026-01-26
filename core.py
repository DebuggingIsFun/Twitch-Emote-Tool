from PIL import Image, ImageDraw
import cv2
import numpy as np
import os

def detect_emotes_with_rects(filename):
    """Detect rectangles, number filled ones, return marked image + cell data"""
    
    # OpenCV edge detection pipeline
    img = cv2.imread(filename, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 40, 120)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.dilate(edges, kernel, iterations=2)
    closed = cv2.erode(closed, kernel, iterations=2)

    # Find valid rectangles (size + aspect ratio filtered)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rects = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 15000:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / float(h)
        if 0.7 < aspect < 1.4:
            rects.append((x, y, w, h))

    rects = sorted(rects, key=lambda r: (r[1] // 100, r[0]))  # Row-major order

    # PIL image for drawing + content analysis
    pil_img = Image.open(filename).convert("RGBA")
    draw = ImageDraw.Draw(pil_img)

    def has_content(rgba_crop, brightness_threshold=15, min_fraction=0.03):
        arr = np.array(rgba_crop)
        rgb = arr[:, :, :3]
        brightness = rgb.mean(axis=2)
        bright_mask = brightness > brightness_threshold
        frac = np.count_nonzero(bright_mask) / float(bright_mask.size)
        return frac >= min_fraction

    # Mark cells + number filled ones
    cell_infos = []
    filled_count = 1
    for (x, y, w, h) in rects:
        full_cell = pil_img.crop((x, y, x + w, y + h))
        filled = has_content(full_cell)
        
        if filled:
            draw.rectangle([x, y, x+w-1, y+h-1], outline="lime", width=4)
            draw.text((x+10, y+10), str(filled_count), fill="white", font_size=24)
            cell_infos.append({"rect": (x, y, w, h), "has_content": True, "id": filled_count})
            filled_count += 1
        else:
            draw.rectangle([x, y, x+w-1, y+h-1], outline="red", width=2)
            cell_infos.append({"rect": (x, y, w, h), "has_content": False})
    
    return pil_img, cell_infos

def export_emotes(current_filename, name_entries, selected_platforms):
    """Export emotes in platform-specific sizes"""
    
    # Platform size requirements
    platform_sizes = {
        "twitch": [(300, 300), (112, 112), (56, 56), (28, 28)],
        "twitchbages": [(200, 200), (72, 72), (36, 36), (18, 18)],
        "discord": [(128, 128)],
        "youtube": [(100, 100), (48, 48), (24, 24)],
        "kick": [(500, 500), (128, 128), (64, 64), (32, 32)]
    }

    base_img = Image.open(current_filename).convert("RGBA")
    out_dir = os.path.join(os.path.dirname(current_filename), "emotes_export_multi")
    os.makedirs(out_dir, exist_ok=True)

    exported_count = 0
    for cell, name in name_entries:
        base_name = name.strip() or f"emote_{cell['id']}"
        x, y, w, h = cell["rect"]
        crop = base_img.crop((x, y, x + w, y + h))

        for platform in selected_platforms:
            for size_w, size_h in platform_sizes[platform]:
                sized_emote = crop.resize((size_w, size_h), Image.Resampling.LANCZOS)
                safe_name = "".join(c for c in base_name if c.isalnum() or c in (" ", "-", "_")).rstrip()
                if not safe_name:
                    safe_name = f"emote_{cell['id']}"
                
                filename = f"{safe_name}_{size_w}x{size_h}.png"
                out_path = os.path.join(out_dir, filename)
                sized_emote.save(out_path, format="PNG")
                exported_count += 1
    
    return exported_count, out_dir
