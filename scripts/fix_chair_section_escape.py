from pathlib import Path

TARGET = Path('src/tech_agent/chair_section.py')


def main() -> int:
    if not TARGET.exists():
        raise FileNotFoundError(f'Cannot find {TARGET}. Run this from the project root, e.g. C:\\Agent_6.8')

    text = TARGET.read_text(encoding='utf-8')
    original = text

    replacements = [
        (
            'return pat.sub(new_section.rstrip() + "\\n\\n", report, count=1)',
            'return pat.sub(lambda _m: new_section.rstrip() + "\\n\\n", report, count=1)',
        ),
        (
            "return pat.sub(new_section.rstrip() + '\\n\\n', report, count=1)",
            "return pat.sub(lambda _m: new_section.rstrip() + '\\n\\n', report, count=1)",
        ),
        (
            'return pattern.sub(new_section.rstrip() + "\\n\\n", report, count=1)',
            'return pattern.sub(lambda _m: new_section.rstrip() + "\\n\\n", report, count=1)',
        ),
        (
            "return pattern.sub(new_section.rstrip() + '\\n\\n', report, count=1)",
            "return pattern.sub(lambda _m: new_section.rstrip() + '\\n\\n', report, count=1)",
        ),
    ]

    changed = False
    for old, new in replacements:
        if old in text:
            text = text.replace(old, new)
            changed = True

    if not changed:
        # More conservative line-based fallback: only rewrite lines that do a regex .sub with new_section as a literal replacement.
        lines = text.splitlines()
        new_lines = []
        line_changed = False
        for line in lines:
            stripped = line.strip()
            if (
                stripped.startswith('return ')
                and '.sub(' in stripped
                and 'new_section.rstrip()' in stripped
                and 'lambda' not in stripped
                and 'report' in stripped
                and 'count=1' in stripped
            ):
                indent = line[: len(line) - len(line.lstrip())]
                # Preserve variable name before .sub(
                var_name = stripped.split('.sub(', 1)[0].replace('return ', '').strip()
                quote = '"' if '"\\n\\n"' in stripped else "'"
                newline_literal = f'{quote}\\n\\n{quote}'
                line = f"{indent}return {var_name}.sub(lambda _m: new_section.rstrip() + {newline_literal}, report, count=1)"
                line_changed = True
            new_lines.append(line)
        if line_changed:
            text = '\n'.join(new_lines) + ('\n' if original.endswith('\n') else '')
            changed = True

    if not changed:
        print('[INFO] No matching unsafe re.sub replacement line found. The file may already be fixed.')
        return 0

    backup = TARGET.with_suffix('.py.bak_escape_fix')
    backup.write_text(original, encoding='utf-8')
    TARGET.write_text(text, encoding='utf-8')
    print(f'[OK] Patched regex replacement escape issue in {TARGET}')
    print(f'[OK] Backup saved to {backup}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
