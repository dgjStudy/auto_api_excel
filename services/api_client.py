import urllib.parse
import requests

def parse_sample_url(sample_url):
    """
    샘플 URL 문자열을 입력받아 Base URL과 쿼리 파라미터 딕셔너리로 분리합니다.
    """
    if not sample_url or not sample_url.strip():
        return "", {}
        
    sample_url = sample_url.strip()
    
    # URL 이외에 개행 등이 섞여있는 경우 처리
    if "\n" in sample_url:
        sample_url = sample_url.split("\n")[0].strip()
        
    parsed = urllib.parse.urlparse(sample_url)
    base_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    
    # 쿼리 파라미터 추출 (parse_qs는 리스트로 반환하므로 단일 값 추출 처리)
    raw_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    params = {}
    for k, v in raw_params.items():
        if v:
            # serviceKey 등 인코딩된 문자열을 안전하게 unquote 처리
            params[k] = urllib.parse.unquote(v[0])
        else:
            params[k] = ""
            
    return base_url, params

def fetch_api_data(base_url, params, headers=None):
    """
    Base URL과 쿼리 파라미터 딕셔너리를 사용하여 REST API를 호출합니다.
    """
    if not base_url:
        return None, "오류: Base API URL이 필요합니다."
        
    # serviceKey가 전달된 경우 2중 인코딩 방지를 위해 unquote 보장
    cleaned_params = {}
    for k, v in params.items():
        if k == "serviceKey":
            cleaned_params[k] = urllib.parse.unquote(str(v))
        else:
            cleaned_params[k] = str(v)
            
    try:
        response = requests.get(base_url, params=cleaned_params, headers=headers, timeout=15)
        if response.status_code != 200:
            return None, f"API 요청 실패 (HTTP {response.status_code}):\n{response.text[:500]}"
        return response.text, None
    except requests.exceptions.RequestException as e:
        return None, f"API 호출 중 네트워크 예외 발생:\n{e}"

def fetch_all_pages(base_url, params, total_count, num_of_rows=10, max_pages=50, progress_callback=None):
    """
    totalCount 기반으로 전체 페이지 데이터를 순차 호출하여 텍스트 리스트로 수집합니다.
    """
    import math
    page_key = "pageNo"
    for k in params.keys():
        if k.lower() in ["pageno", "page", "pageindex"]:
            page_key = k
            break
            
    rows_key = "numOfRows"
    for k in params.keys():
        if k.lower() in ["numofrows", "rows", "pagesize", "display"]:
            rows_key = k
            break
            
    total_pages = math.ceil(total_count / float(num_of_rows))
    actual_pages = min(total_pages, max_pages)
    
    raw_responses = []
    
    for current_p in range(1, actual_pages + 1):
        if progress_callback:
            progress_callback(current_p, actual_pages)
            
        page_params = params.copy()
        page_params[page_key] = str(current_p)
        page_params[rows_key] = str(num_of_rows)
        
        raw_text, err = fetch_api_data(base_url, page_params)
        if err:
            break
        if raw_text:
            raw_responses.append(raw_text)
            
    return raw_responses, None

