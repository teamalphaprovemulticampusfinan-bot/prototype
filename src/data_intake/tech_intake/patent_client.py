# src/data_intake/tech_intake/patent_client.py

import logging
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

import requests

from .config import (
    KIPRIS_API_KEY,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    SLEEP_SECONDS,
)

logger = logging.getLogger(__name__)


class PatentClient:
    """
    KIPRIS Open API 호출용 클라이언트

    수집 대상:
    - 등록 특허 수
    - 청구항 / 초록 텍스트 (키워드 추출용)
    - IPC 분류
    - 존속기간
    """

    BASE_URL = "http://plus.kipris.or.kr/kipo-api/kipi"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or KIPRIS_API_KEY
        if not self.api_key:
            raise ValueError("KIPRIS_API_KEY가 설정되지 않았습니다.")

    # ------------------------------------------------------------------
    # 내부 공통 요청
    # ------------------------------------------------------------------

    def _get(self, endpoint: str, params: Dict) -> ET.Element:
        """KIPRIS XML API 공통 GET 요청 (재시도 포함)"""

        url = f"{self.BASE_URL}/{endpoint}"
        params = {"accessKey": self.api_key, **params}
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                root = ET.fromstring(response.content)
                self._check_error(root)
                return root

            except Exception as e:
                last_error = e
                logger.warning(
                    "KIPRIS 재시도 %d/%d — %s | %s", attempt, MAX_RETRIES, endpoint, e
                )
                time.sleep(SLEEP_SECONDS)

        raise RuntimeError(
            f"KIPRIS API 요청 실패 ({MAX_RETRIES}회 시도): {endpoint} — {last_error}"
        )

    def _check_error(self, root: ET.Element) -> None:
        """KIPRIS 응답 내 오류 코드 확인"""

        error = root.findtext(".//error/errorCode")
        if error and error != "00":
            message = root.findtext(".//error/errorMessage", "")
            raise RuntimeError(f"KIPRIS API 오류: code={error}, message={message}")

    # ------------------------------------------------------------------
    # 특허 검색
    # ------------------------------------------------------------------

    def search_patents(
        self,
        applicant: str,
        registered_only: bool = True,
        page_no: int = 1,
        page_count: int = 500,
    ) -> List[Dict]:
        """
        출원인 기업명으로 특허 목록 조회

        Parameters
        ----------
        applicant : str
            출원인 기업명 (예: "삼성전자")
        registered_only : bool
            True면 등록 특허만 반환
        page_no : int
        page_count : int
            최대 500

        Returns
        -------
        List[Dict]
            특허 목록 (출원번호, 출원일, 등록여부 등)
        """

        root = self._get(
            "patUtiModInfoSearchSevice/patUtiModInfoSearchSevice/applSearchList",
            {
                "applicant": applicant,
                "pageNo": page_no,
                "numOfRows": page_count,
            },
        )

        patents = []

        for item in root.findall(".//item"):
            status = item.findtext("registerStatus", "")

            if registered_only and status != "등록":
                continue

            patents.append(
                {
                    "application_number": item.findtext("applicationNumber"),
                    "application_date": item.findtext("applicationDate"),
                    "title": item.findtext("inventionTitle"),
                    "register_status": status,
                    "registration_number": item.findtext("registrationNumber"),
                    "registration_date": item.findtext("registrationDate"),
                    "ipc_code": item.findtext("ipcNumber"),
                }
            )

        logger.info(
            "특허 검색 완료 — applicant=%s, 결과=%d건 (등록만=%s)",
            applicant, len(patents), registered_only,
        )

        return patents

    def get_registered_patent_count(self, applicant: str) -> int:
        """등록 특허 수만 반환"""

        return len(self.search_patents(applicant=applicant, registered_only=True))

    # ------------------------------------------------------------------
    # 특허 상세 정보
    # ------------------------------------------------------------------

    def get_abstract(self, application_number: str) -> Optional[str]:
        """특허 초록 텍스트 조회"""

        root = self._get(
            "patUtiModInfoSearchSevice/patUtiModInfoSearchSevice/abstractInfo",
            {"applicationNumber": application_number},
        )

        return root.findtext(".//abstract")

    def get_claims(self, application_number: str) -> List[str]:
        """
        청구항 텍스트 목록 조회

        Returns
        -------
        List[str]
            청구항 텍스트 리스트 (청구항 1, 2, 3 ...)
        """

        root = self._get(
            "patUtiModInfoSearchSevice/patUtiModInfoSearchSevice/claimInfo",
            {"applicationNumber": application_number},
        )

        return [
            item.findtext("claim", "")
            for item in root.findall(".//item")
            if item.findtext("claim")
        ]

    def get_ipc_codes(self, application_number: str) -> List[str]:
        """IPC 분류 코드 목록 조회"""

        root = self._get(
            "patUtiModInfoSearchSevice/patUtiModInfoSearchSevice/ipcInfo",
            {"applicationNumber": application_number},
        )

        return [
            item.findtext("ipcCode", "")
            for item in root.findall(".//item")
            if item.findtext("ipcCode")
        ]

    # ------------------------------------------------------------------
    # 통합 수집
    # ------------------------------------------------------------------

    def collect_patent_texts(
        self,
        applicant: str,
        max_patents: int = 20,
    ) -> List[Dict]:
        """
        기업명으로 등록 특허의 초록 + 청구항 텍스트를 통합 수집

        Parameters
        ----------
        applicant : str
            출원인 기업명
        max_patents : int
            텍스트 수집 대상 최대 특허 수 (API 부하 고려)

        Returns
        -------
        List[Dict]
            [
                {
                    "application_number": ...,
                    "title": ...,
                    "abstract": ...,
                    "claims": [...],
                    "ipc_codes": [...],
                }
            ]
        """

        patents = self.search_patents(applicant=applicant, registered_only=True)
        targets = patents[:max_patents]

        results = []

        for patent in targets:
            app_no = patent.get("application_number")

            if not app_no:
                continue

            try:
                abstract = self.get_abstract(app_no)
                claims = self.get_claims(app_no)
                ipc_codes = self.get_ipc_codes(app_no)

                results.append(
                    {
                        "application_number": app_no,
                        "title": patent.get("title"),
                        "registration_number": patent.get("registration_number"),
                        "registration_date": patent.get("registration_date"),
                        "abstract": abstract,
                        "claims": claims,
                        "ipc_codes": ipc_codes,
                    }
                )

            except Exception as e:
                logger.warning(
                    "특허 상세 수집 실패, 스킵 — app_no=%s | %s", app_no, e
                )
                continue

        logger.info(
            "특허 텍스트 수집 완료 — applicant=%s, %d/%d건",
            applicant, len(results), len(targets),
        )

        return results