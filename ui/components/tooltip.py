import customtkinter as ctk

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        try:
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + 20
        except Exception:
            return
            
        self.tooltip = ctk.CTkToplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        self.tooltip.attributes("-topmost", True)
        
        label = ctk.CTkLabel(self.tooltip, text=self.text, justify='left',
                             fg_color=("#333333", "#2b2b2b"), text_color="white",
                             corner_radius=6, font=("Malgun Gothic", 12),
                             padx=10, pady=6)
        label.pack()

    def leave(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
