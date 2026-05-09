import asyncio
import io
import os
import json
import logging
import hashlib
import base64
import importlib
import re
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import (
    AI_ENHANCE_LEVEL,
    AI_ENHANCE_REPORT,
    ANTHROPIC_API_KEY,
    APP_VERSION,
    DATA_EVIDENCE_DIR,
    DB_PATH,
    DEBUG,
    PROJECT_ROOT,
    PSI_API_KEY,
    REPORT_FOOTER_AUTHOR,
    REPORT_FOOTER_ORG,
    REPORT_HTML_EVIDENCE_MAX,
    WAVE_API_KEY,
    WAVE_REPORT_TYPE,
)
from app.connectors.lighthouse_connector import (
    classify_accessibility_audits,
    compute_score_breakdown,
    extract_accessibility_audits,
    get_accessibility_category,
    get_accessibility_score,
    run_lighthouse,
)
from app.connectors.wave_connector import WaveAPIError, run_wave
from app.database import (
    count_audits,
    get_audit,
    get_historico_url,
    init_db,
    list_audits,
    save_audit,
    search_urls,
)
from app.models.request_models import AuditRequest
from app.services.consolidation import build_report
from app.services.extractors import (
    extract_lighthouse_issues,
    extract_passed_tipo_set,
    extract_wave_items,
    wave_items_to_issues,
)

_log = logging.getLogger("uvicorn.error")

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _build_report_html(audit_row: dict) -> str:
    """HTML do relatório a partir de um registo completo da tabela `audits`."""
    return _jinja_env.get_template("report.html").render(
        audit=audit_row,
        app_version=APP_VERSION,
        report_evidence_max=REPORT_HTML_EVIDENCE_MAX,
        report_footer_org=REPORT_FOOTER_ORG,
        report_footer_author=REPORT_FOOTER_AUTHOR,
        now_year=datetime.now().year,
    )


