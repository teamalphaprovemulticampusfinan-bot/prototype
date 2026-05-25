# src/data_intake/tech_intake/collector.py

import logging
from datetime import datetime
from typing import List, Optional

from .dart_client import DartClient
from .patent_client import PatentClient
from .web_client import WebClient
from .schemas import RawTechData, SourceInfo
from .config import KIPRIS_API_KEY

logger = logging.getLogger(__name__)


class TechDataCollector:
    """DART 기반 사업보고서 / 특허 / 홈페이지 수집기"""

    def __init__(self):
        self.dart = DartClient()
        self.web = WebClient()
        self.patent = PatentClient() if KIPRIS_API_KEY else None

        if not self.patent:
            logger.warning("KIPRIS_API_KEY 없음 — 특허 수집 비활성화")

    def collect(
        self,
        company_name: Optional[str] = None,
        stock_code: Optional[str] = None,
        bgn_de: str = "20200101",
        end_de: Optional[str] = None,
        latest_only: bool = True,
        homepage_url: Optional[str] = None,
    ) -> List[RawTechData]:
        """
        기업 사업보고서 XML / 특허 / 홈페이지 수집

        Parameters
        ----------
        company_name : str
            기업명 (company_name / stock_code 중 하나 필수)
        stock_code : str
            종목코드
        bgn_de : str
            조회 시작일 (YYYYMMDD)
        end_de : str, optional
            조회 종료일 (YYYYMMDD), None이면 오늘까지
        latest_only : bool
            True면 최신 1개만, False면 전체
        homepage_url : str, optional
            기업 홈페이지 URL — 없으면 웹 수집 스킵

        Returns
        -------
        List[RawTechData]
        """

        if not company_name and not stock_code:
            raise ValueError("company_name 또는 stock_code 중 하나 필요")

        company_label = company_name or stock_code  # 로그/스키마용 식별자

        # 1. corp_code 찾기
        corp_code = self.dart.find_corp_code(
            company_name=company_name,
            stock_code=stock_code,
        )

        if not corp_code:
            raise ValueError(f"corp_code 조회 실패 — company={company_label}")

        logger.info("corp_code 확인: %s → %s", company_label, corp_code)

        # 2. 사업보고서 목록 조회
        reports = self.dart.get_business_reports(
            corp_code=corp_code,
            bgn_de=bgn_de,
            end_de=end_de,
        )

        if not reports:
            logger.warning("사업보고서 없음 — company=%s, bgn_de=%s", company_label, bgn_de)
            return []

        # 최신순 정렬
        reports.sort(key=lambda x: x.get("rcept_dt", ""), reverse=True)

        if latest_only:
            reports = reports[:1]

        logger.info("수집 대상 보고서: %d건 — company=%s", len(reports), company_label)

        # 3. XML 원문 수집
        results: List[RawTechData] = []

        for report in reports:
            rcept_no = report.get("rcept_no")
            report_name = report.get("report_nm", "")

            if not rcept_no:
                logger.warning("rcept_no 없음, 스킵 — report=%s", report_name)
                continue

            try:
                xml_text = self.dart.get_document_xml(rcept_no)
            except Exception as e:
                logger.error("XML 수집 실패, 스킵 — rcept_no=%s | %s", rcept_no, e)
                continue

            results.append(
                RawTechData(
                    company=company_label,
                    source=SourceInfo(
                        major_source="DART",
                        middle_source=report_name,
                        source_url=None,
                    ),
                    raw_text=xml_text,
                    collected_at=datetime.now(),       # str → datetime
                    metadata={
                        "corp_code": corp_code,
                        "rcept_no": rcept_no,
                        "report_name": report_name,
                        "report_date": report.get("rcept_dt"),
                    },
                )
            )

        logger.info("DART 수집 완료: %d건 — company=%s", len(results), company_label)

        # 4. 특허 수집
        if self.patent:
            results.extend(self._collect_patents(company_label=company_label))

        # 5. 홈페이지 수집
        if homepage_url:
            results.extend(self._collect_web(company_label=company_label, homepage_url=homepage_url))

        logger.info("전체 수집 완료: %d건 — company=%s", len(results), company_label)
        return results

    # ------------------------------------------------------------------
    # 특허 수집
    # ------------------------------------------------------------------

    def _collect_patents(self, company_label: str) -> List[RawTechData]:
        """KIPRIS에서 등록 특허 초록+청구항 수집"""

        results: List[RawTechData] = []

        try:
            patents = self.patent.collect_patent_texts(applicant=company_label)
        except Exception as e:
            logger.error("특허 수집 실패 — company=%s | %s", company_label, e)
            return results

        for patent in patents:
            text_parts = []

            if patent.get("abstract"):
                text_parts.append(f"[초록] {patent['abstract']}")

            for i, claim in enumerate(patent.get("claims", []), start=1):
                text_parts.append(f"[청구항{i}] {claim}")

            if not text_parts:
                continue

            results.append(
                RawTechData(
                    company=company_label,
                    source=SourceInfo(
                        major_source="특허",
                        middle_source=patent.get("title", ""),
                        source_url=None,
                    ),
                    raw_text="\n".join(text_parts),
                    collected_at=datetime.now(),
                    metadata={
                        "application_number": patent.get("application_number"),
                        "registration_number": patent.get("registration_number"),
                        "registration_date": patent.get("registration_date"),
                        "ipc_codes": patent.get("ipc_codes", []),
                    },
                )
            )

        logger.info("특허 수집 완료: %d건 — company=%s", len(results), company_label)
        return results

    # ------------------------------------------------------------------
    # 홈페이지 수집
    # ------------------------------------------------------------------

    def _collect_web(self, company_label: str, homepage_url: str) -> List[RawTechData]:
        """홈페이지 및 하위 IR/제품 페이지 수집"""

        results: List[RawTechData] = []

        # 메인 페이지
        try:
            main_text = self.web.fetch_text(homepage_url)
            results.append(
                RawTechData(
                    company=company_label,
                    source=SourceInfo(
                        major_source="홈페이지",
                        middle_source="메인",
                        source_url=homepage_url,
                    ),
                    raw_text=main_text,
                    collected_at=datetime.now(),
                    metadata={"url": homepage_url},
                )
            )
        except Exception as e:
            logger.error("홈페이지 메인 수집 실패 — %s | %s", homepage_url, e)
            return results

        # 하위 후보 페이지 (IR, 제품, 기술 등)
        try:
            candidate_urls = self.web.discover_candidate_pages(homepage_url)
        except Exception as e:
            logger.warning("후보 페이지 탐색 실패 — %s | %s", homepage_url, e)
            return results

        if not candidate_urls:
            return results

        fetched = self.web.fetch_multiple(candidate_urls[:10])

        for item in fetched:
            if not item.get("text"):
                continue

            results.append(
                RawTechData(
                    company=company_label,
                    source=SourceInfo(
                        major_source="홈페이지",
                        middle_source="서브페이지",
                        source_url=item["url"],
                    ),
                    raw_text=item["text"],
                    collected_at=datetime.now(),
                    metadata={"url": item["url"]},
                )
            )

        logger.info("홈페이지 수집 완료: %d건 — company=%s", len(results), company_label)
        return results