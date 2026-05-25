# Tech history input templates

이 폴더는 `src_eval` 전용 Tech history 평가 입력값입니다. 기존 `src` 운영 레포트 산출 흐름은 건드리지 않습니다.

월별 평가는 `monthly`, 일별 평가는 `daily` 폴더를 읽습니다. 날짜 컬럼이 있는 행은 반드시 `as_of_date` 이전 행만 사용됩니다.
날짜 컬럼이 없는 공통 정보는 보조 근거로만 사용되며, `signal` 또는 `score` 컬럼이 있으면 연속 신호로 반영됩니다.

주요 근거: Hall-Jaffe-Trajtenberg 특허 인용/기업가치, Lanjouw-Schankerman/OECD 특허품질 복합지표, TRL/TRA 성숙도 프레임워크, IFC/Bpifrance Deep-Tech 상업화 단계.
