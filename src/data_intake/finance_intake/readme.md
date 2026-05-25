# finance_intake

금융 데이터 수집/정규화/검증 파이프라인

KIND 투자경고, DART 재무제표, 주가 및 수급 데이터를 수집하여 CSV 형태로 저장하는 데이터 파이프라인입니다.

---

# 프로젝트 구조

```text
team-a/
│
├─ data/
│  ├─ _global_common/
│  │  └─ warning_data.csv
│  └─ {섹터}/
│     └─ {기업명}/
│        └─ finance/
│           ├─ {기업명}_재무데이터.csv
│           └─ {기업명}_stock.csv
│
├─ src/
│  └─ data_intake/
│     └─ finance_intake/
│        ├─ runner.py
│        ├─ collector.py
│        ├─ normalizer.py
│        ├─ validator.py
│        ├─ schemas.py
│        ├─ corp_codes.csv
│        ├─ rnd.csv
│        ├─ shares.csv
│        └─ finance_intake.readme.md
│
└─ .venv/
```

---

# 주요 기능

## 1. warning

KIND 투자경고/위험/주의 종목 수집

수집 항목:

* 회사명
* 종목코드
* 구분
* 지정일
* 해제일
* 비고

저장 위치:

```text
data/_global_common/
```

---

## 2. financial

DART 재무제표 데이터 수집

수집 항목:

* 매출액
* 영업이익
* 순이익
* 자산총계
* 부채총계
* 자본총계
* CAPEX
* OCF
* FCF
* 이자비용
* R&D
* 무형자산상각비

계산 지표:

* ROE
* 영업이익률
* 부채비율
* 이자보상배율

저장 위치:

```text
data/{섹터}/{기업명}/finance/
```

---

## 3. stock

주가 / 시장 / 수급 데이터 수집

수집 항목:

* OHLCV
* 수익률
* 시장수익률
* 이상수익률
* CAR
* MDD
* 이동평균
* EPS
* PSR
* VIX
* VKOSPI
* 기관 수급
* 외국인 수급

저장 위치:

```text
data/{섹터}/{기업명}/finance/
```

---

# 실행 환경

* Python 3.11+
* Windows PowerShell
* VSCode

---

# 실행 방법

## 1. 프로젝트 루트 이동

```powershell
cd C:\Users\smile\team-a
```

---

## 2. 가상환경 활성화

```powershell
.venv\Scripts\activate
```

정상 예시:

```text
(.venv) PS C:\Users\smile\team-a>
```

---

## 3. 필수 라이브러리 설치

```powershell
pip install pandas numpy requests yfinance beautifulsoup4 lxml python-dotenv openpyxl xlrd
```

warning 모드 사용 시:

```powershell
pip install selenium webdriver-manager
```

---

## 4. DART API KEY 설정

`src/.env`

```env
DART_API_KEY=발급받은키
```

발급 사이트:

https://opendart.fss.or.kr/

---

# 실행 명령어

## warning 실행

```powershell
python -m src.data_intake.finance_intake.runner --mode warning
```

---

## stock 실행

삼성전자:

```powershell
python -m src.data_intake.finance_intake.runner --mode stock --stock 005930 --sector 반도체
```

카카오:

```powershell
python -m src.data_intake.finance_intake.runner --mode stock --stock 035720 --sector IT
```

---

## financial 실행

```powershell
python -m src.data_intake.finance_intake.runner --mode financial --stock 005930 --sector 반도체
```

---

## 전체 실행

```powershell
python -m src.data_intake.finance_intake.runner --mode all --stock 005930 --sector 반도체
```

---

# 여러 종목 일괄 실행

`schemas.py`

```python
STOCK_CODES = [
    "000990",  # DB하이텍
    "102710",  # ENF테크놀로지
    "083450",  # GST
    "095340",  # ISC
    "108320",  # LX세미콘
    "036540",  # SFA반도체
    "399720",  # 가온칩스
    "033640",  # 네패스
    "348210",  # 넥스틴
    "213420",  # 덕산네오룩스
    "005290",  # 동진쎄미켐
    "131970",  # 두산테스나
    "187220",  # 디티앤씨
    "058470",  # 리노공업
    "059090",  # 미코
    "357780",  # 솔브레인
    "092600",  # 앤씨앤
    "102120",  # 어보브반도체
    "039440",  # 에스티아이
    "170920",  # 엘티씨
    "240810",  # 원익IPS
    "104830",  # 원익머트리얼즈
    "101160",  # 월덱스
    "084370",  # 유진테크
    "080220",  # 제주반도체
    "114570",  # 지스마트글로벌
    "045970",  # 코아시아
    "064760",  # 티씨케이
    "054450",  # 텔레칩스
    "319660",  # 피에스케이
    "042700",  # 한미반도체
    "014680",  # 한솔케미칼
]
```

실행 (--sector 필수):

```powershell
python -m src.data_intake.finance_intake.runner --mode all --sector 반도체
```

---

# 데이터 흐름

```text
collect
  ↓
normalize
  ↓
validate
  ↓
save
```

---

# 주요 모듈 설명

## collector.py

외부 API / yfinance / DART / 네이버 금융 데이터 수집

---

## normalizer.py

원시 데이터 정규화 및 파생지표 계산

---

## validator.py

데이터 검증

* 결측치
* 중복
* 이상값

---

## schemas.py

* 설정값
* 경로
* dataclass
* 컬럼 정의

---

## runner.py

CLI 실행 진입점

---

# corp_codes.csv

예시:

```csv
stock_code,corp_code,corp_name
005930,00126380,삼성전자
035420,00266961,NAVER
```

---

# shares.csv

EPS / PSR fallback용 발행주식수

```csv
stock_code,shares
005930,5969782550
035420,164263395
```

---

# 실행 결과 예시

정상 실행 시:

```text
[stock] 저장 완료:
[financial] 저장 완료:
[warning] 저장 완료:
```

출력됩니다.

---

# 자주 발생하는 오류

## ModuleNotFoundError

원인:

* collector.py 없음
* normalizer.py 없음
* schemas.py 없음

해결:

```powershell
Remove-Item -Recurse -Force .\src\data_intake\finance_intake\__pycache__
```

---

## DART_API_KEY 없음

원인:

`.env` 파일 미설정

해결:

```env
DART_API_KEY=발급키
```

---

## EPS 전체 NaN

원인:

* 발행주식수 조회 실패
* shares.csv 없음

---

## yfinance 조회 실패

원인:

* ticker 없음
* 네트워크 문제
* 상장폐지

---

# 추천 개선사항

* logging 적용
* retry/backoff 적용
* parquet 저장
* Airflow 스케줄링
* Docker 컨테이너화
* pytest 테스트 코드
* config.yaml 분리