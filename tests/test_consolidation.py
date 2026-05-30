"""Consolidação, convergência cruzada e prioridades."""
from app.services.consolidation import (
    assign_prioridade,
    build_report,
    calcular_nivel_risco_executivo,
    calcular_prioridade_barreira,
    detect_divergencias,
    enriquecer_prioridades_barreiras,
    inferir_wcag_nivel,
    merge_barreiras_por_tipo_e_url,
    merge_by_normalized_type,
)


def _issue(
    *,
    tool: str,
    tipo: str,
    url: str = "https://example.com/",
    confirmado: list[str],
    status: str = "automatico_detectado",
    evidencia: list[str] | None = None,
    occ: int = 1,
    wave_cat: str | None = None,
    issue_orig: str = "x",
    lh_id: str | None = None,
):
    return {
        "tool": tool,
        "issue_id_original": issue_orig,
        "issue_tipo_normalizado": tipo,
        "titulo_tecnico": "t",
        "descricao_tecnica": "d",
        "wcag_criterio": "4.1.2",
        "publico_afetado": "Leitores de tela",
        "evidencia_localizacao": evidencia,
        "status_deteccao": status,
        "confirmado_por": confirmado,
        "validacao_manual_necessaria": False,
        "ocorrencias_count": occ,
        "wave_categoria": wave_cat,
        "lighthouse_audit_id": lh_id,
        "page_url": url,
    }


def test_merge_by_fingerprint_splits_different_selectors():
    a = _issue(
        tool="lighthouse",
        tipo="link_sem_nome_acessivel",
        confirmado=["lighthouse"],
        evidencia=["a.btn"],
        issue_orig="link-name",
        lh_id="link-name",
    )
    b = _issue(
        tool="wave",
        tipo="link_sem_nome_acessivel",
        confirmado=["wave"],
        evidencia=["footer a"],
        wave_cat="error",
        issue_orig="link_empty",
    )
    m = merge_by_normalized_type([a, b])
    assert len(m) == 2


def test_second_pass_merges_lighthouse_and_wave_same_tipo():
    a = _issue(
        tool="lighthouse",
        tipo="link_sem_nome_acessivel",
        confirmado=["lighthouse"],
        evidencia=["a.one"],
        issue_orig="link-name",
        lh_id="link-name",
    )
    b = _issue(
        tool="wave",
        tipo="link_sem_nome_acessivel",
        confirmado=["wave"],
        evidencia=["a.two"],
        wave_cat="error",
        issue_orig="link_empty",
    )
    first = merge_by_normalized_type([a, b])
    assert len(first) == 2
    second = merge_barreiras_por_tipo_e_url(first)
    assert len(second) == 1
    row = second[0]
    assert set(row["confirmado_por"]) == {"lighthouse", "wave"}
    assert row["status_deteccao"] == "automatico_convergente"
    assert row["tool"] == "consolidated"
    assert "a.one" in (row["evidencia_localizacao"] or [])
    assert "a.two" in (row["evidencia_localizacao"] or [])


def test_assign_prioridade_convergente_alta():
    assert (
        assign_prioridade(["lighthouse", "wave"], "automatico_convergente", None) == "alta"
    )


def test_build_report_runs_end_to_end():
    lh = [
        _issue(
            tool="lighthouse",
            tipo="controle_sem_nome_acessivel",
            confirmado=["lighthouse"],
            evidencia=["button.x"],
            issue_orig="button-name",
            lh_id="button-name",
        )
    ]
    w_bar = [
        _issue(
            tool="wave",
            tipo="contraste_insuficiente",
            confirmado=["wave"],
            wave_cat="contrast",
            issue_orig="contrast",
            occ=5,
        )
    ]
    rep = build_report(lh, w_bar, [], [], [])
    assert "barreiras_automaticas" in rep
    assert "checks_manuais" in rep
    assert rep.get("divergencias") == []
    b = rep["barreiras_automaticas"]
    tipos = {x["issue_tipo_normalizado"] for x in b}
    assert "controle_sem_nome_acessivel" in tipos
    assert "contraste_insuficiente" in tipos
    assert rep.get("itens_aprovados") == []
    for row in b:
        assert row.get("rotulo_exibicao")
        assert row.get("categoria_executiva")
        assert row.get("categoria_grafico") in (
            "contraste",
            "botao",
            "imagem",
            "link",
            "form",
            "aria",
            "outro",
        )


