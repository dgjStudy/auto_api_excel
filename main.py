import customtkinter as ctk
from dotenv import load_dotenv
from ui.app import UniversalApiApp

# CustomTkinter 기본 설정
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# 환경변수(.env) 로드
load_dotenv()

def main():
    app = UniversalApiApp()
    app.mainloop()

if __name__ == "__main__":
    main()
