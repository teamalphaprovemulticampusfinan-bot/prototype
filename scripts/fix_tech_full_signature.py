from __future__ import annotations

from pathlib import Path

MARKER = "# --- AlphaProve compatibility wrapper: build_tech_full_report accepts runner kwargs ---"


def main() -> int:
    path = Path("src/tech_agent/tech_full_report.py")
    if not path.exists():
        raise FileNotFoundError(f"not found: {path}")

    text = path.read_text(encoding="utf-8")

    if MARKER in text:
        print("[OK] tech_full_report.py already has compatibility wrapper.")
        return 0

    target = "def build_tech_full_report("
    if target not in text:
        raise RuntimeError("build_tech_full_report function was not found.")

    text = text.replace(target, "def _build_tech_full_report_impl(", 1)

    wrapper = r'''
# --- AlphaProve compatibility wrapper: build_tech_full_report accepts runner kwargs ---
def build_tech_full_report(*args, **kwargs):
    """Compatibility wrapper used by Tech runner and standalone rebuild scripts.

    The Tech runner may pass extra metadata such as opinion, summary, bridge,
    compact_summary, chair_summary, company_name, etc. The full-report builder
    should not fail because of those metadata arguments. This wrapper forwards
    only arguments accepted by the real implementation and safely ignores
    presentation-only metadata.
    """
    import inspect

    impl = _build_tech_full_report_impl
    sig = inspect.signature(impl)
    params = sig.parameters

    accepted_kwargs = {}
    accepts_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

    if accepts_var_kw:
        accepted_kwargs.update(kwargs)
    else:
        allowed = {
            name
            for name, p in params.items()
            if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        }
        accepted_kwargs.update({k: v for k, v in kwargs.items() if k in allowed})

        # common alias handling between old/new runner versions
        if "company_name" in kwargs and "company" in allowed and "company" not in accepted_kwargs:
            accepted_kwargs["company"] = kwargs["company_name"]
        if "company" in kwargs and "company_name" in allowed and "company_name" not in accepted_kwargs:
            accepted_kwargs["company_name"] = kwargs["company"]

    return impl(*args, **accepted_kwargs)

'''

    main_guard = '\nif __name__ == "__main__":'
    if main_guard in text:
        text = text.replace(main_guard, "\n" + wrapper.rstrip() + "\n" + main_guard, 1)
    else:
        text = text.rstrip() + "\n\n" + wrapper.lstrip()

    path.write_text(text, encoding="utf-8")
    print("[PATCH] src/tech_agent/tech_full_report.py updated.")
    print("[NEXT] python -m py_compile src\\tech_agent\\tech_full_report.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
