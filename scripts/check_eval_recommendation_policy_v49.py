from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


FORBIDDEN_PATTERNS = [
    (
        "fixed weighted_signal +0.25 Buy threshold",
        re.compile(r"weighted_signal\s*(?:>|>=)\s*(?:\+)?0\.25", re.IGNORECASE),
    ),
    (
        "fixed weighted_signal -0.25 Sell threshold",
        re.compile(r"weighted_signal\s*(?:<|<=)\s*-0\.25", re.IGNORECASE),
    ),
    (
        "absolute signal 0.25 recommendation band",
        re.compile(r"abs\s*\(\s*weighted_signal\s*\)\s*(?:<|<=)\s*0\.25", re.IGNORECASE),
    ),
    (
        "qcut recommendation bucket",
        re.compile(r"qcut\s*\(", re.IGNORECASE),
    ),
    (
        "tertile recommendation bucket",
        re.compile(r"\btertile\b", re.IGNORECASE),
    ),
    (
        "mechanical 1/3 Hold bucket",
        re.compile(r"frac\s*(?:<|<=)\s*(?:1\s*/\s*3|2\s*/\s*3)", re.IGNORECASE),
    ),
]


ALLOWLIST_PATH_PARTS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
}


ALLOWLIST_FILES = {
    "check_eval_recommendation_policy_v49.py",
}


ALLOWLIST_CONTEXT_PATTERNS = [
    re.compile(r"no fixed weighted_signal band", re.IGNORECASE),
    re.compile(r"forbidden_pattern", re.IGNORECASE),
    re.compile(r"FORBIDDEN_PATTERNS", re.IGNORECASE),
    re.compile(r"tertile recommendation bucket", re.IGNORECASE),
    re.compile(r"qcut recommendation bucket", re.IGNORECASE),
    re.compile(r"fixed weighted_signal", re.IGNORECASE),
]


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & ALLOWLIST_PATH_PARTS:
        return True
    if path.name in ALLOWLIST_FILES:
        return True
    if path.suffix.lower() != ".py":
        return True
    return False


def is_allowed_context(line: str) -> bool:
    return any(p.search(line) for p in ALLOWLIST_CONTEXT_PATTERNS)


def scan(root: Path) -> list[tuple[str, int, str, str]]:
    hits: list[tuple[str, int, str, str]] = []

    for path in sorted(root.rglob("*.py")):
        if should_skip(path):
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="cp949", errors="ignore")

        for lineno, line in enumerate(text.splitlines(), start=1):
            if is_allowed_context(line):
                continue

            for name, pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    hits.append((str(path), lineno, name, line.strip()))

    return hits


def smoke_import(root: Path) -> list[str]:
    errors: list[str] = []

    target_files = [
        root / "evaluation" / "decision_labels.py",
        root / "evaluation" / "probability_tensor.py",
        root / "auditor_agent" / "dynamic_model_averaging.py",
        root / "auditor_agent" / "prompts.py",
        root / "auditor_agent" / "quantity_prompts.py",
        root / "chair_agent" / "prompts.py",
    ]

    for path in target_files:
        if not path.exists():
            errors.append(f"missing: {path}")
            continue

        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except Exception as exc:
            errors.append(f"{path}: {type(exc).__name__}: {exc}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="src_eval")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()

    print("=" * 80)
    print("[v49 DMA recommendation policy check]")
    print(f"root: {root}")
    print("policy: no fixed weighted_signal band; Hold is reject/no-trade for tied/unavailable direction")

    if not root.exists():
        print(f"[ERROR] root not found: {root}")
        return 2

    hits = scan(root)
    smoke_errors = smoke_import(root)

    print(f"forbidden_pattern_count: {len(hits)}")
    for path, lineno, name, line in hits:
        try:
            rel = Path(path).resolve().relative_to(Path.cwd().resolve())
        except Exception:
            rel = Path(path)
        print(f"- {rel}:{lineno}: {name}: {line}")

    print(f"smoke_error_count: {len(smoke_errors)}")
    for err in smoke_errors:
        print(f"- {err}")

    print("=" * 80)

    if args.strict and (hits or smoke_errors):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
