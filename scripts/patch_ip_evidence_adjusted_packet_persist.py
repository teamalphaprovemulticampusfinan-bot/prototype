from pathlib import Path
import re

path = Path("src/tech_agent/chair_summary.py")
text = path.read_text(encoding="utf-8")

backup = path.with_suffix(".py.bak_ip_evidence_packet_persist")
backup.write_text(text, encoding="utf-8")

marker = "# === IP_EVIDENCE_ADJUSTED_PACKET_PERSIST_V1 ==="

if marker in text:
    print("[SKIP] packet persist patch already exists.")
    raise SystemExit(0)

needle = '''    if not wrote:
        _ipev_write_json(tech_dir / "tech_chair_summary.json", summary)

    block = _ipev_md_block(summary)
'''

replacement = '''    if not wrote:
        _ipev_write_json(tech_dir / "tech_chair_summary.json", summary)

    # === IP_EVIDENCE_ADJUSTED_PACKET_PERSIST_V1 ===
    # Audit/traceability artifact:
    # Save the final Tech-to-Value Bridge score after IP Evidence Composite adjustment.
    tv = summary.get("tech_to_value") if isinstance(summary.get("tech_to_value"), dict) else {}

    adjusted_packet = {
        "created_at": _IpevBridgeDatetime.now().isoformat(timespec="seconds"),
        "company_slug": company_slug,
        "company_name": company_name,
        "field": field,
        "status": summary.get("ip_evidence_bridge_adjustment_status"),
        "formula": tv.get("ip_evidence_formula")
            or "final_bridge_score_after_ip_evidence = peer_adjusted_bridge_score_before_ip_evidence + ip_evidence_composite_adjustment_points",
        "base_bridge_score": tv.get("base_bridge_score"),
        "peer_adjusted_bridge_score_before_ip_evidence": tv.get("peer_adjusted_bridge_score_before_ip_evidence"),
        "ip_evidence_composite_score": tv.get("ip_evidence_composite_score"),
        "ip_evidence_composite_bridge_signal": tv.get("ip_evidence_composite_bridge_signal"),
        "ip_evidence_composite_adjustment_points": tv.get("ip_evidence_composite_adjustment_points"),
        "final_bridge_score_after_ip_evidence": tv.get("final_bridge_score_after_ip_evidence"),
        "peer_adjusted_bridge_score": tv.get("peer_adjusted_bridge_score"),
        "ip_evidence_adjusted_score": tv.get("ip_evidence_adjusted_score"),
        "ip_evidence_adjusted_grade": tv.get("ip_evidence_adjusted_grade"),
        "source_file": tv.get("ip_evidence_composite_source_file"),
        "usage_rule": (
            "This packet is an audit artifact for the Tech-to-Value Bridge after "
            "IP Evidence Composite adjustment. It does not represent direct revenue, "
            "customer adoption, mass production, or FCF evidence by itself."
        ),
    }

    _ipev_write_json(
        tech_dir / "tech_to_value_bridge_ip_evidence_adjusted.json",
        adjusted_packet,
    )

    if company_slug:
        _ipev_write_json(
            tech_dir / f"{company_slug}_tech_to_value_bridge_ip_evidence_adjusted.json",
            adjusted_packet,
        )

    block = _ipev_md_block(summary)
'''

if needle not in text:
    raise SystemExit("[ERROR] target block not found in _ipev_persist_summary().")

text = text.replace(needle, replacement)

path.write_text(text, encoding="utf-8")

print("[DONE] chair_summary.py patched for adjusted bridge packet persist")
print(f"[BACKUP] {backup}")
