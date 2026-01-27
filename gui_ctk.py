import customtkinter as ctk
from CTkFileDialog import askopenfilename
from PIL import Image
import webbrowser


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
        bug_btn.place(x=50, y=310)
        
        cancel_btn = ctk.CTkButton(
            self.app, text="Cancel", 
            width=60, height=30, 
            command=self.on_cancel
        )
        cancel_btn.place(x=200, y=310)
        
        # Credits
        credits_frame = ctk.CTkFrame(self.app, height=25)
        credits_frame.place(x=0, y=350, relwidth=1.0)
        
        credits_label = ctk.CTkLabel(
            credits_frame, 
            text="Made by streamingdummy",
            font=ctk.CTkFont(size=10),
            cursor="hand2"
        )
        credits_label.pack(pady=5)
        credits_label.bind("<Button-1>", lambda e: webbrowser.open("https://twitch.tv/streamingdummy"))
    
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
        
        self.preview_window = ctk.CTkToplevel(self.app)
        self.preview_window.title("Preview & Name Emotes")
        
        # Calculate window size based on image
        img_width, img_height = marked_img.size
        max_width = 800
        max_height = 600
        
        scale = min(max_width / img_width, max_height / img_height, 1.0)
        display_width = int(img_width * scale)
        display_height = int(img_height * scale)
        
        # Window size: image + naming panel
        window_width = display_width + 250
        window_height = max(display_height + 50, 400)
        self.preview_window.geometry(f"{window_width}x{window_height}")
        
        # Image display
        display_img = marked_img.resize((display_width, display_height), Image.Resampling.LANCZOS)
        ctk_image = ctk.CTkImage(light_image=display_img, dark_image=display_img, size=(display_width, display_height))
        
        img_label = ctk.CTkLabel(self.preview_window, image=ctk_image, text="")
        img_label.place(x=10, y=10)
        
        # Naming panel
        naming_frame = ctk.CTkScrollableFrame(self.preview_window, width=220, height=window_height - 100)
        naming_frame.place(x=display_width + 20, y=10)
        
        self.name_entries = []
        filled_cells = [c for c in cell_infos if c["has_content"]]
        
        for cell in filled_cells:
            row_frame = ctk.CTkFrame(naming_frame)
            row_frame.pack(pady=5, fill="x")
            
            label = ctk.CTkLabel(row_frame, text=f"Emote #{cell['id']}:", width=80)
            label.pack(side="left", padx=5)
            
            entry = ctk.CTkEntry(row_frame, width=120, placeholder_text="Enter name")
            entry.pack(side="left", padx=5)
            
            self.name_entries.append((cell, entry))
        
        # Export button
        export_btn = ctk.CTkButton(
            self.preview_window, 
            text="Export Emotes", 
            command=self.export_emotes,
            width=150, height=40
        )
        export_btn.place(x=display_width + 50, y=window_height - 60)
    
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
        success_window.geometry("300x120")
        
        ctk.CTkLabel(success_window, text=f"Exported {exported_count} files!").pack(pady=10)
        ctk.CTkLabel(success_window, text=f"Location: {out_dir}", wraplength=280).pack(pady=5)
        ctk.CTkButton(success_window, text="OK", command=success_window.destroy).pack(pady=10)
    
    def on_cancel(self):
        if self.naming_window:
            self.naming_window.destroy()
        self.app.destroy()
    
    def run(self):
        self.app.mainloop()
