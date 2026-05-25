# src/data_intake/tech_intake/web_client.py

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config import REQUEST_TIMEOUT, MAX_RETRIES, SLEEP_SECONDS

logger = logging.getLogger(__name__)

# 병렬 수집 최대 스레드 수
_MAX_WORKERS = 5


class WebClient:
    """
    홈페이지 / IR / 보도자료 / 기사 텍스트 수집용 클라이언트
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            }
        )

    # ------------------------------------------------------------------
    # 기본 수집
    # ------------------------------------------------------------------

    def fetch_html(self, url: str) -> str:
        """URL에서 HTML 원문 가져오기 (재시도 포함)"""

        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                response.encoding = response.apparent_encoding
                return response.text

            except Exception as e:
                last_error = e
                logger.warning("fetch_html 재시도 %d/%d — %s | %s", attempt, MAX_RETRIES, url, e)
                time.sleep(SLEEP_SECONDS)

        raise RuntimeError(f"웹 페이지 수집 실패 ({MAX_RETRIES}회 시도): {url} — {last_error}")

    def extract_text_from_html(self, html: str) -> str:
        """HTML에서 본문 텍스트 추출"""

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()

        return self.clean_text(soup.get_text(" "))

    def fetch_text(self, url: str) -> str:
        """URL에서 HTML을 가져와 텍스트만 반환"""

        return self.extract_text_from_html(self.fetch_html(url))

    # ------------------------------------------------------------------
    # 다중 URL 수집 (병렬)
    # ------------------------------------------------------------------

    def fetch_multiple(
        self,
        urls: List[str],
        max_workers: int = _MAX_WORKERS,
    ) -> List[Dict[str, Optional[str]]]:
        """
        여러 URL 텍스트 병렬 수집

        실패한 URL은 error 필드에 저장
        """

        results: Dict[str, Dict] = {}

        def _fetch(url: str) -> Dict:
            try:
                return {"url": url, "text": self.fetch_text(url), "error": None}
            except Exception as e:
                logger.warning("fetch_multiple 실패 — %s | %s", url, e)
                return {"url": url, "text": None, "error": str(e)}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(_fetch, url): url for url in urls}

            for future in as_completed(future_to_url):
                result = future.result()
                results[result["url"]] = result

        # 입력 순서 유지
        return [results[url] for url in urls]

    # ------------------------------------------------------------------
    # 링크 추출
    # ------------------------------------------------------------------

    def extract_links(
        self,
        base_url: str,
        html: str,
        keywords: Optional[List[str]] = None,
    ) -> List[str]:
        """
        HTML에서 링크 추출

        keywords가 있으면 URL 또는 링크 텍스트에 키워드 포함된 링크만 반환
        예: ["IR", "제품", "기술", "R&D"]
        """

        soup = BeautifulSoup(html, "html.parser")
        links: set[str] = set()

        for a in soup.find_all("a", href=True):
            full_url = urljoin(base_url, a["href"])
            label = a.get_text(" ", strip=True)

            if keywords:
                target = f"{full_url} {label}".lower()
                if not any(kw.lower() in target for kw in keywords):
                    continue

            links.add(full_url)

        return list(links)

    def discover_candidate_pages(self, homepage_url: str) -> List[str]:
        """기업 홈페이지에서 기술/제품/IR 관련 후보 페이지 링크 찾기"""

        html = self.fetch_html(homepage_url)

        keywords = [
            "ir", "investor", "product", "products",
            "technology", "r&d", "research", "business",
            "solution", "소재", "제품", "기술", "연구",
            "사업", "투자", "홍보",
        ]

        return self.extract_links(base_url=homepage_url, html=html, keywords=keywords)

    # ------------------------------------------------------------------
    # 텍스트 정제
    # ------------------------------------------------------------------

    def clean_text(self, text: str) -> str:
        """공백/특수문자 정리"""

        # 유니코드 공백 문자 통일 (\u3000 전각공백, \xa0 non-breaking space 등)
        text = re.sub(r"[\u00a0\u1680\u2000-\u200b\u202f\u205f\u3000\ufeff]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()