from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path

BAND = "0" + ".25"
NEG_BAND = "-" + BAND

FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("weighted_signal >= +" + BAND, re.compile(r"weighted_signal\s*>=\s*\+?" + re.escape(BAND))),
    ("weighted_signal <= " + NEG_BAND, re.compile(r"weighted_signal\s*<=\s*" + re.escape(NEG_BAND))),
    ("buy_th default " + BAND, re.compile(r"buy_th\s*[:=][^\n]*" + re.escape(BAND))),
    ("sell_th default " + NEG_BAND, re.compile(r"sell_th\s*[:=][^\n]*" + re.escape(NEG_BAND))),
    ("threshold baseline text", re.compile(r"baseline\s*(?:±|\+/-)?\s*" + re.escape(BAND), re.IGNORECASE)),
    ("tertile Hold bucket", re.compile(r"frac\s*<=\s*1/3|frac\s*<=\s*2/3|qcut\(|tertile", re.IGNORECASE)),
]

SKIP_DIR_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "resources",
    "data",
    "workspace",
    "history_sheets_exports",
}

CHECK_SUFFIXES = {".py", ".md", ".txt", ".ps1", ".json", ".yaml", ".yml"}


def should_scan(path: Path, base: Path | None = None) -> bool:
    if path.suffix.lower() not in CHECK_SUFFIXES:
        return False
    try:
        parts = set(path.relative_to(base or Path.cwd()).parts)
    except Exception:
        parts = set(path.parts)
    if parts & SKIP_DIR_PARTS:
        return False
    return True


def scan(root: Path) -> list[tuple[str, str, int, str]]:
    problems: list[tuple[str, str, int, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or not should_scan(path, root):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="cp949", errors="ignore")
        rel = path.relative_to(root).as_posix()
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            # Do not flag this checker defining the forbidden regex patterns.
            if rel.endswith("check_eval_recommendation_policy_v50.py") and ("FORBIDDEN_PATTERNS" in text or "re.compile" in stripped):
                continue
            if stripped.startswith("#"):
                continue
            for name, pat in FORBIDDEN_PATTERNS:
                if pat.search(line):
                    problems.append((rel, name, line_no, line.strip()))
    return problems


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def smoke(root: Path) -> list[str]:
    errors: list[str] = []
    os.environ["ALPHAPROVE_EVAL_HOLD_POLICY"] = "reject_option_directional_argmax"
    sys.path.insert(0, str(root.resolve()))
    try:
        import importlib
        prob = importlib.import_module("evaluation.probability_tensor")
        dec = importlib.import_module("evaluation.decision_labels")
        pos = {"매수": 0.45, "보유": 0.50, "매도": 0.05}
        neg = {"매수": 0.05, "보유": 0.50, "매도": 0.45}
        tie = {"매수": 0.30, "보유": 0.40, "매도": 0.30}
        if prob.label_from_probabilities(pos) != "매수":
            errors.append("probability_tensor positive directional posterior did not return 매수")
        if prob.label_from_probabilities(neg) != "매도":
            errors.append("probability_tensor negative directional posterior did not return 매도")
        if prob.label_from_probabilities(tie) != "보유":
            errors.append("probability_tensor tied direction did not return 보유")
        if dec.recommendation_from_probabilities(pos) != "매수":
            errors.append("decision_labels positive directional posterior did not return 매수")
        if dec.recommendation_from_probabilities(neg) != "매도":
            errors.append("decision_labels negative directional posterior did not return 매도")
        dma = importlib.import_module("auditor_agent.dynamic_model_averaging")
        dd = {
            "finance": {"signal": 0.30, "recommendation": "보유", "recommendation_label_source": "neutral_placeholder_no_categorical_label"},
            "market": {"signal": 0.20, "recommendation": "보유", "recommendation_label_source": "neutral_placeholder_no_categorical_label"},
            "macro": {"signal": -0.10, "recommendation": "보유", "recommendation_label_source": "neutral_placeholder_no_categorical_label"},
        }
        weights = {"finance": 1/3, "market": 1/3, "macro": 1/3}
        m = dma.compute_dma_label_posterior(dd, weights)
        if m.get("final_recommendation") != "매수":
            errors.append("auditor DMA soft signal posterior still collapses directional positive signals into 보유")
    except Exception as exc:
        errors.append(f"smoke import/test failed: {exc}")
    finally:
        try:
            sys.path.remove(str(root.resolve()))
        except ValueError:
            pass
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Check v50 DMA/posterior reject-option recommendation policy.")
    ap.add_argument("--root", default="./src_eval", help="src_eval root")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"[ERROR] root not found: {root}")
        return 2

    problems = scan(root.parent if root.name == "src_eval" else root)
    # Focus on editable evaluation/prompt/scripts files.  Do not flag unrelated numeric weights in agent scoring resources.
    problems = [p for p in problems if p[0].startswith(("src_eval/evaluation/", "src_eval/auditor_agent/", "src_eval/chair_agent/", "scripts/", "README"))]
    smoke_errors = smoke(root)

    print("=" * 80)
    print("[v50 DMA recommendation policy check]")
    print(f"root: {root}")
    print("policy: no fixed weighted_signal band; Hold is reject/no-trade for tied/unavailable direction")
    print(f"forbidden_pattern_count: {len(problems)}")
    for rel, name, line_no, line in problems[:50]:
        print(f"- {rel}:{line_no}: {name}: {line}")
    if len(problems) > 50:
        print(f"... {len(problems) - 50} more")
    print(f"smoke_error_count: {len(smoke_errors)}")
    for err in smoke_errors:
        print(f"- {err}")
    print("=" * 80)

    if args.strict and (problems or smoke_errors):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
