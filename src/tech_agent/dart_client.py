from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Dict, Optional
import xml.etree.ElementTree as ET

import requests

from .config import DART_API_KEY, REQUEST_TIMEOUT, ROOT_DIR
from .utils import ensure_dir


class OpenDartClient:
    CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
    LIST_URL = "https://opendart.fss.or.kr/api/list.json"
    DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or DART_API_KEY
        self.cache_dir = ROOT_DIR / ".cache" / "dart"
        ensure_dir(self.cache_dir)

    def _require_api_key(self):
        if not self.api_key:
            raise ValueError("DART_API_KEY가 비어 있습니다. .env에 설정하세요.")

    def _corp_code_cache_path(self) -> Path:
        return self.cache_dir / "corp_code_map.json"

    def load_corp_code_map(self, force_refresh: bool = False) -> Dict[str, str]:
        self._require_api_key()

        cache_path = self._corp_code_cache_path()
        if cache_path.exists() and not force_refresh:
            try:
                return json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        resp = requests.get(
            self.CORP_CODE_URL,
            params={"crtfc_key": self.api_key},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        xml_name = zf.namelist()[0]
        xml_bytes = zf.read(xml_name)

        root = ET.fromstring(xml_bytes)

        mapping: Dict[str, str] = {}
        for item in root.findall(".//list"):
            corp_code = (item.findtext("corp_code") or "").strip()
            stock_code = (item.findtext("stock_code") or "").strip()
            if corp_code and stock_code:
                mapping[stock_code] = corp_code

        cache_path.write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return mapping

    def get_corp_code(self, stock_code: str) -> str:
        stock_code = (stock_code or "").strip()
        if not stock_code:
            return ""
        mapping = self.load_corp_code_map()
        return mapping.get(stock_code, "")

    def get_latest_business_report_receipt_no(self, stock_code: str) -> str:
        self._require_api_key()

        corp_code = self.get_corp_code(stock_code)
        if not corp_code:
            return ""

        resp = requests.get(
            self.LIST_URL,
            params={
                "crtfc_key": self.api_key,
                "corp_code": corp_code,
                "bgn_de": "20220101",
                "end_de": "20991231",
                "pblntf_ty": "A",
                "last_reprt_at": "Y",
                "page_count": 100,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        items = data.get("list", []) or []
        preferred = ["사업보고서", "반기보고서", "분기보고서"]
        for name in preferred:
            for row in items:
                report_nm = row.get("report_nm", "")
                if name in report_nm:
                    return row.get("rcept_no", "")

        if items:
            return items[0].get("rcept_no", "")
        return ""

    def get_document_xml(self, rcept_no: str) -> bytes:
        self._require_api_key()

        if not rcept_no:
            return b""

        resp = requests.get(
            self.DOCUMENT_URL,
            params={"crtfc_key": self.api_key, "rcept_no": rcept_no},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        xml_name = zf.namelist()[0]
        return zf.read(xml_name)

    def get_latest_business_text(self, stock_code: str) -> str:
        rcept_no = self.get_latest_business_report_receipt_no(stock_code)
        if not rcept_no:
            return ""

        xml_bytes = self.get_document_xml(rcept_no)
        if not xml_bytes:
            return ""

        try:
            root = ET.fromstring(xml_bytes)
            text_parts = []
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    text_parts.append(elem.text.strip())
            return "\n".join(text_parts)
        except Exception:
            return xml_bytes.decode("utf-8", errors="ignore")