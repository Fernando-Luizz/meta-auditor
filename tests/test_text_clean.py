"""Testes de normalização de texto para relatórios."""

from app.services.text_clean import (
    normalize_executive_plaintext,
    normalize_html_breaks,
    normalize_report_dashes,
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


def test_normalize_executive_plaintext_no_literal_br() -> None:
    s = normalize_executive_plaintext("Primeiro&lt;br/&gt;Segundo <br> Terceiro")
    assert "<br" not in s.lower()
    assert "lt;br" not in s.lower()
    assert "\n" in s
