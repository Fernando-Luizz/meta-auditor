"""
Persistência SQLite com aiosqlite.

Schema:
    tabela `audits` — uma linha por auditoria completada.

Funções públicas:
    init_db(db_path)          — cria tabela e índices se não existirem.
    save_audit(db_path, ...)  — insere um registro; retorna o id gerado.
    list_audits(db_path)      — lista resumos das últimas N auditorias.
    get_historico_url(db_path, url, limit) — série temporal por URL.
    search_urls(db_path, q, limit)         — autocomplete de URLs auditadas.
    get_audit(db_path, id)    — retorna um registro completo (com report).
    count_audits(db_path)     — total de linhas em `audits`.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

# ── DDL ─────────────────────────────────────────────────────────────────────
_DDL = """
CREATE TABLE IF NOT EXISTS audits (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    url                 TEXT    NOT NULL,
    created_at          TEXT    NOT NULL,           -- ISO-8601 UTC
    lh_score            REAL,                       -- 0.0–1.0 (null se PSI falhou)
    wave_aim_score      REAL,                       -- 0.0–10.0 (null se WAVE falhou)
    lh_failed_count     INTEGER NOT NULL DEFAULT 0,
    wave_error_count    INTEGER NOT NULL DEFAULT 0,
    wave_contrast_count INTEGER NOT NULL DEFAULT 0,
    barreiras_count     INTEGER NOT NULL DEFAULT 0,
    divergencias_count  INTEGER NOT NULL DEFAULT 0,
    score_risco         REAL,                       -- 0.0–3.0 (null se sem barreiras)
    score_breakdown     TEXT,                       -- JSON do compute_score_breakdown()
    report              TEXT    NOT NULL,            -- JSON do build_report()
    lighthouse_raw_path TEXT,                       -- relativo à raiz do projeto (data/raw/…)
    wave_raw_path       TEXT
);

CREATE INDEX IF NOT EXISTS idx_audits_url        ON audits(url);
CREATE INDEX IF NOT EXISTS idx_audits_created_at ON audits(created_at DESC);
"""


async def _ensure_audit_columns(db) -> None:
    """Bases antigas: acrescenta colunas de caminhos dos JSON brutos."""
    cur = await db.execute("PRAGMA table_info(audits)")
    rows = await cur.fetchall()
    names = {r[1] for r in rows}
    if "lighthouse_raw_path" not in names:
        await db.execute("ALTER TABLE audits ADD COLUMN lighthouse_raw_path TEXT")
    if "wave_raw_path" not in names:
        await db.execute("ALTER TABLE audits ADD COLUMN wave_raw_path TEXT")
    if "score_risco" not in names:
        await db.execute("ALTER TABLE audits ADD COLUMN score_risco REAL")


async def init_db(db_path: Path) -> None:
    """Inicializa o banco — cria arquivo, tabela e índices se não existirem."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(_DDL)
        await _ensure_audit_columns(db)
        await db.commit()


async def save_audit(
    db_path: Path,
    *,
    url: str,
    lh_score: float | None,
    wave_aim_score: float | None,
    lh_failed_count: int,
    wave_error_count: int,
    wave_contrast_count: int,
    barreiras_count: int,
    divergencias_count: int,
    score_breakdown: dict | None,
    report: dict,
    lighthouse_raw_path: str | None = None,
    wave_raw_path: str | None = None,
    score_risco: float | None = None,
) -> int:
    """
    Insere uma auditoria completa no banco.

    Returns:
        O id (ROWID) gerado pelo SQLite.
    """
    now = datetime.now(timezone.utc).isoformat()
    sb_json = json.dumps(score_breakdown, ensure_ascii=False) if score_breakdown else None
    rep_json = json.dumps(report, ensure_ascii=False)

    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            INSERT INTO audits (
                url, created_at,
                lh_score, wave_aim_score,
                lh_failed_count, wave_error_count, wave_contrast_count,
                barreiras_count, divergencias_count,
                score_risco,
                score_breakdown, report,
                lighthouse_raw_path, wave_raw_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                url,
                now,
                lh_score,
                wave_aim_score,
                lh_failed_count,
                wave_error_count,
                wave_contrast_count,
                barreiras_count,
                divergencias_count,
                score_risco,
                sb_json,
                rep_json,
                lighthouse_raw_path,
                wave_raw_path,
            ),
        )
        await db.commit()
        return int(cur.lastrowid)


