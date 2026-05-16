"""Consolidação, convergência cruzada e prioridades."""
from app.services.consolidation import (
    assign_prioridade,
    build_report,
    detect_divergencias,
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


def test_display_labels_link_sem_nome_familia_executiva():
    from app.services.display_labels import executive_group_for, issue_display_label

    assert executive_group_for("link_sem_nome_acessivel") == "Links e controles sem nome"
    assert issue_display_label("controle_sem_nome_acessivel", None, None) == "Controle sem nome acessível"
    assert issue_display_label("heading_sem_conteudo", None, None) == "Cabeçalho sem texto"
    assert issue_display_label("empty-heading", None, "empty-heading") == "Cabeçalho sem texto"
    assert issue_display_label("botao_completamente_vazio", None, None) == "Botão sem texto"
