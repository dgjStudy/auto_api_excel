import os
import requests
import pandas as pd
import xmltodict
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading

def fetch_data(api_key, api_endpoint):
    """공공데이터 포털 API를 호출하여 데이터를 가져옵니다."""
    if not api_key or not api_endpoint:
        return None, "오류: API 키와 엔드포인트를 입력해주세요."
        
    params_str = f"serviceKey={api_key}&pageNo=1&numOfRows=10&LAWD_CD=11110&DEAL_YMD=202312"
    request_url = f"{api_endpoint}?{params_str}"
    
    try:
        response = requests.get(request_url)
        response.raise_for_status()
        return response.text, None
    except requests.exceptions.RequestException as e:
        return None, f"API 호출 중 예외 발생:\n{e}"

def process_xml_to_dataframe(xml_data):
    """XML 데이터를 파싱하여 pandas DataFrame으로 변환합니다."""
    try:
        data_dict = xmltodict.parse(xml_data)
        
        try:
            items = data_dict['response']['body']['items']['item']
        except (KeyError, TypeError):
            return None, "표준 데이터 구조(response->body->items->item)를 찾지 못했습니다."
            
        if isinstance(items, dict):
            items = [items]
            
        df = pd.DataFrame(items)
        return df, None
        
    except Exception as e:
        return None, f"XML 처리 중 오류 발생:\n{e}"


class PublicDataApp:
    def __init__(self, root):
        self.root = root
        self.root.title("공공데이터 수집기")
        self.root.geometry("800x500")
        
        # 데이터프레임 저장용
        self.current_df = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # API 설정 입력 프레임
        input_frame = ttk.LabelFrame(self.root, text="API 설정", padding="10")
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(input_frame, text="API 주소:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.entry_endpoint = ttk.Entry(input_frame, width=70)
        self.entry_endpoint.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(input_frame, text="API Key:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.entry_key = ttk.Entry(input_frame, width=70)
        self.entry_key.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        # 상단 컨트롤 프레임
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        self.btn_fetch = ttk.Button(control_frame, text="데이터 수집", command=self.on_fetch_clicked)
        self.btn_fetch.pack(side=tk.LEFT, padx=5)
        
        self.btn_save = ttk.Button(control_frame, text="엑셀 다운로드", command=self.on_save_clicked)
        self.btn_save.pack(side=tk.LEFT, padx=5)
        self.btn_save.state(['disabled']) # 데이터가 없을 때는 비활성화
        
        self.status_var = tk.StringVar()
        self.status_var.set("대기 중...")
        status_label = ttk.Label(control_frame, textvariable=self.status_var, foreground="gray")
        status_label.pack(side=tk.RIGHT, padx=5)
        
        # 메인 데이터 프레임 (Treeview)
        data_frame = ttk.Frame(self.root, padding="10")
        data_frame.pack(fill=tk.BOTH, expand=True)
        
        # 스크롤바 추가
        tree_scroll_y = ttk.Scrollbar(data_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x = ttk.Scrollbar(data_frame, orient='horizontal')
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.tree = ttk.Treeview(data_frame, yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        
        # 더블 클릭 이벤트 바인딩
        self.tree.bind("<Double-1>", self.on_row_double_click)
        
    def on_fetch_clicked(self):
        self.btn_fetch.state(['disabled'])
        self.status_var.set("API 요청 중...")
        
        # 백그라운드 스레드에서 API 호출하여 UI 멈춤 방지
        thread = threading.Thread(target=self.fetch_and_process_data)
        thread.daemon = True
        thread.start()
        
    def fetch_and_process_data(self):
        api_key = self.entry_key.get().strip()
        api_endpoint = self.entry_endpoint.get().strip()
        
        xml_content, err = fetch_data(api_key, api_endpoint)
        
        if err:
            self.root.after(0, self.show_error, err)
            return
            
        if xml_content:
            df, parse_err = process_xml_to_dataframe(xml_content)
            if parse_err:
                self.root.after(0, self.show_error, parse_err)
                return
                
            if df is not None and not df.empty:
                self.root.after(0, self.update_table, df)
            else:
                self.root.after(0, self.show_error, "데이터가 비어 있습니다.")
                
    def show_error(self, message):
        self.btn_fetch.state(['!disabled'])
        self.status_var.set("오류 발생")
        messagebox.showerror("오류", message)
        
    def update_table(self, df):
        self.current_df = df
        
        # Treeview 초기화
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # 열(Column) 설정 - 사용자 요청에 따라 특정 열(최대 5개)만 메인 화면에 표시
        display_columns = list(df.columns)[:5]
        
        self.tree["columns"] = display_columns
        self.tree["show"] = "headings"
        
        for col in display_columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor=tk.CENTER)
            
        # 데이터 삽입 (태그에 원본 DataFrame의 인덱스를 저장하여 나중에 찾기 쉽게 함)
        for index, row in df.iterrows():
            values = [row[col] for col in display_columns]
            self.tree.insert("", tk.END, values=values, tags=(str(index),))
            
        self.btn_fetch.state(['!disabled'])
        self.btn_save.state(['!disabled'])
        self.status_var.set(f"수집 완료 (총 {len(df)}건) - 항목을 더블클릭하여 전체 정보 확인")
        
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
            
        # 저장된 인덱스로 전체 데이터 조회
        row_index = int(tags[0])
        row_data = self.current_df.iloc[row_index]
        
        self.show_detail_popup(row_data)
        
    def show_detail_popup(self, row_data):
        popup = tk.Toplevel(self.root)
        popup.title("상세 정보")
        popup.geometry("400x500")
        
        # Text 렌더링 방식 수정하여 스크롤 가능하게 처리
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
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
            title="엑셀 파일로 저장",
            initialfile="public_data_output.xlsx"
        )
        
        if file_path:
            try:
                self.current_df.to_excel(file_path, index=False)
                messagebox.showinfo("저장 완료", f"데이터가 성공적으로 저장되었습니다.\n{file_path}")
            except Exception as e:
                messagebox.showerror("저장 오류", f"엑셀 파일 저장 중 오류가 발생했습니다:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    
    # 테마 설정 (기본보다 깔끔한 테마 적용)
    style = ttk.Style()
    if 'clam' in style.theme_names():
        style.theme_use('clam')
        
    app = PublicDataApp(root)
    root.mainloop()