def test_build_report_itens_aprovados_limita_e_filtra():
    passed = [{"id": f"a{i}", "title": f"Título {i}", "score": 1} for i in range(25)]
    rep = build_report([], [], [], [], [], lh_passed_audits=passed)
    items = rep.get("itens_aprovados") or []
    assert len(items) == 20
    assert items[0] == {"id": "a0", "title": "Título 0"}
    rep2 = build_report(
        [],
        [],
        [],
        [],
        [],
        lh_passed_audits=[{"id": "x"}, {"title": "Só título"}],
    )
    assert rep2.get("itens_aprovados") == [{"id": "", "title": "Só título"}]


def test_divergencia_detectada_lh_passou_wave_barreira():
    w = _issue(
        tool="wave",
        tipo="contraste_insuficiente",
        confirmado=["wave"],
        wave_cat="contrast",
        issue_orig="c",
        occ=3,
    )
    d = detect_divergencias([w], {"contraste_insuficiente"})
    assert len(d) == 1
    assert d[0]["issue_tipo_normalizado"] == "contraste_insuficiente"
    assert d[0]["lighthouse_status"] == "passou"
    assert d[0]["wave_count"] == 3
    assert d[0]["decisao"] == "resultado_mais_restritivo_prevalece"
    assert "Lighthouse" in d[0]["nota"] and "WAVE" in d[0]["nota"]


def test_sem_divergencia_quando_lh_tambem_reprovou():
    w = _issue(
        tool="wave",
        tipo="link_sem_nome_acessivel",
        confirmado=["wave"],
        wave_cat="error",
        issue_orig="l",
        occ=1,
    )
    assert detect_divergencias([w], set()) == []


def test_divergencia_wave_error_gera_nota_diferente_de_contraste():
    w_err = _issue(
        tool="wave",
        tipo="imagem_sem_texto_alternativo",
        confirmado=["wave"],
        wave_cat="error",
        issue_orig="a",
        occ=2,
    )
    w_con = _issue(
        tool="wave",
        tipo="contraste_insuficiente",
        confirmado=["wave"],
        wave_cat="contrast",
        issue_orig="c",
        occ=1,
    )
    d_err = detect_divergencias([w_err], {"imagem_sem_texto_alternativo"})[0]["nota"]
    d_con = detect_divergencias([w_con], {"contraste_insuficiente"})[0]["nota"]
    assert "erro confirmado" in d_err
    assert "PSI" in d_con or "Lighthouse" in d_con


def test_divergencia_acumula_wave_count_mesmo_tipo():
    a = _issue(
        tool="wave",
        tipo="imagem_sem_texto_alternativo",
        confirmado=["wave"],
        wave_cat="error",
        issue_orig="alt_missing",
        occ=2,
    )
    b = _issue(
        tool="wave",
        tipo="imagem_sem_texto_alternativo",
        confirmado=["wave"],
        wave_cat="error",
        issue_orig="alt_link_missing",
        occ=3,
    )
    d = detect_divergencias([a, b], {"imagem_sem_texto_alternativo"})
    assert len(d) == 1
    assert d[0]["wave_count"] == 5


def test_divergencias_ordenadas_por_wave_count():
    low = _issue(
        tool="wave",
        tipo="tipo_baixo",
        confirmado=["wave"],
        wave_cat="error",
        occ=1,
    )
    high = _issue(
        tool="wave",
        tipo="tipo_alto",
        confirmado=["wave"],
        wave_cat="error",
        occ=99,
    )
    d = detect_divergencias([low, high], {"tipo_baixo", "tipo_alto"})
    assert [x["issue_tipo_normalizado"] for x in d] == ["tipo_alto", "tipo_baixo"]


