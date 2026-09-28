import os
import requests
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from dotenv import load_dotenv
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# 백엔드 모듈 임포트
from services.api_client import parse_sample_url, fetch_api_data
from services.data_parser import flatten_to_dataframe

# CustomTkinter 기본 설정 (기본 테마: 블루, 모드: Dark)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# 한글 폰트 설정 (Windows 기준 맑은 고딕)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# .env 파일 로드
load_dotenv()

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

class UniversalApiApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("범용 API 데이터 수집 및 엑셀 변환기")
        self.geometry("980x700")
        self.minsize(850, 600)
        
        # 저장용 데이터
        self.current_df = None
        self.param_entries = {}  # {param_key: entry_widget}
        
        self.setup_ui()
        
    def setup_ui(self):
        # 1. 샘플 URL 입력 프레임
        sample_frame = ctk.CTkFrame(self, corner_radius=10)
        sample_frame.pack(fill=tk.X, padx=15, pady=8)
        
        lbl_title1 = ctk.CTkLabel(sample_frame, text="1. 샘플 URL 입력 (자동 분석)", font=("Malgun Gothic", 13, "bold"))
        lbl_title1.grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=12, pady=(8, 4))

        # 테마(다크/화이트 모드) 전환 버튼 추가
        self.theme_segmented = ctk.CTkSegmentedButton(
            sample_frame, 
            values=["🌙 다크 모드", "☀️ 화이트 모드"], 
            command=self.change_theme,
            font=("Malgun Gothic", 11, "bold")
        )
        self.theme_segmented.set("🌙 다크 모드")
        self.theme_segmented.grid(row=0, column=4, sticky=tk.E, padx=(5, 12), pady=(8, 4))

        lbl_sample = ctk.CTkLabel(sample_frame, text="샘플 URL:", font=("Malgun Gothic", 12))
        lbl_sample.grid(row=1, column=0, sticky=tk.W, padx=(12, 4), pady=6)
        
        lbl_sample_help = ctk.CTkLabel(sample_frame, text="❓", text_color="#3B82F6", cursor="hand2", font=("Malgun Gothic", 13, "bold"))
        lbl_sample_help.grid(row=1, column=1, sticky=tk.W, padx=(0, 8))
        ToolTip(lbl_sample_help, "공공데이터 포털에서 제공하는 '전체 요청 주소(Request URL)'입니다.\n예: http://apis.data.go.kr/.../get?serviceKey=인증키&pageNo=1...")
        
        self.entry_sample_url = ctk.CTkEntry(sample_frame, placeholder_text="공공데이터 Request URL 전체 주소를 입력하세요...", font=("Malgun Gothic", 12))
        self.entry_sample_url.grid(row=1, column=2, sticky=tk.EW, padx=5, pady=6)
        
        # 이전 URL 불러오기
        if os.path.exists(".last_url"):
            try:
                with open(".last_url", "r", encoding="utf-8") as f:
                    last_url = f.read().strip()
                    if last_url:
                        self.entry_sample_url.insert(0, last_url)
                        self.after(100, self.on_analyze_url)
            except Exception:
                pass
        
        btn_analyze = ctk.CTkButton(sample_frame, text="URL 분석", width=90, command=self.on_analyze_url, font=("Malgun Gothic", 12, "bold"))
        btn_analyze.grid(row=1, column=3, padx=5, pady=6)
        
        btn_clear = ctk.CTkButton(sample_frame, text="초기화", width=75, fg_color="#6B7280", hover_color="#4B5563", command=self.on_clear_url, font=("Malgun Gothic", 12))
        btn_clear.grid(row=1, column=4, padx=(5, 12), pady=6)
        
        sample_frame.columnconfigure(2, weight=1)
        
        # 2. API 엔드포인트 및 파라미터 프레임
        self.api_frame = ctk.CTkFrame(self, corner_radius=10)
        self.api_frame.pack(fill=tk.X, padx=15, pady=8)
        
        lbl_title2 = ctk.CTkLabel(self.api_frame, text="2. API 설정 및 파라미터 (동적 추출)", font=("Malgun Gothic", 13, "bold"))
        lbl_title2.grid(row=0, column=0, columnspan=4, sticky=tk.W, padx=12, pady=(8, 4))
        
        lbl_base = ctk.CTkLabel(self.api_frame, text="Base URL:", font=("Malgun Gothic", 12))
        lbl_base.grid(row=1, column=0, sticky=tk.W, padx=(12, 4), pady=6)
        
        lbl_base_help = ctk.CTkLabel(self.api_frame, text="❓", text_color="#3B82F6", cursor="hand2", font=("Malgun Gothic", 13, "bold"))
        lbl_base_help.grid(row=1, column=1, sticky=tk.W, padx=(0, 8))
        ToolTip(lbl_base_help, "파라미터(조건값)가 붙기 전의 '기본 API 주소(API 엔드포인트)'입니다.\n샘플 URL에서 물음표(?) 바로 앞까지의 주소에 해당합니다.")

        self.entry_base_url = ctk.CTkEntry(self.api_frame, placeholder_text="API 엔드포인트 Base URL", font=("Malgun Gothic", 12))
        self.entry_base_url.grid(row=1, column=2, sticky=tk.EW, padx=(5, 12), pady=6, columnspan=2)
        self.api_frame.columnconfigure(2, weight=1)
        
        # 파라미터 폼이 동적으로 배치될 내부 프레임
        self.params_container = ctk.CTkFrame(self.api_frame, fg_color="transparent")
        self.params_container.grid(row=2, column=0, columnspan=4, sticky=tk.EW, padx=12, pady=5)
        
        # 3. 컨트롤 버튼 및 상태 프레임
        control_frame = ctk.CTkFrame(self, fg_color="transparent")
        control_frame.pack(fill=tk.X, padx=15, pady=4)
        
        self.btn_fetch = ctk.CTkButton(control_frame, text="🚀 데이터 수집", font=("Malgun Gothic", 13, "bold"), command=self.on_fetch_clicked)
        self.btn_fetch.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_fetch.configure(state="disabled")
        
        self.btn_save = ctk.CTkButton(control_frame, text="📥 엑셀 다운로드", fg_color="#10B981", hover_color="#059669", text_color="white", font=("Malgun Gothic", 13, "bold"), command=self.on_save_clicked)
        self.btn_save.pack(side=tk.LEFT, padx=4)
        self.btn_save.configure(state="disabled")
        
        self.btn_stats = ctk.CTkButton(control_frame, text="📊 통계/차트", fg_color="#8B5CF6", hover_color="#7C3AED", text_color="white", font=("Malgun Gothic", 13, "bold"), command=self.show_statistics)
        self.btn_stats.pack(side=tk.LEFT, padx=4)
        self.btn_stats.configure(state="disabled")
        
        self.status_var = tk.StringVar()
        self.status_var.set("샘플 URL을 입력하고 'URL 분석'을 누르면 수집 버튼이 활성화됩니다.")
        status_label = ctk.CTkLabel(control_frame, textvariable=self.status_var, font=("Malgun Gothic", 11), text_color="#9CA3AF")
        status_label.pack(side=tk.RIGHT, padx=5)
        
        # 4. 데이터 그리드 프레임 (Treeview + Custom 스타일 적용)
        data_frame = ctk.CTkFrame(self, corner_radius=10)
        data_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(8, 15))
        
        tree_scroll_y = ttk.Scrollbar(data_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        tree_scroll_x = ttk.Scrollbar(data_frame, orient='horizontal')
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 5))
        
        self.tree = ttk.Treeview(data_frame, yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=(5, 0), pady=(5, 0))
        
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        
        self.tree.bind("<Double-1>", self.on_row_double_click)

        # 초기 Treeview 스타일 적용
        self.update_treeview_style("Dark")

    def change_theme(self, choice_text):
        if "다크" in choice_text or "Dark" in choice_text:
            ctk.set_appearance_mode("Dark")
            self.update_treeview_style("Dark")
        else:
            ctk.set_appearance_mode("Light")
            self.update_treeview_style("Light")

    def update_treeview_style(self, mode):
        style = ttk.Style()
        style.theme_use("clam")
        if mode == "Dark":
            style.configure("Treeview", 
                            background="#2A2D32", 
                            foreground="#E5E7EB", 
                            fieldbackground="#2A2D32", 
                            rowheight=28,
                            font=("Malgun Gothic", 10))
            style.configure("Treeview.Heading", 
                            background="#1F2937", 
                            foreground="#F9FAFB", 
                            relief="flat", 
                            font=("Malgun Gothic", 11, "bold"))
            style.map("Treeview", background=[('selected', '#3B82F6')], foreground=[('selected', '#FFFFFF')])
            style.map("Treeview.Heading", background=[('active', '#374151')])
        else:
            style.configure("Treeview", 
                            background="#FFFFFF", 
                            foreground="#111827", 
                            fieldbackground="#FFFFFF", 
                            rowheight=28,
                            font=("Malgun Gothic", 10))
            style.configure("Treeview.Heading", 
                            background="#E5E7EB", 
                            foreground="#111827", 
                            relief="flat", 
                            font=("Malgun Gothic", 11, "bold"))
            style.map("Treeview", background=[('selected', '#2563EB')], foreground=[('selected', '#FFFFFF')])
            style.map("Treeview.Heading", background=[('active', '#D1D5DB')])
        
    def on_clear_url(self):
        self.entry_sample_url.delete(0, tk.END)
        self.entry_base_url.delete(0, tk.END)
        for child in self.params_container.winfo_children():
            child.destroy()
        self.param_entries.clear()
        self.btn_fetch.configure(state="disabled")
        self.btn_save.configure(state="disabled")
        self.btn_stats.configure(state="disabled")
        self.status_var.set("URL과 파라미터가 초기화되었습니다.")
        if os.path.exists(".last_url"):
            try:
                os.remove(".last_url")
            except Exception:
                pass

    def on_analyze_url(self):
        sample_url = self.entry_sample_url.get().strip()
        if not sample_url:
            messagebox.showwarning("경고", "샘플 URL을 입력해 주세요.")
            self.btn_fetch.configure(state="disabled")
            return
            
        # URL 유효성 간단 검증 (http:// 또는 https:// 포함 여부)
        if not (sample_url.startswith("http://") or sample_url.startswith("https://")):
            messagebox.showerror("오류", "유효하지 않은 URL 형태입니다.\nhttp:// 또는 https://로 시작하는 올바른 API URL을 입력하세요.")
            self.btn_fetch.configure(state="disabled")
            return
            
        base_url, params = parse_sample_url(sample_url)
        if not base_url:
            messagebox.showerror("오류", "URL에서 Base API 주소를 추출하지 못했습니다.")
            self.btn_fetch.configure(state="disabled")
            return

        # 분석 시 파일에 저장
        try:
            with open(".last_url", "w", encoding="utf-8") as f:
                f.write(sample_url)
        except Exception:
            pass
            
        # Base URL 설정 및 파라미터 생성
        self.entry_base_url.delete(0, tk.END)
        self.entry_base_url.insert(0, base_url)
        self.render_param_inputs(params)
        
        # 분석 완료 후 수집 버튼 활성화
        self.btn_fetch.configure(state="normal")
        self.status_var.set(f"✅ URL 분석 성공: {len(params)}개 파라미터 추출 완료. '데이터 수집' 버튼을 누르세요.")
        
    def render_param_inputs(self, params):
        for child in self.params_container.winfo_children():
            child.destroy()
        self.param_entries.clear()
        
        row = 0
        col = 0
        for key, val in params.items():
            lbl = ctk.CTkLabel(self.params_container, text=f"{key}:", font=("Malgun Gothic", 11, "bold"))
            lbl.grid(row=row, column=col*2, sticky=tk.W, padx=(5, 2), pady=3)
            
            ent = ctk.CTkEntry(self.params_container, width=180, font=("Malgun Gothic", 11))
            ent.insert(0, str(val))
            ent.grid(row=row, column=col*2+1, sticky=tk.W, padx=(2, 15), pady=3)
            
            self.param_entries[key] = ent
            
            col += 1
            if col >= 2: # 2열씩 배치
                col = 0
                row += 1
                
    def on_fetch_clicked(self):
        base_url = self.entry_base_url.get().strip()
        if not base_url:
            messagebox.showwarning("경고", "Base API URL이 비어 있습니다.")
            return
            
        params = {k: entry.get().strip() for k, entry in self.param_entries.items()}
        
        self.btn_fetch.configure(state="disabled")
        self.status_var.set("⏳ API 수집 및 데이터 파싱 중...")
        
        thread = threading.Thread(target=self.fetch_and_process_data, args=(base_url, params))
        thread.daemon = True
        thread.start()
        
    def fetch_and_process_data(self, base_url, params):
        raw_text, err = fetch_api_data(base_url, params)
        
        if err:
            self.after(0, self.show_error, err)
            return
            
        df, parse_err = flatten_to_dataframe(raw_text)
        if parse_err:
            self.after(0, self.show_error, parse_err)
            return
            
        if df is not None and not df.empty:
            self.after(0, self.update_table, df)
        else:
            self.after(0, self.show_error, "수집된 데이터가 비어 있습니다.")
            
    def show_error(self, message):
        self.btn_fetch.configure(state="normal")
        self.status_var.set("❌ 오류 발생")
        messagebox.showerror("오류", message)
        
    def update_table(self, df):
        self.current_df = df
        
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        display_columns = list(df.columns)[:10] # 주요 상위 10개 컬럼 표시
        
        self.tree["columns"] = display_columns
        self.tree["show"] = "headings"
        
        for col in display_columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130, anchor=tk.W)
            
        for index, row in df.iterrows():
            values = [str(row[col]) if pd.notna(row[col]) else "" for col in display_columns]
            self.tree.insert("", tk.END, values=values, tags=(str(index),))
            
        self.btn_fetch.configure(state="normal")
        self.btn_save.configure(state="normal")
        self.btn_stats.configure(state="normal")
        self.status_var.set(f"✅ 수집 완료 (총 {len(df)}건, {len(df.columns)}개 열) - 항목 더블클릭 시 전체 필드 확인")
        
    def on_row_double_click(self, event):
        if self.current_df is None:
            return
            
        selected_item = self.tree.selection()
        if not selected_item:
            return
            
        item = self.tree.item(selected_item[0])
        tags = item.get("tags")
        if not tags:
            return
            
        row_index = int(tags[0])
        row_data = self.current_df.iloc[row_index]
        self.show_detail_popup(row_data)
        
    def show_detail_popup(self, row_data):
        popup = ctk.CTkToplevel(self)
        popup.title("전체 필드 상세 정보")
        popup.geometry("480x580")
        popup.attributes("-topmost", True)
        
        lbl_title = ctk.CTkLabel(popup, text="상세 데이터 항목", font=("Malgun Gothic", 14, "bold"))
        lbl_title.pack(pady=(12, 6))

        textbox = ctk.CTkTextbox(popup, font=("Consolas", 11), corner_radius=8)
        textbox.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        content = ""
        for key, value in row_data.items():
            content += f"[{key}]\n{value}\n\n"
            
        textbox.insert("1.0", content)
        textbox.configure(state="disabled")
        
    def on_save_clicked(self):
        if self.current_df is None or self.current_df.empty:
            return
            
        import datetime
        import re
        from urllib.parse import urlparse
        
        base_url = self.entry_base_url.get().strip()
        default_name = "api_data"
        if base_url:
            parsed = urlparse(base_url)
            domain = parsed.netloc
            path_parts = [p for p in parsed.path.split('/') if p]
            last_path = path_parts[-1] if path_parts else ""
            
            parts = [p for p in [domain, last_path] if p]
            if parts:
                raw_name = "_".join(parts)
                default_name = re.sub(r'[\\/*?:"<>|]', '_', raw_name)
                
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        initial_filename = f"{default_name}_{date_str}.xlsx"
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="데이터 저장",
            initialfile=initial_filename
        )
        
        if file_path:
            try:
                if file_path.endswith(".csv"):
                    self.current_df.to_csv(file_path, index=False, encoding='utf-8-sig')
                else:
                    self.current_df.to_excel(file_path, index=False)
                messagebox.showinfo("저장 완료", f"데이터가 성공적으로 저장되었습니다.\n{file_path}")
            except Exception as e:
                messagebox.showerror("저장 오류", f"파일 저장 중 오류가 발생했습니다:\n{e}")

    def show_statistics(self):
        if self.current_df is None or self.current_df.empty:
            return
            
        df = self.current_df.copy()
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        # 숫자 컬럼이 없으면 숫자 자동 변환 시도
        if not num_cols:
            for col in df.columns:
                try:
                    converted = df[col].astype(str).str.replace(',', '').astype(float)
                    df[col] = converted
                    num_cols.append(col)
                except Exception:
                    pass
                    
        stat_win = ctk.CTkToplevel(self)
        stat_win.title("수집 데이터 요약 및 시각화")
        stat_win.geometry("680x580")
        stat_win.attributes("-topmost", True)
        
        summary_frame = ctk.CTkFrame(stat_win, corner_radius=10)
        summary_frame.pack(fill=tk.X, padx=15, pady=12)
        
        ctk.CTkLabel(summary_frame, text=f"총 수집 레코드: {len(df)} 건", font=("Malgun Gothic", 12, "bold")).pack(anchor=tk.W, padx=12, pady=(8, 2))
        ctk.CTkLabel(summary_frame, text=f"전체 필드(열) 수: {len(df.columns)} 개", font=("Malgun Gothic", 11)).pack(anchor=tk.W, padx=12, pady=(0, 8))
        
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
        canvas = FigureCanvasTkAgg(fig, master=stat_win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

if __name__ == "__main__":
    app = UniversalApiApp()
    app.mainloop()
