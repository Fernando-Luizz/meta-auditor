"""Inferência de elementos afetados em barreiras de contraste."""
from app.services.contrast_elements import (
    correcao_contraste_deterministica,
    criterio_pronto_contraste_det,
    enrich_contrast_fields,
    inferir_elementos_contraste,
    impacto_contraste_deterministico,
    is_contrast_barrier,
)
from app.services.text_clean import normalize_barrier_ai_texts
from app.services.display_labels import attach_display_fields


def _barreira(evidencia: list[str] | None = None, **extra) -> dict:
    return {
        "issue_tipo_normalizado": "contraste_insuficiente",
        "issue_id_original": "color-contrast",
        "evidencia_localizacao": evidencia,
        **extra,
    }


def test_inferir_h2_e_paragrafo_tcu():
    b = _barreira(["main h2.titulo", "section p.intro"])
    assert (
        inferir_elementos_contraste(b)
        == "elementos de texto indicados pela ferramenta, como título de seção e parágrafo"
    )


def test_inferir_ignora_h1_no_caminho():
    path = "HTML > BODY > MAIN > H1 + SECTION > DIV > H2"
    b = _barreira([path, "HTML > BODY > MAIN > H1 + SECTION > DIV > P"])
    assert inferir_elementos_contraste(b) == (
        "elementos de texto indicados pela ferramenta, como título de seção e parágrafo"
    )
    assert "título principal" not in inferir_elementos_contraste(b)


def test_is_contrast_wave_issue_id():
    b = {
        "issue_id_original": "contrast",
        "issue_tipo_normalizado": "contraste_insuficiente",
        "wave_categoria": "contrast",
    }
    assert is_contrast_barrier(b)
    enrich_contrast_fields(b)
    assert b.get("is_contraste") is True
    assert "contraste insuficiente entre texto e fundo, conforme indicado pela auditoria automática" in b.get("impacto_contraste_det", "")
    assert "têm dificuldade" in b.get("impacto_contraste_det", "")
    assert "possível" not in b.get("impacto_contraste_det", "")
    assert "Esta barreira pode impedir a leitura" not in b.get("impacto_contraste_det", "")


def test_inferir_apenas_botao():
    b = _barreira(["button.btn-primary", "input[type=submit]"])
    assert inferir_elementos_contraste(b) == "botões indicados pela ferramenta"


def test_inferir_fallback_sem_seletores():
    b = _barreira(None)
    assert inferir_elementos_contraste(b) == "elementos indicados pela ferramenta"


def test_impacto_botao_vs_texto():
    texto = _barreira(["h2", "p"])
    botao = _barreira(["button.cta"])
    assert "identificar ou ler a ação" in impacto_contraste_deterministico(botao)
    assert "ampliação, baixa iluminação" in impacto_contraste_deterministico(texto)


def test_enrich_via_attach_display_fields():
    b = _barreira(["h2", "p"])
    attach_display_fields([b])
    assert is_contrast_barrier(b)
    assert "título de seção" in b["elementos_contraste_humano"]
    assert "conforme indicado pela auditoria automática" in b["impacto_contraste_det"]
    assert "têm dificuldade" in b["impacto_contraste_det"]
    assert "possível" not in b["impacto_contraste_det"]
    assert "4.5:1" in b["correcao_contraste_det"]
    assert "elementos de texto como" in b["elementos_contraste_onde_frase"]


def test_correcao_menciona_elementos():
    b = _barreira(["button.x"])
    enrich_contrast_fields(b)
    assert "botões indicados pela ferramenta" in correcao_contraste_deterministica(b)


def test_criterio_pronto_contraste_texto_grande_nao_graficos():
    b = _barreira(ocorrencias_count=2)
    txt = criterio_pronto_contraste_det(b)
    assert "dos 2 elementos" in txt
    assert "4.5:1 em texto normal" in txt
    assert "3:1 em texto grande" in txt
    assert "WCAG 1.4.3" in txt
    assert "elementos gráficos" not in txt


def test_normalize_barrier_ai_texts_overrides_contrast_criterio():
    b = _barreira(ocorrencias_count=2)
    b["texto_ticket"] = {
        "titulo": "Corrigir contraste",
        "descricao": "Texto ilegível.",
        "criterio_de_pronto": "Atingir 3:1 (elementos gráficos).",
    }
    normalize_barrier_ai_texts(b)
    assert "3:1 em texto grande" in b["texto_ticket"]["criterio_de_pronto"]
    assert "elementos gráficos" not in b["texto_ticket"]["criterio_de_pronto"]
