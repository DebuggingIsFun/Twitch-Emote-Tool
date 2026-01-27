import customtkinter as ctk
from CTkFileDialog import askopenfilename
from PIL import Image
import webbrowser
import os


class EmoteGUI:
    def __init__(self):
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.app = ctk.CTk()
        self.app.title("Emote Tool")
        
        # Variables for checkboxes
        self.twitch_var = ctk.StringVar(value="on")
        self.twtich_badge_var = ctk.StringVar(value="off")
        self.kick_var = ctk.StringVar(value="off")
        self.youtube_var = ctk.StringVar(value="off")
        self.discord_var = ctk.StringVar(value="off")
        self.debug_var = ctk.StringVar(value="off")
        
        # Storage for later
        self.current_filename = None
        self.name_entries = []
        self.preview_window = None
        
        self.setup_ui()
    
    def center_window(self):
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
        self.app.resizable(False, False)
        
        # File input section
        file_frame = ctk.CTkFrame(self.app)
        file_frame.place(x=20, y=15, relwidth=0.9)
        
        file_btn = ctk.CTkButton(
            file_frame, text="Select PNG", 
            command=self.open_file_dialog,
            width=100, height=30
        )
        file_btn.pack(pady=5)
        
        # Checkboxes
        self.create_checkboxes()
        
        # Buttons
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
        
        # Credits
        credits_frame = ctk.CTkFrame(self.app, height=25)
        credits_frame.place(x=0, y=350, relwidth=1.0)

        credits_label = ctk.CTkLabel(
        credits_frame, 
        text="Credits to: Pewy (Created the PNG Template) \n Morksen (Oirignal Tool Creator) \n DebugginIsFun aká kami_no_teki", 
        font=ctk.CTkFont(size=10)
        )
        credits_label.pack(pady=3)
    
    def create_checkboxes(self):
        checkboxes = [
            ("Twitch Emotes", self.twitch_var),
            ("Twitch Badges", self.twtich_badge_var),
            ("Kick Emotes", self.kick_var),
            ("YouTube Emotes", self.youtube_var),
            ("Discord Emotes", self.discord_var),
            ("Create Debug Logs for Bug Report", self.debug_var)
        ]
        
        for i, (text, var) in enumerate(checkboxes):
            checkbox = ctk.CTkCheckBox(
                self.app, text=text, variable=var, onvalue="on", offvalue="off",
                width=220, height=25, font=ctk.CTkFont(size=12)
            )
            checkbox.place(x=20, y=60 + i * 35)
    
    def open_file_dialog(self):
        from core import detect_emotes_with_rects
        
        filename = askopenfilename(title="Select PNG file")
        if not filename or not filename.lower().endswith(".png"):
            if filename:
                error_label = ctk.CTkLabel(self.app, text="Please select PNG only!", text_color="red")
                error_label.pack()
                error_label.after(3000, error_label.destroy)
            return
        
        self.current_filename = filename
        
        # Get debug state from checkbox
        debug_enabled = self.debug_var.get() == "on"
        
        # Pass debug_enabled to the function
        marked_img, cell_infos = detect_emotes_with_rects(filename, debug_enabled)
        
        self.show_preview_window(marked_img, cell_infos)
    
    def show_preview_window(self, marked_img, cell_infos):
        if self.preview_window is not None:
            self.preview_window.destroy()

        filled_cells = [c for c in cell_infos if c["has_content"]]
        filled_count = len(filled_cells)
        total_cells = len(cell_infos)

        self.preview_window = ctk.CTkToplevel(self.app)
        self.preview_window.title(f"Emote Detection - {filled_count}/{total_cells} filled")

        # Smart scaling from old version
        screen_width = self.preview_window.winfo_screenwidth()
        screen_height = self.preview_window.winfo_screenheight()
        max_img_width = int(screen_width * 0.7)
        max_img_height = int(screen_height * 0.7)

        orig_width, orig_height = marked_img.size
        scale = min(max_img_width / orig_width, max_img_height / orig_height, 0.45)
        preview_width = int(orig_width * scale)
        preview_height = int(orig_height * scale)

        # Resize image for display
        preview_img = marked_img.resize((preview_width, preview_height), Image.Resampling.LANCZOS)
        photo = ctk.CTkImage(light_image=preview_img, dark_image=preview_img, size=(preview_width, preview_height))

        # Left side: Image and info
        left_frame = ctk.CTkFrame(self.preview_window)
        left_frame.pack(side="left", fill="both", padx=20, pady=20)

        img_label = ctk.CTkLabel(left_frame, image=photo, text="")
        img_label.image = photo
        img_label.pack(pady=10)

        info_text = f"Green: {filled_count} filled | Red: {total_cells - filled_count} empty\n{os.path.basename(self.current_filename)}"
        info_label = ctk.CTkLabel(left_frame, text=info_text, font=ctk.CTkFont(size=14))
        info_label.pack(pady=(0, 10))

        # Right side: Naming panel
        right_frame = ctk.CTkFrame(self.preview_window)
        right_frame.pack(side="right", fill="both", padx=(0, 20), pady=20)

        naming_label = ctk.CTkLabel(right_frame, text="Name Your Emotes", font=ctk.CTkFont(size=16, weight="bold"))
        naming_label.pack(pady=(10, 15))

        # Scrollable frame for entries
        naming_scroll = ctk.CTkScrollableFrame(right_frame, width=200, height=preview_height - 100)
        naming_scroll.pack(fill="both", expand=True, padx=10)

        self.name_entries = []
        for cell in filled_cells:
            row_frame = ctk.CTkFrame(naming_scroll)
            row_frame.pack(pady=5, fill="x")

            label = ctk.CTkLabel(row_frame, text=f"#{cell['id']}:", width=40)
            label.pack(side="left", padx=5)

            entry = ctk.CTkEntry(row_frame, width=140, placeholder_text="Enter name")
            entry.pack(side="left", padx=5)

            self.name_entries.append((cell, entry))

        # Export button
        export_btn = ctk.CTkButton(
            right_frame,
            text="Export Emotes",
            command=self.export_emotes,
            width=150, height=40
        )
        export_btn.pack(pady=15)

        # Auto-size window after content is added
        self.preview_window.update_idletasks()
        window_width = preview_width + 300
        window_height = preview_height + 100
        self.preview_window.geometry(f"{window_width}x{window_height}")

    
    def export_emotes(self):
        from core import export_emotes
        
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
        
        if not selected_platforms:
            error_window = ctk.CTkToplevel(self.app)
            error_window.title("Error")
            error_window.geometry("250x100")
            ctk.CTkLabel(error_window, text="Please select at least one platform!").pack(pady=20)
            ctk.CTkButton(error_window, text="OK", command=error_window.destroy).pack()
            return
        
        # Get debug state
        debug_enabled = self.debug_var.get() == "on"
        
        name_list = [(cell, entry.get()) for cell, entry in self.name_entries]
        
        # Pass debug_enabled to export
        exported_count, out_dir = export_emotes(self.current_filename, name_list, selected_platforms, debug_enabled)
        
        # Show success message
        success_window = ctk.CTkToplevel(self.app)
        success_window.title("Export Complete")
        success_window.geometry("300x200")
        
        ctk.CTkLabel(success_window, text=f"Exported {exported_count} files!").pack(pady=10)
        ctk.CTkLabel(success_window, text=f"Location: {out_dir}", wraplength=280).pack(pady=5)
        #ctk.CTkButton(success_window, text="OK", command=success_window.destroy).pack(pady=10)
    
        def close_all():
            success_window.destroy()
            self.app.quit()
    
        ctk.CTkButton(success_window, text="OK", command=close_all).pack(pady=10)

    def on_cancel(self):
        if self.naming_window:
            self.naming_window.destroy()
        self.app.destroy()
    
    def run(self):
        self.app.mainloop()
