import tkinter as tk
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

class StatsPopup(ctk.CTkToplevel):
    def __init__(self, parent, df):
        super().__init__(parent)
        self.title("수집 데이터 요약 및 시각화")
        self.geometry("680x580")
        self.attributes("-topmost", True)
        
        summary_frame = ctk.CTkFrame(self, corner_radius=10)
        summary_frame.pack(fill=tk.X, padx=15, pady=12)
        
        ctk.CTkLabel(summary_frame, text=f"총 수집 레코드: {len(df)} 건", font=("Malgun Gothic", 12, "bold")).pack(anchor=tk.W, padx=12, pady=(8, 2))
        ctk.CTkLabel(summary_frame, text=f"전체 필드(열) 수: {len(df.columns)} 개", font=("Malgun Gothic", 11)).pack(anchor=tk.W, padx=12, pady=(0, 8))
        
        # 숫자 컬럼 추출
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        if not num_cols:
            for col in df.columns:
                try:
                    converted = df[col].astype(str).str.replace(',', '').astype(float)
                    df[col] = converted
                    num_cols.append(col)
                except Exception:
                    pass

        # 테마에 따른 차트 스타일 설정
        current_mode = ctk.get_appearance_mode()
        is_dark = current_mode.lower() == "dark"
        
        bg_color = '#1D1E1F' if is_dark else '#FFFFFF'
        text_color = '#FFFFFF' if is_dark else '#111827'
        
        if is_dark:
            plt.style.use('dark_background')
        else:
            plt.style.use('default')
            
        fig = Figure(figsize=(6, 4), dpi=100, facecolor=bg_color)
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg_color)
        ax.tick_params(colors=text_color)
        for spine in ax.spines.values():
            spine.set_color(text_color)
        
        if num_cols:
            target_col = num_cols[0]
            plot_data = df[target_col].dropna().head(30)
            if not plot_data.empty:
                plot_data.plot(kind='bar', ax=ax, color='#3B82F6')
                ax.set_title(f"수치 항목 분포 ({target_col})", color=text_color, fontproperties="Malgun Gothic")
            else:
                ax.text(0.5, 0.5, "유효한 수치 데이터가 없습니다.", ha='center', va='center', fontdict={'size':12}, color=text_color)
                ax.set_title(f"수치 항목 분포 ({target_col}) - 데이터 없음", color=text_color, fontproperties="Malgun Gothic")
        else:
            first_col = df.columns[0]
            plot_data = df[first_col].value_counts().head(10)
            if not plot_data.empty:
                plot_data.plot(kind='bar', ax=ax, color='#10B981')
                ax.set_title(f"상위 빈도 항목 분포 ({first_col})", color=text_color, fontproperties="Malgun Gothic")
            else:
                ax.text(0.5, 0.5, "유효한 데이터가 없습니다.", ha='center', va='center', fontdict={'size':12}, color=text_color)
                ax.set_title(f"상위 빈도 항목 분포 ({first_col}) - 데이터 없음", color=text_color, fontproperties="Malgun Gothic")
            
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
