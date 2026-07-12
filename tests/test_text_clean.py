"""Testes de normalização de texto para relatórios."""

from app.services.text_clean import (
    barrier_exec_text,
    format_html_tag_literals,
    normalize_barrier_ai_texts,
    normalize_executive_plaintext,
    normalize_html_breaks,
    normalize_report_dashes,
    normalize_report_markup_text,
    strip_emoji,
    truncate_words,
)


def test_normalize_report_dashes_preserves_numeric_ranges() -> None:
    assert "30-40%" in normalize_report_dashes("30\u201340%")
    assert "30-40%" in normalize_report_dashes("30\u201440%")
    assert "4-6" in normalize_report_dashes("4\u20136")


def test_normalize_report_dashes_prose_em_dash() -> None:
    assert "Link: destino claro" in normalize_report_dashes("Link \u2014 destino claro")
    assert "A: B" in normalize_report_dashes("A \u2014 B")


def test_strip_emoji_removes_pictographs() -> None:
    assert "ok" in strip_emoji("ok 👍 test").lower()


def test_normalize_html_breaks_double_encoded_entities() -> None:
    out = normalize_html_breaks("a&amp;lt;br&amp;gt;b")
    assert "<br" not in out.lower()
    assert "\n" in out or "a" in out


def test_normalize_report_markup_text_unescapes_double_encoded_tags() -> None:
    out = normalize_report_markup_text(
        "&lt;code&gt;&amp;lt;main&amp;gt;&lt;/code&gt;"
    )
    assert out == "<main>"
    assert "&lt;" not in out
    assert "&amp;" not in out
    assert "<code>" not in out


def test_normalize_report_markup_text_unescapes_numeric_entities() -> None:
    assert normalize_report_markup_text("&#34;campo de texto&#34;") == '"campo de texto"'


def test_normalize_pt_text_fixes_conductar_anglicism() -> None:
    assert "Realizar teste manual" in normalize_executive_plaintext(
        "Conductar teste manual com usuários que possuem limitações motoras"
    )
    assert "conductar" not in normalize_executive_plaintext("Conductar teste").lower()


def test_normalize_report_markup_text_strips_code_wrapper() -> None:
    out = normalize_report_markup_text("<code>&lt;ul&gt;</code> ou <ol>")
    assert "<code>" not in out
    assert "<ul>" in out


def test_format_html_tag_literals_wraps_tags_in_code() -> None:
    out = str(
        format_html_tag_literals(
            "Use um único elemento <main> com <ul> ou <ol> e <li> filhos."
        )
    )
    assert "<code>&lt;main&gt;</code>" in out
    assert "<code>&lt;ul&gt;</code>" in out
    assert "<code>&lt;li&gt;</code>" in out
    assert "<main>" not in out


def test_normalize_executive_plaintext_no_literal_br() -> None:
    s = normalize_executive_plaintext("Primeiro&lt;br/&gt;Segundo <br> Terceiro")
    assert "<br" not in s.lower()
    assert "lt;br" not in s.lower()
    assert "\n" in s


def test_normalize_barrier_ai_texts_label_in_name_fixes() -> None:
    b = {
        "issue_id_original": "label-content-name-mismatch",
        "issue_tipo_normalizado": "rotulo_difere_do_nome_acessivel",
        "wcag_criterio": "2.5.3 Label in Name",
        "como_corrigir_claro": (
            "O texto visível em cada cartão precisa ser idêntico ao nome que o sistema registra internamente."
        ),
        "versao_dev": "WCAG 2.5.3 Label in Name: Nível AA",
        "texto_ticket": {"descricao": "2.5.3 Label in Name: Nível AA"},
    }
    normalize_barrier_ai_texts(b)
    assert "idêntic" not in b["como_corrigir_claro"].lower()
    assert "conter o texto visível" in b["como_corrigir_claro"]
    assert "Nível A" in b["versao_dev"]
    assert "Nível AA" not in b["texto_ticket"]["descricao"]


def test_barrier_exec_text_cartao_servico_from_evcodes() -> None:
    b = {
        "issue_id_original": "label-content-name-mismatch",
        "wcag_criterio": "2.5.3 Label in Name",
        "evcodes": ["a.service-card href=?id=carta_de_servico_renovar_cnh"],
        "como_corrigir_claro": (
            "O nome acessível deve conter o texto visível do link, preferencialmente no início, "
            "para que usuários de controle por voz consigam acionar o elemento pelo texto que enxergam na tela."
        ),
    }
    out = barrier_exec_text(b["como_corrigir_claro"], b)
    assert "cartão" in out
    assert "do link" not in out


def test_truncate_words_cuts_on_word_boundary() -> None:
    text = (
        "O time de conteúdo e desenvolvimento precisa garantir que cada imagem-link tenha um "
        "texto alternativo que explique a ação ou o destino do link. "
        "Quando o usuário lê o texto na tela e fala esse comando, o sistema deve reconhecer "
        "a frase sem variações ou truncamentos adicionais no nome acessível do controle interativo visível."
    )
    out = truncate_words(text, 320)
    assert out.endswith("...")
    assert " ou o..." not in out
    assert "destino" in out or "ação" in out


def test_truncate_words_short_text_unchanged() -> None:
    assert truncate_words("Texto curto", 50) == "Texto curto"


def test_normalize_executive_plaintext_fixes_severidade_lex() -> None:
    out = normalize_executive_plaintext(
        "O portal apresenta 3 barreiras de alta prioridade e 2 de média prioridade."
    )
    assert "severidade alta" in out
    assert "severidade média" in out
    assert "alta prioridade" not in out.lower()
    assert "média prioridade" not in out.lower()
