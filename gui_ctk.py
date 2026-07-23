"""Emote Tool main window.

Layout is intentionally built with `.place()` (see `LAYOUT`) - migrating
to `grid()` is tracked as a follow-up in `CHANGELOG.md`. Widgets
specific to dialogs and the animated preview live in `gui_widgets`.
"""

import os
import webbrowser
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from animations import DEFAULT_FPS, DEFAULT_INTENSITY
from core import (
    _ANIMATED_PLATFORM_SIZE,
    detect_emotes_with_rects,
    export_animated_emotes,
    export_emotes,
    sanitize_filename,
)
from gui_widgets import LivePreviewWindow, open_info_popup, open_transient_error


ANIMATION_LABELS = [
    ("slide_in", "Slide In"),
    ("slide_out", "Slide Out"),
    ("shake", "Shake"),
    ("spin", "Spin"),
    ("rainbow", "Rainbow"),
    ("pulse", "Pulse"),
    ("bounce", "Bounce"),
    ("fade_in", "Fade In"),
    ("fade_out", "Fade Out"),
    ("zoom_in", "Zoom In"),
    ("zoom_out", "Zoom Out"),
    ("flip", "Flip"),
    ("wobble", "Wobble"),
    ("heart_beat", "Heart Beat"),
    ("floating", "Floating"),
    ("wiggle", "Wiggle"),
    ("jam", "Jam"),
    ("tilt", "Tilt"),
    ("zoom_close", "Zoom Close"),
    ("mega_bounce", "Mega Bounce"),
    ("pet", "Pet"),
    ("flag", "Flag"),
    ("party", "Party"),
]

ANIMATION_CHOICES = ["(none)"] + [label for _, label in ANIMATION_LABELS]
_LABEL_TO_NAME = {label: name for name, label in ANIMATION_LABELS}

FPS_RANGE = (5, 30)
INTENSITY_RANGE = (0.25, 1.5)
SLIDER_STEPS = 25

BUG_REPORT_URL = "https://github.com/DebuggingIsFun/Twitch-Emote-Tool/issues"

LAYOUT = {
    "window": (380, 600),
    "checkbox_start_y": 65,
    "checkbox_step": 30,
    "animated_header_y": 255,
    "animated_toggle_y": 280,
    "animated_hint_y": 310,
    "buttons_y": 485,
    "credits_y": 535,
    "credits_height": 60,
}


def resolve_animation_name(display_label):
    """Translate a dropdown label back to the internal animation name.
    Returns None for "(none)" or any unrecognized label."""
    return _LABEL_TO_NAME.get(display_label)


class EmoteGUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.app = ctk.CTk()
        self.app.title("Emote Tool")

        self.twitch_var = ctk.StringVar(value="on")
        self.twitch_badge_var = ctk.StringVar(value="off")
        self.kick_var = ctk.StringVar(value="off")
        self.youtube_var = ctk.StringVar(value="off")
        self.discord_var = ctk.StringVar(value="off")
        self.debug_var = ctk.StringVar(value="off")
        # Master animated toggle: when "on", the static PNG export is
        # skipped and the per-emote animation pickers in the preview
        # window drive the export.
        self.animated_var = ctk.StringVar(value="off")

        self.current_filename = None
        # Each row is `(cell, entry, anim_var, preview_btn, fps_var, intensity_var)`.
        self.name_entries = []
        self.preview_window = None
        # Cropped RGBA cell images keyed by cell id, populated when the
        # preview window is built so live preview / slider drags don't
        # re-read the source PNG and re-crop on every event.
        self._cell_crops = {}
        # LivePreviewWindow controllers keyed by cell id. Each owns its
        # CTk toplevel, frame cache, and the after() tick loop.
        self._live_preview_windows = {}

        self._build_main_window()
        self._center_window()

    def _center_window(self):
        width, height = LAYOUT["window"]
        sw, sh = self.app.winfo_screenwidth(), self.app.winfo_screenheight()
        self.app.geometry(
            f"{width}x{height}+{(sw - width) // 2}+{(sh - height) // 2}"
        )

    def _build_main_window(self):
        w, h = LAYOUT["window"]
        self.app.geometry(f"{w}x{h}")
        self.app.resizable(False, False)

        file_frame = ctk.CTkFrame(self.app)
        file_frame.place(x=20, y=15, relwidth=0.9)
        ctk.CTkButton(
            file_frame, text="Select PNG", command=self._open_file_dialog,
            width=140, height=34,
        ).pack(pady=5)

        self._build_checkboxes()
        self._build_animated_section()

        ctk.CTkButton(
            self.app, text="Report Bug",
            command=lambda: webbrowser.open(BUG_REPORT_URL),
            width=110, height=34, font=ctk.CTkFont(size=12),
        ).place(x=40, y=LAYOUT["buttons_y"])
        ctk.CTkButton(
            self.app, text="Cancel", command=self._on_cancel,
            width=110, height=34,
        ).place(x=230, y=LAYOUT["buttons_y"])

        credits_frame = ctk.CTkFrame(self.app, height=LAYOUT["credits_height"])
        credits_frame.place(x=0, y=LAYOUT["credits_y"], relwidth=1.0)
        ctk.CTkLabel(
            credits_frame,
            text=(
                "Credits to: \n Pewy (Created the PNG Template) \n"
                " Morksen (Oirignal Tool Creator) \n"
                " DebugginIsFun aká kami_no_teki"
            ),
            font=ctk.CTkFont(size=10),
        ).pack(pady=5)

    def _build_checkboxes(self):
        """Stack the platform checkboxes vertically with the configured spacing."""
        checkboxes = [
            ("Twitch Emotes", self.twitch_var),
            ("Twitch Badges", self.twitch_badge_var),
            ("Kick Emotes", self.kick_var),
            ("YouTube Emotes", self.youtube_var),
            ("Discord Emotes", self.discord_var),
            ("Create Debug Logs for Bug Report", self.debug_var),
        ]
        y = LAYOUT["checkbox_start_y"]
        for text, var in checkboxes:
            ctk.CTkCheckBox(
                self.app, text=text, variable=var, onvalue="on", offvalue="off",
                width=320, height=26, font=ctk.CTkFont(size=12),
            ).place(x=20, y=y)
            y += LAYOUT["checkbox_step"]

    def _build_animated_section(self):
        """Header + master toggle + helper hint for the animated export path."""
        ctk.CTkLabel(
            self.app, text="Animated Emotes (GIF)",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).place(x=20, y=LAYOUT["animated_header_y"])
        self.animated_master = ctk.CTkCheckBox(
            self.app, text="Export as animated GIFs (skip static)",
            variable=self.animated_var, onvalue="on", offvalue="off",
            width=320, height=26, font=ctk.CTkFont(size=12),
        )
        self.animated_master.place(x=20, y=LAYOUT["animated_toggle_y"])
        ctk.CTkLabel(
            self.app, text="Pick effects per emote in the preview window.",
            font=ctk.CTkFont(size=10), text_color="gray",
        ).place(x=20, y=LAYOUT["animated_hint_y"])

    def _open_file_dialog(self):
        filename = filedialog.askopenfilename(
            title="Select PNG file",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
        )
        # Other formats would break the alpha-based edge detection.
        if not filename:
            return
        if not filename.lower().endswith(".png"):
            open_transient_error(self.app, "Please select PNG only!")
            return

        self.current_filename = filename
        debug_enabled = self.debug_var.get() == "on"
        marked_img, cell_infos = detect_emotes_with_rects(filename, debug_enabled)
        self._show_preview_window(marked_img, cell_infos)

    def _show_preview_window(self, marked_img, cell_infos):
        """Display detection results with the naming interface."""
        if self.preview_window is not None:
            self.preview_window.destroy()
        for w in list(self._live_preview_windows.values()):
            w.close()
        self._live_preview_windows.clear()

        filled_cells = [c for c in cell_infos if c["has_content"]]
        filled_count, total_cells = len(filled_cells), len(cell_infos)
        animated_mode = self.animated_var.get() == "on"

        # Open the source image once and crop every filled cell into
        # the cache. Live preview and slider drags then only need to
        # resize, not re-read the file and re-crop.
        self._cell_crops = {
            c["id"]: self._crop_cell_from_source(c) for c in filled_cells
        }

        self.preview_window = ctk.CTkToplevel(self.app)
        self.preview_window.title(f"Emote Detection - {filled_count}/{total_cells} filled")

        screen_w = self.preview_window.winfo_screenwidth()
        screen_h = self.preview_window.winfo_screenheight()
        max_w, max_h = int(screen_w * 0.7), int(screen_h * 0.7)
        orig_w, orig_h = marked_img.size
        # Cap at 0.45 so very tall sheets don't push the window off-screen.
        scale = min(max_w / orig_w, max_h / orig_h, 0.45)
        preview_w, preview_h = int(orig_w * scale), int(orig_h * scale)
        preview_img = marked_img.resize((preview_w, preview_h), Image.Resampling.LANCZOS)
        photo = ctk.CTkImage(
            light_image=preview_img, dark_image=preview_img, size=(preview_w, preview_h),
        )

        left = ctk.CTkFrame(self.preview_window)
        left.pack(side="left", fill="both", padx=20, pady=20)
        img_label = ctk.CTkLabel(left, image=photo, text="")
        img_label.image = photo  # keep reference
        img_label.pack(pady=10)

        mode_text = "ANIMATED mode (GIF only)" if animated_mode else "Static PNG export"
        ctk.CTkLabel(
            left,
            text=(
                f"Green: {filled_count} filled | Red: {total_cells - filled_count} empty\n"
                f"{os.path.basename(self.current_filename)}\n"
                f"Mode: {mode_text}"
            ),
            font=ctk.CTkFont(size=14),
        ).pack(pady=(0, 10))

        right = ctk.CTkFrame(self.preview_window)
        right.pack(side="right", fill="both", padx=(0, 20), pady=20)
        ctk.CTkLabel(
            right,
            text="Name + Animate Your Emotes" if animated_mode else "Name Your Emotes",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(10, 15))

        scroll = ctk.CTkScrollableFrame(right, width=380, height=preview_h - 100)
        scroll.pack(fill="both", expand=True, padx=10)
        self.name_entries = [
            self._build_emote_row(scroll, cell, animated_mode) for cell in filled_cells
        ]

        export_label = "Export Animated GIFs" if animated_mode else "Export Emotes"
        ctk.CTkButton(
            right, text=export_label, command=self._export_emotes, width=180, height=40,
        ).pack(pady=15)

        self.preview_window.update_idletasks()
        self.preview_window.geometry(f"{preview_w + 380}x{preview_h + 100}")

    def _build_emote_row(self, parent, cell, animated_mode):
        """Build one emote's row: number, name entry, optional
        animation dropdown, FPS / intensity sliders, Preview button."""
        row = ctk.CTkFrame(parent)
        row.pack(pady=5, fill="x")

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.pack(fill="x", padx=5, pady=(5, 0))
        ctk.CTkLabel(top, text=f"#{cell['id']}:", width=40).pack(side="left", padx=5)
        entry = ctk.CTkEntry(top, width=240, placeholder_text=self._auto_name(cell))
        entry.pack(side="left", padx=5)

        anim_var = preview_btn = fps_var = intensity_var = None
        if animated_mode:
            anim_var, preview_btn, fps_var, intensity_var = self._build_animation_controls(row, cell)

        return (cell, entry, anim_var, preview_btn, fps_var, intensity_var)

    def _build_animation_controls(self, row, cell):
        """Build the animation dropdown + Preview button + FPS/Intensity slider row."""
        controls = ctk.CTkFrame(row, fg_color="transparent")
        controls.pack(fill="x", padx=5, pady=2)

        anim_var = ctk.StringVar(value=ANIMATION_CHOICES[0])
        dropdown = ctk.CTkOptionMenu(
            controls, values=ANIMATION_CHOICES, variable=anim_var,
            width=140, height=26, font=ctk.CTkFont(size=11),
            command=lambda _choice, c=cell, v=anim_var: self._on_dropdown_changed(c, v),
        )
        dropdown.pack(side="left", padx=5)
        # Opening the live preview proactively on first click feels
        # faster than waiting for the change callback.
        dropdown.bind(
            "<Button-1>",
            lambda _e, c=cell, v=anim_var: self._on_dropdown_pressed(c, v),
            add="+",
        )

        preview_btn = ctk.CTkButton(
            controls, text="Preview", width=70, height=26, font=ctk.CTkFont(size=11),
            command=lambda c=cell, v=anim_var: self._open_live_preview(c, v),
        )
        preview_btn.pack(side="right", padx=5)

        slider_row = ctk.CTkFrame(row, fg_color="transparent")
        slider_row.pack(fill="x", padx=5, pady=(0, 5))
        fps_var = ctk.DoubleVar(value=DEFAULT_FPS)
        intensity_var = ctk.DoubleVar(value=DEFAULT_INTENSITY)
        self._build_slider_row(slider_row, cell, anim_var, fps_var, intensity_var)
        return anim_var, preview_btn, fps_var, intensity_var

    def _build_slider_row(self, parent, cell, anim_var, fps_var, intensity_var):
        """Two side-by-side labeled sliders with live value readouts."""
        def make_slider(frame, label, var, from_, to, width, value_fmt, on_change):
            value_lbl = ctk.CTkLabel(frame, text=value_fmt(var.get()), font=ctk.CTkFont(size=10))
            value_lbl.pack(side="right")
            ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=10), width=28).pack(side="left")
            ctk.CTkSlider(
                frame, from_=from_, to=to, number_of_steps=SLIDER_STEPS,
                variable=var, width=width,
                command=lambda _v, lbl=value_lbl, v=var, cb=on_change:
                    (lbl.configure(text=value_fmt(v.get())), cb()),
            ).pack(side="left", padx=2)

        on_change = lambda: self._on_slider_changed(cell, anim_var, fps_var, intensity_var)
        fps_frame = ctk.CTkFrame(parent, fg_color="transparent")
        fps_frame.pack(side="left", padx=(5, 10), pady=2)
        make_slider(fps_frame, "FPS", fps_var, *FPS_RANGE, 110, lambda v: f"{int(v)}", on_change)

        int_frame = ctk.CTkFrame(parent, fg_color="transparent")
        int_frame.pack(side="left", padx=(0, 5), pady=2)
        make_slider(
            int_frame, "Int", intensity_var, *INTENSITY_RANGE, 120,
            lambda v: f"{v:.2f}", on_change,
        )

    def _on_slider_changed(self, cell, anim_var, fps_var, intensity_var):
        """Re-generate the live preview when FPS or intensity changes.
        No-op if there is no open preview yet or "(none)" is selected."""
        if cell["id"] not in self._live_preview_windows:
            return
        anim_name = resolve_animation_name(anim_var.get())
        if anim_name is None:
            return
        self._set_live_preview_animation(cell, anim_name)

    def _auto_name(self, cell):
        """Default placeholder name: <InputFileBasename>_Emote<XX>.
        Uses `sanitize_filename` so the placeholder is always a valid
        filename component under the same rules the exporter applies."""
        basename = os.path.splitext(os.path.basename(self.current_filename or "emote"))[0]
        return f"{sanitize_filename(basename)}_Emote{cell['id']:02d}"

    def _on_dropdown_pressed(self, cell, anim_var):
        """First time the user touches the dropdown for this cell: open
        the live preview window. Subsequent changes use the change callback."""
        if cell["id"] in self._live_preview_windows:
            return
        self._ensure_live_preview(cell)
        anim_name = resolve_animation_name(anim_var.get())
        if anim_name is not None:
            self._set_live_preview_animation(cell, anim_name)

    def _on_dropdown_changed(self, cell, anim_var):
        anim_name = resolve_animation_name(anim_var.get())
        if anim_name is None:
            existing = self._live_preview_windows.pop(cell["id"], None)
            if existing is not None:
                existing.close()
            return
        self._ensure_live_preview(cell)
        self._set_live_preview_animation(cell, anim_name)

    def _ensure_live_preview(self, cell):
        """Return the LivePreviewWindow for `cell`, creating it if needed.
        Drops stale entries (window destroyed externally)."""
        existing = self._live_preview_windows.get(cell["id"])
        if existing is not None:
            try:
                if existing.win.winfo_exists():
                    return existing
            except Exception:
                pass
            self._live_preview_windows.pop(cell["id"], None)

        return LivePreviewWindow(
            self.preview_window, cell, self._live_preview_windows,
            preview_size=_ANIMATED_PLATFORM_SIZE["twitch"],
        )

    def _set_live_preview_animation(self, cell, anim_name):
        preview = self._ensure_live_preview(cell)
        if preview is None:
            return
        fps, intensity = self._emote_tuning(cell)
        base = self._render_emote_base(cell, _ANIMATED_PLATFORM_SIZE["twitch"])
        preview.set_animation(base, anim_name, fps=fps, intensity=intensity)

    def _open_live_preview(self, cell, anim_var):
        """Manual open from the Preview button. Pops a hint if no animation is selected."""
        anim_name = resolve_animation_name(anim_var.get())
        if anim_name is None:
            open_info_popup(
                self.preview_window, "Nothing to preview",
                "Pick an animation from the dropdown first.", geometry="240x90",
            )
            return
        self._ensure_live_preview(cell)
        self._set_live_preview_animation(cell, anim_name)

    def _emote_tuning(self, cell):
        """Return the (fps, intensity) currently set for `cell`."""
        fps, intensity = DEFAULT_FPS, DEFAULT_INTENSITY
        for row in self.name_entries:
            if row[0] is cell:
                if row[4] is not None:
                    fps = max(1, int(round(float(row[4].get()))))
                if row[5] is not None:
                    intensity = float(row[5].get())
                break
        return fps, intensity

    def _render_emote_base(self, cell, size):
        """Resize a cached cell crop to `size` for live preview / export.
        The crop itself is populated once per preview window in
        `_show_preview_window` so this never re-reads the source file."""
        crop = self._cell_crops.get(cell["id"])
        if crop is None:
            # Stale call after a fresh `Select PNG`; rebuild lazily.
            crop = self._crop_cell_from_source(cell)
            self._cell_crops[cell["id"]] = crop
        return crop.resize(size, Image.Resampling.LANCZOS)

    def _crop_cell_from_source(self, cell):
        """Open the source PNG and crop `cell` with the standard 5px inset."""
        base_img = Image.open(self.current_filename).convert("RGBA")
        x, y, w, h = cell["rect"]
        padding = 5
        return base_img.crop((x + padding, y + padding, x + w - padding, y + h - padding))

    def _selected_platforms(self):
        platforms = []
        if self.twitch_var.get() == "on":
            platforms.append("twitch")
        if self.twitch_badge_var.get() == "on":
            platforms.append("twitch_badges")
        if self.discord_var.get() == "on":
            platforms.append("discord")
        if self.youtube_var.get() == "on":
            platforms.append("youtube")
        if self.kick_var.get() == "on":
            platforms.append("kick")
        return platforms

    def _export_emotes(self):
        """Gather settings and dispatch to the static or animated exporter."""
        animated_mode = self.animated_var.get() == "on"
        debug_enabled = self.debug_var.get() == "on"

        # Apply the auto-name fallback to any emote whose name field
        # the user left blank.
        name_list = [
            (cell, typed.strip() or self._auto_name(cell))
            for cell, entry, *_ in self.name_entries
            for typed in [entry.get()]
        ]

        if animated_mode:
            per_emote = self._collect_per_emote_animations()
            if not per_emote:
                open_info_popup(
                    self.app, "Nothing to export",
                    "Pick an animation for at least one emote.", geometry="280x100",
                )
                return
            platforms = self._selected_platforms() or ["twitch"]
            count, out_dir = export_animated_emotes(
                self.current_filename, name_list, platforms, per_emote, debug_enabled,
            )
            self._show_success(count, out_dir, animated=True)
            return

        platforms = self._selected_platforms()
        if not platforms:
            open_info_popup(
                self.app, "Error", "Please select at least one platform!",
                geometry="250x100",
            )
            return
        count, out_dir = export_emotes(
            self.current_filename, name_list, platforms, debug_enabled,
        )
        self._show_success(count, out_dir, animated=False)

    def _collect_per_emote_animations(self):
        """Build the `{cell_id: {animations, fps, intensity}}` dict for
        the animated export. Emotes with "(none)" selected are skipped."""
        per_emote = {}
        for cell, _entry, anim_var, _btn, fps_var, int_var in self.name_entries:
            if anim_var is None:
                continue
            anim_name = resolve_animation_name(anim_var.get())
            if anim_name is None:
                continue
            per_emote[cell["id"]] = {
                "animations": [anim_name],
                "fps": max(1, int(round(float(fps_var.get())))) if fps_var is not None else DEFAULT_FPS,
                "intensity": float(int_var.get()) if int_var is not None else DEFAULT_INTENSITY,
            }
        return per_emote

    def _show_success(self, exported_count, out_dir, animated):
        win = ctk.CTkToplevel(self.app)
        win.title("Animated Export Complete" if animated else "Export Complete")
        win.geometry("340x220")
        kind = "animated files" if animated else "files"
        ctk.CTkLabel(win, text=f"Exported {exported_count} {kind}!").pack(pady=10)
        ctk.CTkLabel(win, text=f"Location: {out_dir}", wraplength=320).pack(pady=5)
        ctk.CTkButton(win, text="OK", command=lambda: (win.destroy(), self.app.quit())).pack(pady=10)

    def _on_cancel(self):
        for w in list(self._live_preview_windows.values()):
            w.close()
        self._live_preview_windows.clear()
        self._cell_crops.clear()
        if self.preview_window:
            self.preview_window.destroy()
        self.app.destroy()

    def run(self):
        self.app.mainloop()
