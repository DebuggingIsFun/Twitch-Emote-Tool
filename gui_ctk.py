import customtkinter as ctk
from tkinter import filedialog
from PIL import Image
import webbrowser
import os


class EmoteGUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")  # Make it Dark theme
        ctk.set_default_color_theme("blue")
        
        self.app = ctk.CTk()
        self.app.title("Emote Tool")
        
        # StringVars track checkbox states ("on"/"off")
        self.twitch_var = ctk.StringVar(value="on")  # Twitch enabled by default
        self.twtich_badge_var = ctk.StringVar(value="off")
        self.kick_var = ctk.StringVar(value="off")
        self.youtube_var = ctk.StringVar(value="off")
        self.discord_var = ctk.StringVar(value="off")
        self.debug_var = ctk.StringVar(value="off")
        
        # Store data between detection and export phases
        self.current_filename = None
        self.name_entries = []
        self.preview_window = None
        
        self.setup_ui()
    
    def center_window(self):
        """Position main window in screen center"""
        self.app.update_idletasks()
        width = 300
        height = 405
        screen_width = self.app.winfo_screenwidth()
        screen_height = self.app.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.app.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        self.center_window()
        self.app.geometry("300x405")
        self.app.resizable(False, False)  # Fixed size keeps layout predictable
        
        # File selection button at top
        file_frame = ctk.CTkFrame(self.app)
        file_frame.place(x=20, y=15, relwidth=0.9)
        
        file_btn = ctk.CTkButton(
            file_frame, text="Select PNG", 
            command=self.open_file_dialog,
            width=100, height=30
        )
        file_btn.pack(pady=5)
        
        # Platform selection checkboxes
        self.create_checkboxes()
        
        # Bottom buttons
        bug_btn = ctk.CTkButton(
            self.app, text="Report Bug", 
            command=lambda: webbrowser.open("https://github.com/DebuggingIsFun/Twitch-Emote-Tool/issues"),
            width=60, height=30, font=ctk.CTkFont(size=12)
        )
        bug_btn.place(x=50, y=290)
        
        cancel_btn = ctk.CTkButton(
            self.app, text="Cancel", 
            width=60, height=30, 
            command=self.on_cancel
        )
        cancel_btn.place(x=200, y=290)
        
        # Credits footer
        credits_frame = ctk.CTkFrame(self.app, height=25)
        credits_frame.place(x=0, y=350, relwidth=1.0)
        
        credits_label = ctk.CTkLabel(
            credits_frame, 
            text="Credits to: \n Pewy (Created the PNG Template) \n Morksen (Oirignal Tool Creator) \n DebugginIsFun aká kami_no_teki", 
            font=ctk.CTkFont(size=10)
        )
        credits_label.pack(pady=3)
    
    def create_checkboxes(self):
        """Create all platform selection checkboxes with consistent spacing"""
        checkboxes = [
            ("Twitch Emotes", self.twitch_var),
            ("Twitch Badges", self.twtich_badge_var),
            ("Kick Emotes", self.kick_var),
            ("YouTube Emotes", self.youtube_var),
            ("Discord Emotes", self.discord_var),
            ("Create Debug Logs for Bug Report", self.debug_var)
        ]
        
        # Vertical stack with 35px spacing
        for i, (text, var) in enumerate(checkboxes):
            checkbox = ctk.CTkCheckBox(
                self.app, text=text, variable=var, onvalue="on", offvalue="off",
                width=220, height=25, font=ctk.CTkFont(size=12)
            )
            checkbox.place(x=20, y=60 + i * 35)
    
    def open_file_dialog(self):
        """Handle file selection and trigger detection"""
        from core import detect_emotes_with_rects
        
        filename = filedialog.askopenfilename(
            title="Select PNG file",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        
        # Validate PNG file type - other formats won't work correctly
        if not filename or not filename.lower().endswith(".png"):
            if filename:
                error_label = ctk.CTkLabel(self.app, text="Please select PNG only!", text_color="red")
                error_label.pack()
                error_label.after(3000, error_label.destroy)  # Auto-remove after 3 seconds
            return
        
        self.current_filename = filename
        
        # Pass debug flag to detection
        debug_enabled = self.debug_var.get() == "on"
        
        # Run detection and show results
        marked_img, cell_infos = detect_emotes_with_rects(filename, debug_enabled)
        
        self.show_preview_window(marked_img, cell_infos)
    
    def show_preview_window(self, marked_img, cell_infos):
        """Display detection results with naming interface"""
        # Close old preview if exists
        if self.preview_window is not None:
            self.preview_window.destroy()
        
        filled_cells = [c for c in cell_infos if c["has_content"]]
        filled_count = len(filled_cells)
        total_cells = len(cell_infos)

        self.preview_window = ctk.CTkToplevel(self.app)
        self.preview_window.title(f"Emote Detection - {filled_count}/{total_cells} filled")

        # === Smart Image Scaling ===
        # Scale image to fit 70% of screen while maintaining aspect ratio
        screen_width = self.preview_window.winfo_screenwidth()
        screen_height = self.preview_window.winfo_screenheight()
        max_img_width = int(screen_width * 0.7)
        max_img_height = int(screen_height * 0.7)

        orig_width, orig_height = marked_img.size
        scale = min(max_img_width / orig_width, max_img_height / orig_height, 0.45)
        preview_width = int(orig_width * scale)
        preview_height = int(orig_height * scale)

        # LANCZOS provides best quality for preview downscaling
        preview_img = marked_img.resize((preview_width, preview_height), Image.Resampling.LANCZOS)
        photo = ctk.CTkImage(light_image=preview_img, dark_image=preview_img, size=(preview_width, preview_height))

        # === Left Panel: Preview Image ===
        left_frame = ctk.CTkFrame(self.preview_window)
        left_frame.pack(side="left", fill="both", padx=20, pady=20)

        img_label = ctk.CTkLabel(left_frame, image=photo, text="")
        img_label.image = photo  # Keep reference to prevent garbage collection
        img_label.pack(pady=10)
        
        info_text = f"Green: {filled_count} filled | Red: {total_cells - filled_count} empty\n{os.path.basename(self.current_filename)}"
        info_label = ctk.CTkLabel(left_frame, text=info_text, font=ctk.CTkFont(size=14))
        info_label.pack(pady=(0, 10))

        # === Right Panel: Emote Naming ===
        right_frame = ctk.CTkFrame(self.preview_window)
        right_frame.pack(side="right", fill="both", padx=(0, 20), pady=20)

        naming_label = ctk.CTkLabel(right_frame, text="Name Your Emotes", font=ctk.CTkFont(size=16, weight="bold"))
        naming_label.pack(pady=(10, 15))

        # Scrollable list for many emotes
        naming_scroll = ctk.CTkScrollableFrame(right_frame, width=200, height=preview_height - 100)
        naming_scroll.pack(fill="both", expand=True, padx=10)

        # Create numbered input field for each filled cell
        self.name_entries = []
        for cell in filled_cells:
            row_frame = ctk.CTkFrame(naming_scroll)
            row_frame.pack(pady=5, fill="x")

            # Show emote number from detection
            label = ctk.CTkLabel(row_frame, text=f"#{cell['id']}:", width=40)
            label.pack(side="left", padx=5)

            entry = ctk.CTkEntry(row_frame, width=140, placeholder_text="Enter name")
            entry.pack(side="left", padx=5)

            # Store tuple of cell data + entry widget for export phase
            self.name_entries.append((cell, entry))

        # Export button at bottom
        export_btn = ctk.CTkButton(
            right_frame,
            text="Export Emotes",
            command=self.export_emotes,
            width=150, height=40
        )
        export_btn.pack(pady=15)
        
        # Size window to fit content
        self.preview_window.update_idletasks()
        window_width = preview_width + 300
        window_height = preview_height + 100
        self.preview_window.geometry(f"{window_width}x{window_height}")
    
    def export_emotes(self):
        """Gather settings and trigger export process"""
        from core import export_emotes
        
        # Collect selected platforms from checkboxes
        selected_platforms = []
        if self.twitch_var.get() == "on":
            selected_platforms.append("twitch")
        if self.twtich_badge_var.get() == "on":
            selected_platforms.append("twitchbages")
        if self.discord_var.get() == "on":
            selected_platforms.append("discord")
        if self.youtube_var.get() == "on":
            selected_platforms.append("youtube")
        if self.kick_var.get() == "on":
            selected_platforms.append("kick")
        
        # Prevent export without platform selection
        if not selected_platforms:
            error_window = ctk.CTkToplevel(self.app)
            error_window.title("Error")
            error_window.geometry("250x100")
            ctk.CTkLabel(error_window, text="Please select at least one platform!").pack(pady=20)
            ctk.CTkButton(error_window, text="OK", command=error_window.destroy).pack()
            return
        
        # Pass debug flag and user-entered names to export
        debug_enabled = self.debug_var.get() == "on"
        name_list = [(cell, entry.get()) for cell, entry in self.name_entries]
        
        exported_count, out_dir = export_emotes(self.current_filename, name_list, selected_platforms, debug_enabled)
        
        # Show success message with file count and location
        success_window = ctk.CTkToplevel(self.app)
        success_window.title("Export Complete")
        success_window.geometry("300x200")
        
        ctk.CTkLabel(success_window, text=f"Exported {exported_count} files!").pack(pady=10)
        ctk.CTkLabel(success_window, text=f"Location: {out_dir}", wraplength=280).pack(pady=5)
    
        def close_all():
            """Close app after export confirmation"""
            success_window.destroy()
            self.app.quit()
    
        ctk.CTkButton(success_window, text="OK", command=close_all).pack(pady=10)
    
    def on_cancel(self):
        """Clean up and close application"""
        if self.preview_window:
            self.preview_window.destroy()
        self.app.destroy()
    
    def run(self):
        self.app.mainloop()
