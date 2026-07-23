"""Reusable CustomTkinter dialogs and the live-preview window.

The main `EmoteGUI` class stays focused on layout and event wiring; the
standalone widgets in this file are self-contained and easy to test
or reuse.
"""

import customtkinter as ctk
from PIL import Image

from animations import DEFAULT_FPS, DEFAULT_INTENSITY, generate_frames


def open_info_popup(parent, title, message, geometry="260x100", ok_text="OK"):
    """Tiny modal-less message window with a single OK button."""
    win = ctk.CTkToplevel(parent)
    win.title(title)
    win.geometry(geometry)
    ctk.CTkLabel(win, text=message).pack(pady=15)
    ctk.CTkButton(win, text=ok_text, command=win.destroy).pack()
    return win


def open_transient_error(parent, message, duration_ms=3000):
    """Show `message` in a red label that auto-dismisses after
    `duration_ms`. Used for inline form validation errors."""
    label = ctk.CTkLabel(parent, text=message, text_color="red")
    label.pack()
    label.after(duration_ms, label.destroy)
    return label


class LivePreviewWindow:
    """Per-emote animated GIF preview window.

    Owns its CTkImage frame cache, the after_id for the playback tick,
    and the per-emote FPS / intensity state. Closing the window
    cancels the tick loop and removes itself from any external
    registry passed to the constructor.
    """

    def __init__(self, parent, cell, registry, preview_size, default_fps=DEFAULT_FPS):
        self._cell = cell
        self._registry = registry
        self._size = preview_size
        self._fps = default_fps

        self.win = ctk.CTkToplevel(parent)
        self.win.title(f"Preview #{cell['id']}")
        self.win.geometry(f"{preview_size[0] + 40}x{preview_size[1] + 80}")
        self.win.attributes("-topmost", True)

        self.title = ctk.CTkLabel(self.win, text="(select an animation)", font=ctk.CTkFont(size=11))
        self.title.pack(pady=(8, 4))
        self.img_label = ctk.CTkLabel(self.win, text="")
        self.img_label.pack(pady=4)

        self._frames = []
        self._i = 0
        self._after_id = None
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        registry[cell["id"]] = self

    def close(self):
        if self._after_id is not None:
            try:
                self.win.after_cancel(self._after_id)
            except Exception:
                pass
        self._registry.pop(self._cell["id"], None)
        try:
            self.win.destroy()
        except Exception:
            pass

    def _tick(self):
        if not self.win.winfo_exists() or not self._frames:
            return
        photo = self._frames[self._i]
        self.img_label.configure(image=photo, text="")
        self.img_label.image = photo
        self._i = (self._i + 1) % len(self._frames)
        self._after_id = self.win.after(int(1000 / max(1, self._fps)), self._tick)

    def set_animation(self, base_image, animation_name, fps=None, intensity=None):
        """Regenerate frames for the new selection and restart playback."""
        if fps is not None:
            self._fps = max(1, int(round(fps)))
        if intensity is None:
            intensity = DEFAULT_INTENSITY
        self.title.configure(
            text=f"#{self._cell['id']} - {animation_name} "
            f"({self._fps} fps, int {intensity:.2f})"
        )

        if self._after_id is not None:
            try:
                self.win.after_cancel(self._after_id)
            except Exception:
                pass

        frames = generate_frames(base_image, animation_name, intensity=intensity)
        size = self._size
        self._frames = [
            ctk.CTkImage(light_image=f.convert("RGBA"), dark_image=f.convert("RGBA"), size=size)
            for f in frames
        ]
        self._i = 0

        if not self._frames:
            self.img_label.configure(image="", text="(no frames)")
            return
        self._tick()
