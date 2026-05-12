"""
Extratores: PSI/Lighthouse e WAVE -> dicionários mínimos para normalização/consolidação.
"""
from __future__ import annotations

from app.services.normalize_maps import normalize_lighthouse_audit, normalize_wave_item

# WAVE: categorias que entram como barreira automática ou alerta (não misturar com feature/estrutura informativa).
WAVE_BARRIER_CATEGORIES = frozenset({"error", "contrast"})
WAVE_ALERT_CATEGORIES = frozenset({"alert"})
WAVE_INFORMATIVE_CATEGORIES = frozenset({"feature", "structure", "aria"})


def lighthouse_occurrence_count(audit: dict) -> int:
    d = audit.get("details")
    if not isinstance(d, dict):
        return 1
    items = d.get("items")
    if isinstance(items, list) and items:
        return len(items)
    return 1


def _evidencia_lighthouse(audit: dict) -> list[str]:
    """
    Extrai uma linha de evidência POR ELEMENTO com falha, no formato:
        [lhId] selector — snippet

    Corrige o bug em que vários elementos com o mesmo seletor CSS (ex: todas as
    imagens de uma mesma classe) apareciam como uma única evidência repetida.
    O lhId (ex: '1-45-IMG') é único por elemento na página — garante distinção.
    """
    out: list[str] = []
    seen_ids: set[str] = set()

    def _node_to_line(node: dict) -> str | None:
        """Compõe uma linha legível a partir de um nó Lighthouse."""
        if not isinstance(node, dict):
            return None
        lhid = node.get("lhId") or ""
        sel = (node.get("selector") or "").strip()
        sn = (node.get("snippet") or "").strip()[:200]
        if not (sel or sn):
            return None
        prefix = f"[{lhid}] " if lhid else ""
        if sel and sn:
            return f"{prefix}{sel} — {sn}"
        return f"{prefix}{sel or sn}"

    def _collect_nodes(obj: object) -> None:
        """Percorre details recursivamente coletando nós, sem deduplicar por texto."""
        if isinstance(obj, dict):
            if obj.get("type") == "node" or ("selector" in obj or "snippet" in obj):
                lhid = obj.get("lhId") or ""
                if lhid and lhid in seen_ids:
                    return
                line = _node_to_line(obj)
                if line:
                    if lhid:
                        seen_ids.add(lhid)
                    out.append(line)
            for k, v in obj.items():
                if k not in (
                    "selector",
                    "snippet",
                    "lhId",
                    "type",
                    "nodeLabel",
                    "explanation",
                    "boundingRect",
                    "nodeType",
                ):
                    _collect_nodes(v)
        elif isinstance(obj, list):
            for x in obj:
                _collect_nodes(x)

    d = audit.get("details")
    if isinstance(d, dict):
        _collect_nodes(d)
    return out[:80]


def _lhids_from_audit(audit: dict) -> list[str]:
    """
    Extrai lhIds únicos dos nós com falha de um audit Lighthouse.
    São chaves de `lighthouseResult.fullPageScreenshot.nodes` (bounding rects na screenshot PSI).
    """
    out: list[str] = []
    seen: set[str] = set()

    def _collect(obj: object) -> None:
        if isinstance(obj, dict):
            lhid = obj.get("lhId")
            if isinstance(lhid, str) and lhid and lhid not in seen:
                seen.add(lhid)
                out.append(lhid)
            for k, v in obj.items():
                if k != "lhId":
                    _collect(v)
        elif isinstance(obj, list):
            for x in obj:
                _collect(x)

    d = audit.get("details")
    if isinstance(d, dict):
        _collect(d)
    return out[:20]


def _semantic_lighthouse_data(audit: dict) -> dict | None:
    """
    Extrai dados semânticos úteis para auditorias Lighthouse em que
    screenshot não é a melhor evidência.

    Caso tratado agora:
    - label-content-name-mismatch / rotulo_difere_do_nome_acessivel
    """
    aid = str(audit.get("id") or "")
    details = audit.get("details")
    if not isinstance(details, dict):
        return None

    items = details.get("items")
    if not isinstance(items, list) or not items:
        return None

    if aid == "label-content-name-mismatch":
        first = items[0] if isinstance(items[0], dict) else {}

        node = first.get("node") if isinstance(first.get("node"), dict) else {}
        acessivel = str(node.get("nodeLabel") or "").strip()

        visivel = ""
        sub = first.get("subItems")
        if isinstance(sub, dict):
            subitems = sub.get("items")
            if isinstance(subitems, list):
                for si in subitems:
                    if not isinstance(si, dict):
                        continue
                    related = si.get("relatedNode")
                    if isinstance(related, dict):
                        lbl = str(related.get("nodeLabel") or "").strip()
                        if lbl:
                            visivel = lbl
                            break

        if visivel or acessivel:
            problema = ""
            if visivel and acessivel:
                if not acessivel.lower().startswith(visivel.lower()):
                    problema = "O nome acessível não começa com o texto visível."
                elif acessivel != visivel:
                    problema = "O nome acessível contém o texto visível, mas não coincide exatamente."
                else:
                    problema = "Texto visível e nome acessível coincidem."

            return {
                "tipo": "label_content_name_mismatch",
                "visivel": visivel or None,
                "acessivel": acessivel or None,
                "problema": problema or None,
            }

    return None


