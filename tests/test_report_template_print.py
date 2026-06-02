"""Garante classes e CSS de impressão do Apêndice A1 (evita omitir A1.2 no PDF)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_HTML = ROOT / "app" / "templates" / "report.html"
REPORT_BODY_B = ROOT / "app" / "templates" / "report_body_b.html"
REPORT_MACROS = ROOT / "app" / "templates" / "_report_macros.html"


def _final_print_block(css: str) -> str:
    """Último bloco @media print (regras que vencem no PDF Playwright)."""
    marker = "/* PDF Playwright: sem cabeçalho/rodapé fixos"
    return css.split(marker, 1)[1]


def test_report_template_has_no_ai_usage_chip():
    html = REPORT_HTML.read_text(encoding="utf-8")
    assert "ma-usage-chip" not in html
    assert "cost_usd" not in html
    assert "total_tokens" not in html


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


def test_print_css_a1_tickets_keep_sub_cards_intact_in_pdf():
    block = _final_print_block(REPORT_HTML.read_text(encoding="utf-8"))
    idx = block.index(".ap-block--a1 .ap-ticket-sub,")
    section = block[idx : idx + 420]
    assert "break-inside: avoid !important" in section
    assert "overflow: visible !important" in section


def test_print_css_a1_outer_stack_allows_page_break():
    css = REPORT_HTML.read_text(encoding="utf-8")
    assert ".ap-block--a1 .ap-ticket-stack" in css
    stack_section = css.split(".ap-block--a1 .ap-ticket-stack", 1)[1][:200]
    assert "break-inside: auto !important" in stack_section


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


def test_label_in_name_executive_group_not_aria():
    from app.services.display_labels import executive_group_for, pour_bucket_for

    assert executive_group_for("rotulo_difere_do_nome_acessivel") == "Rótulo visível e nome acessível"
    assert executive_group_for("rotulo_difere_do_nome_acessivel") != "ARIA e semântica"
    assert pour_bucket_for({"issue_tipo_normalizado": "rotulo_difere_do_nome_acessivel"}) == "o"
    assert pour_bucket_for(
        {
            "issue_id_original": "label-content-name-mismatch",
            "issue_tipo_normalizado": "rotulo_difere_do_nome_acessivel",
            "wcag_criterio": "2.5.3 Label in Name",
        }
    ) == "o"
    assert pour_bucket_for({"issue_tipo_normalizado": "contraste_insuficiente"}) == "p"
    assert pour_bucket_for({"issue_tipo_normalizado": "aria_referencia_quebrada"}) == "r"


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


def test_a1_ai_ticket_uses_deterministic_contrast_criterio():
    body = REPORT_BODY_B.read_text(encoding="utf-8")
    assert "_ap_is_contrast" in body
    assert "criterio_pronto_det(b)" in body


def test_public_impact_chart_renders_voice_control():
    body = REPORT_BODY_B.read_text(encoding="utf-8")

    assert "cnt.voz" in body
    assert "ma_chart_pub_svg('voz')" in body
    assert "'Controle por voz', cnt.voz" in body
    assert "cnt.voz==0" in body


def test_evidence_executive_labels_no_validated_capture_wording():
    body = REPORT_BODY_B.read_text(encoding="utf-8")
    assert "_has_precise_visual" in body
    assert "_has_context_visual" in body
    assert "_is_wave_only" in body
    assert "Elemento destacado" in body
    assert "Imagem de contexto" in body
    assert "Onde procurar" in body
    assert "contraste insuficiente indicado pela auditoria" in body
    assert "possível contraste" not in body
    assert "confirmada pelo WAVE" in body
    assert "marcação visual exata do elemento na imagem" in body
    assert "seletores completos estão no" in body
    assert "Sem marcação visual exata" not in body
    assert "textos e botões" not in body
    assert "criterio_pronto_det" in body
    assert "Controle por voz" in body
    assert 'loading="eager"' in body
    assert "Captura ao vivo validada" not in body
    assert "Elemento detectado — recorte visual indisponível" not in body
    assert "Como ler esta imagem" not in body
    assert "ev-caption-hint" not in body


def test_evidence_context_note_for_management():
    body = REPORT_BODY_B.read_text(encoding="utf-8")
    assert "ev-caption-note" in body
    assert "não marca o ponto exato do achado" in body or "marcação visual exata do elemento" in body
    assert "ação recomendada está descrita abaixo" in body
    assert "WebAIM Contrast Checker" not in body


def test_evidence_context_card_styles():
    css = REPORT_HTML.read_text(encoding="utf-8")
    assert ".ev-caption-note {" in css
    assert ".ev-context-card {" in css
    assert ".ev-badge--context {" in css
    assert "background: #fffbeb" in css
    assert "border: 1px solid #fcd34d" in css


def test_macros_contrast_uses_dynamic_element_fields():
    macros = REPORT_MACROS.read_text(encoding="utf-8")
    assert "correcao_contraste_det" in macros
    assert "impacto_contraste_det" in macros
    assert "conforme indicado pela auditoria automática" in macros
    assert "têm dificuldade" in macros
    assert "Esta barreira pode impedir a leitura" not in macros.split("impacto_contraste_det")[1][:400]
    idx = macros.index("impacto_contraste_det")
    assert "bloqueia o acesso" not in macros[idx : idx + 400]
    body = REPORT_BODY_B.read_text(encoding="utf-8")
    assert "elementos_contraste_onde_frase" in body
    assert "is_contraste" in body
    rb = (ROOT / "app" / "templates" / "report_body.html").read_text(encoding="utf-8")
    assert "{% for b in bars %}" in rb
    assert "criterio_pronto_det" in body
