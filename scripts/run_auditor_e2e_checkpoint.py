import sys, os, csv, json
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from auditor_agent.decision_rubric import compute_portfolio_decision, AGENT_ORDER

csv_path = r"c:\Agent_6.9\data\반도체\_sector_common\history_sheets_exports\monthly\backtest\20260526_10_12_reliable_v2\backtest_2025_10_2025_12_reliable_v2\signal_df_latest_live_checkpoint.csv"

# Prefer a direct history CSV path to avoid expensive filesystem globbing during
# DMA component weight lookups.  This keeps the run read-only and fast.
os.environ['ALPHAPROVE_DMA_HISTORY_CSV'] = csv_path

rows = []
try:
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader):
            rows.append(r)
            if i >= 19:
                break
except UnicodeDecodeError:
    with open(csv_path, 'r', encoding='cp949', newline='') as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader):
            rows.append(r)
            if i >= 19:
                break

print(f"Loaded {len(rows)} rows from checkpoint")

counts = {"매수":0, "보유":0, "매도":0}
samples_hold = []

for r in rows:
    agent_packets = {a: dict(r) for a in AGENT_ORDER}
    out = compute_portfolio_decision(agent_packets)
    final = out.get('final_recommendation') or out.get('base_recommendation') or '보유'
    counts[final] = counts.get(final, 0) + 1
    if final == '보유' and len(samples_hold) < 5:
        samples_hold.append({
            'ticker': r.get('ticker') or r.get('종목코드') or r.get('company') or r.get('name'),
            'final': final,
            'weighted_signal': out.get('weighted_signal'),
            'label_posterior': out.get('label_posterior'),
            'core_pillars': out.get('core_pillar_summary')
        })

print('Final counts (sample up to 20 rows):', counts)
print('\nSample Hold rows:')
print(json.dumps(samples_hold, ensure_ascii=False, indent=2))
