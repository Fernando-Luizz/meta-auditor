"""Testes de normalização de texto para relatórios."""

from app.services.text_clean import (
    format_html_tag_literals,
    normalize_executive_plaintext,
    normalize_html_breaks,
    normalize_report_dashes,
    normalize_report_markup_text,
    strip_emoji,
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
