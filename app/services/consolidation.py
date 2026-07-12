"""Consolida achados por tipo normalizado, URL e localização."""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from app.services.display_labels import attach_display_fields

WCAG_LEVEL_BY_CRITERION: dict[str, str] = {
    "1.1.1": "a",
    "1.2.1": "a",
    "1.2.2": "a",
    "1.2.3": "a",
    "1.3.1": "a",
    "1.3.2": "a",
    "1.4.1": "a",
    "2.1.1": "a",
    "2.1.2": "a",
    "2.4.1": "a",
    "2.4.2": "a",
    "2.4.3": "a",
    "2.4.4": "a",
    "2.5.3": "a",
    "3.1.1": "a",
    "3.3.2": "a",
    "4.1.2": "a",
    "1.4.3": "aa",
    "1.4.4": "aa",
    "1.4.10": "aa",
    "1.4.11": "aa",
    "2.4.6": "aa",
    "2.4.7": "aa",
    "2.5.8": "aa",
    "1.3.6": "aaa",
    "2.5.5": "aaa",
}

_NIVEL_RISCO_CRITICO_MIN = 2.80
_NIVEL_RISCO_MEDIO_MIN = 1.50


def normalizar(valor) -> str:
    if not valor:
        return ""
    return str(valor).lower().strip()


def inferir_wcag_nivel(wcag_criterio) -> str:
    texto = str(wcag_criterio or "")
    criterios = re.findall(r"\b\d\.\d\.\d+\b", texto)
    niveis = [
        WCAG_LEVEL_BY_CRITERION.get(c)
        for c in criterios
        if WCAG_LEVEL_BY_CRITERION.get(c)
    ]
    if "a" in niveis:
        return "a"
    if "aa" in niveis:
        return "aa"
    if "aaa" in niveis:
        return "aaa"
    return "aa"


def _inferir_fase_correcao(barreira: dict) -> str:
    issue_id = str(
        barreira.get("issue_id_original") or barreira.get("issue_tipo_normalizado") or ""
    ).lower()
    if any(
        k in issue_id
        for k in (
            "image-alt",
            "imagem_sem",
            "lang",
            "button-name",
            "controle_sem_nome",
            "button_empty",
            "botao_completamente_vazio",
            "label",
            "heading",
        )
    ):
        return "fase_1"
    if any(
        k in issue_id
        for k in ("contrast", "contraste", "target-size", "alvo_interacao", "link")
    ):
        return "fase_2"
    return "fase_3"


def _status_deteccao_para_pontos(barreira: dict) -> str:
    status = normalizar(barreira.get("status_deteccao"))
    confirmado = [normalizar(t) for t in (barreira.get("confirmado_por") or []) if t]
    if status in ("automatico_convergente", "intersecao", "interseção") or len(confirmado) >= 2:
        return "automatico_convergente"
    if len(confirmado) == 1 and "lighthouse" in confirmado:
        return "exclusivo_lh"
    if len(confirmado) == 1 and "wave" in confirmado:
        return "exclusivo_wave"
    return status or "automatico_detectado"


def calcular_prioridade_barreira(barreira: dict) -> tuple[str, int]:
    pontos = 0

    prioridade = normalizar(barreira.get("prioridade", "baixa"))
    status = _status_deteccao_para_pontos(barreira)
    fase = normalizar(barreira.get("fase_correcao") or _inferir_fase_correcao(barreira))

    wcag_nivel = normalizar(
        barreira.get("wcag_nivel") or inferir_wcag_nivel(barreira.get("wcag_criterio"))
    )

    try:
        ocorrencias = int(
            barreira.get("ocorrencias_count")
            or barreira.get("ocorrencias")
            or barreira.get("n_ocorrencias")
            or 1
        )
    except (TypeError, ValueError):
        ocorrencias = 1

    pontos += {
        "alta": 300,
        "media": 200,
        "média": 200,
        "baixa": 100,
    }.get(prioridade, 100)

    pontos += {"a": 20, "aa": 10, "aaa": 0}.get(wcag_nivel, 10)

    pontos += {
        "automatico_convergente": 15,
        "intersecao": 15,
        "interseção": 15,
        "exclusivo_lh": 8,
        "exclusivo_wave": 8,
        "automatico_detectado": 8,
        "divergencia": 3,
        "divergência": 3,
    }.get(status, 8)

    pontos += min(10, ocorrencias)

    if fase in ("fase_1", "fase 1", "fase1"):
        pontos += 5

    if pontos >= 300:
        return "P1", pontos
    if pontos >= 200:
        return "P2", pontos
    return "P3", pontos