def _evidencia_wave_item(item: dict) -> list[str]:
    """Reporttype 3/4: apenas campos de localização WAVE (evita confundir description com seletor)."""
    out: list[str] = []
    seen: set[str] = set()

    def add(s: str) -> None:
        t = s.strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)

    def from_block(block: object) -> None:
        if isinstance(block, list):
            for x in block[:120]:
                if isinstance(x, str):
                    add(x)
        elif isinstance(block, dict):
            for sk in ("selector", "xpath"):
                inner = block.get(sk)
                if isinstance(inner, list):
                    for x in inner[:120]:
                        if isinstance(x, str):
                            add(x)
                elif isinstance(inner, str):
                    add(inner)

    for key in ("xpaths", "selectors"):
        block = item.get(key)
        from_block(block)
        if isinstance(block, dict):
            for v in block.values():
                from_block(v)

    return out[:120]


def _onde_esta_humano(evidencias: list[str] | None) -> str:
    """Resumo em linguagem humana da localização provável do problema."""
    if not evidencias:
        return "Localização não identificada automaticamente"

    joined = " ".join(evidencias[:3]).lower()
    rules = [
        (("header", "cabec", "topbar"), "Cabeçalho da página"),
        (("nav", "menu"), "Menu de navegação"),
        (("footer", "rodape"), "Rodapé da página"),
        (("form", "input", "search", "busca"), "Formulário/campo de entrada"),
        (("main", "content", "section"), "Conteúdo principal da página"),
        (("banner", "carousel", "slider"), "Banner/carrossel"),
        (("table", "tbody", "thead"), "Tabela de conteúdo"),
        (("list", "ul", "ol", "li"), "Lista de itens"),
        (("iframe", "frame"), "Frame/iframe incorporado"),
    ]
    for keys, label in rules:
        if any(k in joined for k in keys):
            return label
    return "Elemento técnico identificado no DOM (ver evidência)"


def extract_lighthouse_issues(
    failed_audits: list[dict],
    manual_audits: list[dict],
    page_url: str,
) -> tuple[list[dict], list[dict]]:
    """
    Retorna (barreiras automáticas detectadas, checks_manuais) no schema interno de achado.
    """
    auto: list[dict] = []
    for a in failed_audits:
        if not isinstance(a, dict):
            continue
        aid = str(a.get("id") or "")
        meta = normalize_lighthouse_audit(aid, str(a.get("title") or ""), str(a.get("description") or ""))
        evid = _evidencia_lighthouse(a)
        lhids = _lhids_from_audit(a)
        semantic_data = _semantic_lighthouse_data(a)
        auto.append({
            "tool": "lighthouse",
            "issue_id_original": aid,
            "issue_tipo_normalizado": meta["issue_tipo_normalizado"],
            "titulo_tecnico": meta["titulo_tecnico"],
            "descricao_tecnica": str(a.get("description") or ""),
            "wcag_criterio": meta.get("wcag_criterio") or "",
            "publico_afetado": meta.get("publico_afetado") or "",
            "correcao_sugerida": meta.get("correcao_sugerida") or "",
            "evidencia_localizacao": evid or None,
            "evidencia_lhids": lhids or None,
            "dados_semanticos": semantic_data,
            "onde_esta": _onde_esta_humano(evid),
            "status_deteccao": "automatico_detectado",
            "confirmado_por": ["lighthouse"],
            "validacao_manual_necessaria": False,
            "ocorrencias_count": lighthouse_occurrence_count(a),
            "wave_categoria": None,
            "lighthouse_audit_id": aid,
            "page_url": page_url,
        })

    manual_out: list[dict] = []
    for a in manual_audits:
        if not isinstance(a, dict):
            continue
        aid = str(a.get("id") or "")
        meta = normalize_lighthouse_audit(aid, str(a.get("title") or ""), str(a.get("description") or ""))
        evid = _evidencia_lighthouse(a)
        lhids = _lhids_from_audit(a)
        semantic_data = _semantic_lighthouse_data(a)
        manual_out.append({
            "tool": "lighthouse",
            "issue_id_original": aid,
            "issue_tipo_normalizado": meta["issue_tipo_normalizado"],
            "titulo_tecnico": meta["titulo_tecnico"],
            "descricao_tecnica": str(a.get("description") or ""),
            "wcag_criterio": meta.get("wcag_criterio") or "",
            "publico_afetado": meta.get("publico_afetado") or "",
            "correcao_sugerida": meta.get("correcao_sugerida") or "",
            "evidencia_localizacao": evid or None,
            "evidencia_lhids": lhids or None,
            "dados_semanticos": semantic_data,
            "onde_esta": _onde_esta_humano(evid),
            "status_deteccao": "manual_pendente",
            "confirmado_por": ["lighthouse"],
            "validacao_manual_necessaria": True,
            "ocorrencias_count": 1,
            "wave_categoria": None,
            "lighthouse_audit_id": aid,
            "page_url": page_url,
        })

    return auto, manual_out


