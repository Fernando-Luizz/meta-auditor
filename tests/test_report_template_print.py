"""Garante classes e CSS de impressão do Apêndice A1 (evita omitir A1.2 no PDF)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_HTML = ROOT / "app" / "templates" / "report.html"
REPORT_BODY_B = ROOT / "app" / "templates" / "report_body_b.html"


def _final_print_block(css: str) -> str:
    """Último bloco @media print (regras que vencem no PDF Playwright)."""
    marker = "/* PDF Playwright: sem cabeçalho/rodapé fixos"
    return css.split(marker, 1)[1]


def test_print_css_hides_fixed_header_and_footer_in_pdf():
    block = _final_print_block(REPORT_HTML.read_text(encoding="utf-8"))
    assert ".ma-print-header," in block
    assert "display: none !important" in block.split(".ma-print-header")[1]
    assert "position: static !important" in block


def test_print_css_page_margin_without_fixed_header():
    block = _final_print_block(REPORT_HTML.read_text(encoding="utf-8"))
    assert "margin: 10mm 8mm 12mm 8mm !important" in block


def test_pdf_export_top_margin_matches_template_page():
    from app.services import pdf_export

    assert pdf_export._PDF_MARGIN_TOP == "10mm"
    assert pdf_export._PDF_MARGIN_SIDE == "8mm"
    assert pdf_export._PDF_MARGIN_BOTTOM == "12mm"


def test_print_css_shows_executive_cover_not_hidden():
    css = REPORT_HTML.read_text(encoding="utf-8")
    assert ".ma-header {" in css or ".ma-header{" in css.replace(" ", "")
    assert "display: block !important" in css
    assert "display: none !important" not in css.split(".ma-header {")[1].split("}")[0]


def test_a1_block_has_print_specific_classes():
    body = REPORT_BODY_B.read_text(encoding="utf-8")
    assert 'class="ap-block ap-block--a1"' in body
    assert 'class="ap-barrier-block ap-barrier-block--a1"' in body


def test_print_css_allows_a1_page_breaks():
    css = REPORT_HTML.read_text(encoding="utf-8")
    assert ".ap-block.ap-block--a1" in css
    assert ".ap-block--a1 .ap-barrier-block" in css
    assert "break-inside: auto !important" in css
    assert ".ap-block--a1 .tk-row" in css
    assert "display: block !important" in css


def test_report_body_uses_clean_report_text_not_format_html_tags():
    body = REPORT_BODY_B.read_text(encoding="utf-8")
    assert "clean_report_text" in body
    assert "format_html_tags" not in body
    assert "|safe" not in body.split("correcao_detalhada")[1][:2000]


def test_print_css_a1_tickets_allow_natural_break_in_pdf():
    block = _final_print_block(REPORT_HTML.read_text(encoding="utf-8"))
    idx = block.index(".ap-block--a1 .ap-ticket-sub,")
    section = block[idx : idx + 380]
    assert "break-inside: auto !important" in section


def test_report_html_has_no_window_print():
    html = REPORT_HTML.read_text(encoding="utf-8")
    assert "window.print" not in html


def test_report_html_footer_avoids_orphan_page_in_pdf():
    block = _final_print_block(REPORT_HTML.read_text(encoding="utf-8"))
    assert ".footer {" in block
    assert "page-break-before: avoid" in block.split(".footer {", 1)[1]


def test_pdf_export_definitive_print_css():
    css = REPORT_HTML.read_text(encoding="utf-8")
    assert "FIX DEFINITIVO DE PDF" in css
    assert "overflow-wrap: anywhere !important" in css


def test_titulo_pagina_invalido_nao_cai_em_idioma():
    from app.services.display_labels import executive_group_for

    assert executive_group_for("titulo_pagina_invalido") == "Títulos e estrutura"


def test_print_css_keeps_ticket_subhead_with_following_content():
    block = _final_print_block(REPORT_HTML.read_text(encoding="utf-8"))
    assert ".ap-ticket-subhead," in block
    assert "break-after: avoid-page !important" in block


def test_print_css_barrier_cards_allow_page_breaks():
    css = REPORT_HTML.read_text(encoding="utf-8")
    assert ".ma-bc{" in css.replace(" ", "") or ".ma-bc {" in css
    assert "break-inside: auto" in css
    assert "page-break-inside: auto !important" in css
    assert ".ma-bc-appendix-ref--quiet" in css
    assert "display: none !important" in css


def test_print_css_appendix_blocks_do_not_force_blank_page():
    css = REPORT_HTML.read_text(encoding="utf-8")
    assert ".ap-block + .ap-block" in css
    assert "page-break-before: auto !important" in css


def test_pdf_export_disables_browser_header_footer():
    from app.services.pdf_export import render_report_pdf, render_report_pdf_from_urls
    import inspect

    assert "display_header_footer=False" in inspect.getsource(render_report_pdf)
    assert "display_header_footer=False" in inspect.getsource(render_report_pdf_from_urls)
    assert "prefer_css_page_size=True" in inspect.getsource(render_report_pdf_from_urls)


def test_build_pdf_target_urls_includes_internal_base():
    from app.services.pdf_export import build_pdf_target_urls
    import os

    os.environ["META_AUDITOR_INTERNAL_BASE_URL"] = "http://127.0.0.1:8000"
    urls = build_pdf_target_urls(5, "http://localhost:8010")
    assert urls[0] == "http://127.0.0.1:8000/audits/5/report.html?pdf=1"
    assert any("localhost:8010" in u for u in urls)


def test_report_html_print_query_redirects_to_export_pdf():
    from app.main import audit_report_html
    import inspect

    src = inspect.getsource(audit_report_html)
    assert "print_mode" in src
    assert "RedirectResponse" in src
    assert "export.pdf" in src