def _motivo_prioridade_correcao(barreira: dict, prioridade_correcao: str) -> str:
    partes: list[str] = []
    prio = normalizar(barreira.get("prioridade"))
    if prio == "alta":
        partes.append("severidade alta")
    elif prio in ("media", "média"):
        partes.append("severidade média")
    else:
        partes.append("severidade baixa")

    wcag_nivel = normalizar(
        barreira.get("wcag_nivel") or inferir_wcag_nivel(barreira.get("wcag_criterio"))
    )
    partes.append(f"WCAG nível {wcag_nivel.upper()}")

    status = _status_deteccao_para_pontos(barreira)
    if status == "automatico_convergente":
        partes.append("confirmação convergente Lighthouse + WAVE")
    elif status == "exclusivo_lh":
        partes.append("detectado apenas pelo Lighthouse")
    elif status == "exclusivo_wave":
        partes.append("detectado apenas pelo WAVE")
    else:
        partes.append("detecção automática")

    try:
        occ = int(barreira.get("ocorrencias_count") or 1)
    except (TypeError, ValueError):
        occ = 1
    partes.append(f"{occ} ocorrência{'s' if occ != 1 else ''}")

    fase = normalizar(barreira.get("fase_correcao") or _inferir_fase_correcao(barreira))
    if fase in ("fase_1", "fase 1", "fase1"):
        partes.append("correção rápida estimada")
    elif fase in ("fase_2", "fase 2", "fase2"):
        partes.append("esforço médio estimado")
    else:
        partes.append("projeto estrutural estimado")

    return f"{prioridade_correcao}: " + "; ".join(partes) + "."


def calcular_nivel_risco_executivo(score_risco: float, n_alta: int) -> str:
    if score_risco >= _NIVEL_RISCO_CRITICO_MIN:
        return "CRÍTICO"
    if n_alta >= 1:
        return "ALTO"
    if score_risco >= _NIVEL_RISCO_MEDIO_MIN:
        return "MÉDIO"
    return "BAIXO"


def _ordenar_barreiras_por_prioridade_correcao(barreiras: list[dict]) -> list[dict]:
    rank = {"P1": 0, "P2": 1, "P3": 2}

    def _key(b: dict) -> tuple:
        pc = b.get("prioridade_correcao") or "P3"
        return (
            rank.get(pc, 3),
            -int(b.get("score_prioridade_barreira") or 0),
            str(b.get("titulo_tecnico") or b.get("issue_tipo_normalizado") or ""),
        )

    return sorted(barreiras, key=_key)


def enriquecer_prioridades_barreiras(barreiras: list[dict]) -> list[dict]:
    out: list[dict] = []
    for b in barreiras:
        row = dict(b)
        if not row.get("fase_correcao"):
            row["fase_correcao"] = _inferir_fase_correcao(row)
        row["wcag_nivel"] = inferir_wcag_nivel(row.get("wcag_criterio"))
        p_class, p_score = calcular_prioridade_barreira(row)
        row["prioridade_correcao"] = p_class
        row["score_prioridade_barreira"] = p_score
        row["motivo_prioridade_correcao"] = _motivo_prioridade_correcao(row, p_class)
        out.append(row)
    return _ordenar_barreiras_por_prioridade_correcao(out)