def _raw_path_for_db(file_path: Path) -> str:
    """Caminho relativo à raiz do projeto (segmentos com /)."""
    return str(file_path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")


def _resolved_raw_path(rel: str | None) -> Path | None:
    """Caminho absoluto a um ficheiro bruto, só se existir e estiver debaixo de PROJECT_ROOT."""
    if not rel or not isinstance(rel, str):
        return None
    p = (PROJECT_ROOT / rel.replace("\\", "/")).resolve()
    try:
        p.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return None
    return p if p.is_file() else None


def _audit_export_zip_bytes(audit_id: int, row: dict) -> bytes:
    """ZIP com brutos Lighthouse/WAVE, relatório consolidado (JSON) e HTML (testes)."""
    report = row.get("report")
    if not isinstance(report, dict):
        report = {}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        readme = (
            "Meta-Auditor — pacote temporário para testes\n"
            f"auditoria_id={audit_id}\n"
            f"url={row.get('url') or ''}\n"
            f"created_at={row.get('created_at') or ''}\n"
            "\n"
            "Conteúdo:\n"
            "  01_lighthouse_psi_bruto.json — resposta bruta PageSpeed (Lighthouse)\n"
            "  02_wave_bruto.json — resposta bruta WAVE\n"
            "  03_relatorio_consolidado.json — relatório normalizado (consolidação)\n"
            "  04_relatorio.html — relatório em HTML (mesmo do browser)\n"
        )
        zf.writestr("00_leia-me.txt", readme)

        lh_p = _resolved_raw_path(row.get("lighthouse_raw_path"))
        if lh_p is not None:
            zf.write(lh_p, "01_lighthouse_psi_bruto.json")
        else:
            zf.writestr(
                "01_lighthouse_psi_bruto_AUSENTE.txt",
                "Ficheiro Lighthouse/PSI bruto indisponível (caminho não guardado, ficheiro "
                "apagado ou auditoria antiga sem esta coluna na base de dados).\n",
            )

        wv_p = _resolved_raw_path(row.get("wave_raw_path"))
        if wv_p is not None:
            zf.write(wv_p, "02_wave_bruto.json")
        else:
            zf.writestr(
                "02_wave_bruto_AUSENTE.txt",
                "Ficheiro WAVE bruto indisponível (caminho não guardado, ficheiro apagado ou "
                "auditoria antiga sem esta coluna na base de dados).\n",
            )

        zf.writestr(
            "03_relatorio_consolidado.json",
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        )
        zf.writestr("04_relatorio.html", _build_report_html(row))
    return buf.getvalue()


def _wave_category_count(categories: object, name: str) -> int:
    if not isinstance(categories, dict):
        return 0
    block = categories.get(name)
    if isinstance(block, dict):
        return int(block.get("count") or 0)
    return 0


def _wave_aim_score_from_raw(raw_wave: dict) -> float | None:
    stats = raw_wave.get("statistics")
    if not isinstance(stats, dict):
        return None
    v = stats.get("AIMscore")
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _find_screenshot_data_url(obj: object) -> str | None:
    """Procura o primeiro data URL de imagem no JSON bruto do Lighthouse."""
    if isinstance(obj, dict):
        data = obj.get("data")
        if isinstance(data, str) and data.startswith("data:image/"):
            return data
        for v in obj.values():
            found = _find_screenshot_data_url(v)
            if found:
                return found
    elif isinstance(obj, list):
        for x in obj:
            found = _find_screenshot_data_url(x)
            if found:
                return found
    return None


def _crop_lh_screenshot_evidence(lh_raw: dict, lhids: list[str]) -> bytes | None:
    """
    Recorta e destaca elemento no fullPageScreenshot do Lighthouse (sem rede).

    Usa lighthouseResult.fullPageScreenshot.screenshot (data URL) e
    fullPageScreenshot.nodes[lhId] com top/left/width/height na mesma escala da imagem.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except ImportError:
        _log.warning("Pillow não instalado — crop de evidência Lighthouse indisponível.")
        return None

    try:
        lr = lh_raw.get("lighthouseResult") or lh_raw
        fps = lr.get("fullPageScreenshot")
        if not isinstance(fps, dict):
            return None

        screenshot_info = fps.get("screenshot") or {}
        nodes_map = fps.get("nodes") or {}
        if not isinstance(nodes_map, dict):
            nodes_map = {}

        data_url = screenshot_info.get("data") or ""
        img_w = int(screenshot_info.get("width") or 0)
        img_h = int(screenshot_info.get("height") or 0)
        if not data_url or not img_w or not img_h:
            return None

        if "," not in data_url:
            return None
        _, b64part = data_url.split(",", 1)
        img_bytes = base64.b64decode(b64part)
        full_img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

        rect = None
        matched_lhid = None
        for lhid in lhids:
            node = nodes_map.get(lhid)
            if isinstance(node, dict):
                rect = node
                matched_lhid = lhid
                break

        if rect is None:
            return None

        el_top = float(rect.get("top") or 0)
        el_left = float(rect.get("left") or 0)
        el_w = float(rect.get("width") or 0)
        el_h = float(rect.get("height") or 0)

        if el_w < 1 or el_h < 1:
            return None

        pad_v = max(80, int(el_h * 0.5))
        pad_h = max(80, int(el_w * 0.5))

        crop_left = max(0, int(el_left - pad_h))
        crop_top = max(0, int(el_top - pad_v))
        crop_right = min(img_w, int(el_left + el_w + pad_h))
        crop_bottom = min(img_h, int(el_top + el_h + pad_v))

        if (crop_right - crop_left) < 10 or (crop_bottom - crop_top) < 10:
            return None

        cropped = full_img.crop((crop_left, crop_top, crop_right, crop_bottom))
        out_img = cropped.convert("RGB")
        draw = ImageDraw.Draw(out_img, "RGBA")

        box_left = int(el_left - crop_left)
        box_top = int(el_top - crop_top)
        box_right = box_left + int(el_w)
        box_bottom = box_top + int(el_h)

        overlay_color = (220, 38, 38, 60)
        draw.rectangle([box_left, box_top, box_right, box_bottom], fill=overlay_color)

        border_color = (220, 38, 38, 255)
        for offset in range(3):
            draw.rectangle(
                [box_left - offset, box_top - offset, box_right + offset, box_bottom + offset],
                outline=border_color,
            )

        label = f" {matched_lhid or '?'} "
        label_x = max(0, box_left - 1)
        label_y = max(0, box_top - 18)
        label_bg = (220, 38, 38, 220)
        label_fg = (255, 255, 255, 255)

        font = None
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
        except Exception:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
            except Exception:
                try:
                    from pathlib import Path as _Path

                    win_arial = _Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf"
                    if win_arial.is_file():
                        font = ImageFont.truetype(str(win_arial), 11)
                except Exception:
                    font = ImageFont.load_default()

        if font is None:
            font = ImageFont.load_default()

        bbox = draw.textbbox((label_x, label_y), label, font=font)
        draw.rectangle(bbox, fill=label_bg)
        draw.text((label_x, label_y), label, fill=label_fg, font=font)

        buf = io.BytesIO()
        out_img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    except Exception as exc:
        _log.warning("_crop_lh_screenshot_evidence falhou: %s", exc)
        return None


def _placeholder_evidence_png(title: str = "Imagem indisponível") -> bytes | None:
    """PNG sintético para o relatório não mostrar thumbnail quebrando (404)."""
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except ImportError:
        return None
    subtitle = "Sem Lighthouse brut · captura falhou ou indisponível (ex.: PSI 429, Docker)."
    w, h = 420, 120
    img = Image.new("RGB", (w, h), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w - 1, h - 1], outline=(203, 213, 225), width=1)
    try:
        from pathlib import Path as _Path

        font_path = _Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeui.ttf"
        ft = ImageFont.truetype(str(font_path), 15) if font_path.is_file() else ImageFont.load_default()
        fs = ImageFont.truetype(str(font_path), 11) if font_path.is_file() else ImageFont.load_default()
    except Exception:
        ft = fs = ImageFont.load_default()
    draw.text((12, 16), title, fill=(55, 65, 81), font=ft)
    draw.text((12, 48), subtitle, fill=(107, 114, 128), font=fs)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _normalize_selector(raw: str) -> str:
    s = " ".join(str(raw).strip().split())
    if not s:
        return ""
    if "BODY >" in s.upper():
        tail = s.upper().rfind("BODY >")
        s = "body > " + s[tail + len("BODY >") :]
    s = re.sub(r"^\s*HTML\s*>\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^\s*BODY\s*>\s*", "body > ", s, flags=re.IGNORECASE)
    return s.strip()


def _barrier_selector_candidates(barrier: dict) -> list[str]:
    ev = barrier.get("evidencia_localizacao")
    if not isinstance(ev, list):
        ev = []
    out: list[str] = []
    seen: set[str] = set()

    def strip_lh_preface(line: str) -> str:
        """Remove prefixo Lighthouse '[lhId]' e texto após — (selector costuma ficar primeiro)."""
        s = line.strip()
        s = re.sub(r"^\[[^\]\s]+\]\s*", "", s)
        for sep in (" — ", " – ", " - "):
            if sep in s:
                s = s.split(sep, 1)[0].strip()
                break
        return s

    def add(sel: str) -> None:
        s = _normalize_selector(sel)
        if not s or s in seen:
            return
        seen.add(s)
        out.append(s)

    for e in ev:
        s_raw = str(e or "").strip()
        if not s_raw or s_raw.startswith("<") or s_raw.lower().startswith("xpath"):
            continue
        s_use = strip_lh_preface(s_raw)
        add(s_use)
        m_id = re.search(r"#([A-Za-z_][\w:-]*)", s_use)
        if m_id:
            add(f"#{m_id.group(1)}")
        m_class = re.search(r"\.([A-Za-z_][\w:-]*)", s_use)
        if m_class:
            add(f".{m_class.group(1)}")
    return out


async def _capture_barrier_image(url: str, selectors: list[str], out_file: Path, compact: bool) -> None:
    def _capture_sync() -> None:
        pw_mod = importlib.import_module("playwright.sync_api")
        sync_playwright = pw_mod.sync_playwright

        viewport = {"width": 800, "height": 520} if compact else {"width": 1366, "height": 900}
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport=viewport)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception:
                browser.close()
                raise

            for sel in selectors[:10]:
                try:
                    loc = page.locator(sel).first
                    if loc.count() < 1:
                        continue
                    loc.scroll_into_view_if_needed(timeout=4000)
                    page.wait_for_timeout(250)
                    loc.screenshot(path=str(out_file), type="png")
                    browser.close()
                    return
                except Exception:
                    continue

            page.screenshot(path=str(out_file), type="png", full_page=not compact)
            browser.close()

    await asyncio.to_thread(_capture_sync)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _log.warning(
        "Meta-Auditor %s | PROJECT_ROOT=%s | WAVE_REPORT_TYPE=%s | DB=%s",
        APP_VERSION,
        PROJECT_ROOT,
        WAVE_REPORT_TYPE,
        DB_PATH,
    )
    await init_db(DB_PATH)
    yield


app = FastAPI(
    title="Meta-Auditor de Acessibilidade",
    version=APP_VERSION,
    description="Auditoria de URLs: Lighthouse/PSI (score + audits) e WAVE (achados + localização).",
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """UI mínima (formulário + histórico); documentação interativa em /docs."""
    html = _jinja_env.get_template("index.html").render(app_version=APP_VERSION)
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")


@app.get("/info")
async def api_info():
    return {
        "service": "Meta-Auditor de Acessibilidade",
        "ui": "/",
        "docs": "/docs",
        "health": "/health",
        "audit": "POST /audit com body {\"url\": \"https://...\"}",
        "audits": "GET /audits?limit=50 | GET /audits/{id} | GET /audits/{id}/report.html",
        "export": "GET /audits/{id}/export.html | export.json | export.zip (Content-Disposition: attachment)",
    }


@app.get("/audits/{audit_id}/export.zip")
async def audit_export_zip(audit_id: int):
    """Brutos LH+WAVE + relatorio JSON + HTML num único ZIP (apoiar testes)."""
    row = await get_audit(DB_PATH, audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    payload = _audit_export_zip_bytes(audit_id, row)
    name = f"meta-auditoria-{audit_id}.zip"
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@app.get("/audits/{audit_id}/export.json", response_class=JSONResponse)
async def audit_export_json(audit_id: int):
    """Registo completo em JSON (mesmo conteúdo que GET /audits/{id}) com cabeçalho de descarga."""
    row = await get_audit(DB_PATH, audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    name = f"meta-auditoria-{audit_id}.json"
    return JSONResponse(
        content=row,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@app.get("/audits/{audit_id}/export.html", response_class=HTMLResponse)
async def audit_export_html(audit_id: int):
    """Relatório HTML como ficheiro (descarga), não abre no separador do browser."""
    row = await get_audit(DB_PATH, audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    html = _build_report_html(row)
    name = f"relatorio-acessibilidade-{audit_id}.html"
    return HTMLResponse(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@app.get("/audits/{audit_id}/report.html", response_class=HTMLResponse)
async def audit_report_html(audit_id: int):
    """Relatório legível (HTML) a partir do registo na base de dados — sem CDN."""
    row = await get_audit(DB_PATH, audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    html = _build_report_html(row)
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")


@app.get("/audits/{audit_id}/evidence-image")
async def audit_evidence_image(audit_id: int, barrier_idx: int = Query(0, ge=0), compact: bool = True):
    """
    Evidência por barreira.

    Prioridade: (1) cache em disco — (2) crop do fullPageScreenshot Lighthouse (lhIds)
    — (3) Playwright ao vivo — (4) screenshot global do bruto Lighthouse.
    """
    row = await get_audit(DB_PATH, audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    report = row.get("report") if isinstance(row.get("report"), dict) else {}
    bars = report.get("barreiras_automaticas") if isinstance(report.get("barreiras_automaticas"), list) else []
    if barrier_idx >= len(bars):
        raise HTTPException(status_code=404, detail="Barreira não encontrada")
    barrier = bars[barrier_idx] if isinstance(bars[barrier_idx], dict) else {}

    url = str(row.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=404, detail="URL da auditoria indisponível")

    lhids: list[str] = []
    raw_lhids = barrier.get("evidencia_lhids")
    if isinstance(raw_lhids, list):
        lhids = [str(x) for x in raw_lhids if x]

    selectors = _barrier_selector_candidates(barrier)
    key_src = f"{audit_id}|{barrier_idx}|{compact}|{url}|{'|'.join(lhids)}|{'|'.join(selectors)}"
    key = hashlib.sha256(key_src.encode("utf-8", errors="replace")).hexdigest()[:20]
    out_file = DATA_EVIDENCE_DIR / f"audit-{audit_id}-barreira-{barrier_idx}-{key}.png"

    if out_file.exists():
        return Response(
            content=out_file.read_bytes(),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    if lhids:
        lh_path = _resolved_raw_path(row.get("lighthouse_raw_path"))
        if lh_path is not None:
            try:
                lh_raw = json.loads(lh_path.read_text(encoding="utf-8"))
                png_bytes = _crop_lh_screenshot_evidence(lh_raw, lhids)
                if png_bytes:
                    DATA_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
                    out_file.write_bytes(png_bytes)
                    _log.info(
                        "Evidência LH crop: auditoria=%d barreira=%d lhids=%s",
                        audit_id,
                        barrier_idx,
                        lhids,
                    )
                    return Response(
                        content=png_bytes,
                        media_type="image/png",
                        headers={"Cache-Control": "public, max-age=86400"},
                    )
            except Exception as exc:
                _log.warning("Crop Lighthouse falhou (auditoria=%d barreira=%d): %s", audit_id, barrier_idx, exc)

    if selectors:
        try:
            await _capture_barrier_image(url, selectors, out_file, compact=compact)
            if out_file.exists():
                _log.info("Evidência Playwright: auditoria=%d barreira=%d", audit_id, barrier_idx)
                return Response(
                    content=out_file.read_bytes(),
                    media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"},
                )
        except Exception as exc:
            _log.warning("Playwright falhou (auditoria=%d barreira=%d): %s", audit_id, barrier_idx, exc)

    lh_path = _resolved_raw_path(row.get("lighthouse_raw_path"))
    if lh_path is None:
        ph = _placeholder_evidence_png()
        if ph:
            return Response(content=ph, media_type="image/png", headers={"X-Meta-Evidence": "placeholder"})
        raise HTTPException(status_code=404, detail="Imagem de evidência indisponível")
    try:
        raw = json.loads(lh_path.read_text(encoding="utf-8"))
    except Exception:
        ph = _placeholder_evidence_png("Bruto Lighthouse inválido")
        if ph:
            return Response(content=ph, media_type="image/png", headers={"X-Meta-Evidence": "placeholder"})
        raise HTTPException(status_code=500, detail="Falha ao ler bruto Lighthouse")
    data_url = _find_screenshot_data_url(raw)
    if not data_url:
        ph = _placeholder_evidence_png("Sem screenshot no Lighthouse bruto")
        if ph:
            return Response(content=ph, media_type="image/png", headers={"X-Meta-Evidence": "placeholder"})
        raise HTTPException(status_code=404, detail="Screenshot não encontrado no bruto Lighthouse")
    try:
        header, b64data = data_url.split(",", 1)
        mime = "image/webp"
        if "image/png" in header:
            mime = "image/png"
        elif "image/jpeg" in header:
            mime = "image/jpeg"
        _log.warning(
            "Fallback screenshot global (auditoria=%d barreira=%d)",
            audit_id,
            barrier_idx,
        )
        return Response(content=base64.b64decode(b64data), media_type=mime)
    except Exception:
        ph = _placeholder_evidence_png("Screenshot Lighthouse inválido")
        if ph:
            return Response(content=ph, media_type="image/png", headers={"X-Meta-Evidence": "placeholder"})
        raise HTTPException(status_code=500, detail="Screenshot inválido no bruto Lighthouse")


@app.get("/audits")
async def audits_list(
    limit: int = Query(50, ge=1, le=200, description="Máximo de registros (mais recentes primeiro)"),
    url: str | None = Query(None, description="Filtrar por URL exata e retornar histórico comparativo."),
    order_by: str = Query(
        "created_at",
        description="Campo para ordenação: created_at | score_risco | lh_score | wave_aim_score | barreiras_count",
    ),
    order_dir: str = Query("desc", description="Direção da ordenação: asc | desc"),
):
    """Lista auditorias; com ?url retorna série temporal da URL (ASC)."""
    if url:
        rows = await get_historico_url(DB_PATH, url=url, limit=limit)
        return {"url": url, "total": len(rows), "audits": rows}

    rows = await list_audits(DB_PATH, limit=limit, order_by=order_by, order_dir=order_dir)
    total = await count_audits(DB_PATH)
    return {"total": total, "audits": rows}


@app.get("/audits/buscar-urls")
async def audits_search_urls(
    q: str = Query("", description="Substring para autocomplete das URLs auditadas."),
    limit: int = Query(10, ge=1, le=50),
):
    urls = await search_urls(DB_PATH, q=q, limit=limit)
    return {"urls": urls}


@app.get("/audits/{audit_id}")
async def audits_get(audit_id: int):
    """Relatório completo de uma auditoria (report + score_breakdown como dict)."""
    row = await get_audit(DB_PATH, audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    return row


async def _fetch_wave_optional(url: str) -> tuple[dict, Path | None]:
    """Chama WAVE só se existir API key; caso contrário devolve dados vazio sem erro."""
    if not WAVE_API_KEY:
        return {}, None
    return await run_wave(url)


@app.post("/audit")
async def start_audit(request: AuditRequest):
    """
    Recebe uma URL pública. Em paralelo: PSI (Lighthouse ACCESSIBILITY) e WAVE (reporttype configurável).
    Brutos em data/raw/. Resposta: Lighthouse, WAVE e relatório consolidado (sem misturar score com contagens WAVE).

    Falha só (502) quando *nenhum* dos dois dados estiver disponível: sem Lighthouse *e* sem WAVE válido.
    Se WAVE_API_KEY não estiver definida, o WAVE é omitido (relatório só Lighthouse quando o PSI responder).
    """
    url = str(request.url)
    raw_psi: dict = {}
    raw_wave: dict = {}
    lh_raw_path: Path | None = None
    wave_raw_path: Path | None = None
    psi_error: str | None = None
    wave_error: str | None = None
    wave_skipped_no_key = not bool(WAVE_API_KEY)

    psi_result, wave_result = await asyncio.gather(
        run_lighthouse(url),
        _fetch_wave_optional(url),
        return_exceptions=True,
    )

    if isinstance(psi_result, Exception):
        psi_error = _describe_psi_exception(psi_result)
        _log.warning("PSI indisponivel para %s: %s", url, psi_error)
    else:
        raw_psi, lh_raw_path = psi_result

    if isinstance(wave_result, Exception):
        wave_error = _describe_wave_exception(wave_result)
        _log.warning("WAVE indisponivel para %s: %s", url, wave_error)
    else:
        raw_wave, wave_raw_path = wave_result

    has_lighthouse = not psi_error
    has_wave = wave_raw_path is not None

    # 502 apenas sem Lighthouse e sem JSON WAVE válido gravado em disco.
    if not has_lighthouse and not has_wave:
        parts = []
        if psi_error:
            parts.append(f"PSI={psi_error}")
        if wave_skipped_no_key:
            parts.append(
                "WAVE omitido (sem WAVE_API_KEY); PSI não devolveu dados — "
                "adicione WAVE_API_KEY ao .env ou aguarde cota PSI / use PSI_API_KEY"
            )
        elif wave_error:
            parts.append(f"WAVE={wave_error}")
        msg = " | ".join(parts) if parts else "Nenhum dado PSI/WAVE disponível"
        raise HTTPException(status_code=502, detail=msg)

    if psi_error and has_wave:
        _log.info("Auditoria parcial apenas WAVE para %s (%s)", url, psi_error)

    lhr = raw_psi.get("lighthouseResult") or {}
    categories_returned = list((lhr.get("categories") or {}).keys())

    a11y_category = get_accessibility_category(raw_psi)
    score = get_accessibility_score(raw_psi)

    audits = extract_accessibility_audits(raw_psi)
    classified = classify_accessibility_audits(audits) if audits else {
        "failed": [],
        "passed": [],
        "manual": [],
        "not_applicable": [],
        "informative": [],
        "errors": [],
    }
    score_breakdown = compute_score_breakdown(raw_psi) if raw_psi and (raw_psi.get("lighthouseResult")) else None
    failed_audits = classified["failed"]

    lh_auto, lh_manual = extract_lighthouse_issues(
        classified["failed"],
        classified["manual"],
        url,
    )

    wave_flat = extract_wave_items(raw_wave)
    w_bar, w_alert, w_info = wave_items_to_issues(wave_flat, url)
    lh_passed_tipos = extract_passed_tipo_set(classified["passed"])
    report = build_report(
        lh_auto, w_bar, w_alert, w_info, lh_manual, lh_passed_tipo_set=lh_passed_tipos
    )

    # ── Extensão experimental: texto auxiliar via IA (desligada por defeito) ──
    if AI_ENHANCE_REPORT and ANTHROPIC_API_KEY:
        try:
            from app.services.ai_enhancer import enhance_report

            await enhance_report(
                report=report,
                url=url,
                api_key=ANTHROPIC_API_KEY,
                lh_score=score,
                wave_score=_wave_aim_score_from_raw(raw_wave),
                level=AI_ENHANCE_LEVEL,
            )
        except Exception as _ai_exc:
            _log.warning("enhance_report falhou (não crítico): %s", _ai_exc)

    wave_cats = raw_wave.get("categories") if isinstance(raw_wave.get("categories"), dict) else {}
    wave_error_count = _wave_category_count(wave_cats, "error")
    wave_contrast_count = _wave_category_count(wave_cats, "contrast")
    barreiras_count = len(report.get("barreiras_automaticas") or [])
    divergencias_count = len(report.get("divergencias") or [])
    score_risco = (report.get("score_risco") or {}).get("valor")

    if wave_skipped_no_key:
        wave_meta = {"status": "skipped_no_key", "error": None}
    elif wave_error:
        wave_meta = {"status": "failed", "error": wave_error}
    else:
        wave_meta = {"status": "ok", "error": None}

    collection_meta = {
        "lighthouse": {"status": "ok" if not psi_error else "failed", "error": psi_error},
        "wave": wave_meta,
    }
    report["metadados_coleta"] = collection_meta

    audit_id = await save_audit(
        DB_PATH,
        url=url,
        lh_score=score,
        wave_aim_score=_wave_aim_score_from_raw(raw_wave),
        lh_failed_count=len(failed_audits),
        wave_error_count=wave_error_count,
        wave_contrast_count=wave_contrast_count,
        barreiras_count=barreiras_count,
        divergencias_count=divergencias_count,
        score_risco=score_risco,
        score_breakdown=score_breakdown,
        report=report,
        lighthouse_raw_path=_raw_path_for_db(lh_raw_path) if lh_raw_path else None,
        wave_raw_path=_raw_path_for_db(wave_raw_path) if wave_raw_path else None,
    )

    wave_stats = raw_wave.get("statistics") if isinstance(raw_wave.get("statistics"), dict) else {}
    wave_categories_summary: dict = {}
    for cname, cdata in wave_cats.items():
        if isinstance(cdata, dict):
            wave_categories_summary[cname] = {
                "description": cdata.get("description"),
                "count": cdata.get("count"),
            }

    body = {
        "app_version": APP_VERSION,
        "audit_id": audit_id,
        "url": url,
        "status": "completed",
        "lighthouse": {
            "categories_returned": categories_returned,
            "accessibility_score": score,
            "score_breakdown": score_breakdown,
            "failed_audits_count": len(failed_audits),
            "accessibility": {
                "score": score,
                "title": a11y_category.get("title"),
                "description": a11y_category.get("description"),
                "manual_checks_count": len(classified["manual"]),
                "passed_audits_count": len(classified["passed"]),
                "not_applicable_count": len(classified["not_applicable"]),
                "error_count": len(classified["errors"]),
                "failed_audits": classified["failed"],
                "manual_checks": classified["manual"],
            },
        },
        "wave": {
            "reporttype": WAVE_REPORT_TYPE,
            "statistics": wave_stats,
            "categories_summary": wave_categories_summary,
            "items_extracted_count": len(wave_flat),
        },
        "providers": collection_meta,
        "report": report,
        "raw_saved": {
            "lighthouse": bool(lh_raw_path),
            "wave": bool(wave_raw_path),
        },
    }
    if DEBUG:
        body["debug"] = {"project_root": str(PROJECT_ROOT)}
    return JSONResponse(content=body, status_code=200)


def _raise_429():
    raise HTTPException(
        status_code=429,
        detail=(
            "Google PageSpeed Insights está limitando requisições (429). "
            "Aguarde 10–30 minutos e tente de novo. "
            "Confira em GET /health se psi_api_key_configured é true; se for false, ative a .venv e reinicie o uvicorn."
        ),
    )


def _raise_400(google_message: str = ""):
    msg = (google_message or "").upper()
    if (
        "FAILED_DOCUMENT_REQUEST" in msg
        or "ERR_TIMED_OUT" in msg
        or "UNABLE TO RELIABLY LOAD" in msg
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "O Lighthouse não conseguiu carregar a página a tempo (timeout). "
                "A URL pode estar lenta, indisponível ou bloqueando o servidor do Google. "
                "Tente outra URL (ex.: https://example.com) ou teste de novo mais tarde."
            ),
        )
    base = (
        "Google PageSpeed Insights recusou a requisição (400). "
        "Confira: (1) A API 'PageSpeed Insights API' está ativada no projeto no Google Cloud; "
        "(2) A chave em .env está correta e sem espaços; (3) Se a chave tem restrição, permita 'PageSpeed Insights API'. "
    )
    if google_message:
        base += f"Resposta do Google: {google_message[:500]}"
    raise HTTPException(status_code=400, detail=base)


def _describe_psi_exception(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        body = ""
        try:
            body = (exc.response.text or "")[:500]
        except Exception:
            body = ""
        body_up = body.upper()
        if status == 429:
            return "429 Too Many Requests (quota/rate-limit no PageSpeed Insights)"
        if status == 400 and (
            "NO_FCP" in body_up or "FAILED_DOCUMENT_REQUEST" in body_up or "ERR_TIMED_OUT" in body_up
        ):
            return "400 NO_FCP/timeout: Lighthouse nao conseguiu renderizar a pagina no PSI"
        return f"HTTP {status}: {body or str(exc)}"
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return f"Timeout/conexao no PSI: {exc!s}"
    return str(exc)


def _describe_wave_exception(exc: Exception) -> str:
    if isinstance(exc, WaveAPIError):
        return exc.message or "erro retornado pela API WAVE"
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        body = ""
        try:
            body = (exc.response.text or "")[:500]
        except Exception:
            body = ""
        return f"HTTP {status}: {body or str(exc)}"
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return f"Timeout/conexao na API WAVE: {exc!s}"
    return str(exc)


@app.get("/health")
async def health_check():
    data = {
        "status": "ok",
        "version": APP_VERSION,
        "psi_api_key_configured": bool(PSI_API_KEY),
        "wave_api_key_configured": bool(WAVE_API_KEY),
        "wave_report_type": WAVE_REPORT_TYPE,
        "ai_enhance_configured": bool(ANTHROPIC_API_KEY),
        "ai_enhance_enabled": AI_ENHANCE_REPORT,
        "ai_enhance_level": AI_ENHANCE_LEVEL,
    }
    if DEBUG:
        data["project_root"] = str(PROJECT_ROOT)
    return data
