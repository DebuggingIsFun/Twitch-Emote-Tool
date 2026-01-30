from PIL import Image, ImageDraw
import cv2
import numpy as np
import os
import logging


def setup_logging(filename):
    """
    Set up logging to write to debug.log in same folder as the image.
    Returns the logger and the debug directory path.
    """
    # Place debug.log next to source image for easy bug reporting
    debug_dir = os.path.dirname(filename)
    log_path = os.path.join(debug_dir, "debug.log")
    
    # Create a logger
    logger = logging.getLogger("emote_debug")
    logger.setLevel(logging.DEBUG)
    
    # Clear old handlers to avoid duplicate logs if function is called multiple times
    logger.handlers.clear()
    
    # Create file handler - writes to debug.log
    file_handler = logging.FileHandler(log_path, mode='w')
    file_handler.setLevel(logging.DEBUG)
    
    # Create format with timestamp
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    return logger, debug_dir


def detect_emotes_with_rects(filename, debug_enabled=False):
    """Detect rectangles, number filled ones, return marked image + cell data"""
    
    # Optional debug logging for bug reports
    logger = None
    debug_dir = None
    if debug_enabled:
        logger, debug_dir = setup_logging(filename)
        logger.info("=== EMOTE DETECTION STARTED ===")
        logger.info(f"Input file: {filename}")
    
    # === STEP 1: Edge Detection Pipeline ===
    # Using OpenCV to find rectangle boundaries in the emote grid
    img = cv2.imread(filename, cv2.IMREAD_COLOR)
    
    if debug_enabled:
        logger.info(f"Image loaded - Size: {img.shape[1]}x{img.shape[0]} pixels")
    
    # Convert to grayscale - edges are easier to detect without color noise
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Blur reduces noise that would create false edges
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Canny finds edges by detecting brightness gradients
    edges = cv2.Canny(blur, 40, 120)

    # Morphological operations close gaps in rectangle borders
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.dilate(edges, kernel, iterations=2) # Expand edges to connect gaps
    closed = cv2.erode(closed, kernel, iterations=2) # Shrink back to original size
    
    if debug_enabled:
        logger.debug("Edge detection completed (Canny + morphological operations)")

    # === STEP 2: Find and Filter Rectangles ===
    # Extract contours (connected edge regions) from the processed image
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if debug_enabled:
        logger.info(f"Found {len(contours)} total contours")
    
    rects = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Filter by minimum size - emote cells are expected to be reasonably large
        if area < 15000:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / float(h)
        # Filter by aspect ratio - emote cells are roughly square (0.7-1.4 allows slight rectangles)
        if 0.7 < aspect < 1.4:
            rects.append((x, y, w, h))
    
    # Sort rectangles top-to-bottom, left-to-right (reading order)
    # Dividing y by 100 groups rectangles into rows
    rects = sorted(rects, key=lambda r: (r[1] // 100, r[0]))
    
    if debug_enabled:
        logger.info(f"Filtered to {len(rects)} valid rectangles (area > 15000, aspect ratio 0.7-1.4)")

    # === STEP 3: Analyze Cell Content ===
    # Switch to PIL for easier image manipulation and drawing
    pil_img = Image.open(filename).convert("RGBA")
    draw = ImageDraw.Draw(pil_img)

    def has_content(rgba_crop, brightness_threshold=15, min_fraction=0.03):
        """Check if cell contains emote by measuring bright pixel percentage"""
        arr = np.array(rgba_crop)
        rgb = arr[:, :, :3]
        # Calculate brightness (average of RGB channels)
        brightness = rgb.mean(axis=2)
        # Count pixels above threshold
        bright_mask = brightness > brightness_threshold
        frac = np.count_nonzero(bright_mask) / float(bright_mask.size)
        # If 3%+ of pixels are bright, cell has content
        return frac >= min_fraction

    # === STEP 4: Mark Cells and Number Filled Ones ===
    cell_infos = []
    filled_count = 1
    for (x, y, w, h) in rects:
        full_cell = pil_img.crop((x, y, x + w, y + h))
        filled = has_content(full_cell)
        
        if filled:
            # Green border + number for filled cells
            draw.rectangle([x, y, x+w-1, y+h-1], outline="lime", width=4)
            draw.text((x+10, y+10), str(filled_count), fill="white", font_size=24)
            cell_infos.append({"rect": (x, y, w, h), "has_content": True, "id": filled_count})
            
            if debug_enabled:
                logger.debug(f"Cell #{filled_count}: FILLED at position ({x}, {y}), size {w}x{h}")
            
            filled_count += 1
        else:
            # Red border for empty cells
            draw.rectangle([x, y, x+w-1, y+h-1], outline="red", width=2)
            cell_infos.append({"rect": (x, y, w, h), "has_content": False})
            
            if debug_enabled:
                logger.debug(f"Cell: EMPTY at position ({x}, {y}), size {w}x{h}")
    
    if debug_enabled:
        logger.info(f"Detection complete: {filled_count - 1} filled, {len(rects) - (filled_count - 1)} empty")
        
        # Save debug preview image
        debug_img_path = os.path.join(debug_dir, "debug.png")
        pil_img.save(debug_img_path)
        logger.info(f"Debug preview saved: {debug_img_path}")
        logger.info("=== DETECTION PHASE COMPLETE ===")
    
    return pil_img, cell_infos


def export_emotes(current_filename, name_entries, selected_platforms, debug_enabled=False):
    """Export emotes in platform-specific sizes"""
    
    # Set up logging if debug is enabled
    logger = None
    if debug_enabled:
        logger, _ = setup_logging(current_filename)
        logger.info("=== EXPORT STARTED ===")
        logger.info(f"Source file: {current_filename}")
        logger.info(f"Platforms selected: {selected_platforms}")
        logger.info(f"Emotes to export: {len(name_entries)}")
    
    # Platform size requirements
    platform_sizes = {
        "twitch": [(112, 112), (56, 56), (28, 28)],
        "twitchbages": [(72, 72), (36, 36), (18, 18)],
        "discord": [(128, 128),(64, 64), (32, 32)],
        "youtube": [ (48, 48), (24, 24)],
        "kick": [(128, 128), (64, 64), (32, 32)]
    }

    base_img = Image.open(current_filename).convert("RGBA")
    # Create output folder next to source image
    out_dir = os.path.join(os.path.dirname(current_filename), "emotes_export_multi")
    os.makedirs(out_dir, exist_ok=True)
    
    if debug_enabled:
        logger.info(f"Output directory: {out_dir}")

    exported_count = 0
    for cell, name in name_entries:
        # Use provided name or fallback to numbered default
        base_name = name.strip() or f"emote_{cell['id']}"
        x, y, w, h = cell["rect"]
        crop = base_img.crop((x, y, x + w, y + h))
        
        if debug_enabled:
            logger.info(f"Processing emote #{cell['id']}: '{base_name}'")

        # Generate all required sizes for each selected platform
        for platform in selected_platforms:
            for size_w, size_h in platform_sizes[platform]:
                # LANCZOS gives best quality for downscaling
                sized_emote = crop.resize((size_w, size_h), Image.Resampling.LANCZOS)
                # Sanitize filename - remove special characters that cause file system issues
                safe_name = "".join(c for c in base_name if c.isalnum() or c in (" ", "-", "_")).rstrip()
                if not safe_name:
                    safe_name = f"emote_{cell['id']}"
                
                filename = f"{safe_name}_{size_w}x{size_h}.png"
                out_path = os.path.join(out_dir, filename)
                sized_emote.save(out_path, format="PNG")
                exported_count += 1
                
                if debug_enabled:
                    logger.debug(f"  Saved: {filename} for {platform}")
    
    if debug_enabled:
        logger.info(f"=== EXPORT COMPLETE: {exported_count} files created ===")
    
    return exported_count, out_dir
