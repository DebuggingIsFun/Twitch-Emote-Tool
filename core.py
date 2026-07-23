"""Emote detection and export.

Two public entry points:
- `detect_emotes_with_rects(...)`: edge-detect a PNG grid of emotes,
  number the filled cells, and return a marked preview plus a list of
  cell metadata.
- `export_emotes(...)` / `export_animated_emotes(...)`: write static
  PNGs and/or animated GIFs to a per-image output folder, sized for
  one or more streaming platforms.
"""

import logging
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from animations import (
    DEFAULT_FPS,
    DEFAULT_INTENSITY,
    SUPPORTED_ANIMATIONS,
    generate_frames,
    save_gif,
)


# ---- Debug logging helpers ---------------------------------------------

_LOGGER_NAME = "emote_debug"


def setup_logging(filename):
    """Write a per-run `debug.log` next to the source image.

    Returns `(logger, debug_dir)`. The directory is created if missing,
    and existing handlers are cleared so repeated calls in a single
    process don't double-log.
    """
    base_dir = os.path.dirname(filename)
    debug_dir = os.path.join(base_dir, "debug")
    os.makedirs(debug_dir, exist_ok=True)

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    handler = logging.FileHandler(os.path.join(debug_dir, "debug.log"), mode="w")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    return logger, debug_dir


def _save_debug_image(debug_dir, filename, image, logger):
    """Save a debug image, handling both OpenCV (numpy) and PIL inputs."""
    path = os.path.join(debug_dir, filename)
    if isinstance(image, np.ndarray):
        cv2.imwrite(path, image)
    else:
        image.save(path)
    logger.debug(f"Saved debug image: {filename}")


# ---- Detection: edge pipeline ------------------------------------------

_MIN_CONTOUR_AREA = 15000
_MIN_ASPECT, _MAX_ASPECT = 0.7, 1.4
_ROW_BAND = 100  # rectangles in the same y//100 stripe are treated as one row

# has_content thresholds: a cell is "filled" if ANY of these is strong
# on its own, or if multiple weak signals co-occur (so dark/transparent
# emotes don't get mis-flagged while grid artifacts don't false-positive).
_HAS_CONTENT_ALPHA = 0.05
_HAS_CONTENT_BRIGHT_MIN = 0.03
_HAS_CONTENT_WEAK_TOTAL = 0.04
_HAS_CONTENT_EDGE_MIN = 0.02
_HAS_CONTENT_ALPHA_PIXEL = 16
_HAS_CONTENT_BRIGHT_PIXEL = 15
_HAS_CONTENT_EDGE_DELTA = 8