def test_build_report_retorna_divergencias_com_lh_passed():
    lh = [
        _issue(
            tool="lighthouse",
            tipo="outro_tipo",
            confirmado=["lighthouse"],
            evidencia=["x"],
            issue_orig="i",
            lh_id="i",
        )
    ]
    w = _issue(
        tool="wave",
        tipo="contraste_insuficiente",
        confirmado=["wave"],
        wave_cat="contrast",
        occ=4,
    )
    rep = build_report(lh, [w], [], [], [], lh_passed_tipo_set={"contraste_insuficiente"})
    assert len(rep["divergencias"]) == 1
    assert rep["divergencias"][0]["issue_tipo_normalizado"] == "contraste_insuficiente"


def test_build_report_preserva_page_url_e_rotulo_uma_pagina():
    u = "https://example.com/"
    lh = [
        _issue(
            tool="lighthouse",
            tipo="t1",
            confirmado=["lighthouse"],
            url=u,
            issue_orig="i",
            lh_id="i",
        )
    ]
    rep = build_report(lh, [], [], [], [])
    row = rep["barreiras_automaticas"][0]
    assert row.get("page_url") == u
    assert row.get("page_label") == "Página principal"
    assert rep.get("multi_page") is False
    assert rep.get("page_map") == {"Página principal": u}


def test_build_report_multi_page_rotulos_numericos():
    u1 = "https://a.example/p1"
    u2 = "https://a.example/p2"
    lh = [
        _issue(
            tool="lighthouse",
            tipo="t_a",
            confirmado=["lighthouse"],
            url=u1,
            evidencia=["sel1"],
            issue_orig="a",
            lh_id="a",
        ),
    ]
    w = [
        _issue(
            tool="wave",
            tipo="t_b",
            confirmado=["wave"],
            url=u2,
            wave_cat="error",
            evidencia=["sel2"],
            issue_orig="b",
        ),
    ]
    rep = build_report(lh, w, [], [], [])
    assert rep.get("multi_page") is True
    by_url = {r.get("page_url"): r.get("page_label") for r in rep["barreiras_automaticas"]}
    assert by_url[u1] == "Página 1"
    assert by_url[u2] == "Página 2"
    inv = rep.get("page_map") or {}
    assert inv.get("Página 1") == u1 and inv.get("Página 2") == u2


def test_build_report_sem_lh_passed_divergencias_vazio():
    lh = [
        _issue(
            tool="lighthouse",
            tipo="t",
            confirmado=["lighthouse"],
            issue_orig="i",
            lh_id="i",
        )
    ]
    w = _issue(
        tool="wave",
        tipo="contraste_insuficiente",
        confirmado=["wave"],
        wave_cat="contrast",
        occ=1,
    )
    rep = build_report(lh, [w], [], [], [])
    assert rep["divergencias"] == []


def test_divergencia_nao_listada_quando_mesmo_tipo_ja_falhou_no_lh():
    """LH e WAVE no mesmo tipo: sem entrada em passed — barreira convergente, sem divergência."""
    lh_fail = [
        _issue(
            tool="lighthouse",
            tipo="link_sem_nome_acessivel",
            confirmado=["lighthouse"],
            evidencia=["a"],
            issue_orig="link-name",
            lh_id="link-name",
        )
    ]
    w = _issue(
        tool="wave",
        tipo="link_sem_nome_acessivel",
        confirmado=["wave"],
        wave_cat="error",
        issue_orig="le",
        occ=2,
    )
    rep = build_report(lh_fail, [w], [], [], [], lh_passed_tipo_set=set())
    assert rep["divergencias"] == []
    rows = rep["barreiras_automaticas"]
    assert len(rows) == 1
    assert rows[0]["status_deteccao"] == "automatico_convergente"
    assert "lighthouse" in rows[0]["confirmado_por"] and "wave" in rows[0]["confirmado_por"]


