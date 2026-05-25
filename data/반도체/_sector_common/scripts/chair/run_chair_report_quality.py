# -*- coding: utf-8 -*-
"""
Run Chair final report quality evaluation without importing chair_agent.__init__.

Example:
  python scripts\run_chair_report_quality.py --company-dir nepes --company "네패스"
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    module_path = SRC / "chair_agent" / "report_quality.py"
    spec = importlib.util.spec_from_file_location("chair_report_quality_standalone", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"report_quality.py 로드 실패: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return int(module.main())


if __name__ == "__main__":
    raise SystemExit(main())
