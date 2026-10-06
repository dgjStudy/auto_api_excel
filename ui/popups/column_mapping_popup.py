import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

class ColumnMappingPopup(ctk.CTkToplevel):
    def __init__(self, parent, columns, on_confirm_callback):
        super().__init__(parent)
        self.title("엑셀 한글 컬럼명 매핑 설정")
        self.geometry("520x560")
        self.resizable(False, False)
        
        self.columns = columns
        self.on_confirm_callback = on_confirm_callback
        self.mapping_entries = {}
        
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui()
        
    def setup_ui(self):
        lbl_title = ctk.CTkLabel(
            self, 
            text="🏷️ 영문 API 필드 ➡️ 한글 컬럼명 매핑", 
            font=("Malgun Gothic", 14, "bold")
        )
        lbl_title.pack(pady=(15, 5))
        
        lbl_sub = ctk.CTkLabel(
            self, 
            text="엑셀에 저장될 컬럼명을 지정하세요. (비워두면 기존 필드명 유지)", 
            font=("Malgun Gothic", 11),
            text_color="#9CA3AF"
        )
        lbl_sub.pack(pady=(0, 10))
        
        # 스크롤 가능한 프레임
        scroll_frame = ctk.CTkScrollableFrame(self, width=470, height=390)
        scroll_frame.pack(padx=15, pady=5, fill=tk.BOTH, expand=True)
        
        headers_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        headers_frame.pack(fill=tk.X, pady=(0, 5))
        
        ctk.CTkLabel(headers_frame, text="원본 API 필드명", font=("Malgun Gothic", 11, "bold"), width=200, anchor="w").pack(side=tk.LEFT, padx=5)
        ctk.CTkLabel(headers_frame, text="변경할 한글 컬럼명", font=("Malgun Gothic", 11, "bold"), width=220, anchor="w").pack(side=tk.LEFT, padx=5)
        
        for col in self.columns:
            row_frame = ctk.CTkFrame(scroll_frame)
            row_frame.pack(fill=tk.X, pady=3, padx=2)
            
            lbl_col = ctk.CTkLabel(row_frame, text=str(col), font=("Malgun Gothic", 11), width=190, anchor="w")
            lbl_col.pack(side=tk.LEFT, padx=(8, 5), pady=4)
            
            ent_map = ctk.CTkEntry(row_frame, width=220, placeholder_text=f"예: {col} 한글명", font=("Malgun Gothic", 11))
            ent_map.pack(side=tk.LEFT, padx=5, pady=4)
            
            self.mapping_entries[col] = ent_map
            
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=15, pady=12)
        
        btn_confirm = ctk.CTkButton(
            btn_frame, 
            text="💾 적용 후 엑셀 저장", 
            fg_color="#10B981", 
            hover_color="#059669", 
            font=("Malgun Gothic", 12, "bold"),
            command=self.on_confirm
        )
        btn_confirm.pack(side=tk.RIGHT, padx=5)
        
        btn_cancel = ctk.CTkButton(
            btn_frame, 
            text="취소", 
            fg_color="#6B7280", 
            hover_color="#4B5563", 
            font=("Malgun Gothic", 12),
            command=self.destroy
        )
        btn_cancel.pack(side=tk.RIGHT, padx=5)
        
    def on_confirm(self):
        mapping = {}
        for col, ent in self.mapping_entries.items():
            mapped_val = ent.get().strip()
            if mapped_val:
                mapping[col] = mapped_val
        self.destroy()
        self.on_confirm_callback(mapping)