def test_score_risco_alto_quando_ha_barreira_alta_mesmo_com_media_baixa():
    """1 convergente (alta) + 3 só Lighthouse (média) → score 2,0; nível deve ser ALTO."""
    tipos = [
        "controle_sem_nome_acessivel",
        "formulario_sem_rotulo",
        "link_sem_nome_acessivel",
        "imagem_sem_texto_alternativo",
    ]
    lh = [
        _issue(
            tool="lighthouse",
            tipo=t,
            confirmado=["lighthouse"],
            evidencia=[f"sel-{t}"],
            issue_orig=f"lh-{t}",
            lh_id=f"lh-{t}",
        )
        for t in tipos
    ]
    w_conv = _issue(
        tool="wave",
        tipo=tipos[0],
        confirmado=["wave"],
        wave_cat="error",
        evidencia=["sel-wave"],
        issue_orig="le",
    )
    rep = build_report(lh, [w_conv], [], [], [])
    sr = rep["score_risco"]
    assert sr["n_alta"] == 1
    assert sr["n_media"] == 3
    assert sr["valor"] == 2.25  # (3 + 2 + 2 + 2) / 4 — regra antiga (>2,5) caía em MÉDIO
    assert sr["nivel"] == "ALTO"


def test_score_risco_limite_250_com_barreira_alta_nivel_alto():
    """2 convergentes + 2 só Lighthouse → score 2,50; regra antiga (>2,5) caía em MÉDIO."""
    tipos = ["tipo_a", "tipo_b", "tipo_c", "tipo_d"]
    lh = [
        _issue(
            tool="lighthouse",
            tipo=t,
            confirmado=["lighthouse"],
            evidencia=[f"lh-{t}"],
            issue_orig=f"id-{t}",
            lh_id=f"id-{t}",
        )
        for t in tipos
    ]
    w = [
        _issue(
            tool="wave",
            tipo=tipos[0],
            confirmado=["wave"],
            wave_cat="error",
            evidencia=["w-a"],
            issue_orig="wa",
        ),
        _issue(
            tool="wave",
            tipo=tipos[1],
            confirmado=["wave"],
            wave_cat="error",
            evidencia=["w-b"],
            issue_orig="wb",
        ),
    ]
    rep = build_report(lh, w, [], [], [])
    sr = rep["score_risco"]
    assert sr["n_alta"] == 2
    assert sr["n_media"] == 2
    assert sr["valor"] == 2.5
    assert sr["nivel"] == "ALTO"


def test_nivel_risco_critico_quando_score_280_ou_mais():
    assert calcular_nivel_risco_executivo(3.00, 3) == "CRÍTICO"
    assert calcular_nivel_risco_executivo(2.86, 6) == "CRÍTICO"
    assert calcular_nivel_risco_executivo(2.80, 1) == "CRÍTICO"


def test_nivel_risco_alto_quando_score_abaixo_280_com_barreira_alta():
    assert calcular_nivel_risco_executivo(2.60, 3) == "ALTO"
    assert calcular_nivel_risco_executivo(2.33, 2) == "ALTO"
    assert calcular_nivel_risco_executivo(2.47, 7) == "ALTO"


def test_nivel_risco_medio_e_baixo_sem_barreira_alta():
    assert calcular_nivel_risco_executivo(2.00, 0) == "MÉDIO"
    assert calcular_nivel_risco_executivo(1.50, 0) == "MÉDIO"
    assert calcular_nivel_risco_executivo(1.00, 0) == "BAIXO"


def test_prioridade_barreira_severidade_dominante():
    alta = {"prioridade": "alta", "wcag_criterio": "4.1.2", "status_deteccao": "automatico_detectado", "confirmado_por": ["lighthouse"]}
    media = {"prioridade": "media", "wcag_criterio": "4.1.2", "status_deteccao": "automatico_detectado", "confirmado_por": ["lighthouse"]}
    baixa = {"prioridade": "baixa", "wcag_criterio": "4.1.2", "status_deteccao": "automatico_detectado", "confirmado_por": ["lighthouse"]}
    assert calcular_prioridade_barreira(alta)[0] == "P1"
    assert calcular_prioridade_barreira(media)[0] == "P2"
    assert calcular_prioridade_barreira(baixa)[0] == "P3"


