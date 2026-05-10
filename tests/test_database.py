"""Testes da camada app.database (SQLite real em arquivo temporário)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.database import count_audits, get_audit, init_db, list_audits, save_audit


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


def _run(coro):
    return asyncio.run(coro)


def test_init_db_creates_file(db_path: Path):
    _run(init_db(db_path))
    assert db_path.is_file()


def test_save_audit_returns_incrementing_id(db_path: Path):
    _run(init_db(db_path))
    rep = {"barreiras_automaticas": [], "divergencias": []}
    sb = {"total_weight": 10, "score_calculated": 100.0}
    a1 = _run(
        save_audit(
            db_path,
            url="https://a.example/",
            lh_score=0.9,
            wave_aim_score=8.0,
            lh_failed_count=1,
            wave_error_count=2,
            wave_contrast_count=3,
            barreiras_count=4,
            divergencias_count=0,
            score_breakdown=sb,
            report=rep,
        )
    )
    a2 = _run(
        save_audit(
            db_path,
            url="https://b.example/",
            lh_score=None,
            wave_aim_score=None,
            lh_failed_count=0,
            wave_error_count=0,
            wave_contrast_count=0,
            barreiras_count=0,
            divergencias_count=1,
            score_breakdown=None,
            report=rep,
        )
    )
    assert a1 == 1 and a2 == 2


def test_count_audits(db_path: Path):
    _run(init_db(db_path))
    assert _run(count_audits(db_path)) == 0
    rep = {"x": 1}
    _run(
        save_audit(
            db_path,
            url="https://u/",
            lh_score=1.0,
            wave_aim_score=10.0,
            lh_failed_count=0,
            wave_error_count=0,
            wave_contrast_count=0,
            barreiras_count=0,
            divergencias_count=0,
            score_breakdown={},
            report=rep,
        )
    )
    assert _run(count_audits(db_path)) == 1


def test_get_audit_deserializes_json(db_path: Path):
    _run(init_db(db_path))
    rep = {"barreiras_automaticas": [{"issue_tipo_normalizado": "t"}], "divergencias": []}
    sb = {"failed_audits": [], "score_calculated": 95.0}
    _run(
        save_audit(
            db_path,
            url="https://c.example/",
            lh_score=0.5,
            wave_aim_score=5.0,
            lh_failed_count=2,
            wave_error_count=1,
            wave_contrast_count=1,
            barreiras_count=3,
            divergencias_count=0,
            score_breakdown=sb,
            report=rep,
        )
    )
    row = _run(get_audit(db_path, 1))
    assert row is not None
    assert row["url"] == "https://c.example/"
    assert row["lh_score"] == 0.5
    assert row["wave_aim_score"] == 5.0
    assert row["barreiras_count"] == 3
    assert row["divergencias_count"] == 0
    assert row["report"] == rep
    assert row["score_breakdown"] == sb
    assert isinstance(row["report"], dict)


def test_get_audit_not_found(db_path: Path):
    _run(init_db(db_path))
    assert _run(get_audit(db_path, 999)) is None


def test_save_audit_stores_raw_paths(db_path: Path):
    _run(init_db(db_path))
    rep: dict = {"barreiras_automaticas": [], "divergencias": []}
    _run(
        save_audit(
            db_path,
            url="https://raw.test/",
            lh_score=0.8,
            wave_aim_score=7.0,
            lh_failed_count=0,
            wave_error_count=0,
            wave_contrast_count=0,
            barreiras_count=0,
            divergencias_count=0,
            score_breakdown=None,
            report=rep,
            lighthouse_raw_path="data/raw/lighthouse_x.json",
            wave_raw_path="data/raw/wave_x.json",
        )
    )
    row = _run(get_audit(db_path, 1))
    assert row is not None
    assert row["lighthouse_raw_path"] == "data/raw/lighthouse_x.json"
    assert row["wave_raw_path"] == "data/raw/wave_x.json"


def test_list_audits_without_report(db_path: Path):
    _run(init_db(db_path))
    rep = {"divergencias": [1, 2]}
    _run(
        save_audit(
            db_path,
            url="https://list/",
            lh_score=None,
            wave_aim_score=4.0,
            lh_failed_count=0,
            wave_error_count=5,
            wave_contrast_count=6,
            barreiras_count=7,
            divergencias_count=2,
            score_breakdown=None,
            report=rep,
        )
    )
    rows = _run(list_audits(db_path, limit=10))
    assert len(rows) == 1
    r0 = rows[0]
    assert "report" not in r0
    assert r0["url"] == "https://list/"
    assert r0["divergencias_count"] == 2
    assert r0["wave_contrast_count"] == 6
    assert r0["psi_unavailable"] is False
    assert r0["psi_error"] == ""


def test_list_audits_includes_psi_unavailable_flag(db_path: Path):
    _run(init_db(db_path))
    rep = {
        "metadados_coleta": {
            "lighthouse": {
                "status": "failed",
                "error": "400 NO_FCP/timeout",
            }
        }
    }
    _run(
        save_audit(
            db_path,
            url="https://psi-offline/",
            lh_score=None,
            wave_aim_score=6.0,
            lh_failed_count=0,
            wave_error_count=1,
            wave_contrast_count=0,
            barreiras_count=1,
            divergencias_count=0,
            score_breakdown=None,
            report=rep,
        )
    )
    rows = _run(list_audits(db_path, limit=10))
    assert len(rows) == 1
    assert rows[0]["psi_unavailable"] is True
    assert "NO_FCP" in rows[0]["psi_error"]


def test_list_audits_order_newest_first(db_path: Path):
    _run(init_db(db_path))
    rep: dict = {}
    for i, u in enumerate(["https://old/", "https://new/"], start=1):
        _id = _run(
            save_audit(
                db_path,
                url=u,
                lh_score=float(i),
                wave_aim_score=None,
                lh_failed_count=0,
                wave_error_count=0,
                wave_contrast_count=0,
                barreiras_count=0,
                divergencias_count=0,
                score_breakdown=None,
                report=rep,
            )
        )
        assert _id == i
    listed = _run(list_audits(db_path, limit=50))
    assert [r["url"] for r in listed] == ["https://new/", "https://old/"]


def test_list_audits_respects_limit(db_path: Path):
    _run(init_db(db_path))
    for i in range(5):
        _run(
            save_audit(
                db_path,
                url=f"https://x{i}.example/",
                lh_score=1.0,
                wave_aim_score=None,
                lh_failed_count=0,
                wave_error_count=0,
                wave_contrast_count=0,
                barreiras_count=0,
                divergencias_count=0,
                score_breakdown=None,
                report={},
            )
        )
    two = _run(list_audits(db_path, limit=2))
    assert len(two) == 2
    assert _run(count_audits(db_path)) == 5