def extract_passed_tipo_set(passed_audits: list[dict]) -> set[str]:
    """
    Conjunto de issue_tipo_normalizado para audits Lighthouse com score=1 (binary).
    Usado para detectar divergências com WAVE (LH passou, WAVE barreira no mesmo tipo).
    """
    out: set[str] = set()
    for a in passed_audits:
        if not isinstance(a, dict):
            continue
        aid = str(a.get("id") or "")
        meta = normalize_lighthouse_audit(aid, str(a.get("title") or ""), str(a.get("description") or ""))
        tipo = meta.get("issue_tipo_normalizado")
        if tipo:
            out.add(tipo)
    return out


def extract_wave_items(wave_response: dict) -> list[dict]:
    """Achados WAVE por item (reporttype >= 2)."""
    out: list[dict] = []
    categories = wave_response.get("categories") or {}
    if not isinstance(categories, dict):
        return out

    for cat_name, cat_data in categories.items():
        if not isinstance(cat_data, dict):
            continue
        items_block = cat_data.get("items") or {}
        if not isinstance(items_block, dict):
            continue
        for _key, item in items_block.items():
            if not isinstance(item, dict):
                continue
            iid = str(item.get("id") or _key or "")
            if not iid:
                continue
            out.append({
                "wave_category": str(cat_name).lower(),
                "id": iid,
                "description": str(item.get("description") or ""),
                "count": int(item.get("count") or 0),
                "raw_item": item,
            })
    return out


def wave_items_to_issues(wave_items: list[dict], page_url: str) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Separa em (barreiras, alertas, informativos).
    Barreiras WAVE usam status_deteccao=automatico_detectado (uma ferramenta); convergência é na consolidação.
    """
    barreira: list[dict] = []
    alertas: list[dict] = []
    informativos: list[dict] = []

    for row in wave_items:
        cat = row["wave_category"]
        iid = row["id"]
        desc = row["description"]
        cnt = max(0, row["count"])
        meta = normalize_wave_item(cat, iid, desc)
        item = row.get("raw_item") or {}
        evid = _evidencia_wave_item(item) if isinstance(item, dict) else []

        base = {
            "tool": "wave",
            "issue_id_original": iid,
            "issue_tipo_normalizado": meta["issue_tipo_normalizado"],
            "titulo_tecnico": meta["titulo_tecnico"],
            "descricao_tecnica": desc,
            "wcag_criterio": meta.get("wcag_criterio") or "",
            "publico_afetado": meta.get("publico_afetado") or "",
            "correcao_sugerida": meta.get("correcao_sugerida") or "",
            "evidencia_localizacao": evid or None,
            "evidencia_lhids": None,
            "onde_esta": _onde_esta_humano(evid),
            "confirmado_por": ["wave"],
            "validacao_manual_necessaria": False,
            "ocorrencias_count": cnt if cnt > 0 else 1,
            "wave_categoria": cat,
            "lighthouse_audit_id": None,
            "page_url": page_url,
        }

        if cat in WAVE_BARRIER_CATEGORIES:
            base["status_deteccao"] = "automatico_detectado"
            barreira.append(base)
        elif cat in WAVE_ALERT_CATEGORIES:
            base["status_deteccao"] = "alerta_revisao"
            alertas.append(base)
        elif cat in WAVE_INFORMATIVE_CATEGORIES:
            base["status_deteccao"] = "informativo"
            informativos.append(base)
        else:
            base["status_deteccao"] = "informativo"
            informativos.append(base)

    return barreira, alertas, informativos
