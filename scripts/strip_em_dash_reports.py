"""
Remove travessão (U+2014 EM DASH) dos templates de relatório visíveis no PDF.
Preserva o bloco clean_exec_text em _report_macros.html (linhas com replace('—'...)).
Substituições: ' — ' -> ': '; placeholders '—' em defaults Jinja -> en dash U+2013.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "app" / "templates"

FILES = [
    TEMPLATES / "_report_macros.html",
    TEMPLATES / "report_body_a.html",
    TEMPLATES / "report_body_b.html",
    TEMPLATES / "report_body_part1.html",
    TEMPLATES / "report_body_part2.html",
    TEMPLATES / "report_body_part3.html",
    TEMPLATES / "report.html",
]

EM = "\u2014"
EN = "\u2013"


def protect_clean_exec_text_lines(lines: list[str]) -> set[int]:
    """Linhas 1-based dentro do macro clean_exec_text (preserva replace('—'...))."""
    protect: set[int] = set()
    inside = False
    for i, line in enumerate(lines, start=1):
        if "{% macro clean_exec_text" in line:
            inside = True
        if inside:
            protect.add(i)
            if "{% endmacro %}" in line or "{%- endmacro %}" in line:
                break
    return protect


def line_placeholder_em_to_en(line: str) -> str:
    """Troca apenas U+2014 usado como marcador vazio em get(..., '—') etc., por U+2013."""
    s = line
    s = re.sub(r",\s*'—'\)", f", '{EN}')", s)
    s = re.sub(r',\s*"—"\)', f', "{EN}")', s)
    s = re.sub(r"or\s+'—'", f"or '{EN}'", s)
    s = re.sub(r'or\s+"—"', f'or "{EN}"', s)
    s = re.sub(r"\{\%\-\s*if\s+raw\s*==\s*''\s*-\%\}—", "{%- if raw == '' -%}" + EN, s)
    s = re.sub(r">\s*—\s*</div>", f">{EN}</div>", s)
    s = re.sub(r"else\s+'—'", f"else '{EN}'", s)
    return s


def strip_em_from_line(line: str) -> str:
    s = line_placeholder_em_to_en(line)
    while " — " in s:
        s = s.replace(" — ", ": ")
    s = s.replace("—?", "?")
    s = s.replace("—.", ".")
    s = s.replace("—,", ",")
    s = s.replace("—:", ":")
    s = s.replace("(—", "(")
    s = s.replace("—)", ")")
    s = s.replace('—"', ': "')
    s = s.replace('"—', '": ')
    if EM in s:
        s = s.replace(EM + " ", ": ")
        s = s.replace(" " + EM, ",")
        s = s.replace(EM, ": ")
    return s


def process_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    protected: set[int] = set()
    if path.name == "_report_macros.html":
        protected = protect_clean_exec_text_lines([ln.rstrip("\r\n") for ln in lines])
        if not protected:
            print(f"WARN: clean_exec_text block not found in {path}", file=sys.stderr)

    out: list[str] = []
    changed = 0
    for i, line in enumerate(lines, start=1):
        if i in protected:
            out.append(line)
            continue
        new_line = strip_em_from_line(line)
        if new_line != line:
            changed += 1
        out.append(new_line)
    path.write_text("".join(out), encoding="utf-8", newline="")
    return changed


def main() -> None:
    total = 0
    for f in FILES:
        if not f.exists():
            print(f"SKIP missing {f}", file=sys.stderr)
            continue
        n = process_file(f)
        total += n
        print(f"{f.name}: {n} lines altered")
    print(f"Total line changes (approx): {total}")


if __name__ == "__main__":
    main()
