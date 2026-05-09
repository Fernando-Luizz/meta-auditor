"""
Consolida achados por tipo normalizado + URL + assinatura de localização.
Não mistura score Lighthouse com contagens WAVE.

Passagens:
1) merge_by_normalized_type: agrupa por (tipo, URL, fingerprint da evidência).
2) merge_barreiras_por_tipo_e_url: junta linhas com o mesmo tipo na mesma URL (convergência
   Lighthouse + WAVE mesmo quando os fingerprints de seletor diferem).

status_deteccao:
- automatico_detectado: uma ferramenta (ou agregado sem convergência cruzada)
- automatico_convergente: Lighthouse e WAVE no mesmo grupo consolidado
"""
from __future__ import annotations

import hashlib
from collections import defaultdict


def _location_fingerprint(iss: dict) -> str:
    """
    Distingue ocorrências do mesmo tipo na mesma URL quando há evidência de localização.
    Sem localização, partilha chave __no_loc__ (visão mais agregada).
    """
    ev = iss.get("evidencia_localizacao")
    if not isinstance(ev, list) or not ev:
        return "__no_loc__"
    flat = sorted(str(x).strip() for x in ev if x and str(x).strip())
    if not flat:
        return "__no_loc__"
    digest = hashlib.sha256("\n".join(flat).encode("utf-8", errors="replace")).hexdigest()[:24]
    return digest


def assign_prioridade(
    confirmado_por: list[str],
    status_deteccao: str,
    wave_categoria: str | None,
) -> str:
    if status_deteccao == "manual_pendente":
        return "revisao_manual"
    if status_deteccao == "informativo":
        return "baixa"
    if status_deteccao == "alerta_revisao":
        return "baixa"
    if status_deteccao == "automatico_convergente":
        return "alta"
    if len(confirmado_por) >= 2:
        return "alta"
    if wave_categoria in ("error", "contrast"):
        return "alta"
    return "media"


def _merge_evidencia(parts: list[list[str] | None]) -> list[str] | None:
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        for x in p:
            if x not in seen:
                seen.add(x)
                out.append(x)
    return out or None


def _merge_lhids(parts: list[list[str] | None]) -> list[str] | None:
    """Preserva lhIds de issues Lighthouse quando grupos são fundidos."""
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        for x in p:
            s = str(x).strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
    return out[:20] or None


def merge_by_normalized_type(issues: list[dict]) -> list[dict]:
    """
    Agrupa por (issue_tipo_normalizado, page_url, fingerprint_localização).
    Une confirmado_por; status automatico_convergente se mais de uma ferramenta.
    """
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for iss in issues:
        fp = _location_fingerprint(iss)
        key = (iss["issue_tipo_normalizado"], iss.get("page_url") or "", fp)
        groups[key].append(iss)

    merged: list[dict] = []
    for _key, group in groups.items():
        if len(group) == 1:
            g0 = dict(group[0])
            g0["prioridade"] = assign_prioridade(
                g0["confirmado_por"],
                g0["status_deteccao"],
                g0.get("wave_categoria"),
            )
            merged.append(g0)
            continue

        tools: list[str] = []
        for iss in group:
            for t in iss["confirmado_por"]:
                if t not in tools:
                    tools.append(t)
        tools.sort()

        occ = sum(int(i.get("ocorrencias_count") or 0) for i in group)
        descs = [i.get("descricao_tecnica") for i in group if i.get("descricao_tecnica")]
        desc_join = " | ".join(dict.fromkeys(str(d) for d in descs)) if descs else ""

        wcags = [i.get("wcag_criterio") for i in group if i.get("wcag_criterio")]
        wcag_join = " | ".join(dict.fromkeys(str(w) for w in wcags)) if wcags else ""

        pub = [i.get("publico_afetado") for i in group if i.get("publico_afetado")]
        pub_join = " | ".join(dict.fromkeys(str(p) for p in pub)) if pub else ""
        cor = [i.get("correcao_sugerida") for i in group if i.get("correcao_sugerida")]
        cor_join = " | ".join(dict.fromkeys(str(c) for c in cor)) if cor else ""
        onde = [i.get("onde_esta") for i in group if i.get("onde_esta")]
        onde_join = " | ".join(dict.fromkeys(str(o) for o in onde)) if onde else ""

        base = dict(group[0])
        base["tool"] = "consolidated" if len(tools) > 1 else base["tool"]
        base["confirmado_por"] = tools
        base["ocorrencias_count"] = occ
        base["descricao_tecnica"] = desc_join or base.get("descricao_tecnica", "")
        base["wcag_criterio"] = wcag_join or base.get("wcag_criterio", "")
        base["publico_afetado"] = pub_join or base.get("publico_afetado", "")
        base["correcao_sugerida"] = cor_join or base.get("correcao_sugerida", "")
        base["onde_esta"] = onde_join or base.get("onde_esta", "")
        base["evidencia_localizacao"] = _merge_evidencia([i.get("evidencia_localizacao") for i in group])
        base["evidencia_lhids"] = _merge_lhids([i.get("evidencia_lhids") for i in group])

        if len(tools) > 1:
            base["status_deteccao"] = "automatico_convergente"
        else:
            base["status_deteccao"] = "automatico_detectado"

        base["validacao_manual_necessaria"] = False
        base["prioridade"] = assign_prioridade(tools, base["status_deteccao"], base.get("wave_categoria"))
        merged.append(base)

    merged.sort(key=lambda x: (-_priority_rank(x["prioridade"]), x["issue_tipo_normalizado"]))
    return merged


