import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import pandas as pd

from services.api_client import parse_sample_url, fetch_api_data, fetch_all_pages
from services.data_parser import flatten_to_dataframe, extract_meta_info, flatten_multiple_to_dataframe
from services.excel_exporter import save_styled_excel
from services.history_manager import load_history, save_bookmark, delete_bookmark

from ui.components.tooltip import ToolTip
from ui.theme import apply_treeview_style
from ui.popups.detail_popup import DetailPopup
from ui.popups.stats_popup import StatsPopup
from ui.popups.column_mapping_popup import ColumnMappingPopup

class UniversalApiApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("범용 API 데이터 수집 및 엑셀 변환기 v1.1.0")
        self.geometry("1060x780")
        self.minsize(940, 680)
        
        # 저장용 데이터
        self.current_df = None
        self.param_entries = {}  # {param_key: entry_widget}
        self.detected_meta = {}
        
        self.setup_ui()
        self.refresh_bookmarks_combo()
        
    def setup_ui(self):
        # 1. 샘플 URL 입력 프레임
        sample_frame = ctk.CTkFrame(self, corner_radius=10)
        sample_frame.pack(fill=tk.X, padx=15, pady=(8, 4))
        
        lbl_title1 = ctk.CTkLabel(sample_frame, text="1. 샘플 URL 입력 및 즐겨찾기", font=("Malgun Gothic", 13, "bold"))
        lbl_title1.grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=12, pady=(6, 2))

        # 테마(다크/화이트 모드) 전환 버튼
        self.theme_segmented = ctk.CTkSegmentedButton(
            sample_frame, 
            values=["🌙 다크 모드", "☀️ 화이트 모드"], 
            command=self.change_theme,
            font=("Malgun Gothic", 11, "bold")
        )
        self.theme_segmented.set("🌙 다크 모드")
        self.theme_segmented.grid(row=0, column=5, sticky=tk.E, padx=(5, 12), pady=(6, 2))

        # 즐겨찾기 메뉴
        lbl_bookmark = ctk.CTkLabel(sample_frame, text="⭐ 즐겨찾기:", font=("Malgun Gothic", 11, "bold"))
        lbl_bookmark.grid(row=1, column=0, sticky=tk.W, padx=(12, 2), pady=2)

        self.cmb_bookmark = ctk.CTkComboBox(
            sample_frame, 
            values=["저장된 API 선택..."], 
            width=220,
            command=self.on_bookmark_selected,
            font=("Malgun Gothic", 11)
        )
        self.cmb_bookmark.set("저장된 API 선택...")
        self.cmb_bookmark.grid(row=1, column=2, sticky=tk.W, padx=2, pady=2)

        btn_save_bm = ctk.CTkButton(sample_frame, text="⭐ 등록", width=55, fg_color="#F59E0B", hover_color="#D97706", command=self.on_add_bookmark, font=("Malgun Gothic", 11, "bold"))
        btn_save_bm.grid(row=1, column=3, sticky=tk.W, padx=2, pady=2)

        lbl_sample = ctk.CTkLabel(sample_frame, text="샘플 URL:", font=("Malgun Gothic", 12))
        lbl_sample.grid(row=2, column=0, sticky=tk.W, padx=(12, 4), pady=4)
        
        lbl_sample_help = ctk.CTkLabel(sample_frame, text="❓", text_color="#3B82F6", cursor="hand2", font=("Malgun Gothic", 13, "bold"))
        lbl_sample_help.grid(row=2, column=1, sticky=tk.W, padx=(0, 8))
        ToolTip(lbl_sample_help, "공공데이터 포털에서 제공하는 '전체 요청 주소(Request URL)'입니다.")
        
        self.entry_sample_url = ctk.CTkEntry(sample_frame, placeholder_text="공공데이터 Request URL 전체 주소를 입력하세요...", font=("Malgun Gothic", 12))
        self.entry_sample_url.grid(row=2, column=2, columnspan=2, sticky=tk.EW, padx=5, pady=4)
        
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
        btn_analyze.grid(row=2, column=4, padx=5, pady=4)
        
        btn_clear = ctk.CTkButton(sample_frame, text="초기화", width=75, fg_color="#6B7280", hover_color="#4B5563", command=self.on_clear_url, font=("Malgun Gothic", 12))
        btn_clear.grid(row=2, column=5, padx=(5, 12), pady=4)
        
        sample_frame.columnconfigure(2, weight=1)
        
        # 2. API 엔드포인트 및 파라미터 프레임
        self.api_frame = ctk.CTkFrame(self, corner_radius=10)
        self.api_frame.pack(fill=tk.X, padx=15, pady=4)
        
        lbl_title2 = ctk.CTkLabel(self.api_frame, text="2. API 설정 및 파라미터 (동적 추출)", font=("Malgun Gothic", 13, "bold"))
        lbl_title2.grid(row=0, column=0, columnspan=4, sticky=tk.W, padx=12, pady=(6, 2))
        
        lbl_base = ctk.CTkLabel(self.api_frame, text="Base URL:", font=("Malgun Gothic", 12))
        lbl_base.grid(row=1, column=0, sticky=tk.W, padx=(12, 4), pady=4)
        
        lbl_base_help = ctk.CTkLabel(self.api_frame, text="❓", text_color="#3B82F6", cursor="hand2", font=("Malgun Gothic", 13, "bold"))
        lbl_base_help.grid(row=1, column=1, sticky=tk.W, padx=(0, 8))
        ToolTip(lbl_base_help, "파라미터(조건값)가 붙기 전의 기본 API 주소입니다.")

        self.entry_base_url = ctk.CTkEntry(self.api_frame, placeholder_text="API 엔드포인트 Base URL", font=("Malgun Gothic", 12))
        self.entry_base_url.grid(row=1, column=2, sticky=tk.EW, padx=(5, 12), pady=4, columnspan=2)
        self.api_frame.columnconfigure(2, weight=1)
        
        # 파라미터 폼 내부 프레임
        self.params_container = ctk.CTkFrame(self.api_frame, fg_color="transparent")
        self.params_container.grid(row=2, column=0, columnspan=4, sticky=tk.EW, padx=12, pady=3)

        # 🔄 옵션: 자동 전체 수집 체크박스
        self.chk_fetch_all = ctk.CTkCheckBox(
            self.api_frame, 
            text="🔄 전체 페이지 일괄 수집 (totalCount 자동 감지)", 
            font=("Malgun Gothic", 11, "bold"),
            text_color="#3B82F6"
        )
        self.chk_fetch_all.grid(row=3, column=0, columnspan=4, sticky=tk.W, padx=12, pady=(2, 6))
        
        # 3. 컨트롤 버튼 및 상태 프레임
        control_frame = ctk.CTkFrame(self, fg_color="transparent")
        control_frame.pack(fill=tk.X, padx=15, pady=3)
        
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
        
        # 4. 데이터 그리드 프레임 (Treeview)
        data_frame = ctk.CTkFrame(self, corner_radius=10)
        data_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(8, 5))
        
        tree_container = ctk.CTkFrame(data_frame, fg_color="transparent")
        tree_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        tree_scroll_y = ctk.CTkScrollbar(tree_container, orientation="vertical")
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree_scroll_x = ctk.CTkScrollbar(tree_container, orientation="horizontal")
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.tree = ttk.Treeview(tree_container, yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        tree_scroll_y.configure(command=self.tree.yview)
        tree_scroll_x.configure(command=self.tree.xview)
        
        self.tree.bind("<Double-1>", self.on_row_double_click)

        # 5. 페이징 바 프레임
        self.page_frame = ctk.CTkFrame(data_frame, fg_color="transparent")
        self.page_frame.pack(fill=tk.X, padx=10, pady=(2, 6))

        self.btn_prev_page = ctk.CTkButton(self.page_frame, text="◀ 이전", width=70, height=28, font=("Malgun Gothic", 11, "bold"), command=self.prev_page, state="disabled")
        self.btn_prev_page.pack(side=tk.LEFT, padx=5)

        self.lbl_page_info = ctk.CTkLabel(self.page_frame, text="페이지: 0 / 0 (총 0건)", font=("Malgun Gothic", 12, "bold"))
        self.lbl_page_info.pack(side=tk.LEFT, padx=15)

        self.btn_next_page = ctk.CTkButton(self.page_frame, text="다음 ▶", width=70, height=28, font=("Malgun Gothic", 11, "bold"), command=self.next_page, state="disabled")
        self.btn_next_page.pack(side=tk.LEFT, padx=5)

        lbl_size = ctk.CTkLabel(self.page_frame, text="페이지 당 개수:", font=("Malgun Gothic", 11))
        lbl_size.pack(side=tk.RIGHT, padx=(10, 5))

        self.cmb_page_size = ctk.CTkComboBox(
            self.page_frame, 
            values=["10개씩 보기", "15개씩 보기", "20개씩 보기", "30개씩 보기"], 
            width=105, 
            height=26,
            font=("Malgun Gothic", 11),
            command=self.on_page_size_changed
        )
        self.cmb_page_size.set("10개씩 보기")
        self.cmb_page_size.pack(side=tk.RIGHT, padx=5)

        self.current_page = 1
        self.page_size = 10
        self.total_pages = 1

        apply_treeview_style("Dark")

    def refresh_bookmarks_combo(self):
        history = load_history()
        names = [item.get("name") for item in history if item.get("name")]
        if names:
            self.cmb_bookmark.configure(values=names)
        else:
            self.cmb_bookmark.configure(values=["저장된 API 없음"])

    def on_add_bookmark(self):
        sample_url = self.entry_sample_url.get().strip()
        base_url = self.entry_base_url.get().strip()
        if not sample_url or not base_url:
            messagebox.showwarning("경고", "먼저 URL을 입력하고 분석해 주세요.")
            return
            
        dialog = ctk.CTkInputDialog(text="즐겨찾기에 등록할 별칭을 입력하세요:", title="즐겨찾기 추가")
        name = dialog.get_input()
        if name and name.strip():
            params = {k: entry.get().strip() for k, entry in self.param_entries.items()}
            ok, msg = save_bookmark(name.strip(), sample_url, base_url, params)
            if ok:
                messagebox.showinfo("성공", msg)
                self.refresh_bookmarks_combo()
                self.cmb_bookmark.set(name.strip())
            else:
                messagebox.showerror("오류", msg)

    def on_bookmark_selected(self, selected_name):
        history = load_history()
        for item in history:
            if item.get("name") == selected_name:
                self.entry_sample_url.delete(0, tk.END)
                self.entry_sample_url.insert(0, item.get("sample_url", ""))
                self.entry_base_url.delete(0, tk.END)
                self.entry_base_url.insert(0, item.get("base_url", ""))
                self.render_param_inputs(item.get("params", {}))
                self.btn_fetch.configure(state="normal")
                self.status_var.set(f"⭐ 즐겨찾기 '{selected_name}' 로드 완료.")
                break

    def on_page_size_changed(self, choice):
        try:
            num = int(choice.replace("개씩 보기", "").strip())
            self.page_size = num
            if self.current_df is not None and not self.current_df.empty:
                import math
                self.total_pages = max(1, math.ceil(len(self.current_df) / self.page_size))
                self.current_page = 1
                self.render_page_data()
        except Exception:
            pass

    def change_theme(self, choice_text):
        if "다크" in choice_text or "Dark" in choice_text:
            ctk.set_appearance_mode("Dark")
            apply_treeview_style("Dark")
        else:
            ctk.set_appearance_mode("Light")
            apply_treeview_style("Light")

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

    def on_analyze_url(self):
        sample_url = self.entry_sample_url.get().strip()
        if not sample_url:
            messagebox.showwarning("경고", "샘플 URL을 입력해 주세요.")
            self.btn_fetch.configure(state="disabled")
            return
            
        if not (sample_url.startswith("http://") or sample_url.startswith("https://")):
            messagebox.showerror("오류", "유효하지 않은 URL 형태입니다.")
            self.btn_fetch.configure(state="disabled")
            return
            
        base_url, params = parse_sample_url(sample_url)
        if not base_url:
            messagebox.showerror("오류", "Base API 주소를 추출하지 못했습니다.")
            self.btn_fetch.configure(state="disabled")
            return

        try:
            with open(".last_url", "w", encoding="utf-8") as f:
                f.write(sample_url)
        except Exception:
            pass
            
        self.entry_base_url.delete(0, tk.END)
        self.entry_base_url.insert(0, base_url)
        self.render_param_inputs(params)
        
        self.btn_fetch.configure(state="normal")
        self.status_var.set(f"✅ URL 분석 성공: {len(params)}개 파라미터 추출 완료.")
        
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
            if col >= 2:
                col = 0
                row += 1
                
    def on_fetch_clicked(self):
        base_url = self.entry_base_url.get().strip()
        if not base_url:
            messagebox.showwarning("경고", "Base API URL이 비어 있습니다.")
            return
            
        params = {k: entry.get().strip() for k, entry in self.param_entries.items()}
        is_fetch_all = bool(self.chk_fetch_all.get())
        
        self.btn_fetch.configure(state="disabled")
        self.status_var.set("⏳ API 수집 중...")
        
        thread = threading.Thread(target=self.fetch_and_process_data, args=(base_url, params, is_fetch_all))
        thread.daemon = True
        thread.start()
        
    def fetch_and_process_data(self, base_url, params, is_fetch_all):
        raw_text, err = fetch_api_data(base_url, params)
        if err:
            self.after(0, self.show_error, err)
            return
            
        meta = extract_meta_info(raw_text)
        self.detected_meta = meta
        
        if is_fetch_all and meta.get("totalCount") and meta["totalCount"] > 0:
            num_rows = meta.get("numOfRows") or 10
            total_cnt = meta["totalCount"]
            
            def on_progress(p, total_p):
                self.after(0, lambda: self.status_var.set(f"🔄 전체 수집 중... ({p}/{total_p} 페이지)"))
                
            raw_texts, page_err = fetch_all_pages(base_url, params, total_cnt, num_rows, max_pages=50, progress_callback=on_progress)
            df, parse_err = flatten_multiple_to_dataframe(raw_texts)
        else:
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
        self.current_page = 1
        import math
        self.total_pages = max(1, math.ceil(len(df) / self.page_size))
        
        display_columns = list(df.columns)[:10]
        
        self.tree["columns"] = display_columns
        self.tree["show"] = "headings"
        
        for col in display_columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor=tk.W)
            
        self.render_page_data()
            
        self.btn_fetch.configure(state="normal")
        self.btn_save.configure(state="normal")
        self.btn_stats.configure(state="normal")
        
        meta_msg = ""
        if self.detected_meta.get("totalCount"):
            meta_msg = f" (전체 API 건수: {self.detected_meta['totalCount']}건)"
        self.status_var.set(f"✅ 수집 완료 (총 {len(df)}건 추출){meta_msg}")

    def render_page_data(self):
        if self.current_df is None or self.current_df.empty:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        display_columns = list(self.tree["columns"])
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        page_df = self.current_df.iloc[start_idx:end_idx]

        for index, row in page_df.iterrows():
            values = [str(row[col]) if pd.notna(row[col]) else "" for col in display_columns]
            self.tree.insert("", tk.END, values=values, tags=(str(index),))

        self.lbl_page_info.configure(text=f"페이지: {self.current_page} / {self.total_pages} (총 {len(self.current_df)}건)")
        
        self.btn_prev_page.configure(state="disabled" if self.current_page <= 1 else "normal")
        self.btn_next_page.configure(state="disabled" if self.current_page >= self.total_pages else "normal")

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.render_page_data()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.render_page_data()
        
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
        DetailPopup(self, row_data)
        
    def on_save_clicked(self):
        if self.current_df is None or self.current_df.empty:
            return
            
        ColumnMappingPopup(self, list(self.current_df.columns), self.execute_excel_save)

    def execute_excel_save(self, column_mapping):
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
                    df_to_save = self.current_df.copy()
                    if column_mapping:
                        df_to_save.rename(columns=column_mapping, inplace=True)
                    df_to_save.to_csv(file_path, index=False, encoding='utf-8-sig')
                else:
                    save_styled_excel(self.current_df, file_path, column_mapping)
                messagebox.showinfo("저장 완료", f"서식이 적용된 엑셀 데이터가 저장되었습니다.\n{file_path}")
            except Exception as e:
                messagebox.showerror("저장 오류", f"파일 저장 중 오류가 발생했습니다:\n{e}")

    def show_statistics(self):
        if self.current_df is None or self.current_df.empty:
            return
        StatsPopup(self, self.current_df.copy())