def _extract_rectangles(img_bgr):
    """Run the edge detection pipeline and return filtered rects sorted
    in reading order (top-to-bottom, left-to-right within each row)."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 40, 120)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(edges, kernel, iterations=2)
    closed = cv2.erode(dilated, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rects = []
    for cnt in contours:
        if cv2.contourArea(cnt) < _MIN_CONTOUR_AREA:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        aspect = w / float(h)
        if _MIN_ASPECT < aspect < _MAX_ASPECT:
            rects.append((x, y, w, h))
    return sorted(rects, key=lambda r: (r[1] // _ROW_BAND, r[0])), contours, closed


def _has_content(rgba_crop, brightness_threshold=_HAS_CONTENT_BRIGHT_PIXEL, min_fraction=_HAS_CONTENT_BRIGHT_MIN):
    """Return True if `rgba_crop` looks like a filled emote cell.

    Combines three signals - non-transparent pixel fraction, bright
    pixel fraction, and intra-cell edge density - so dark or
    transparent emotes are still detected and anti-aliased grid
    artifacts do not cause false positives.
    """
    arr = np.array(rgba_crop)
    h, w = arr.shape[:2]
    if h == 0 or w == 0:
        return False

    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]
    alpha_frac = (alpha > _HAS_CONTENT_ALPHA_PIXEL).mean()
    bright_frac = (rgb.mean(axis=2) > brightness_threshold).mean()

    gray = rgb.mean(axis=2).astype(np.uint8)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    edge_density = (gx > _HAS_CONTENT_EDGE_DELTA).mean() + (gy > _HAS_CONTENT_EDGE_DELTA).mean()

    if alpha_frac >= _HAS_CONTENT_ALPHA or bright_frac >= min_fraction:
        return True
    return (alpha_frac + bright_frac) >= _HAS_CONTENT_WEAK_TOTAL and edge_density > _HAS_CONTENT_EDGE_MIN


def _load_label_font(size=24):
    """Return a TTF label font, falling back to Pillow's bitmap default
    when no TTF is available (e.g. minimal Linux installs)."""
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def detect_emotes_with_rects(filename, debug_enabled=False):
    """Detect rectangles, mark filled cells, return the marked image
    and per-cell metadata.

    Each metadata dict has shape `{"rect": (x, y, w, h), "has_content": bool}`
    plus an `"id"` field on filled cells (1-based, in reading order).
    """
    logger, debug_dir = (None, None)
    if debug_enabled:
        logger, debug_dir = setup_logging(filename)
        logger.info("=== EMOTE DETECTION STARTED ===")
        logger.info(f"Input file: {filename}")

    img = cv2.imread(filename, cv2.IMREAD_COLOR)
    if debug_enabled:
        logger.info(f"Image loaded - Size: {img.shape[1]}x{img.shape[0]} pixels")
        _save_debug_image(debug_dir, "01_original.png", img, logger)

    rects, contours, closed = _extract_rectangles(img)

    if debug_enabled:
        logger.info(f"Found {len(contours)} total contours")
        contour_debug = img.copy()
        cv2.drawContours(contour_debug, contours, -1, (0, 255, 255), 2)
        _save_debug_image(debug_dir, "07_all_contours.png", contour_debug, logger)
        logger.info(
            f"Filtered to {len(rects)} valid rectangles "
            f"(area > {_MIN_CONTOUR_AREA}, aspect ratio {_MIN_ASPECT}-{_MAX_ASPECT})"
        )
        rect_debug = img.copy()
        for (x, y, w, h) in rects:
            cv2.rectangle(rect_debug, (x, y), (x + w, y + h), (0, 255, 0), 3)
        _save_debug_image(debug_dir, "08_accepted_rectangles.png", rect_debug, logger)

    pil_img = Image.open(filename).convert("RGBA")
    draw = ImageDraw.Draw(pil_img)
    label_font = _load_label_font()

    cell_infos = []
    filled_count = 0
    for (x, y, w, h) in rects:
        cell_img = pil_img.crop((x, y, x + w, y + h))
        if _has_content(cell_img):
            filled_count += 1
            draw.rectangle([x, y, x + w - 1, y + h - 1], outline="lime", width=4)
            draw.text((x + 10, y + 10), str(filled_count), fill="white", font=label_font)
            cell_infos.append({"rect": (x, y, w, h), "has_content": True, "id": filled_count})
        else:
            draw.rectangle([x, y, x + w - 1, y + h - 1], outline="red", width=2)
            cell_infos.append({"rect": (x, y, w, h), "has_content": False})

    if debug_enabled:
        logger.info(f"Detection complete: {filled_count} filled, {len(rects) - filled_count} empty")
        debug_img_path = os.path.join(debug_dir, "debug.png")
        pil_img.save(debug_img_path)
        logger.info(f"Debug preview saved: {debug_img_path}")
        logger.info("=== DETECTION PHASE COMPLETE ===")

    return pil_img, cell_infos


# ---- Filename / export helpers -----------------------------------------

_CELL_PADDING = 5
_FILENAME_KEEP = (" ", "-", "_")


def sanitize_filename(name):
    """Strip characters that cause file-system issues; fall back to
    a safe placeholder when the result is empty. Public so callers like
    the GUI placeholder-text builder can use the same rule the export
    code applies to the on-disk filenames."""
    safe = "".join(c for c in name if c.isalnum() or c in _FILENAME_KEEP).rstrip()
    return safe or "emote"


# Back-compat alias for any external caller that imported the old name.
_sanitize_filename = sanitize_filename


def _crop_cell(base_img, cell):
    """Crop the cell out of `base_img`, inset by `_CELL_PADDING`."""
    x, y, w, h = cell["rect"]
    return base_img.crop((x + _CELL_PADDING, y + _CELL_PADDING, x + w - _CELL_PADDING, y + h - _CELL_PADDING))


def _resolve_out_path(out_dir, base_filename, written_paths):
    """Return a path inside `out_dir` that does not collide with an
    already-written file this run, appending `_2`, `_3`, ... as needed.
    `written_paths` is mutated to include the returned path."""
    out_path = os.path.join(out_dir, base_filename)
    if out_path not in written_paths and not os.path.exists(out_path):
        written_paths.add(out_path)
        return out_path

    stem, ext = os.path.splitext(base_filename)
    suffix = 2
    while True:
        candidate_path = os.path.join(out_dir, f"{stem}_{suffix}{ext}")
        if candidate_path not in written_paths and not os.path.exists(candidate_path):
            written_paths.add(candidate_path)
            return candidate_path
        suffix += 1


# ---- Platform tables ---------------------------------------------------

PLATFORM_SIZES = {
    "twitch": [(112, 112), (56, 56), (28, 28)],
    "twitch_badges": [(72, 72), (36, 36), (18, 18)],
    "discord": [(128, 128), (64, 64), (32, 32)],
    "youtube": [(48, 48), (24, 24)],
    "kick": [(128, 128), (64, 64), (32, 32)],
}

# Animated platforms: only the largest size is exported, because most
# platforms cap animated emotes on file size rather than multiple sizes.
_ANIMATED_PLATFORM_SIZE = {
    "twitch": (112, 112),
    "twitch_badges": (72, 72),
    "discord": (128, 128),
    "youtube": (48, 48),
    "kick": (128, 128),
}

# Per-platform file-size caps for animated emotes. Twitch's 1MB cap is
# the project baseline (the user explicitly designed for it); other
# values are commonly-documented community limits.
_ANIMATED_PLATFORM_MAX_BYTES = {
    "twitch": 1 * 1024 * 1024,
    "twitch_badges": 1 * 1024 * 1024,
    "discord": 256 * 1024,  # Discord animated emoji cap
    "youtube": 1 * 1024 * 1024,
    "kick": 1 * 1024 * 1024,
}

# When a generated GIF exceeds the cap, intensity is multiplied by this
# factor and the GIF is regenerated. 0.85 keeps the ramp smooth.
_AUTOSHRINK_STEP = 0.85
_AUTOSHRINK_MAX_ATTEMPTS = 6
_AUTOSHRINK_FLOOR = 0.20


def _save_animated_gif_with_cap(base, animation, fps, initial_intensity, out_path, platform, logger=None):
    """Save the GIF, then auto-shrink intensity until the file fits
    the platform's size cap. Returns the final `(intensity, file_bytes)`.

    The first attempt uses `initial_intensity` directly. If the file is
    over the cap, intensity is multiplied by `_AUTOSHRINK_STEP` and the
    GIF is regenerated, up to `_AUTOSHRINK_MAX_ATTEMPTS` times. If the
    GIF is still too large after all attempts, the last (oversize) file
    is kept and the oversize is logged as a warning.
    """
    cap = _ANIMATED_PLATFORM_MAX_BYTES.get(platform)

    intensity = float(initial_intensity)
    save_gif(generate_frames(base, animation, intensity=intensity), out_path, fps=fps, logger=logger)
    bytes_written = os.path.getsize(out_path)
    if cap is None:
        return intensity, bytes_written

    attempts = 1
    while bytes_written > cap and attempts < _AUTOSHRINK_MAX_ATTEMPTS:
        intensity *= _AUTOSHRINK_STEP
        if intensity < _AUTOSHRINK_FLOOR:
            break
        save_gif(generate_frames(base, animation, intensity=intensity), out_path, fps=fps, logger=logger)
        bytes_written = os.path.getsize(out_path)
        attempts += 1
        if logger is not None:
            logger.debug(
                f"  Auto-shrunk {os.path.basename(out_path)}: "
                f"intensity={intensity:.2f}, {bytes_written / 1024:.1f} KB"
            )

    if bytes_written > cap and logger is not None:
        logger.warning(
            f"  {os.path.basename(out_path)} is {bytes_written / 1024:.1f} KB, "
            f"exceeds the {cap / 1024:.0f} KB {platform} cap after {attempts} attempts."
        )
    return intensity, bytes_written


# ---- Public export entry points ----------------------------------------

def _make_out_dir(source_filename, sub="emotes_export_multi"):
    out_dir = os.path.join(os.path.dirname(source_filename), sub)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def _log_export_start(logger, source_filename, platforms, n_emotes, banner):
    if logger is None:
        return
    logger.info(f"=== {banner} ===")
    logger.info(f"Source file: {source_filename}")
    logger.info(f"Platforms selected: {platforms}")
    logger.info(f"Emotes to export: {n_emotes}")


def _resolve_emote_names(name_entries):
    """Return `(cell, base_name)` pairs, applying the same fallback the
    GUI uses so CLI / programmatic callers also get safe names."""
    out = []
    for cell, name in name_entries:
        base = (name or "").strip() or f"emote_{cell['id']}"
        out.append((cell, base))
    return out


def export_emotes(current_filename, name_entries, selected_platforms, debug_enabled=False):
    """Export each filled emote as static PNGs sized for every selected
    platform. Returns `(exported_count, out_dir)`."""
    logger = None
    if debug_enabled:
        logger, _ = setup_logging(current_filename)
    _log_export_start(logger, current_filename, selected_platforms, len(name_entries), "EXPORT STARTED")

    base_img = Image.open(current_filename).convert("RGBA")
    out_dir = _make_out_dir(current_filename)
    if debug_enabled:
        logger.info(f"Output directory: {out_dir}")

    written_paths, exported_count = set(), 0
    for cell, base_name in _resolve_emote_names(name_entries):
        safe_name = _sanitize_filename(base_name) or f"emote_{cell['id']}"
        crop = _crop_cell(base_img, cell)
        if debug_enabled:
            logger.info(f"Processing emote #{cell['id']}: '{safe_name}'")

        for platform in selected_platforms:
            for size_w, size_h in PLATFORM_SIZES[platform]:
                # LANCZOS gives best quality for downscaling.
                sized = crop.resize((size_w, size_h), Image.Resampling.LANCZOS)
                out_path = _resolve_out_path(
                    out_dir, f"{safe_name}_{platform}_{size_w}x{size_h}.png", written_paths
                )
                sized.save(out_path, format="PNG")
                exported_count += 1
                if debug_enabled:
                    logger.debug(f"  Saved: {os.path.basename(out_path)} for {platform}")

    if debug_enabled:
        logger.info(f"=== EXPORT COMPLETE: {exported_count} files created ===")
    return exported_count, out_dir


def _resolve_emote_spec(selected_animations, cell_id):
    """Return `(animations_list, fps, intensity)` for one emote.

    `selected_animations` may be an iterable of names, or a per-cell
    dict mapping cell_id to either a list of names or a full spec dict
    with `animations`/`fps`/`intensity`. Names not in
    `SUPPORTED_ANIMATIONS` are dropped.
    """
    spec = selected_animations.get(cell_id) if isinstance(selected_animations, dict) else None
    if isinstance(spec, dict):
        return (
            [a for a in spec.get("animations", []) if a in SUPPORTED_ANIMATIONS],
            int(spec.get("fps", DEFAULT_FPS)),
            float(spec.get("intensity", DEFAULT_INTENSITY)),
        )
    if isinstance(spec, list):
        return (
            [a for a in spec if a in SUPPORTED_ANIMATIONS],
            DEFAULT_FPS,
            DEFAULT_INTENSITY,
        )
    if spec is None and not isinstance(selected_animations, dict):
        return (
            [a for a in selected_animations if a in SUPPORTED_ANIMATIONS],
            DEFAULT_FPS,
            DEFAULT_INTENSITY,
        )
    return ([], DEFAULT_FPS, DEFAULT_INTENSITY)


def export_animated_emotes(current_filename, name_entries, selected_platforms,
                           selected_animations, debug_enabled=False):
    """Export each filled emote as a looping animated GIF per platform.

    One GIF is produced for every (emote, platform, animation)
    combination. Output goes into the same `emotes_export_multi`
    folder used by `export_emotes` and uses the same collision-safe
    filename scheme.

    `selected_animations` accepts:
      - an iterable of names: applies that set of animations to every
        emote in `name_entries`.
      - a dict `{cell_id: [name, ...]}`: per-emote animation lists.
      - a dict `{cell_id: {"animations": [...], "fps": int, "intensity": float}}`:
        full per-emote spec.

    Names not in `SUPPORTED_ANIMATIONS` are silently dropped.

    Returns `(exported_count, out_dir)`.
    """
    logger = None
    if debug_enabled:
        logger, _ = setup_logging(current_filename)
    _log_export_start(logger, current_filename, selected_platforms, len(name_entries), "ANIMATED EXPORT STARTED")

    base_img = Image.open(current_filename).convert("RGBA")
    out_dir = _make_out_dir(current_filename)
    if debug_enabled:
        logger.info(f"Output directory: {out_dir}")

    written_paths, exported_count, autoshrink_log = set(), 0, []
    for cell, base_name in _resolve_emote_names(name_entries):
        safe_name = _sanitize_filename(base_name) or f"emote_{cell['id']}"
        crop = _crop_cell(base_img, cell)
        anims, fps, intensity = _resolve_emote_spec(selected_animations, cell["id"])
        if not anims:
            continue

        if debug_enabled:
            logger.info(
                f"Processing emote #{cell['id']}: '{safe_name}' "
                f"(animations: {anims}, fps={fps}, intensity={intensity})"
            )

        for platform in selected_platforms:
            if platform not in _ANIMATED_PLATFORM_SIZE:
                continue
            size = _ANIMATED_PLATFORM_SIZE[platform]
            cap_kb = _ANIMATED_PLATFORM_MAX_BYTES.get(platform, 0) / 1024
            base = crop.resize(size, Image.Resampling.LANCZOS)

            for animation in anims:
                base_filename = f"{safe_name}_{platform}_{animation}.gif"
                out_path = _resolve_out_path(out_dir, base_filename, written_paths)
                final_intensity, bytes_written = _save_animated_gif_with_cap(
                    base, animation, fps, intensity, out_path, platform, logger=logger,
                )
                exported_count += 1
                if final_intensity < intensity:
                    autoshrink_log.append((os.path.basename(out_path), final_intensity, bytes_written, cap_kb))
                if debug_enabled:
                    logger.debug(
                        f"  Saved: {os.path.basename(out_path)} for {platform} ({animation}) - "
                        f"{bytes_written / 1024:.1f} KB (cap {cap_kb:.0f} KB, intensity {final_intensity:.2f})"
                    )

    if debug_enabled:
        if autoshrink_log:
            logger.info("Auto-shrink summary (intensity reduced to fit cap):")
            for name, intens, b, cap in autoshrink_log:
                logger.info(f"  {name}: intensity={intens:.2f}, {b / 1024:.1f} KB (cap {cap:.0f} KB)")
        logger.info(f"=== ANIMATED EXPORT COMPLETE: {exported_count} files created ===")

    return exported_count, out_dir
