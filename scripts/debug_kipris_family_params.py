from __future__ import annotations

import os
import time
from pathlib import Path
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("KIPRIS_PLUS_FAMILY_URL", "").strip()
API_KEY = (
    os.getenv("KIPRIS_PLUS_API_KEY", "").strip()
    or os.getenv("KIPRIS_API_KEY", "").strip()
    or os.getenv("KIPRIS_ACCESS_KEY", "").strip()
)

APP_NO = "1020180096318"

PARAM_CANDIDATES = [
    "applicationNumber",
    "applicationNo",
    "appNo",
    "application_number",
    "patentApplicationNumber",
]

KEY_CANDIDATES = [
    "accessKey",
    "serviceKey",
    "ServiceKey",
]

def main() -> int:
    if not BASE_URL:
        print("[ERROR] KIPRIS_PLUS_FAMILY_URL 없음")
        return 1

    if not API_KEY:
        print("[ERROR] KIPRIS_PLUS_API_KEY 없음")
        print("주의: 키 값은 절대 채팅에 붙여넣지 말고 .env 또는 현재 터미널 환경변수에만 넣어.")
        return 1

    print("=" * 80)
    print("[KIPRIS Plus Family 파라미터 후보 테스트]")
    print("url:", BASE_URL)
    print("app no:", APP_NO)
    print("=" * 80)

    for key_name in KEY_CANDIDATES:
        for app_param in PARAM_CANDIDATES:
            params = {
                key_name: API_KEY,
                app_param: APP_NO,
            }

            print()
            print(f"## TRY key={key_name}, app_param={app_param}")

            try:
                r = requests.get(BASE_URL, params=params, timeout=20)
                text = r.text or ""
                print("status_code:", r.status_code)
                print("final_url_without_key:", r.url.replace(API_KEY, "***KEY***"))
                print("preview:")
                print(text[:1200].replace(API_KEY, "***KEY***"))

                lower = text.lower()
                if (
                    "<item" in lower
                    or "family" in lower
                    or "patfam" in lower
                    or "application" in lower
                    or "국가" in text
                    or "패밀리" in text
                ):
                    print("[POSSIBLE OK] 이 조합은 응답 안에 데이터성 문구가 있습니다.")

            except Exception as exc:
                print("[ERROR]", repr(exc))

            time.sleep(0.2)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
