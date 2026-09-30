import tkinter as tk
import customtkinter as ctk

class DetailPopup(ctk.CTkToplevel):
    def __init__(self, parent, row_data):
        super().__init__(parent)
        self.title("전체 필드 상세 정보")
        self.geometry("480x580")
        self.attributes("-topmost", True)
        
        lbl_title = ctk.CTkLabel(self, text="상세 데이터 항목", font=("Malgun Gothic", 14, "bold"))
        lbl_title.pack(pady=(12, 6))

        textbox = ctk.CTkTextbox(self, font=("Consolas", 11), corner_radius=8)
        textbox.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        content = ""
        for key, value in row_data.items():
            content += f"[{key}]\n{value}\n\n"
            
        textbox.insert("1.0", content)
        textbox.configure(state="disabled")
