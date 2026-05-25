# src/market_agent/dart_parser.py
from __future__ import annotations
import io
import json
import re
import time
import zipfile
import os  # ← 추가

import requests
from openai import OpenAI

# 변경
from .config import DART_API_KEY, NVIDIA_PARALLEL_API_KEY, NVIDIA_PARALLEL_BASE_URL, NVIDIA_PARALLEL_MODEL, TICKERS

_DART_API_KEY   = os.getenv("DART_LLM_API_KEY") or NVIDIA_PARALLEL_API_KEY
_DART_BASE_URL  = os.getenv("DART_LLM_BASE_URL") or NVIDIA_PARALLEL_BASE_URL
_DART_MODEL     = os.getenv("DART_LLM_MODEL")    or NVIDIA_PARALLEL_MODEL

client = OpenAI(api_key=_DART_API_KEY, base_url=_DART_BASE_URL)

EXTRACT_PROMPT = """

[기업별 vc_role 정답표 - 반드시 이 표를 최우선으로 사용하세요]
아래 기업명이 사업보고서에 등장하면 반드시 지정된 vc_role을 선택하세요.

네패스 → 후공정/패키징/테스트
한미반도체 → 후공정/패키징/테스트
한솔케미칼 → 소재
덕산테코피아 → 소재
엘티씨 → 소재
DB하이텍 → IDM/제조/메모리
미코 → IDM/제조/메모리
LX세미콘 → 팹리스/설계
제주반도체 → 팹리스/설계
어보브반도체 → 팹리스/MCU
텔레칩스 → 팹리스/설계
코아시아 → 팹리스/설계
가온칩스 → 팹리스/설계
원익IPS → 장비
유진테크 → 장비
피에스케이 → 장비
테스 → 장비
GST → 장비
에스티아이 → 장비
넥스틴 → 장비
솔브레인 → 소재
동진쎄미켐 → 소재
원익머트리얼즈 → 소재
이엔에프테크놀로지 → 소재
티씨케이 → 소재
월덱스 → 소재
ISC → 후공정/패키징/테스트
SFA반도체 → 후공정/패키징/테스트
두산테스나 → 후공정/패키징/테스트
리노공업 → 후공정/패키징/테스트

당신은 반도체 산업 분석가입니다.
아래 사업보고서 텍스트에서 정보를 추출해 JSON만 반환하세요.

[vc_role 분류 규칙 - 반드시 준수]
1. 반드시 아래 보기 중 정확히 하나만 선택하세요. 보기 외 다른 값은 절대 사용 금지.
2. 사업보고서 첫 문장, 사업 개요, 핵심 제품명에 나온 단어를 최우선 근거로 사용하세요.
3. "설계"와 "제조" 둘 다 나오면 자체 공장(fab) 유무로 판단하세요. 자체 fab 있으면 "파운드리/제조", 없으면 팹리스 계열로 선택하세요.
4. 사업보고서에 명시된 객관적 키워드만 근거로 사용하세요. 추측 금지.
5. 첫 번째 판단을 최종으로 하세요. 한번 결정한 분류는 절대 바꾸지 마세요.

[판단 기준]
direct_flag:
- Y: 직접 제품/장비/소재 매출 있음
- N: 기술이전·라이선스 중심

platform_flag:
- Y: 기술플랫폼·라이선스가 핵심
- N: 제조·생산설비가 핵심

vc_role 선택:
- "후공정 장비"
- "전공정 소재"
- "후공정 패키징"
- "반도체 소재"
- "장비+소재 복합"

{{
  "vc_role": "위 보기 중 선택",
  "direct_flag": "Y 또는 N",
  "platform_flag": "Y 또는 N",
  "domestic_peers": "국내 경쟁사 (없으면 null)",
  "global_peers": "글로벌 경쟁사 (없으면 null)",
  "competition_intensity": "높음 또는 중간 또는 낮음",
  "differentiation": "핵심 차별화 1~2문장",
  "confidence": "high 또는 medium 또는 low",
  "evidence_summary": "판단 근거 1문장"
}}


텍스트에 없으면 null, 추측 금지.
사업보고서: {text}
"""


