"""Testes de normalização de texto do ai_enhancer."""

from app.services.ai_enhancer import _acao_gerencial_hint, _normalize_pt_text


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


def test_acao_gerencial_hint_is_specific_per_barrier_type() -> None:
    contraste = _acao_gerencial_hint({"issue_tipo_normalizado": "contraste_insuficiente"})
    hierarquia = _acao_gerencial_hint({"issue_tipo_normalizado": "hierarquia_titulos_incorreta"})
    assert "cores" in contraste or "contraste" in contraste
    assert "títulos" in hierarquia or "titulos" in hierarquia
    assert "confirmação" not in contraste.lower()
    assert contraste != hierarquia


def test_acao_gerencial_hint_target_size_maps_to_motor_action() -> None:
    hint = _acao_gerencial_hint({"issue_tipo_normalizado": "alvo_interacao_pequeno"})
    assert "toque" in hint.lower() or "clique" in hint.lower()