def _merge_barrier_group(group: list[dict]) -> dict:
    """Une várias linhas (mesmo tipo + URL, fingerprints diferentes) numa só."""
    tools: list[str] = []
    for iss in group:
        for t in iss.get("confirmado_por") or []:
            if t not in tools:
                tools.append(t)
    tools.sort()

    occ = sum(int(i.get("ocorrencias_count") or 0) for i in group)
    descs = [i.get("descricao_tecnica") for i in group if i.get("descricao_tecnica")]
    desc_join = " | ".join(dict.fromkeys(str(d) for d in descs)) if descs else ""

    wcags = [i.get("wcag_criterio") for i in group if i.get("wcag_criterio")]
    wcag_join = " | ".join(dict.fromkeys(str(w) for w in wcags)) if wcags else ""

    pubs = [i.get("publico_afetado") for i in group if i.get("publico_afetado")]
    pub_join = " | ".join(dict.fromkeys(str(p) for p in pubs)) if pubs else ""
    cors = [i.get("correcao_sugerida") for i in group if i.get("correcao_sugerida")]
    cor_join = " | ".join(dict.fromkeys(str(c) for c in cors)) if cors else ""
    ondes = [i.get("onde_esta") for i in group if i.get("onde_esta")]
    onde_join = " | ".join(dict.fromkeys(str(o) for o in ondes)) if ondes else ""

    titles = [i.get("titulo_tecnico") for i in group if i.get("titulo_tecnico")]
    titulo = max(titles, key=len) if titles else ""

    orig_ids: list[str] = []
    for i in group:
        oid = str(i.get("issue_id_original") or "")
        if oid and oid not in orig_ids:
            orig_ids.append(oid)
    id_join = " | ".join(orig_ids)

    lh_audit = None
    for i in group:
        if i.get("lighthouse_audit_id"):
            lh_audit = i.get("lighthouse_audit_id")
            break

    wcats = [i.get("wave_categoria") for i in group if i.get("wave_categoria")]
    wave_cat = None
    if "error" in wcats:
        wave_cat = "error"
    elif "contrast" in wcats:
        wave_cat = "contrast"
    elif wcats:
        wave_cat = wcats[0]

    base = dict(group[0])
    base["tool"] = "consolidated" if len(tools) > 1 else base.get("tool", "wave")
    base["confirmado_por"] = tools
    base["ocorrencias_count"] = occ
    base["titulo_tecnico"] = titulo or base.get("titulo_tecnico", "")
    base["descricao_tecnica"] = desc_join or base.get("descricao_tecnica", "")
    base["wcag_criterio"] = wcag_join or base.get("wcag_criterio", "")
    base["publico_afetado"] = pub_join or base.get("publico_afetado", "")
    base["correcao_sugerida"] = cor_join or base.get("correcao_sugerida", "")
    base["onde_esta"] = onde_join or base.get("onde_esta", "")
    base["evidencia_localizacao"] = _merge_evidencia([i.get("evidencia_localizacao") for i in group])
    base["evidencia_lhids"] = _merge_lhids([i.get("evidencia_lhids") for i in group])
    base["issue_id_original"] = id_join or base.get("issue_id_original", "")
    base["lighthouse_audit_id"] = lh_audit
    base["wave_categoria"] = wave_cat

    if len(tools) > 1:
        base["status_deteccao"] = "automatico_convergente"
    else:
        base["status_deteccao"] = "automatico_detectado"
    base["validacao_manual_necessaria"] = False
    base["prioridade"] = assign_prioridade(tools, base["status_deteccao"], wave_cat)
    return base


