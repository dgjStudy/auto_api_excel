import os
import requests
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from dotenv import load_dotenv
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# 백엔드 모듈 임포트
from services.api_client import parse_sample_url, fetch_api_data
from services.data_parser import flatten_to_dataframe

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
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("", 9))
        label.pack(ipadx=3, ipady=3)

    def leave(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class UniversalApiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("범용 API 데이터 수집 및 엑셀 변환기")
        self.root.geometry("900x650")
        
        # 저장용 데이터
        self.current_df = None
        self.param_entries = {}  # {param_key: entry_widget}
        
        self.setup_ui()
        
    def setup_ui(self):
        # 1. 샘플 URL 입력 프레임
        sample_frame = ttk.LabelFrame(self.root, text="1. 샘플 URL 입력 (자동 분석)", padding="10")
        sample_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(sample_frame, text="샘플 URL:").grid(row=0, column=0, sticky=tk.W, pady=2)
        
        lbl_sample_help = ttk.Label(sample_frame, text="❓", foreground="blue", cursor="hand2")
        lbl_sample_help.grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        ToolTip(lbl_sample_help, "공공데이터 포털에서 제공하는 '전체 요청 주소(Request URL)'입니다.\n예: http://apis.data.go.kr/.../get?serviceKey=인증키&pageNo=1...")
        
        self.entry_sample_url = ttk.Entry(sample_frame, width=80)
        self.entry_sample_url.grid(row=0, column=2, sticky=tk.EW, padx=5, pady=2)
        
        # 이전 URL 불러오기
        if os.path.exists(".last_url"):
            try:
                with open(".last_url", "r", encoding="utf-8") as f:
                    last_url = f.read().strip()
                    if last_url:
                        self.entry_sample_url.insert(0, last_url)
            except Exception:
                pass
        
        btn_analyze = ttk.Button(sample_frame, text="URL 분석", command=self.on_analyze_url)
        btn_analyze.grid(row=0, column=3, padx=5, pady=2)
        
        btn_clear = ttk.Button(sample_frame, text="초기화", command=self.on_clear_url)
        btn_clear.grid(row=0, column=4, padx=5, pady=2)
        
        sample_frame.columnconfigure(2, weight=1)
        
        # 2. API 엔드포인트 및 파라미터 프레임
        self.api_frame = ttk.LabelFrame(self.root, text="2. API 설정 및 파라미터 (동적 추출)", padding="10")
        self.api_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(self.api_frame, text="Base URL:").grid(row=0, column=0, sticky=tk.W, pady=2)
        
        lbl_base_help = ttk.Label(self.api_frame, text="❓", foreground="blue", cursor="hand2")
        lbl_base_help.grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        ToolTip(lbl_base_help, "파라미터(조건값)가 붙기 전의 '기본 API 주소(API 엔드포인트)'입니다.\n샘플 URL에서 물음표(?) 바로 앞까지의 주소에 해당합니다.")

        self.entry_base_url = ttk.Entry(self.api_frame, width=80)
        self.entry_base_url.grid(row=0, column=2, sticky=tk.EW, padx=5, pady=2, columnspan=2)
        self.api_frame.columnconfigure(2, weight=1)
        
        # 파라미터 폼이 동적으로 배치될 내부 프레임
        self.params_container = ttk.Frame(self.api_frame)
        self.params_container.grid(row=1, column=0, columnspan=4, sticky=tk.EW, pady=5)
        
        # 3. 컨트롤 버튼 프레임
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X, padx=10)
        
        self.btn_fetch = ttk.Button(control_frame, text="데이터 수집", command=self.on_fetch_clicked)
        self.btn_fetch.pack(side=tk.LEFT, padx=5)
        
        self.btn_save = ttk.Button(control_frame, text="엑셀 다운로드", command=self.on_save_clicked)
        self.btn_save.pack(side=tk.LEFT, padx=5)
        self.btn_save.state(['disabled'])
        
        self.btn_stats = ttk.Button(control_frame, text="데이터 통계/차트", command=self.show_statistics)
        self.btn_stats.pack(side=tk.LEFT, padx=5)
        self.btn_stats.state(['disabled'])
        
        self.status_var = tk.StringVar()
        self.status_var.set("샘플 URL을 입력하고 'URL 분석'을 누르거나 직접 입력하세요.")
        status_label = ttk.Label(control_frame, textvariable=self.status_var, foreground="gray")
        status_label.pack(side=tk.RIGHT, padx=5)
        
        # 4. 데이터 그리드 프레임 (Treeview)
        data_frame = ttk.Frame(self.root, padding="10")
        data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tree_scroll_y = ttk.Scrollbar(data_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x = ttk.Scrollbar(data_frame, orient='horizontal')
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.tree = ttk.Treeview(data_frame, yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        
        self.tree.bind("<Double-1>", self.on_row_double_click)
        
    def on_clear_url(self):
        self.entry_sample_url.delete(0, tk.END)
        self.entry_base_url.delete(0, tk.END)
        for child in self.params_container.winfo_children():
            child.destroy()
        self.param_entries.clear()
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
            return
            
        # 분석 시 파일에 저장 (다음 실행 때 불러오기 위함)
        try:
            with open(".last_url", "w", encoding="utf-8") as f:
                f.write(sample_url)
        except Exception:
            pass
            
        base_url, params = parse_sample_url(sample_url)
        
        # Base URL 설정
        self.entry_base_url.delete(0, tk.END)
        self.entry_base_url.insert(0, base_url)
        
        # 기존 파라미터 UI 제거 및 새 파라미터 UI 생성
        self.render_param_inputs(params)
        self.status_var.set(f"URL 분석 완료: {len(params)}개의 파라미터를 추출했습니다.")
        
    def render_param_inputs(self, params):
        # 기존 위젯 지우기
        for child in self.params_container.winfo_children():
            child.destroy()
        self.param_entries.clear()
        
        row = 0
        col = 0
        for key, val in params.items():
            lbl = ttk.Label(self.params_container, text=f"{key}:")
            lbl.grid(row=row, column=col*2, sticky=tk.W, padx=5, pady=2)
            
            ent = ttk.Entry(self.params_container, width=25)
            ent.insert(0, str(val))
            ent.grid(row=row, column=col*2+1, sticky=tk.W, padx=5, pady=2)
            
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
        
        self.btn_fetch.state(['disabled'])
        self.status_var.set("API 수집 및 데이터 파싱 중...")
        
        thread = threading.Thread(target=self.fetch_and_process_data, args=(base_url, params))
        thread.daemon = True
        thread.start()
        
    def fetch_and_process_data(self, base_url, params):
        raw_text, err = fetch_api_data(base_url, params)
        
        if err:
            self.root.after(0, self.show_error, err)
            return
            
        df, parse_err = flatten_to_dataframe(raw_text)
        if parse_err:
            self.root.after(0, self.show_error, parse_err)
            return
            
        if df is not None and not df.empty:
            self.root.after(0, self.update_table, df)
        else:
            self.root.after(0, self.show_error, "수집된 데이터가 비어 있습니다.")
            
    def show_error(self, message):
        self.btn_fetch.state(['!disabled'])
        self.status_var.set("오류 발생")
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
            
        self.btn_fetch.state(['!disabled'])
        self.btn_save.state(['!disabled'])
        self.btn_stats.state(['!disabled'])
        self.status_var.set(f"수집 완료 (총 {len(df)}건, {len(df.columns)}개 열) - 항목 더블클릭 시 전체 필드 확인")
        
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
        popup = tk.Toplevel(self.root)
        popup.title("전체 필드 상세 정보")
        popup.geometry("450x550")
        
        text_frame = ttk.Frame(popup)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
        
        for key, value in row_data.items():
            text_widget.insert(tk.END, f"[{key}]\n{value}\n\n")
            
        text_widget.config(state=tk.DISABLED)
        
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
                    
        stat_win = tk.Toplevel(self.root)
        stat_win.title("수집 데이터 요약 및 시각화")
        stat_win.geometry("650x550")
        
        summary_frame = ttk.Frame(stat_win, padding="10")
        summary_frame.pack(fill=tk.X)
        
        ttk.Label(summary_frame, text=f"총 수집 레코드: {len(df)} 건", font=("", 11, "bold")).pack(anchor=tk.W)
        ttk.Label(summary_frame, text=f"전체 필드(열) 수: {len(df.columns)} 개").pack(anchor=tk.W)
        
        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)
        
        if num_cols:
            target_col = num_cols[0]
            plot_data = df[target_col].dropna().head(30)
            if not plot_data.empty:
                plot_data.plot(kind='bar', ax=ax, color='skyblue')
                ax.set_title(f"수치 항목 분포 ({target_col})")
            else:
                ax.text(0.5, 0.5, "유효한 수치 데이터가 없습니다.", ha='center', va='center', fontdict={'size':12})
                ax.set_title(f"수치 항목 분포 ({target_col}) - 데이터 없음")
        else:
            first_col = df.columns[0]
            plot_data = df[first_col].value_counts().head(10)
            if not plot_data.empty:
                plot_data.plot(kind='bar', ax=ax, color='lightgreen')
                ax.set_title(f"상위 빈도 항목 분포 ({first_col})")
            else:
                ax.text(0.5, 0.5, "유효한 데이터가 없습니다.", ha='center', va='center', fontdict={'size':12})
                ax.set_title(f"상위 빈도 항목 분포 ({first_col}) - 데이터 없음")
            
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=stat_win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    if 'clam' in style.theme_names():
        style.theme_use('clam')
        
    app = UniversalApiApp(root)
    root.mainloop()
