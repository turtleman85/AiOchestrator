from mcp.server.fastmcp import FastMCP
import requests
import json
import os

# 💡 Datadog API 정보 세팅 (사용자가 입력해야 함)
# TODO: 여기에 실제 API KEY와 APP KEY를 입력하세요!
DATADOG_API_KEY = os.environ.get("DATADOG_API_KEY", "여기에_데이터독_API_KEY_입력")
DATADOG_APP_KEY = os.environ.get("DATADOG_APP_KEY", "여기에_데이터독_APP_KEY_입력")
# GS리테일 데이터독 호스트 (필요시 us5.datadoghq.com 등으로 변경)
DATADOG_SITE = os.environ.get("DATADOG_SITE", "datadoghq.com") 

mcp = FastMCP("Datadog-Monitoring")

@mcp.tool()
def search_datadog_logs(query: str, from_time: str = "now-1h", to_time: str = "now", limit: int = 20) -> str:
    """
    데이터독(Datadog)에서 특정 시간대의 로그를 검색합니다.
    - query: 검색어 (예: 'service:annapurna @http.status_code:500')
    - from_time: 검색 시작 시간 (예: 'now-1h', 'now-15m', '2023-10-01T10:00:00Z')
    - to_time: 검색 종료 시간 (예: 'now')
    - limit: 가져올 최대 로그 수
    """
    url = f"https://api.{DATADOG_SITE}/api/v2/logs/events/search"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "DD-API-KEY": DATADOG_API_KEY,
        "DD-APPLICATION-KEY": DATADOG_APP_KEY
    }
    payload = {
        "filter": {
            "query": query,
            "from": from_time,
            "to": to_time
        },
        "page": {
            "limit": limit
        }
    }
    
    try:
        if DATADOG_API_KEY == "여기에_데이터독_API_KEY_입력":
            return "🚨 [Error] Datadog API Key가 설정되지 않았습니다. mcp_monitoring_server.py 파일에 키를 입력해주세요."
            
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if not data.get("data"):
                return "✅ 해당 조건에 맞는 데이터독 로그가 없습니다."
            
            # 로그 데이터를 보기 좋게 요약
            results = []
            for item in data["data"]:
                attr = item.get("attributes", {})
                timestamp = attr.get("timestamp")
                message = attr.get("message")
                service = attr.get("service")
                status = attr.get("status")
                results.append(f"[{timestamp}] [{service}] [{status}] {message}")
                
            return "✅ [데이터독 로그 검색 결과]\n" + "\n".join(results)
        else:
            return f"⚠️ Datadog API 요청 실패 (HTTP {res.status_code}): {res.text}"
    except Exception as e:
        return f"🚨 Datadog 연결 에러: {str(e)}"

if __name__ == "__main__":
    # Claude가 이 스크립트를 실행할 때 MCP 프로토콜로 통신하도록 구동
    mcp.run()
