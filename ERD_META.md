# 프로젝트 핵심 ERD 메타 정보 & DB 연동 가이드

본 문서는 사내 가상 오피스 시스템에서 활용하는 핵심 데이터베이스 테이블 스키마 정보 및 로컬 클로드(Claude-CLI) 환경에서 MCP(Model Context Protocol)를 이용하여 Oracle DB에 직접 연결하는 방법에 대해 안내합니다.

---

## 📂 1. 데이터베이스 ERD 설계서 위치 및 목록

사내 DB 설계서 파일들은 아래 경로에 스프레드시트 형태로 상주하고 있으며, 오케스트레이션 엔진 가동 시 지라 이슈 및 사용자 요청 맥락에 부합하는 파일만 자동으로 추출하여 AI 지휘 허브(Context)로 주입됩니다.
* **디렉토리 경로**: `C:\Users\LEEJAEJUN\IdeaProjects\db_meta`

### 핵심 ERD 파일
1. **`고객_ERD.xlsx`**: 고객 가입 정보, 마일리지/자산, 동의이력 등 고객 관련 테이블 정의
2. **`SR_ERD.xlsx`**: 고객상담 및 서비스 요청(SR), 이관이력, 조치 평가 관련 테이블 정의
3. **`주문_ERD.xlsx`**: 상품 주문마스터, 아이템 상세 결제 정보, 정합성 검증 테이블 정의

---

## 📊 2. 핵심 테이블 상세 스키마

### 2.1. 고객마스터 (`CST_CUST_M`)
고객의 기본 인적 사항, 상태 및 임직원 할인 한도를 관리하는 기준 테이블입니다.

* **물리 테이블명**: `CST_CUST_M` (고객기본)
* **주요 컬럼 명세**:

| 컬럼명 | 한글 속성명 | 데이터타입 | 길이 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`CUST_NO`** | 고객번호 | NUMBER | 15.0 | **PK** | 고객 고유 식별 번호 |
| **`CUST_NM`** | 고객성명 | VARCHAR2 | 75.0 | Not Null | 고객의 한글/영어 성명 |
| **`CUST_ST_CD`** | 고객상태코드 | VARCHAR2 | 1.0 | Not Null | 고객 상태 (예: `Y` - 정상, `N` - 정지, `W` - 탈퇴) |
| **`SLF_CERT_YN`** | 본인인증여부 | VARCHAR2 | 1.0 | Not Null | 본인인증 통과 여부 (`Y`/`N`) |
| **`RLNM_CERT_YN`** | 실명인증여부 | VARCHAR2 | 1.0 | Not Null | 실명인증 통과 여부 (`Y`/`N`) |
| **`EMP_DC_LIMIT_AMT`** | 임직원할인한도금액 | NUMBER | 15.0 | - | 사내 임직원 대상 부여된 연간 할인 한도 |
| **`GS_TSHOP_MEM_YN`** | GS티샵회원여부 | VARCHAR2 | 1.0 | - | GS T-Shop 회원 연동 여부 |
| **`GSNPNT_ADM_YN`** | GS엔포인트가입여부 | VARCHAR2 | 1.0 | - | GS앤포인트 가입/연동 여부 |
| **`EC_MEM_YN`** | EC회원여부 | VARCHAR2 | 1.0 | - | 온라인 쇼핑몰 회원 여부 |
| **`EC_MEM_TYP_CD`** | EC회원유형코드 | VARCHAR2 | 1.0 | - | 회원 유형 분류 코드 (예: `2` - VIP 등) |
| **`SSNO_PRE7`** | 주민번호앞7자리 | VARCHAR2 | 7.0 | - | 생년월일 + 성별숫자 1자리 (예: `850430-1`) |
| **`CUST_EMAIL_ADDR`** | 고객이메일주소 | VARCHAR2 | 100.0 | - | 이메일 수신 주소 |
| **`CUST_REG_DTM`** | 고객등록일시 | DATE | - | Not Null | 최초 가입 등록 시간 |