def merge_barreiras_por_tipo_e_url(barreiras: list[dict]) -> list[dict]:
    """
    Segunda passagem: mesmo issue_tipo_normalizado + mesma page_url -> uma linha.
    Permite convergência Lighthouse + WAVE quando os fingerprints de localização diferem.
    """
    by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in barreiras:
        k = (row["issue_tipo_normalizado"], row.get("page_url") or "")
        by_key[k].append(row)

    out: list[dict] = []
    for group in by_key.values():
        if len(group) == 1:
            g0 = dict(group[0])
            g0["prioridade"] = assign_prioridade(
                g0["confirmado_por"],
                g0["status_deteccao"],
                g0.get("wave_categoria"),
            )
            out.append(g0)
        else:
            out.append(_merge_barrier_group(group))

    out.sort(key=lambda x: (-_priority_rank(x["prioridade"]), x["issue_tipo_normalizado"]))
    return out


def _priority_rank(p: str) -> int:
    return {"alta": 3, "media": 2, "baixa": 1, "revisao_manual": 0}.get(p, 0)


def apply_prioridade_to_list(issues: list[dict]) -> list[dict]:
    out = []
    for iss in issues:
        row = dict(iss)
        row["prioridade"] = assign_prioridade(
            row["confirmado_por"],
            row["status_deteccao"],
            row.get("wave_categoria"),
        )
        out.append(row)
    out.sort(key=lambda x: (-_priority_rank(x["prioridade"]), x["issue_tipo_normalizado"]))
    return out


def _strip_page_url(issues: list[dict]) -> list[dict]:
    out = []
    for i in issues:
        row = {k: v for k, v in i.items() if k != "page_url"}
        out.append(row)
    return out


def _nota_divergencia(issue_tipo: str, wave_categoria: str, wave_count: int) -> str:
    """Gera a nota explicativa da divergência com base no tipo e categoria."""
    count_str = f"{wave_count} ocorrência{'s' if wave_count != 1 else ''}"
    if issue_tipo == "contraste_insuficiente":
        return (
            f"Lighthouse (Chrome desktop via PSI) não detectou contraste insuficiente; "
            f"WAVE encontrou {count_str}. Motivo provável: motores de renderização diferentes "
            f"(PSI desktop vs engine WAVE). Resultado mais restritivo (WAVE) prevalece."
        )
    if wave_categoria == "error":
        return (
            f"Lighthouse passou neste critério; WAVE detectou {count_str} como erro confirmado. "
            f"Pode indicar conteúdo dinâmico não capturado pelo Lighthouse (Chrome desktop via PSI). "
            f"Resultado mais restritivo (WAVE) prevalece."
        )
    if wave_categoria == "contrast":
        return (
            f"Lighthouse (Chrome desktop via PSI) não detectou problema de contraste; "
            f"WAVE encontrou {count_str}. "
            f"Resultado mais restritivo (WAVE) prevalece."
        )
    return (
        f"Lighthouse passou neste critério; WAVE encontrou {count_str}. "
        f"Resultado mais restritivo (WAVE) prevalece."
    )


