from mcp.server.fastmcp import FastMCP
import requests
import json
import urllib3
import urllib.parse

# SSL 인증서 경고 무시 (사내망/VPC 엔드포인트용)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# OpenSearch 설정
OPENSEARCH_URL = "https://vpc-smtc-prd-logs-es-csobbph4l2jljuk6ngjcr4bwfq.ap-northeast-2.es.amazonaws.com"
AUTH = ("smtcviewer", "smtcViewer123$")

mcp = FastMCP("OpenSearch-Monitoring")

@mcp.tool()
def search_opensearch_logs(query_string: str = "*", index: str = "smtc-backend-*", size: int = 20, from_time: str = "now-1h", to_time: str = "now") -> str:
    """
    OpenSearch에서 에러 로그나 특정 조건의 로그를 검색합니다.
    - query_string: 검색어 (예: 'level:ERROR AND message:NullPointer*', 'url:"/api/v1/users"')
    - index: 검색할 인덱스 (기본값: 'smtc-backend-*')
    - size: 가져올 최대 로그 수
    - from_time: 검색 시작 시간 (예: 'now-1h', 'now-1d')
    - to_time: 검색 종료 시간 (예: 'now')
    """
    url = f"{OPENSEARCH_URL}/{index}/_search"
    headers = {"Content-Type": "application/json"}
    
    # 쿼리 페이로드
    payload = {
        "size": size,
        "query": {
            "bool": {
                "must": [
                    {"query_string": {"query": query_string}}
                ],
                "filter": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte": from_time,
                                "lte": to_time
                            }
                        }
                    }
                ]
            }
        },
        "sort": [
            {"@timestamp": {"order": "desc"}}
        ]
    }
    
    try:
        res = requests.get(url, headers=headers, auth=AUTH, json=payload, verify=False, timeout=15)
        if res.status_code == 200:
            data = res.json()
            hits = data.get("hits", {}).get("hits", [])
            
            if not hits:
                return f"✅ '{query_string}' 조건에 맞는 오픈서치 로그가 없습니다."
                
            results = []
            for hit in hits:
                source = hit.get("_source", {})
                timestamp = source.get("@timestamp") or source.get("log_time") or "N/A"
                level = source.get("level", "N/A")
                message = source.get("message", "No message")
                pod = source.get("k8s.pod.name", "UnknownPod")
                results.append(f"[{timestamp}] [{level}] [{pod}] {message}")
                
            # 대시보드 바로가기 URL 생성 (Kibana/OpenSearch Dashboards 문법 적용)
            encoded_query = urllib.parse.quote(query_string)
            # indexPattern은 annapurna 예시 UUID(a66364e0-4251-11ee-93e6-a90b1b8affa4)를 기본값으로 사용
            dashboard_url = (
                f"https://vpc-smtc-prd-logs-es-csobbph4l2jljuk6ngjcr4bwfq.ap-northeast-2.es.amazonaws.com"
                f"/_dashboards/app/data-explorer/discover#?_a=(discover:(columns:!(_source),isDirty:!f,sort:!()),"
                f"metadata:(indexPattern:a66364e0-4251-11ee-93e6-a90b1b8affa4,view:discover))"
                f"&_g=(filters:!(),refreshInterval:(pause:!t,value:0),time:(from:'{from_time}',to:'{to_time}'))"
                f"&_q=(filters:!(),query:(language:kuery,query:'{encoded_query}'))"
            )
            
            return f"✅ [OpenSearch 로그 검색 결과 ({len(hits)}건)]\n" + "\n".join(results) + f"\n\n🔗 [OpenSearch Dashboards에서 바로보기]({dashboard_url})"
        else:
            return f"⚠️ OpenSearch 요청 실패 (HTTP {res.status_code}): {res.text}"
    except Exception as e:
        return f"🚨 OpenSearch 연결 에러: {str(e)}"

if __name__ == "__main__":
    mcp.run()