async def update_report(db_path: Path, audit_id: int, report: dict) -> None:
    """Atualiza apenas o campo `report` de uma auditoria existente.

    Usado após re-enriquecimento IA para persistir dados de nível 2 que
    falharam na primeira execução (timeout/rate-limit momentâneo).
    """
    rep_json = json.dumps(report, ensure_ascii=False)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE audits SET report = ? WHERE id = ?",
            (rep_json, audit_id),
        )
        await db.commit()


async def list_audits(
    db_path: Path,
    limit: int = 50,
    order_by: str = "created_at",
    order_dir: str = "desc",
) -> list[dict]:
    """
    Retorna os últimos `limit` registros — sem expor o campo `report` completo.
    Ordenável por campos permitidos.
    """
    allowed_order_by = {"created_at", "score_risco", "lh_score", "wave_aim_score", "barreiras_count"}
    allowed_order_dir = {"asc", "desc"}
    safe_order_by = order_by if order_by in allowed_order_by else "created_at"
    safe_order_dir = order_dir.lower() if order_dir.lower() in allowed_order_dir else "desc"

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            f"""
            SELECT
                id, url, created_at,
                lh_score, wave_aim_score,
                lh_failed_count, wave_error_count, wave_contrast_count,
                barreiras_count, divergencias_count,
                score_risco,
                json_extract(report, '$.score_risco.nivel') AS score_risco_nivel,
                report
            FROM audits
            ORDER BY {safe_order_by} {safe_order_dir}, created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cur.fetchall()
        out: list[dict] = []
        for row in rows:
            d = dict(row)
            report_obj: dict = {}
            if isinstance(d.get("report"), str) and d["report"]:
                try:
                    report_obj = json.loads(d["report"])
                except Exception:
                    report_obj = {}
            meta = report_obj.get("metadados_coleta") if isinstance(report_obj, dict) else None
            lh_meta = meta.get("lighthouse") if isinstance(meta, dict) else None
            psi_failed = isinstance(lh_meta, dict) and lh_meta.get("status") == "failed"
            d["psi_unavailable"] = bool(psi_failed)
            d["psi_error"] = str(lh_meta.get("error") or "") if isinstance(lh_meta, dict) else ""
            d.pop("report", None)
            out.append(d)
        return out


async def count_audits(db_path: Path) -> int:
    """Número total de auditorias armazenadas."""
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute("SELECT COUNT(*) FROM audits")
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def get_historico_url(db_path: Path, url: str, limit: int = 30) -> list[dict]:
    """
    Série temporal de uma URL específica, em ordem cronológica (ASC).
    """
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT
                id,
                created_at,
                lh_score,
                wave_aim_score,
                barreiras_count,
                divergencias_count,
                score_risco,
                json_extract(report, '$.score_risco.nivel') AS score_risco_nivel
            FROM audits
            WHERE url = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (url, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def search_urls(db_path: Path, q: str, limit: int = 10) -> list[str]:
    """
    Retorna URLs distintas contendo `q` (case-insensitive por padrão do SQLite LIKE).
    """
    query = (q or "").strip()
    if not query:
        return []
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            """
            SELECT DISTINCT url
            FROM audits
            WHERE url LIKE ?
            ORDER BY url
            LIMIT ?
            """,
            (f"%{query}%", limit),
        )
        rows = await cur.fetchall()
        return [str(r[0]) for r in rows if r and r[0]]


async def get_audit(db_path: Path, audit_id: int) -> dict | None:
    """
    Retorna o registro completo de uma auditoria, incluindo `report` e
    `score_breakdown` já desserializados como dict.
    Retorna None se o id não existir.
    """
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM audits WHERE id = ?",
            (audit_id,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        d = dict(row)
        d["score_breakdown"] = (
            json.loads(d["score_breakdown"]) if d["score_breakdown"] else None
        )
        d["report"] = json.loads(d["report"]) if d["report"] else {}
        return d