def detect_divergencias(
    wave_barrier_issues: list[dict],
    lh_passed_tipo_set: set[str],
) -> list[dict]:
    """
    Detecta o caso inverso da convergência: Lighthouse PASSOU mas WAVE detectou
    o mesmo issue_tipo_normalizado como barreira (error ou contrast).

    Regra do Meta-Auditor: em caso de divergência, o resultado mais restritivo
    (WAVE) prevalece. O achado permanece em barreiras_automaticas; esta seção
    adicional documenta a discrepância para fins de pesquisa e transparência.

    Só gera divergência quando:
    - O issue_tipo_normalizado aparece nos tipos que LH passou explicitamente (score=1).
    - O WAVE o detectou como barreira (error ou contrast) — não alertas.
    - O tipo NÃO está já marcado como automatico_convergente (que indicaria que LH
      também falhou, o oposto da divergência).

    Args:
        wave_barrier_issues: lista de barreiras WAVE (error + contrast) já normalizadas.
        lh_passed_tipo_set: set de issue_tipo_normalizado cujo audit LH teve score=1.

    Returns:
        Lista de dicts com a estrutura:
        {
            "issue_tipo_normalizado": str,
            "titulo_tecnico": str,
            "wcag_criterio": str,
            "publico_afetado": str,
            "lighthouse_status": "passou",
            "wave_count": int,
            "wave_categoria": str,          # "error" ou "contrast"
            "decisao": "resultado_mais_restritivo_prevalece",
            "nota": str,
        }
    """
    # Agregar por tipo (pode haver múltiplos itens WAVE do mesmo tipo na mesma auditoria)
    by_tipo: dict[str, dict] = {}
    for iss in wave_barrier_issues:
        tipo = iss.get("issue_tipo_normalizado") or ""
        if not tipo:
            continue
        # Só divergência se LH passou explicitamente neste tipo
        if tipo not in lh_passed_tipo_set:
            continue
        # Se já existir, acumular a contagem
        if tipo in by_tipo:
            by_tipo[tipo]["wave_count"] += int(iss.get("ocorrencias_count") or 1)
        else:
            wave_cat = iss.get("wave_categoria") or ""
            by_tipo[tipo] = {
                "issue_tipo_normalizado": tipo,
                "titulo_tecnico": iss.get("titulo_tecnico") or tipo,
                "wcag_criterio": iss.get("wcag_criterio") or "",
                "publico_afetado": iss.get("publico_afetado") or "",
                "lighthouse_status": "passou",
                "wave_count": int(iss.get("ocorrencias_count") or 1),
                "wave_categoria": wave_cat,
                "decisao": "resultado_mais_restritivo_prevalece",
            }

    # Gerar nota e ordenar por wave_count decrescente
    result: list[dict] = []
    for tipo, entry in by_tipo.items():
        entry["nota"] = _nota_divergencia(tipo, entry["wave_categoria"], entry["wave_count"])
        result.append(entry)

    result.sort(key=lambda x: -x["wave_count"])
    return result


def build_report(
    lighthouse_failed_issues: list[dict],
    wave_barrier_issues: list[dict],
    wave_alert_issues: list[dict],
    wave_informativo_issues: list[dict],
    manual_issues: list[dict],
    lh_passed_tipo_set: set[str] | None = None,
) -> dict:
    barreiras = merge_by_normalized_type(lighthouse_failed_issues + wave_barrier_issues)
    barreiras = merge_barreiras_por_tipo_e_url(barreiras)
    alertas = apply_prioridade_to_list(wave_alert_issues)
    informativos = apply_prioridade_to_list(wave_informativo_issues)
    manual = apply_prioridade_to_list(manual_issues)

    # Divergências: LH passou, WAVE detectou o mesmo tipo como barreira.
    # Só calculado quando o chamador fornece o conjunto de tipos passados pelo LH.
    divergencias: list[dict] = []
    if lh_passed_tipo_set:
        divergencias = detect_divergencias(wave_barrier_issues, lh_passed_tipo_set)

    # Score de risco agregado por barreira automática:
    # alta=3, media=2, baixa=1. Escala final normalizada 0–3.
    n_alta = sum(1 for b in barreiras if (b.get("prioridade") or "").lower() == "alta")
    n_media = sum(1 for b in barreiras if (b.get("prioridade") or "").lower() == "media")
    n_baixa = sum(1 for b in barreiras if (b.get("prioridade") or "").lower() == "baixa")
    total_barreiras = len(barreiras)
    if total_barreiras > 0:
        score_risco = round(((n_alta * 3) + (n_media * 2) + (n_baixa * 1)) / total_barreiras, 2)
        if score_risco > 2.5:
            nivel_risco = "ALTO"
        elif score_risco >= 1.5:
            nivel_risco = "MÉDIO"
        else:
            nivel_risco = "BAIXO"
    else:
        score_risco = 0.0
        nivel_risco = "SEM BARREIRAS"

    return {
        "barreiras_automaticas": _strip_page_url(barreiras),
        "alertas_revisao": _strip_page_url(alertas),
        "informativos_wave": _strip_page_url(informativos),
        "checks_manuais": _strip_page_url(manual),
        "divergencias": divergencias,
        "score_risco": {
            "valor": score_risco,
            "nivel": nivel_risco,
            "n_alta": n_alta,
            "n_media": n_media,
            "n_baixa": n_baixa,
            "total_barreiras": total_barreiras,
        },
    }
