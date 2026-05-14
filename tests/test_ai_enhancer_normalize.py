"""Testes de normalização de texto do ai_enhancer."""

from app.services.ai_enhancer import _normalize_pt_text


def test_normalize_pt_text_br_tags_to_newlines() -> None:
    assert _normalize_pt_text("a<br>b") == "a\nb"
    assert _normalize_pt_text("a<BR/>b") == "a\nb"
    assert _normalize_pt_text("a<br />b") == "a\nb"


def test_normalize_pt_text_escaped_br_entities() -> None:
    assert "\n" in _normalize_pt_text("x&lt;br&gt;y")
    assert "\n" in _normalize_pt_text("x&lt;br/&gt;y")


def test_normalize_pt_text_double_encoded_br() -> None:
    out = _normalize_pt_text("a&amp;lt;br&amp;gt;b")
    assert "<br" not in out.lower()
    assert "lt;br" not in out.lower()
