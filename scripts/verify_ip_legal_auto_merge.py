from __future__ import annotations

import json
from pathlib import Path

TECH = Path('data') / '반도체' / '네패스' / 'tech'
summary_path = TECH / 'tech_chair_summary.json'
md_path = TECH / 'nepes_tech_chair_summary.md'

print('[CHECK] tech_chair_summary.json exists:', summary_path.exists(), summary_path)
if summary_path.exists():
    data = json.loads(summary_path.read_text(encoding='utf-8'))
    print('[CHECK] ip_legal_feature_merge_status:', data.get('ip_legal_feature_merge_status'))
    print('[CHECK] top-level ip_legal_features keys:', sorted((data.get('ip_legal_features') or {}).keys())[:20])
    selected = data.get('selected_ml') or {}
    legal = selected.get('ip_legal_stability') or {}
    print('[CHECK] selected_ml.ip_legal_stability.legal_stability_score_estimated:', legal.get('legal_stability_score_estimated'))
    print('[CHECK] selected_ml.ip_legal_stability.bridge_signal:', legal.get('bridge_signal'))
    print('[CHECK] selected_ml.ip_legal_stability.bridge_adjustment_points:', legal.get('bridge_adjustment_points'))

print('[CHECK] nepes_tech_chair_summary.md exists:', md_path.exists(), md_path)
if md_path.exists():
    text = md_path.read_text(encoding='utf-8', errors='ignore')
    for keyword in [
        'IP Legal Stability',
        'IP Legal Bridge Signal',
        'KIPRIS 등록률',
        '등록특허 중 존속률',
        '소멸·거절·취하',
    ]:
        print(f'[CHECK] md contains {keyword!r}:', keyword in text)
