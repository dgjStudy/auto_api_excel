import os
import json

HISTORY_FILE = ".api_history.json"

def load_history():
    """
    저장된 API 즐겨찾기/히스토리 항목 리스트를 불러옵니다.
    """
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_bookmark(name, sample_url, base_url, params):
    """
    새로운 API 항목을 즐겨찾기에 추가/저장합니다.
    """
    history = load_history()
    # 동일 이름이 있으면 덮어쓰기
    history = [item for item in history if item.get("name") != name]
    
    item = {
        "name": name,
        "sample_url": sample_url,
        "base_url": base_url,
        "params": params
    }
    history.insert(0, item)
    
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return True, "즐겨찾기에 성공적으로 저장되었습니다."
    except Exception as e:
        return False, f"저장 중 오류 발생: {e}"

def delete_bookmark(name):
    """
    지정한 이름의 즐겨찾기를 삭제합니다.
    """
    history = load_history()
    new_history = [item for item in history if item.get("name") != name]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(new_history, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
