import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def save_styled_excel(df, file_path, column_mapping=None):
    """
    Pandas DataFrame을 openpyxl 서식을 적용하여 엑셀 파일로 저장합니다.
    - column_mapping: {영문컬럼: 한글컬럼} 딕셔너리 (옵션)
    - 헤더 셀 스타일(다크 블루 배경, 흰색 볼드 글씨, 중앙 정렬)
    - 틀 고정 (Freeze Panes: 첫 번째 행)
    - 열 너비 자동 맞춤 (Auto-fit Column Width)
    """
    export_df = df.copy()
    
    # 1. 컬럼 매핑 적용 (한글 컬럼명 변환)
    if column_mapping:
        export_df.rename(columns=column_mapping, inplace=True)
        
    # 2. openpyxl Workbook 생성 및 데이터 쓰기
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "API_Data"
    
    # Gridlines 보이기 설정
    ws.views.sheetView[0].showGridLines = True
    
    # 헤더 작성
    headers = list(export_df.columns)
    ws.append(headers)
    
    # 데이터 행 작성
    for row in export_df.itertuples(index=False):
        ws.append(list(row))
        
    # 3. 스타일 정의
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid") # Dark Slate Gray
    header_font = Font(name="맑은 고딕", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="맑은 고딕", size=10)
    
    thin_border = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB')
    )
    
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # 4. 헤더 서식 적용 및 행 높이 설정
    ws.row_dimensions[1].height = 28
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = thin_border
        
    # 5. 데이터 셀 서식 및 테두리 적용
    for row_num in range(2, len(export_df) + 2):
        ws.row_dimensions[row_num].height = 20
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=row_num, column=col_num)
            cell.font = data_font
            cell.border = thin_border
            # 수치 데이터 정렬 (숫자면 우측 정렬)
            if isinstance(cell.value, (int, float)):
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
    # 6. 틀 고정 (Freeze Panes - 헤더행 고정)
    ws.freeze_panes = "A2"
    
    # 7. 열 너비 자동 조절 (Auto-fit)
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            # 한글 글자 유니코드 고려 길이 계산 (한글/전각 문자는 약 1.8배 폭)
            length = sum(2 if ord(char) > 128 else 1 for char in val_str)
            if length > max_len:
                max_len = length
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)
        
    wb.save(file_path)