def get_corp_codes() -> dict:
    import xml.etree.ElementTree as ET
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={DART_API_KEY}"
    res = requests.get(url)
    zf  = zipfile.ZipFile(io.BytesIO(res.content))
    xml_data = zf.read("CORPCODE.xml").decode("utf-8")
    root = ET.fromstring(xml_data)

    # 종목코드에서 .KQ/.KS 제거
    stock_codes = {v.split(".")[0] for v in TICKERS.values()}

    mapping = {}
    for corp in root.findall("list"):
        stock_code = corp.findtext("stock_code", "").strip()
        corp_code  = corp.findtext("corp_code",  "").strip()
        if stock_code in stock_codes:
            mapping[stock_code] = corp_code

    print(f"✅ corp_code 매핑: {mapping}")
    return mapping


def get_report(corp_code: str, year: int = 2024) -> dict | None:
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code":  corp_code,
        "bgn_de":     f"{year}0101",
        "end_de":     f"{year}1231",
        "pblntf_ty":  "A",
        "page_count": 5,
    }
    res = requests.get(url, params=params).json()
    if res.get("status") != "000" or not res.get("list"):
        print(f"  보고서 없음: {corp_code} {year}년")
        return None
    return {"rcept_no": res["list"][0]["rcept_no"]}


def extract_text(rcept_no: str) -> str:
    url    = "https://opendart.fss.or.kr/api/document.xml"
    params = {"crtfc_key": DART_API_KEY, "rcept_no": rcept_no}
    res    = requests.get(url, params=params)
    zf     = zipfile.ZipFile(io.BytesIO(res.content))
    xml_files = [f for f in zf.namelist() if f.endswith(".xml")]
    biggest   = max(xml_files, key=lambda f: zf.getinfo(f).file_size)
    raw  = zf.read(biggest).decode("utf-8", errors="ignore")
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    total = len(text)
    return text[:6000] + "\n\n[중략]\n\n" + text[total//4: total//4 + 6000]


def extract_features(company_name: str, text: str) -> dict:
    try:
        response = client.chat.completions.create(
            model=_DART_MODEL,
            messages=[{"role": "user", "content": EXTRACT_PROMPT.format(text=text)}],
            max_tokens=1000,
        )
        raw = response.choices[0].message.content
        if not raw:
            raise ValueError("LLM 응답 비어있음")
        raw = raw.strip()
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            cleaned = raw.replace("```json", "").replace("```", "").strip()
            result  = json.loads(cleaned)

    except Exception as e:
        print(f"  ⚠️ LLM 오류 ({e}) → 기본값 반환")
        result = {
            "vc_role":               "미분류",
            "direct_flag":           "N",
            "platform_flag":         "N",
            "domestic_peers":        None,
            "global_peers":          None,
            "competition_intensity": "중간",
            "differentiation":       None,
            "confidence":            "low",
            "evidence_summary":      f"LLM 오류: {e}",
        }

    result["company_name"] = company_name
    for k, v in result.items():
        if isinstance(v, list):
            result[k] = ", ".join(str(i) for i in v)
    return result


def run_dart_parser(companies: dict, corp_code_map: dict) -> list[dict]:
    results = []
    for company_name, ticker in companies.items():
        print(f"\n{'='*40}")
        print(f"처리 중: {company_name}")
        stock_code = ticker.split(".")[0]
        corp_code  = corp_code_map.get(stock_code)
        if not corp_code:
            print(f"  ❌ corp_code 없음")
            continue
        report = get_report(corp_code, 2024)
        if not report:
            continue
        text     = extract_text(report["rcept_no"])
        features = extract_features(company_name, text)
        features["rcept_no"]   = report["rcept_no"]
        features["updated_at"] = __import__("datetime").datetime.now().isoformat()
        results.append(features)

        flag = "⚠️" if features.get("confidence") == "low" else "✅"
        print(f"  {flag} confidence = {features.get('confidence')}")
        print(f"  vc_role     : {features.get('vc_role')}")
        time.sleep(1)

    return results