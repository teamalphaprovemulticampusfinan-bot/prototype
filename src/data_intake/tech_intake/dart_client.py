# src/data_intake/tech_intake/dart_client.py

import logging
import time
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
from typing import Dict, List, Optional

import requests

from .config import (
    DART_API_KEY,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    SLEEP_SECONDS,
)

logger = logging.getLogger(__name__)


class DartClient:
    """OpenDART API 호출용 클라이언트"""

    BASE_URL = "https://opendart.fss.or.kr/api"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or DART_API_KEY
        self._corp_cache: Optional[List[Dict[str, str]]] = None  # 캐싱

    # ------------------------------------------------------------------
    # 내부 공통 요청 메서드
    # ------------------------------------------------------------------

    def _get(self, endpoint: str, params: Dict) -> Dict:
        """DART JSON API 공통 GET 요청 (재시도 포함)"""

        url = f"{self.BASE_URL}/{endpoint}"
        params = {"crtfc_key": self.api_key, **params}
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()

                data = response.json()
                status = data.get("status")

                if status not in (None, "000"):
                    raise RuntimeError(
                        f"DART API 오류: status={status}, message={data.get('message')}"
                    )

                return data

            except Exception as e:
                last_error = e
                logger.warning("DART _get 재시도 %d/%d — %s", attempt, MAX_RETRIES, e)
                time.sleep(SLEEP_SECONDS)

        raise RuntimeError(f"DART API 요청 실패 ({MAX_RETRIES}회 시도): {last_error}")

    def _get_zip(self, endpoint: str, params: Dict) -> bytes:
        """ZIP 파일 반환 엔드포인트 공통 GET 요청 (재시도 포함)"""

        url = f"{self.BASE_URL}/{endpoint}"
        params = {"crtfc_key": self.api_key, **params}
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                return response.content

            except Exception as e:
                last_error = e
                logger.warning("DART _get_zip 재시도 %d/%d — %s", attempt, MAX_RETRIES, e)
                time.sleep(SLEEP_SECONDS)

        raise RuntimeError(f"DART ZIP 요청 실패 ({MAX_RETRIES}회 시도): {last_error}")

    # ------------------------------------------------------------------
    # 기업 코드
    # ------------------------------------------------------------------

    def get_corp_codes(self, force_refresh: bool = False) -> List[Dict[str, str]]:
        """
        DART 고유번호 목록 조회 (캐싱 적용)

        반환 예:
        [
            {
                "corp_code": "00126380",
                "corp_name": "삼성전자",
                "stock_code": "005930",
                "modify_date": "20240101"
            }
        ]
        """

        if self._corp_cache is not None and not force_refresh:
            return self._corp_cache

        content = self._get_zip("corpCode.xml", {})

        with zipfile.ZipFile(BytesIO(content)) as zf:
            xml_data = zf.read(zf.namelist()[0])

        root = ET.fromstring(xml_data)

        self._corp_cache = [
            {
                "corp_code": item.findtext("corp_code"),
                "corp_name": item.findtext("corp_name"),
                "stock_code": item.findtext("stock_code"),
                "modify_date": item.findtext("modify_date"),
            }
            for item in root.findall("list")
        ]

        logger.info("corp_codes 로드 완료: %d건", len(self._corp_cache))
        return self._corp_cache

    def find_corp_code(
        self,
        company_name: Optional[str] = None,
        stock_code: Optional[str] = None,
    ) -> Optional[str]:
        """기업명 또는 종목코드로 DART corp_code 찾기"""

        if not company_name and not stock_code:
            raise ValueError("company_name 또는 stock_code 중 하나는 필수입니다.")

        for corp in self.get_corp_codes():
            if stock_code and corp.get("stock_code") == stock_code:
                return corp.get("corp_code")
            if company_name and corp.get("corp_name") == company_name:
                return corp.get("corp_code")

        logger.warning("corp_code 조회 실패 — company_name=%s, stock_code=%s", company_name, stock_code)
        return None

    # ------------------------------------------------------------------
    # 공시 목록
    # ------------------------------------------------------------------

    def get_disclosure_list(
        self,
        corp_code: str,
        bgn_de: str,
        end_de: Optional[str] = None,
        page_no: int = 1,
        page_count: int = 100,
        pblntf_ty: Optional[str] = "A",
    ) -> List[Dict]:
        """
        공시 목록 조회

        pblntf_ty:
            A = 정기공시
            B = 주요사항보고
            C = 발행공시
            D = 지분공시
            E = 기타공시
        """

        params: Dict = {
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "page_no": page_no,
            "page_count": page_count,
        }

        if end_de:
            params["end_de"] = end_de
        if pblntf_ty:
            params["pblntf_ty"] = pblntf_ty

        data = self._get("list.json", params)
        return data.get("list", [])

    def get_business_reports(
        self,
        corp_code: str,
        bgn_de: str,
        end_de: Optional[str] = None,
    ) -> List[Dict]:
        """사업보고서만 필터링"""

        disclosures = self.get_disclosure_list(
            corp_code=corp_code,
            bgn_de=bgn_de,
            end_de=end_de,
            pblntf_ty="A",
        )

        return [
            item for item in disclosures
            if "사업보고서" in item.get("report_nm", "")
        ]

    # ------------------------------------------------------------------
    # 공시 원문
    # ------------------------------------------------------------------

    def get_document_xml(self, rcept_no: str) -> str:
        """
        공시서류 원문 XML 다운로드 (ZIP 압축 해제 포함)
        """

        content = self._get_zip("document.xml", {"rcept_no": rcept_no})

        # ZIP 압축 해제 후 첫 번째 파일 텍스트 반환
        with zipfile.ZipFile(BytesIO(content)) as zf:
            # 파일 목록 확인 후 .xml 파일만 추출
            xml_files = [f for f in zf.namelist() if f.endswith(".xml")]

            if not xml_files:
                raise RuntimeError(f"ZIP 내 XML 파일 없음 — rcept_no={rcept_no}")

            # 가장 큰 XML 파일 선택 (본문일 가능성 높음)
            target = max(xml_files, key=lambda f: zf.getinfo(f).file_size)
            xml_bytes = zf.read(target)

        return xml_bytes.decode("utf-8", errors="replace")