def _location_fingerprint(iss: dict) -> str:
    """
    Distingue ocorrências do mesmo tipo na mesma URL quando há evidência de localização.
    Sem localização, compartilha chave __no_loc__ (visão mais agregada).
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
    """Mantém lhIds ao fundir grupos Lighthouse."""
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


def _merge_semantic_data(parts: list[dict | None]) -> dict | None:
    """
    Mantém o primeiro bloco semântico útil.
    Para o caso atual (Label in Name), um exemplar é suficiente.
    """
    for p in parts:
        if isinstance(p, dict) and any(p.get(k) for k in ("visivel", "acessivel", "problema", "tipo")):
            return p
    return None


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
            g0["dados_semanticos"] = g0.get("dados_semanticos")
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
        lh_pub = [
            i.get("publico_afetado")
            for i in group
            if i.get("publico_afetado") and i.get("tool") in ("lighthouse", "consolidated")
        ]
        pub_join = lh_pub[0] if lh_pub else (" | ".join(dict.fromkeys(str(p) for p in pub)) if pub else "")
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
        base["dados_semanticos"] = _merge_semantic_data([i.get("dados_semanticos") for i in group])

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
    lh_pubs = [
        i.get("publico_afetado")
        for i in group
        if i.get("publico_afetado") and i.get("tool") in ("lighthouse", "consolidated")
    ]
    pub_join = lh_pubs[0] if lh_pubs else (" | ".join(dict.fromkeys(str(p) for p in pubs)) if pubs else "")
    cors = [i.get("correcao_sugerida") for i in group if i.get("correcao_sugerida")]
    cor_join = " | ".join(dict.fromkeys(str(c) for c in cors)) if cors else ""
    ondes = [i.get("onde_esta") for i in group if i.get("onde_esta")]
    onde_join = " | ".join(dict.fromkeys(str(o) for o in ondes)) if ondes else ""

    titles = [i.get("titulo_tecnico") for i in group if i.get("titulo_tecnico")]
    # Prefere título Lighthouse ao fundir (max por len favorecia WAVE genérico).
    lh_titles = [
        i.get("titulo_tecnico")
        for i in group
        if i.get("titulo_tecnico") and i.get("tool") in ("lighthouse", "consolidated")
    ]
    titulo = lh_titles[0] if lh_titles else (titles[0] if titles else "")

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
    base["dados_semanticos"] = _merge_semantic_data([i.get("dados_semanticos") for i in group])
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
            g0["dados_semanticos"] = g0.get("dados_semanticos")
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


def _build_page_map(issues: list[dict]) -> dict[str, str]:
    """Rótulos de página: 1 URL → «Página principal»; N → «Página 1»… (page_url intacta)."""
    urls: list[str] = list(
        dict.fromkeys(
            str(i.get("page_url") or "").strip()
            for i in issues
            if str(i.get("page_url") or "").strip()
        )
    )
    if not urls:
        return {}
    if len(urls) == 1:
        return {urls[0]: "Página principal"}
    return {u: f"Página {idx + 1}" for idx, u in enumerate(urls)}


def _apply_page_labels(issues: list[dict], page_map: dict[str, str]) -> list[dict]:
    """Adiciona `page_label` por URL; mantém `page_url` para links no apêndice."""
    out: list[dict] = []
    for iss in issues:
        row = dict(iss)
        url = str(row.get("page_url") or "").strip()
        row["page_label"] = page_map.get(url, "") if url else ""
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
    """Lighthouse passou e WAVE falhou no mesmo tipo — prevalece WAVE."""
    by_tipo: dict[str, dict] = {}
    for iss in wave_barrier_issues:
        tipo = iss.get("issue_tipo_normalizado") or ""
        if not tipo:
            continue
        if tipo not in lh_passed_tipo_set:
            continue
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
    lh_passed_audits: list[dict] | None = None,
) -> dict:
    _all_issues = (
        lighthouse_failed_issues
        + wave_barrier_issues
        + wave_alert_issues
        + wave_informativo_issues
        + manual_issues
    )
    page_map = _build_page_map(_all_issues)
    multi_page = len(page_map) > 1

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
    barreiras = enriquecer_prioridades_barreiras(barreiras)

    if total_barreiras > 0:
        score_risco = round(((n_alta * 3) + (n_media * 2) + (n_baixa * 1)) / total_barreiras, 2)
        # Score numérico 0–3 inalterado; nível executivo distingue CRÍTICO (≥2,80) de ALTO.
        nivel_risco = calcular_nivel_risco_executivo(score_risco, n_alta)
    else:
        score_risco = 0.0
        nivel_risco = "SEM BARREIRAS"

    # Itens aprovados pelo Lighthouse — máx. 20, só id + title para não inflar o JSON.
    itens_aprovados: list[dict] = [
        {"id": str(a.get("id") or ""), "title": str(a.get("title") or "")}
        for a in (lh_passed_audits or [])
        if a.get("title")
    ][:20]

    out = {
        "barreiras_automaticas": _apply_page_labels(barreiras, page_map),
        "alertas_revisao": _apply_page_labels(alertas, page_map),
        "informativos_wave": _apply_page_labels(informativos, page_map),
        "checks_manuais": _apply_page_labels(manual, page_map),
        "divergencias": divergencias,
        "score_risco": {
            "valor": score_risco,
            "nivel": nivel_risco,
            "n_alta": n_alta,
            "n_media": n_media,
            "n_baixa": n_baixa,
            "total_barreiras": total_barreiras,
        },
        "multi_page": multi_page,
        "page_map": {label: url for url, label in page_map.items()},
        "itens_aprovados": itens_aprovados,
    }
    attach_display_fields(out["barreiras_automaticas"])
    attach_display_fields(out["alertas_revisao"])
    attach_display_fields(out["informativos_wave"])
    attach_display_fields(out["checks_manuais"])
    attach_display_fields(out["divergencias"])
    return out
