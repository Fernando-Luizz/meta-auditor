"""
Gera PDF de uma auditoria pelo ID (servidor local ou HTML em arquivo).

    python scripts/export_report_pdf.py --audit-id 5
    python scripts/export_report_pdf.py --html relatorio.html -o globo.pdf

Requer Chromium do Playwright.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.pdf_export import build_pdf_target_urls, render_report_pdf_from_urls  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Exportar relatório Meta-Auditor para PDF")
    p.add_argument("--audit-id", type=int, help="ID da auditoria no banco local")
    p.add_argument("--html", type=Path, help="Arquivo HTML já exportado")
    p.add_argument("-o", "--output", type=Path, help="Caminho do PDF de saída")
    args = p.parse_args()

    if args.html:
        html = args.html.read_text(encoding="utf-8")
        out = args.output or args.html.with_suffix(".pdf")
    elif args.audit_id is not None:
        import asyncio

        from app.config import DB_PATH
        from app.database import get_audit, init_db
        from app.main import _ensure_nivel2

        async def _prepare() -> None:
            await init_db(DB_PATH)
            row = await get_audit(DB_PATH, args.audit_id)
            if row is None:
                raise SystemExit(f"Auditoria {args.audit_id} não encontrada em {DB_PATH}")
            await _ensure_nivel2(args.audit_id, row)

        asyncio.run(_prepare())
        out = args.output or ROOT / f"relatorio-acessibilidade-{args.audit_id}.pdf"
        urls = build_pdf_target_urls(args.audit_id)
        render_report_pdf_from_urls(urls, out)
        print(f"OK: {out}")
        return
    else:
        p.error("Informe --audit-id ou --html")

    from app.services.pdf_export import render_report_pdf

    pdf = render_report_pdf(html)
    out.write_bytes(pdf)
    print(f"OK: {out}")


if __name__ == "__main__":
    main()
