from pathlib import Path
import re

path = Path(r".\src\chair_agent\graph.py")
text = path.read_text(encoding="utf-8")

pattern = r'''def _run_agent_node\(state: ChairState, agent: str, runner\) -> dict\[str, Any\]:\n.*?\n\n\ndef finance_node'''

replacement = '''def _agent_input_log_message(agent: str) -> str:
    if _agent_history_replay_enabled():
        return f"[Chair] {agent} 입력 패킷 준비 중..."
    return f"[Chair] {agent} 에이전트 실행 중..."


def _run_agent_node(state: ChairState, agent: str, runner) -> dict[str, Any]:
    print(_agent_input_log_message(agent))
    try:
        packet = runner(state["company_dir"], state["company"])
    except Exception as exc:
        print(f"[Chair] {agent} 실패 → Auditor fallback packet 생성: {exc}")
        packet = {
            "agent": agent,
            "company_name": state.get("company"),
            "summary": f"{agent} 실행 실패: {exc}",
            "key_risks": [f"{agent} 산출물 확인 제한"],
            "status": "FAILED",
        }
    tagged = _tag_raw_packet(agent, packet)
    print(f"[Chair] {agent} 완료 → Auditor 입력용 raw packet 수집")
    return {"opinions": [tagged]}


def finance_node'''

new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)

if count != 1:
    raise RuntimeError(
        "패치 실패: graph.py에서 _run_agent_node 블록을 정확히 1개 찾지 못했습니다. "
        f"found={count}"
    )

path.write_text(new_text, encoding="utf-8")
print("[OK] graph.py log wording patched.")
