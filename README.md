# [프로젝트명] - API 데이터 수집 및 시각화 툴

## 📝 프로젝트 개요
API 데이터를 수집하고 엑셀 파일로 변환 및 차트로 시각화 하는 데스크톱 자동화 프로그램입니다.

## 🛠 기술 스택
- **Language:** Python 3.12
- **GUI Framework:** `customtkinter` (Modern Dark/Light UI)
- **Data Processing & Parsing:** `pandas`, `requests`, `xmltodict`
- **Excel Export:** `openpyxl`
- **Utilities:** `python-dotenv`
- **Packaging:** `pyinstaller`

## 🚀 설치 및 사용 방법
1. 우측 **[Releases]** 탭에서 최신 버전의 `main.exe` 파일을 다운로드합니다.
2. 다운로드한 `main.exe`를 실행합니다.
3. 공공데이터 포털에서 사용 신청한 API의 **샘플 URL**을 API 주소 입력란에 입력한 후, URL 분석 버튼을 눌러 파라미터를 적절히 수정한 후 '데이터 수집' 버튼을 눌러 수집합니다.
