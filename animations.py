"""Procedural emote animations.

Each function takes a static RGBA PIL Image (the cropped emote cell) and
returns a list of RGBA PIL Image frames. The caller is responsible for
saving them as a GIF (see `save_gif` below).

All animations preserve transparency. They are intentionally cheap so
that 40 emotes * 24 effects can be exported in a few seconds on a laptop.

Each animation accepts an `intensity` (float, 0.25..1.5) kwarg that
scales the number of frames and (for some effects) the amplitude. The
export path uses this to auto-shrink a GIF until it fits a platform's
file-size cap.
"""

import colorsys
import math
import os
from PIL import Image


SUPPORTED_ANIMATIONS = (
    "slide_in",
    "slide_out",
    "shake",
    "spin",
    "rainbow",
    "pulse",
    "bounce",
    "fade_in",
    "fade_out",
    "zoom_in",
    "zoom_out",
    "flip",
    "wobble",
    "heart_beat",
    "floating",
    "wiggle",
    "jam",
    "tilt",
    "zoom_close",
    "mega_bounce",
    "pet",
    "flag",
    "party",
)

DEFAULT_FPS = 15
DEFAULT_INTENSITY = 1.0
MIN_INTENSITY = 0.25
MAX_INTENSITY = 1.5
MIN_FRAMES = 2


def _clamp_intensity(value):
    """Clamp the user-supplied intensity to the supported range."""
    if value is None:
        return DEFAULT_INTENSITY
    return max(MIN_INTENSITY, min(MAX_INTENSITY, float(value)))


def _scale_frames(default_frames, intensity):
    """Scale an animation's default frame count by intensity, floored at MIN_FRAMES."""
    return max(MIN_FRAMES, int(round(default_frames * _clamp_intensity(intensity))))


def _ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def _ease_in_cubic(t):
    return t ** 3


def _empty_frames(w, h, count):
    return [Image.new("RGBA", (w, h), (0, 0, 0, 0)) for _ in range(count)]