def test_prioridade_barreira_wcag_a_convergente_antes_de_aa_exclusiva():
    alta_a_conv = {
        "prioridade": "alta",
        "wcag_criterio": "4.1.2",
        "status_deteccao": "automatico_convergente",
        "confirmado_por": ["lighthouse", "wave"],
        "ocorrencias_count": 1,
        "issue_id_original": "aria-invalid",
    }
    alta_aa_lh = {
        "prioridade": "alta",
        "wcag_criterio": "1.4.3",
        "status_deteccao": "automatico_detectado",
        "confirmado_por": ["lighthouse"],
        "ocorrencias_count": 1,
        "issue_id_original": "color-contrast",
    }
    p1, s1 = calcular_prioridade_barreira(alta_a_conv)
    p2, s2 = calcular_prioridade_barreira(alta_aa_lh)
    assert p1 == "P1" and p2 == "P1"
    assert s1 > s2
    ordenadas = enriquecer_prioridades_barreiras([alta_aa_lh, alta_a_conv])
    assert ordenadas[0]["issue_id_original"] == "aria-invalid"


def test_prioridade_barreira_ocorrencias_desempatam_mesma_faixa():
    b1 = {
        "prioridade": "alta",
        "wcag_criterio": "1.4.3",
        "status_deteccao": "automatico_detectado",
        "confirmado_por": ["wave"],
        "ocorrencias_count": 2,
        "issue_id_original": "color-contrast",
        "titulo_tecnico": "a",
    }
    b2 = dict(b1)
    b2["ocorrencias_count"] = 12
    b2["titulo_tecnico"] = "b"
    ordenadas = enriquecer_prioridades_barreiras([b1, b2])
    assert ordenadas[0]["ocorrencias_count"] == 12


def test_inferir_wcag_nivel():
    assert inferir_wcag_nivel("4.1.2") == "a"
    assert inferir_wcag_nivel("1.4.3") == "aa"
    assert inferir_wcag_nivel("1.4.3 | 4.1.2") == "a"


def test_build_report_inclui_prioridade_correcao_e_critico():
    tipos = ["tipo_a", "tipo_b", "tipo_c"]
    lh = [
        _issue(
            tool="lighthouse",
            tipo=t,
            confirmado=["lighthouse"],
            evidencia=[f"lh-{t}"],
            issue_orig=f"id-{t}",
            lh_id=f"id-{t}",
        )
        for t in tipos
    ]
    w = [
        _issue(
            tool="wave",
            tipo=t,
            confirmado=["wave"],
            wave_cat="error",
            evidencia=[f"w-{t}"],
            issue_orig=f"w-{t}",
        )
        for t in tipos
    ]
    rep = build_report(lh, w, [], [], [])
    sr = rep["score_risco"]
    assert sr["valor"] == 3.0
    assert sr["nivel"] == "CRÍTICO"
    bars = rep["barreiras_automaticas"]
    assert all(b.get("prioridade_correcao") in ("P1", "P2", "P3") for b in bars)
    assert all(b.get("motivo_prioridade_correcao") for b in bars)
    assert bars[0]["score_prioridade_barreira"] >= bars[-1]["score_prioridade_barreira"]


def test_display_labels_link_sem_nome_familia_executiva():
    from app.services.display_labels import executive_group_for, issue_display_label

    assert executive_group_for("link_sem_nome_acessivel") == "Links e controles sem nome"
    assert issue_display_label("controle_sem_nome_acessivel", None, None) == "Controle sem nome acessível"
    assert issue_display_label("heading_sem_conteudo", None, None) == "Cabeçalho sem texto"
    assert issue_display_label("empty-heading", None, "empty-heading") == "Cabeçalho sem texto"
    assert issue_display_label("botao_completamente_vazio", None, None) == "Botão sem texto"
