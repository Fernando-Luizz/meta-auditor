"""Classes/CSS de impressão do Apêndice A1 (A1.2 no PDF)."""
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
    # Call sites only (skip the Jinja import that also mentions the macro name).
    for part in body.split("correcao_detalhada(")[1:]:
        assert "|safe" not in part[:200]
        assert "clean_report_text" in part[:200]


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


def test_wcag_nivel_exibir_macro_uses_inferir_for_253():
    macros = REPORT_MACROS.read_text(encoding="utf-8")
    assert "inferir_wcag_nivel" in macros
    assert "wcag_nivel_exibir" in macros
    from app.services.consolidation import inferir_wcag_nivel

    assert inferir_wcag_nivel("2.5.3 Label in Name") == "a"


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


def test_score_legend_below_scorecard_in_part_a():
    part_a = (ROOT / "app" / "templates" / "report_body_a.html").read_text(encoding="utf-8")
    assert "_score_legend.html" in part_a
    assert part_a.index("ma-scorecard") < part_a.index("_score_legend.html")
    legend = (ROOT / "app" / "templates" / "_score_legend.html").read_text(encoding="utf-8")
    assert "Escala" in legend and "0–10" in legend
    assert "Score de Risco Meta-Auditor" in legend
    body_b = REPORT_BODY_B.read_text(encoding="utf-8")
    assert body_b.count("Como ler os scores") == 0


def test_approved_list_uses_lighthouse_passed_label():
    body_b = REPORT_BODY_B.read_text(encoding="utf-8")
    assert "lighthouse_passed_label" in body_b
    assert "truncate_words" in body_b
    from app.services.display_labels import lighthouse_passed_label

    label = lighthouse_passed_label(
        {"id": "aria-deprecated-role", "title": "Deprecated ARIA roles were not used"}
    )
    assert "obsoleto" in label.lower()
    assert "Deprecated" not in label


def _sample_audit_row() -> dict:
    return {
        "id": 99,
        "url": "https://www.exemplo.gov.br/",
        "created_at": "2026-05-29T12:00:00",
        "lh_score": 0.82,
        "wave_aim_score": 2.6,
        "wave_error_count": 3,
        "wave_contrast_count": 1,
        "report": {
            "barreiras_automaticas": [
                {
                    "issue_tipo_normalizado": "imagem_link_sem_texto_alternativo",
                    "titulo_tecnico": "Link-imagem sem texto alternativo",
                    "prioridade": "alta",
                    "wcag_criterio": "2.4.4 Link Purpose",
                    "correcao_sugerida": (
                        "O time de conteúdo e desenvolvimento precisa garantir que cada imagem-link tenha um "
                        "texto alternativo que explique a ação ou o destino do link. "
                        "Quando o usuário lê o texto na tela e fala esse comando, o sistema deve reconhecer "
                        "a frase sem variações ou truncamentos adicionais no nome acessível do controle interativo visível."
                    ),
                    "ocorrencias_count": 2,
                    "publico_afetado": "Leitores de tela",
                }
            ],
            "itens_aprovados": [
                {"id": "aria-deprecated-role", "title": "Deprecated ARIA roles were not used"},
                {"id": "aria-allowed-attr", "title": "`[aria-*]` attributes match their roles"},
            ],
            "score_risco": {"valor": 2.5, "nivel": "ALTO", "n_alta": 1, "n_media": 0, "n_baixa": 0},
        },
        "score_breakdown": {"passed_audits_count": 18, "scored_audits_count": 20, "total_weight": 100},
    }


def test_build_report_html_and_pdf_share_ux_fixes():
    from app.main import _build_report_html

    html_screen = _build_report_html(_sample_audit_row(), pdf_mode=False)
    html_pdf = _build_report_html(_sample_audit_row(), pdf_mode=True)

    for html in (html_screen, html_pdf):
        assert "Como ler os scores" in html
        assert html.index("ma-scorecard") < html.index("Como ler os scores")
        assert "Escala" in html and "0–10" in html
        assert "Score de Risco Meta-Auditor" in html
        assert "nível executivo" in html
        assert "sem barreiras de severidade alta" in html
        assert "barreiras de severidade alta" in html
        assert "alta prioridade" not in html.split("Resumo Executivo", 1)[0].lower()
        assert "Meta-Auditor" in html
        assert "/10</span>" in html
        assert "Nenhum papel ARIA obsoleto" in html
        approved = html.split("O que está correto", 1)[1].split("Parâmetros da avaliação", 1)[0]
        assert "Deprecated ARIA" not in approved
        checklist = html.split("Checklist de correção", 1)[1].split("Apêndice", 1)[0]
        assert " ou o..." not in checklist
        assert "truncate_words" not in html  # filtro aplicado no render, não no HTML final
        assert "Checklist de correção" in html

    assert 'class="ma-export-bar no-print"' in html_screen
    assert 'class="ma-export-bar no-print"' not in html_pdf


def test_export_pdf_uses_inline_html_render():
    import inspect

    from app import main as main_mod

    src = inspect.getsource(main_mod.audit_export_pdf)
    assert "render_report_pdf" in src
    assert "_build_report_html(row, pdf_mode=True)" in src