def _transparent(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def _paste_frame(img, w, h, dx, dy):
    """Paste `img` at (dx, dy) onto a transparent (w, h) canvas."""
    frame = _transparent(w, h)
    frame.paste(img, (dx, dy), img)
    return frame


def _centered_scaled_frame(img, w, h, scale_x, scale_y):
    """Resize `img` by (scale_x, scale_y) and paste it centered on a transparent canvas."""
    sw = max(1, int(round(img.width * scale_x)))
    sh = max(1, int(round(img.height * scale_y)))
    scaled = img.resize((sw, sh), Image.Resampling.BICUBIC)
    frame = _transparent(w, h)
    frame.paste(scaled, ((w - sw) // 2, (h - sh) // 2), scaled)
    return frame


def slide_in(img, frames=12, fps=DEFAULT_FPS, **_):
    """Slide in from the left, easing out."""
    w, h = img.size
    out = []
    for i in range(frames):
        t = _ease_out_cubic(i / max(frames - 1, 1))
        offset = int(round((1 - t) * w))
        out.append(_paste_frame(img, w, h, -offset, 0))
    return out


def slide_out(img, frames=12, fps=DEFAULT_FPS, **_):
    """Slide out to the right, easing in."""
    w, h = img.size
    out = []
    for i in range(frames):
        t = _ease_in_cubic(i / max(frames - 1, 1))
        offset = int(round(t * w))
        out.append(_paste_frame(img, w, h, offset, 0))
    return out


def shake(img, frames=12, fps=DEFAULT_FPS, amplitude=4, **_):
    """Sinusoidal horizontal shake with decaying amplitude."""
    w, h = img.size
    out = []
    for i in range(frames):
        decay = 1 - (i / max(frames - 1, 1)) * 0.5
        offset = int(round(amplitude * decay * math.sin(i * 0.9)))
        out.append(_paste_frame(img, w, h, offset, 0))
    return out


def spin(img, frames=24, fps=DEFAULT_FPS, **_):
    """Full 360° rotation, no zoom (preserves emote footprint)."""
    w, h = img.size
    return [img.rotate(-(360.0 * i) / frames, resample=Image.BICUBIC, expand=False) for i in range(frames)]


def rainbow(img, frames=30, fps=DEFAULT_FPS, **_):
    """Cycle hue while keeping saturation, value, and alpha."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)

    src = img.load()
    out = []
    for i in range(frames):
        hue_shift = i / frames
        frame = Image.new("RGBA", (w, h))
        dst = frame.load()
        for y in range(h):
            for x in range(w):
                r, g, b, a = src[x, y]
                if a == 0:
                    dst[x, y] = (0, 0, 0, 0)
                    continue
                hue, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
                hue = (hue + hue_shift) % 1.0
                nr, ng, nb = colorsys.hsv_to_rgb(hue, s, v)
                dst[x, y] = (int(nr * 255), int(ng * 255), int(nb * 255), a)
        out.append(frame)
    return out


def pulse(img, frames=20, fps=DEFAULT_FPS, **_):
    """Scale 0.85 -> 1.15 -> 0.85 around the center."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = []
    for i in range(frames):
        t = i / max(frames - 1, 1)
        tri = 1 - abs(2 * t - 1)
        out.append(_centered_scaled_frame(img, w, h, 0.85 + 0.30 * tri, 0.85 + 0.30 * tri))
    return out


def bounce(img, frames=18, fps=DEFAULT_FPS, **_):
    """Vertical bouncing-ball motion with two bounces per cycle and a squish on impact."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = []
    for i in range(frames):
        t = i / frames
        y = int(round(abs(math.sin(t * 2 * math.pi * 2)) * (h * 0.45)))
        squish_phase = abs(((t * 4) % 2) - 1)
        scale_x = 1.0 - 0.18 * (1 - squish_phase) if squish_phase < 0.4 else 1.0
        if abs(scale_x - 1.0) > 0.01:
            scale_y = 1.0 / max(scale_x, 0.01)
            frame_img = _centered_scaled_frame(img, w, h, scale_x, scale_y)
            out.append(_paste_frame(frame_img, w, h, 0, h - frame_img.height - y))
        else:
            out.append(_paste_frame(img, w, h, 0, h - img.height - y))
    return out


def _with_alpha(img, alpha):
    """Return a copy of `img` with the alpha channel scaled to `alpha` (0..255)."""
    if img.size == (0, 0):
        return img.copy()
    r, g, b, a = img.split()
    a = a.point(lambda v, alpha=alpha: int(v * alpha / 255))
    return Image.merge("RGBA", (r, g, b, a))


def fade_in(img, frames=15, fps=DEFAULT_FPS, **_):
    """Fade from transparent to fully opaque, then hold the last frame for ~1/3 the duration."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = [_with_alpha(img, int(round(255 * _ease_out_cubic(i / max(frames - 1, 1))))) for i in range(frames)]
    out.extend([img.copy()] * max(1, frames // 3))
    return out


def fade_out(img, frames=15, fps=DEFAULT_FPS, **_):
    """Hold, then fade from opaque to transparent."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = [img.copy()] * max(1, frames // 3)
    out.extend([_with_alpha(img, int(round(255 * (1 - _ease_in_cubic(i / max(frames - 1, 1)))))) for i in range(frames)])
    return out


def zoom_in(img, frames=14, fps=DEFAULT_FPS, **_):
    """Scale 0.4 -> 1.05 (slight overshoot) -> 1.0."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = []
    for i in range(frames):
        t = i / max(frames - 1, 1)
        tri = 1 - abs(2 * t - 1)
        scale = min(0.4 + 0.70 * _ease_out_cubic(t) + 0.05 * tri, 1.10)
        out.append(_centered_scaled_frame(img, w, h, scale, scale))
    return out


def zoom_out(img, frames=14, fps=DEFAULT_FPS, **_):
    """Scale 1.4 -> 1.0."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = []
    for i in range(frames):
        t = i / max(frames - 1, 1)
        scale = 1.4 - 0.4 * _ease_out_cubic(t)
        out.append(_centered_scaled_frame(img, w, h, scale, scale))
    return out


def flip(img, frames=20, fps=DEFAULT_FPS, **_):
    """Horizontal mirror sweep. 0deg -> 90deg (edge) -> mirrored."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = []
    for i in range(frames):
        scale_x = math.cos(i / max(frames - 1, 1) * math.pi)
        new_w = max(1, int(round(abs(scale_x) * w)))
        scaled = img.resize((new_w, h), Image.Resampling.BICUBIC)
        if scale_x < 0:
            scaled = scaled.transpose(Image.FLIP_LEFT_RIGHT)
        out.append(_paste_frame(scaled, w, h, (w - new_w) // 2, 0))
    return out


def wobble(img, frames=18, fps=DEFAULT_FPS, **_):
    """Rotation oscillation +/- 10 degrees, easing back to 0."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = []
    for i in range(frames):
        t = i / max(frames - 1, 1)
        angle = 10.0 * math.sin(t * 4 * math.pi) * (1 - 0.7 * t)
        out.append(img.rotate(-angle, resample=Image.BICUBIC, expand=False))
    return out


def heart_beat(img, frames=20, fps=DEFAULT_FPS, **_):
    """Two quick pulses (lub-dub), then rest."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = []
    for i in range(frames):
        t = i / max(frames - 1, 1)
        peak = max(math.exp(-((t - 0.10) ** 2) * 800), math.exp(-((t - 0.30) ** 2) * 800))
        scale = 1.0 + 0.20 * peak
        out.append(_centered_scaled_frame(img, w, h, scale, scale))
    return out


def floating(img, frames=30, fps=DEFAULT_FPS, **_):
    """Slow circular drift (radius ~10% of cell)."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    radius_x, radius_y = w * 0.10, h * 0.10
    out = []
    for i in range(frames):
        t = i / frames
        dx = int(round(math.cos(t * 2 * math.pi) * radius_x))
        dy = int(round(math.sin(t * 2 * math.pi) * radius_y))
        out.append(_paste_frame(img, w, h, dx, dy))
    return out


def wiggle(img, frames=18, fps=DEFAULT_FPS, **_):
    """Alternating horizontal squish (jelly-like), preserving area."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = []
    for i in range(frames):
        t = i / max(frames - 1, 1)
        scale_x = 1.0 + 0.20 * (1 - abs(2 * t - 1))
        out.append(_centered_scaled_frame(img, w, h, scale_x, 1.0 / max(scale_x, 0.01)))
    return out


def jam(img, frames=18, fps=DEFAULT_FPS, **_):
    """Diagonal tilt side-to-side, like nodding along to a beat. Distinct from `tilt` (gentler)."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = []
    for i in range(frames):
        t = i / max(frames - 1, 1)
        angle = 12.0 * math.sin(t * 2 * math.pi - math.pi / 2)
        out.append(img.rotate(-angle, resample=Image.BICUBIC, expand=False))
    return out


def tilt(img, frames=20, fps=DEFAULT_FPS, **_):
    """Two half-sine nudge pulses (~6 deg). Quieter than `wobble`."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = []
    for i in range(frames):
        t = i / max(frames - 1, 1)
        angle = 6.0 * math.sin(t * 4 * math.pi)
        out.append(img.rotate(-angle, resample=Image.BICUBIC, expand=False))
    return out


def zoom_close(img, frames=14, fps=DEFAULT_FPS, **_):
    """Tighter, faster zoom than `zoom_in` with a brief hold near 1.25 then settle to 1.0."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = []
    for i in range(frames):
        t = i / max(frames - 1, 1)
        if t < 0.6:
            scale = 0.6 + 0.65 * _ease_out_cubic(t / 0.6)
        else:
            scale = 1.25 - 0.25 * _ease_out_cubic((t - 0.6) / 0.4)
        out.append(_centered_scaled_frame(img, w, h, scale, scale))
    return out


def mega_bounce(img, frames=20, fps=DEFAULT_FPS, **_):
    """Cartoony bounce: vertical arc up to 55% of the cell, squish on takeoff/landing, slight stretch in the air."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = []
    for i in range(frames):
        t = i / frames
        y = int(round(abs(math.sin(t * math.pi)) * h * 0.55))
        tri = abs(math.sin(t * math.pi))
        squish_phase = abs(((t * 2) % 2) - 1)
        scale_x = 1.0 - 0.20 * (1 - squish_phase)
        scale_y = 1.0 / max(scale_x, 0.01)
        if tri > 0.4:
            scale_y *= 1.0 + 0.10 * (tri - 0.4) / 0.6
        if abs(scale_x - 1.0) > 0.01 or abs(scale_y - 1.0) > 0.01:
            frame_img = _centered_scaled_frame(img, w, h, scale_x, scale_y)
            out.append(_paste_frame(frame_img, w, h, 0, h - frame_img.height - y))
        else:
            out.append(_paste_frame(img, w, h, 0, h - img.height - y))
    return out


def pet(img, frames=18, fps=DEFAULT_FPS, **_):
    """1-3px vertical nudge that mimics a 'breathing' effect without rotation or scale."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    amp = max(1, h // 64)
    out = []
    for i in range(frames):
        t = i / max(frames - 1, 1)
        y = -int(round(amp * (math.sin(t * 4 * math.pi - math.pi / 2) + 1) / 2))
        out.append(_paste_frame(img, w, h, 0, y))
    return out


def flag(img, frames=22, fps=DEFAULT_FPS, **_):
    """Sinusoidal horizontal skew per row (the 'waving flag' effect)."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = []
    for i in range(frames):
        phase = (i / max(frames - 1, 1)) * 2 * math.pi
        frame = _transparent(w, h)
        for y in range(h):
            # Bottom of the flag lags the top, giving the wave its shape.
            depth = y / max(h - 1, 1)
            offset = int(round(math.sin(phase - depth * 1.2) * 3 * depth))
            row = img.crop((0, y, w, y + 1))
            frame.paste(row, (offset, y))
        out.append(frame)
    return out


def party(img, frames=18, fps=DEFAULT_FPS, **_):
    """Small bounce with a hint of tilt. Lighter than `bounce`, more celebratory than `pet`."""
    w, h = img.size
    if w == 0 or h == 0:
        return _empty_frames(w, h, frames)
    out = []
    for i in range(frames):
        t = i / max(frames - 1, 1)
        y = int(round(abs(math.sin(t * 2 * math.pi)) * h * 0.18))
        rotated = img.rotate(-4.0 * math.sin(t * 2 * math.pi), resample=Image.BICUBIC, expand=False)
        out.append(_paste_frame(rotated, w, h, 0, h - rotated.height - y))
    return out


# Registry maps the animation name to (function, default_frame_count).
# Storing the default explicitly avoids relying on `inspect.signature` at call time.
_ANIMATIONS = {
    "slide_in": (slide_in, 12),
    "slide_out": (slide_out, 12),
    "shake": (shake, 12),
    "spin": (spin, 24),
    "rainbow": (rainbow, 30),
    "pulse": (pulse, 20),
    "bounce": (bounce, 18),
    "fade_in": (fade_in, 15),
    "fade_out": (fade_out, 15),
    "zoom_in": (zoom_in, 14),
    "zoom_out": (zoom_out, 14),
    "flip": (flip, 20),
    "wobble": (wobble, 18),
    "heart_beat": (heart_beat, 20),
    "floating": (floating, 30),
    "wiggle": (wiggle, 18),
    "jam": (jam, 18),
    "tilt": (tilt, 20),
    "zoom_close": (zoom_close, 14),
    "mega_bounce": (mega_bounce, 20),
    "pet": (pet, 18),
    "flag": (flag, 22),
    "party": (party, 18),
}


def generate_frames(img, animation, intensity=None, frames=None, **kwargs):
    """Dispatch to the named animation and return a list of frames.

    If `intensity` is given (and `frames` is not), the animation's
    default frame count is scaled by `_scale_frames`. The export path
    uses this to auto-shrink a GIF until it fits a platform's cap.
    """
    entry = _ANIMATIONS.get(animation)
    if entry is None:
        raise ValueError(
            f"Unknown animation '{animation}'. Supported: {', '.join(SUPPORTED_ANIMATIONS)}"
        )
    fn, default_frames = entry
    if frames is None and intensity is not None:
        frames = _scale_frames(default_frames, intensity)
    if frames is not None:
        kwargs["frames"] = frames
    return fn(img, **kwargs)


def save_gif(frames, out_path, fps=DEFAULT_FPS, logger=None, optimize=True):
    """Save a list of RGBA frames as a looping GIF.

    `disposal=2` (restore-to-background) avoids the ghost trail that
    appears when transparent pixels move. `optimize=True` runs Pillow's
    LZW optimizer, typically cutting GIF size by 20-40% - critical for
    staying under Twitch's 1MB per-emote cap.
    """
    if not frames:
        raise ValueError("save_gif called with no frames")

    duration_ms = max(1, int(round(1000 / fps)))
    # Quantize RGBA -> P per frame with an adaptive palette so the GIF
    # keeps the original alpha channel. The first frame's palette is
    # used as the global palette; subsequent frames adapt to it.
    converted = [f.convert("RGBA").convert("P", palette=Image.Palette.ADAPTIVE) for f in frames]
    converted[0].save(
        out_path,
        format="GIF",
        save_all=True,
        append_images=converted[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
        transparency=0,
        optimize=optimize,
    )
    if logger is not None:
        size_kb = os.path.getsize(out_path) / 1024.0 if os.path.exists(out_path) else 0
        logger.debug(f"Saved animated GIF: {out_path} ({len(frames)} frames @ {fps} fps, {size_kb:.1f} KB)")