---

### 2.2. 서비스 요청 마스터 (`SRV_SR_M`)
고객 상담, 불만 접수 및 시스템 기능 장애 접수(SR) 건을 관리하는 마스터 테이블입니다.

* **물리 테이블명**: `SRV_SR_M` (서비스요청기본)
* **주요 컬럼 명세**:

| 컬럼명 | 한글 속성명 | 데이터타입 | 길이 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`SR_NO`** | 서비스요청번호 | VARCHAR2 | 20.0 | **PK** | SR 고유 일련번호 |
| **`CUST_NO`** | 고객번호 | NUMBER | 15.0 | **FK** | `CST_CUST_M.CUST_NO` 연동 |
| **`ORD_NO`** | 주문번호 | NUMBER | 15.0 | **FK** | `ORD_ORD_M.ORD_NO` 연동 (필요 시) |
| **`SR_PROC_ST_CD`** | 요청처리상태코드 | VARCHAR2 | 4.0 | - | 접수/처리중/완료 등 상태 분류 |
| **`SR_CHANL_CD`** | 요청채널코드 | VARCHAR2 | 2.0 | - | 접수 인입 채널 (예: 모바일, 웹, 전화상담 등) |
| **`SR_RSN_LRG_CLS_CD`** | 요청사유대분류 | VARCHAR2 | 10.0 | - | SR 원인 대분류 코드 |
| **`SR_RSN_MID_CLS_CD`** | 요청사유중분류 | VARCHAR2 | 10.0 | - | SR 원인 중분류 코드 |
| **`SR_RSN_SML_CLS_CD`** | 요청사유소분류 | VARCHAR2 | 10.0 | - | SR 원인 소분류 코드 |
| **`ACP_SUMRY_CNTNT`** | 접수요약내용 | VARCHAR2 | 4000.0 | - | 인입된 요청의 한 줄 요약 정보 |
| **`ACP_DTM`** | 접수일시 | DATE | - | - | 접수 처리된 최초 일시 |
| **`ASIGNR_ID`** | 담당자ID | VARCHAR2 | 10.0 | Not Null | 현재 처리 전담 에이전트/사원 ID |

---

### 2.3. 주문 마스터 (`ORD_ORD_M`)
고객의 구매 결제 건별 마스터 로그 정보를 저장합니다.

* **물리 테이블명**: `ORD_ORD_M` (주문마스터)
* **주요 컬럼 명세**:

| 컬럼명 | 한글 속성명 | 데이터타입 | 길이 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ORD_NO`** | 주문번호 | NUMBER | 15.0 | **PK** | 주문 고유 번호 |
| **`CUST_NO`** | 고객번호 | NUMBER | 15.0 | **FK** | `CST_CUST_M.CUST_NO` 연동 |
| **`ORD_DTM`** | 주문일시 | DATE | - | Not Null | 최종 결제 시각 |
| **`ORD_TYP_CD`** | 주문유형코드 | VARCHAR2 | 20.0 | Not Null | 일반/특수/모바일 결제 유형 분류 |
| **`ST_CD`** | 상태코드 | VARCHAR2 | 4.0 | - | 주문 처리 상태 (결제대기/완료/배송중 등) |
| **`REP_PAY_MEAN_CD`** | 대표결제수단코드 | VARCHAR2 | 14.0 | - | 신용카드/현금/포인트 등 대표 수단 코드 |
| **`CARD_CNL_AMT_TOT`** | 카드취소금액총계 | NUMBER | 15.0 | - | 반품/취소 시 환불 처리된 신용카드 총액 |

---

### 2.4. 주문 아이템 상세 (`ORD_ITEM_D`)
하나의 주문 마스터 내에 속한 구매 상품들의 라인별 품목 정보를 보관합니다.

* **물리 테이블명**: `ORD_ITEM_D` (주문아이템상세)
* **주요 컬럼 명세**:

| 컬럼명 | 한글 속성명 | 데이터타입 | 길이 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ORD_ITEM_ID`** | 주문아이템ID | VARCHAR2 | 50.0 | **PK** | 개별 라인 품목 고유 식별자 |
| **`ORD_NO`** | 주문번호 | NUMBER | 15.0 | **FK** | `ORD_ORD_M.ORD_NO` 연동 |
| **`ORD_ITEM_NO`** | 주문아이템번호 | NUMBER | 10.0 | Not Null | 주문 건 내 순번 (1, 2, 3 등) |
| **`PRD_CD`** | 상품코드 | NUMBER | 15.0 | - | 물류 고유 상품 코드 |
| **`PRD_NM`** | 상품명 | VARCHAR2 | 45.0 | - | 노출 상품 명칭 |
| **`STD_UPRC`** | 표준단가 | NUMBER | 15.0 | - | 정상 소비자 권장 판매 단가 |
| **`LAST_UPRC`** | 최종단가 | NUMBER | 22.0 | - | 쿠폰/적립금/할인 등이 반영된 실 결제 행 단가 |
| **`ORD_QTY`** | 주문수량 | NUMBER | 15.0 | - | 구매 품목 수량 |
| **`DLVS_CO_CD`** | 택배회사코드 | VARCHAR2 | 2.0 | - | 배송에 연계된 택배회사 코드 |
| **`INV_NO`** | 송장번호 | VARCHAR2 | 30.0 | - | 운송장 식별 번호 |

