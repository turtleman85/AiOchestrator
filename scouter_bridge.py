from mcp.server.fastmcp import FastMCP
import requests
import json

# 💡 스카우터 Web API 정보 세팅 (포트는 6180으로 찌릅니다)
SCOUTER_API_URL = "http://10.70.97.239:6180/scouter/v1"
AUTH = ('admin', 'admin') # 아이디, 비밀번호

# MCP 서버 객체 생성
mcp = FastMCP("Scouter-Bridge")

@mcp.tool()
def check_scouter_health() -> str:
    """스카우터 서버(10.70.97.239)와 정상적으로 HTTP 통신이 되는지 점검합니다."""
    try:
        res = requests.get(f"{SCOUTER_API_URL}/info/server", auth=AUTH, timeout=3)
        if res.status_code == 200:
            return f"✅ 스카우터 연결 성공! 서버 정보: {res.text}"
        else:
            return f"⚠️ 연결 실패 (HTTP {res.status_code}). 인증 정보나 권한을 확인하세요."
    except requests.exceptions.ConnectionError:
        return "🚨 연결 에러: 10.70.97.239 서버에 6180 포트(Web API)가 닫혀있거나 방화벽에 막혀있습니다."
    except Exception as e:
        return f"🚨 알 수 없는 에러: {str(e)}"

@mcp.tool()
def get_active_service() -> str:
    """현재 운영 서버의 실시간 액티브 서비스(요청을 처리 중인 쓰레드 현황)를 조회합니다."""
    try:
        res = requests.get(f"{SCOUTER_API_URL}/realtime/active-service", auth=AUTH, timeout=5)
        if res.status_code == 200:
            return json.dumps(res.json(), indent=2, ensure_ascii=False)
        return f"조회 실패 (HTTP {res.status_code})"
    except Exception as e:
        return f"에러 발생: {str(e)}"

if __name__ == "__main__":
    # Claude가 이 스크립트를 실행할 때 MCP 프로토콜로 통신하도록 구동
    mcp.run()