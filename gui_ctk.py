import customtkinter as ctk
from CTkFileDialog import askopenfilename
from PIL import Image, ImageTk
import webbrowser
import os

# Global GUI state
class EmoteGUI:
    def __init__(self):
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        self.app = ctk.CTk()
        self.app.title("Emote Tool")
        
        # State
        self.current_filename = None
        self.current_cells = []
        self.name_entries = []
        self.naming_window = None
        
        # Platform checkboxes
        self.twitch_var = ctk.StringVar(value="on")
        self.twtich_badge_var = ctk.StringVar(value="off")
        self.kick_var = ctk.StringVar(value="off")
        self.youtube_var = ctk.StringVar(value="off")
        self.discord_var = ctk.StringVar(value="off")
        
        self.give_file = None
        self.setup_ui()
    
    def setup_ui(self):
        self.center_window()
        self.app.geometry("300x370")
        self.app.resizable(False, False)  # No resize width/height
        
        # File input row
        self.give_file = ctk.CTkEntry(self.app, width=150, height=25, font=("Consolas", 10))
        self.give_file.place(x=20, y=20)
        
        file_btn = ctk.CTkButton(self.app, text="Browse...", command=self.open_file_dialog, width=80, height=25)
        file_btn.place(x=190, y=20)
        
        # Checkboxes
        self.create_checkboxes()
        
        # Control buttons
        #ok_btn = ctk.CTkButton(self.app, text="OK", width=60, height=30)
        #ok_btn.place(x=50, y=275)
        bug_btn = ctk.CTkButton(self.app, text="Report Bug", command=lambda: webbrowser.open("https://github.com/DebuggingIsFun/Twitch-Emote-Tool/issues"),
        width=60, height=30, font=ctk.CTkFont(size=12)
        )
        bug_btn.place(x=50, y=275)
        
        cancel_btn = ctk.CTkButton(self.app, text="Cancel", width=60, height=30, command=self.on_cancel)
        cancel_btn.place(x=200, y=275)

        credits_frame = ctk.CTkFrame(self.app, height=25)
        credits_frame.place(x=0, y=310, relwidth=1.0)

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
            ("Discord Emotes", self.discord_var)
        ]
        
        for i, (text, var) in enumerate(checkboxes):
            checkbox = ctk.CTkCheckBox(
                self.app, text=text, variable=var, onvalue="on", offvalue="off",
                width=220, height=25, font=ctk.CTkFont(size=12)
            )
            checkbox.place(x=20, y=60 + i * 35)
    
    def center_window(self):
        self.app.update_idletasks()
        x = (self.app.winfo_screenwidth() // 2) - (300 // 2)
        y = (self.app.winfo_screenheight() // 2) - (300 // 2)
        self.app.geometry(f"300x300+{x}+{y}")
    
    def open_file_dialog(self):
        from core import detect_emotes_with_rects  # Import here to avoid circular imports
        
        filename = askopenfilename(title="Select PNG file")
        if not filename or not filename.lower().endswith(".png"):
            if filename:
                error_label = ctk.CTkLabel(self.app, text="Please select PNG only!", text_color="red")
                error_label.pack()
                error_label.after(3000, error_label.destroy)
            return
        
        self.current_filename = filename
        marked_img, cell_infos = detect_emotes_with_rects(filename)
        self.current_cells = cell_infos
        self.name_entries = []
        
        self.give_file.delete(0, ctk.END)
        self.give_file.insert(0, filename)
        
        self.show_preview(marked_img, cell_infos)
    
    def show_preview(self, marked_img, cell_infos):
        filled_count = sum(1 for c in cell_infos if c["has_content"])
        total_cells = len(cell_infos)
        
        preview_window = ctk.CTkToplevel(self.app)
        preview_window.title(f"Emote Detection - {filled_count}/{total_cells} filled")
        
        content_frame = ctk.CTkFrame(preview_window)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Smart scaling
        screen_width = preview_window.winfo_screenwidth()
        screen_height = preview_window.winfo_screenheight()
        max_img_width = int(screen_width * 0.7)
        max_img_height = int(screen_height * 0.7)
        
        orig_width, orig_height = marked_img.size
        scale = min(max_img_width/orig_width, max_img_height/orig_height, 0.45)
        preview_width = int(orig_width * scale)
        preview_height = int(orig_height * scale)
        
        preview_img = marked_img.resize((preview_width, preview_height), Image.Resampling.LANCZOS)
        photo = ctk.CTkImage(light_image=preview_img, size=(preview_width, preview_height))
        
        img_label = ctk.CTkLabel(content_frame, image=photo, text="")
        img_label.image = photo
        img_label.pack(pady=10)
        
        info_text = f"Green: {filled_count} filled | Red: {total_cells-filled_count} empty\n{os.path.basename(self.current_filename)}"
        info_label = ctk.CTkLabel(content_frame, text=info_text, font=ctk.CTkFont(size=14))
        info_label.pack(pady=(0, 10))
        
        if filled_count > 0:
            name_btn = ctk.CTkButton(
                content_frame, text=f"Open Naming Window ({filled_count} emotes)",
                command=self.open_naming_window, height=50
            )
            name_btn.pack(pady=10)
        
        #window_width = preview_width + 80  # image width + padding
        #window_height = min(preview_height + 150, int(screen_height * 0.8))  # image + info + button, capped
        #preview_window.geometry(f"{window_width}x{window_height}")

        content_frame.update_idletasks()
        preview_window.geometry(f"{content_frame.winfo_width()+40}x{content_frame.winfo_height()+60}")
    
    def open_naming_window(self):
        filled_cells = [c for c in self.current_cells if c["has_content"]]
        if not filled_cells:
            return
        
        if self.naming_window and self.naming_window.winfo_exists():
            self.naming_window.destroy()
        
        self.naming_window = ctk.CTkToplevel(self.app)
        self.naming_window.title("Name Emotes (numbers match image markers)")
        self.naming_window.geometry("500x450")
        
        frame = ctk.CTkScrollableFrame(self.naming_window)
        frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        self.name_entries = []
        for cell in filled_cells:
            emote_id = cell["id"]
            row_frame = ctk.CTkFrame(frame)
            row_frame.pack(fill="x", padx=10, pady=5)
            
            id_label = ctk.CTkLabel(row_frame, text=f"#{emote_id}", width=50, font=ctk.CTkFont(size=16, weight="bold"))
            id_label.pack(side="left", padx=(10, 5))
            
            entry = ctk.CTkEntry(row_frame, placeholder_text=f"Name for emote #{emote_id}", height=30)
            entry.pack(side="right", fill="x", expand=True, padx=10)
            self.name_entries.append((cell, entry))
        
        export_btn = ctk.CTkButton(
            self.naming_window, text=f"Export {len(filled_cells)} Emotes (PNGs)",
            command=self.export_emotes, height=35, font=ctk.CTkFont(size=14)
        )
        export_btn.pack(pady=(10, 20), fill="x", padx=20)
    
    def export_emotes(self):
        from core import export_emotes
        
        selected_platforms = []
        if self.twitch_var.get() == "on": selected_platforms.append("twitch")
        if self.twtich_badge_var.get() == "on": selected_platforms.append("twitchbages")
        if self.discord_var.get() == "on": selected_platforms.append("discord")
        if self.youtube_var.get() == "on": selected_platforms.append("youtube")
        if self.kick_var.get() == "on": selected_platforms.append("kick")
        
        if not selected_platforms:
            error_window = ctk.CTkToplevel(self.app)
            ctk.CTkLabel(error_window, text="Please select at least one platform!").pack(pady=20)
            ctk.CTkButton(error_window, text="OK", command=error_window.destroy).pack()
            return
        
        name_list = [(cell, entry.get()) for cell, entry in self.name_entries]
        exported_count, out_dir = export_emotes(self.current_filename, name_list, selected_platforms)
        if self.naming_window and self.naming_window.winfo_exists():
            self.naming_window.destroy()
            self.naming_window = None
        
        self.show_success(exported_count, selected_platforms, out_dir)
    
    def show_success(self, exported_count, selected_platforms, out_dir):
        success_window = ctk.CTkToplevel(self.app)
        success_window.title("Export Complete")
        success_window.geometry("450x200")
        
        platforms_text = ", ".join(selected_platforms).title()
        success_label = ctk.CTkLabel(
            success_window, text=f"{exported_count} emotes exported for {platforms_text}\n{out_dir}",
            font=ctk.CTkFont(size=14)
        )
        success_label.pack(expand=True, pady=20)
        
        def close_all():
            success_window.destroy()
            self.app.destroy()
        
        ok_btn = ctk.CTkButton(success_window, text="OK", command=close_all)
        ok_btn.pack(pady=10)
    
    def on_cancel(self):
        if self.naming_window:
            self.naming_window.destroy()
        self.app.destroy()
    
    def run(self):
        self.app.mainloop()
