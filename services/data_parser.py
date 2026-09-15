import json
import xmltodict
import pandas as pd

def detect_format(raw_text):
    """
    텍스트의 시작 구조를 감지하여 'json' 또는 'xml' 포맷을 반환합니다.
    """
    if not raw_text or not raw_text.strip():
        return "unknown"
        
    stripped = raw_text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return "json"
    elif stripped.startswith("<"):
        return "xml"
    else:
        return "unknown"

def _find_list_in_dict(obj):
    """
    딕셔너리 구조 내에서 리스트(배열)를 담고 있는 가장 깊고 큰 요소(반복 데이터)를 탐색합니다.
    """
    candidates = []
    
    def walk(curr_obj, current_path=""):
        if isinstance(curr_obj, list):
            if len(curr_obj) > 0 and isinstance(curr_obj[0], (dict, list, str, int, float)):
                candidates.append((current_path, curr_obj, len(curr_obj)))
        elif isinstance(curr_obj, dict):
            for key, val in curr_obj.items():
                new_path = f"{current_path}.{key}" if current_path else key
                walk(val, new_path)
                
    walk(obj)
    
    if not candidates:
        return None
        
    # 요소 개수가 가장 많은 리스트를 최우선 후보로 선택
    candidates.sort(key=lambda x: x[2], reverse=True)
    return candidates[0][1]

def flatten_to_dataframe(raw_text):
    """
    XML/JSON 텍스트 데이터를 자동으로 파싱하고 2차원 표(DataFrame) 형태로 평탄화(Flattening)합니다.
    """
    fmt = detect_format(raw_text)
    
    if fmt == "unknown":
        return None, "지원하지 않거나 유효하지 않은 데이터 포맷입니다 (XML/JSON 아님)."
        
    try:
        if fmt == "json":
            data_dict = json.loads(raw_text)
        else: # xml
            data_dict = xmltodict.parse(raw_text)
            
        # 단일 리스트 본문인 경우
        if isinstance(data_dict, list):
            df = pd.json_normalize(data_dict)
            return df, None
            
        # 딕셔너리 구조 내에서 리스트 노드 자동 탐색
        best_list = _find_list_in_dict(data_dict)
        
        if best_list is not None:
            df = pd.json_normalize(best_list)
            return df, None
        else:
            # 리스트 구조를 찾지 못했더라도 전체 딕셔너리를 평탄화 시도
            df = pd.json_normalize(data_dict)
            if not df.empty:
                return df, None
            return None, "응답 데이터 내에서 반복되는 데이터 목록(List/Item)을 찾지 못했습니다."
            
    except Exception as e:
        return None, f"데이터 파싱 및 평탄화 변환 중 오류 발생:\n{e}"
