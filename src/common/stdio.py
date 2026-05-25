from __future__ import annotations

import os
import sys


def configure_utf8_stdio() -> None:
    """Make Windows console output tolerate Korean text and symbols."""

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