---

## 🛠️ 3. Oracle DB MCP 연동 및 실제 데이터 조회 방법

현재 로컬의 클로드(Claude) 인터페이스는 **MCP Oracle DB 커넥터**와 바인딩되어 있습니다. 따라서 엑셀 메타 정보 확인을 넘어, 실제 DB에 즉시 쿼리를 수행해 리얼 데이터를 조회하고 검증할 수 있습니다.

### 3.1. DB 조회 명령 예시 (Claude-CLI 프롬프트용)

AI 도우미나 Claude에 직접 조회를 시킬 때는 다음과 같이 자연어로 지시하거나 쿼리를 명시적으로 제시할 수 있습니다.

#### 예제 1) 고객마스터에서 본인 계정 정보 및 직원 한도 조회
```sql
SELECT cust_no, cust_nm, SSNO_PRE7, emp_dc_limit_amt, cust_st_cd 
FROM CST_CUST_M 
WHERE cust_nm = '이재준';
```

#### 예제 2) 특정 주문 번호의 세부 상품 정보 및 단가 매칭 확인
```sql
SELECT b.ord_no, a.ord_item_id, a.prd_nm, a.last_uprc, a.ord_qty 
FROM ORD_ITEM_D a 
INNER JOIN ORD_ORD_M b ON a.ord_no = b.ord_no 
WHERE b.cust_no = 12345678;
```

#### 예제 3) 특정 담당자에게 배정된 미처리(접수/처리중) 서비스 요청 목록 조회
```sql
SELECT sr_no, acp_sumry_cntnt, sr_proc_st_cd, acp_dtm 
FROM SRV_SR_M 
WHERE asignr_id = 'agent_be1' 
  AND sr_proc_st_cd IN ('접수', '처리중')
ORDER BY acp_dtm DESC;
```

### 3.2. 보안 및 데이터 보호 주의사항
* **마스킹 데이터**: 주민등록번호 암호화값(`SSNO_ECP`) 및 주민등록번호 앞7자리값(`SSNO_PRE7`)을 다룰 때는 마스킹 정책을 준수해야 하며, 로그나 리포트에 무가공 복호화값이나 개인 식별 데이터(PII)를 원본 그대로 출력해서는 안 됩니다.
* **조회 최적화**: 대량 로그 테이블 조회 시 `ROWNUM <= 100` 등의 쿼리 필터를 걸어 버퍼 오버플로우와 API 토큰 예산 낭비를 미연에 방지해 주십시오.
