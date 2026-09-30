from tkinter import ttk

def apply_treeview_style(mode: str):
    """
    Treeview 테마 스타일 설정 함수
    """
    style = ttk.Style()
    style.theme_use("clam")
    
    if mode == "Dark":
        bg_color = "#2A2D32"
        fg_color = "#F3F4F6"
        header_bg = "#1F2937"
        header_fg = "#F9FAFB"
    else:
        bg_color = "#FFFFFF"
        fg_color = "#111827"
        header_bg = "#E5E7EB"
        header_fg = "#111827"

    # Treeview 스타일 설정
    style.configure("Treeview", 
                    background=bg_color, 
                    foreground=fg_color, 
                    fieldbackground=bg_color, 
                    rowheight=36,
                    font=("Malgun Gothic", 12))
    style.configure("Treeview.Heading", 
                    background=header_bg, 
                    foreground=header_fg, 
                    relief="flat", 
                    font=("Malgun Gothic", 13, "bold"))
    style.map("Treeview", background=[('selected', '#3B82F6' if mode == "Dark" else '#2563EB')], foreground=[('selected', '#FFFFFF')])
    style.map("Treeview.Heading", background=[('active', '#374151' if mode == "Dark" else '#D1D5DB')])
