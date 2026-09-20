"""
database.py
===========
VajraTwin Local – SQLite persistence layer.

Two tables:
  telemetry_log   – original 2-residual EGT/CHT records (kept for /telemetry)
  twin_log        – full 5-residual + ML diagnostics + RUL prognostics records
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH: Path = Path(__file__).parent / "vajratwin.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create both tables if they do not exist."""
    with _connect() as conn:
        # ── Original EGT/CHT table (unchanged) ───────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_log (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                engine_id        TEXT    NOT NULL,
                timestamp        TEXT    NOT NULL,
                rpm              REAL,
                map_kpa          REAL,
                oat_c            REAL,
                egt_c            REAL,
                cht_c            REAL,
                dt_s             REAL,
                egt_expected     REAL,
                cht_expected     REAL,
                delta_egt        REAL,
                delta_cht        REAL,
                load_factor      REAL,
                mass_airflow     REAL,
                vol_efficiency   REAL,
                inlet_temp_c     REAL,
                advisory         TEXT,
                root_cause       TEXT,
                advisory_source  TEXT
            )
        """)

        # ── Full 5-channel + ML + RUL table ──────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS twin_log (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp             TEXT    NOT NULL,

                -- Raw telemetry (8 channels)
                rpm                   REAL,
                map_kpa               REAL,
                oat_c                 REAL,
                egt_avg_c             REAL,
                cht_avg_c             REAL,
                oil_temp_c            REAL,
                oil_pressure_psi      REAL,
                vibration_rms_g       REAL,

                -- Physics residuals (5 channels)
                delta_egt             REAL,
                delta_cht             REAL,
                delta_oil_temp        REAL,
                delta_oil_pressure    REAL,
                delta_vibration       REAL,

                -- Expected baselines
                expected_egt          REAL,
                expected_cht          REAL,
                expected_oil_temp     REAL,
                expected_oil_pressure REAL,
                expected_vibration    REAL,

                -- ML diagnostics
                anomaly_score         REAL,
                fault_class           TEXT,
                stress_coefficient    REAL,
                diag_status           TEXT,

                -- Prognostics / RUL
                current_health        REAL,
                rul_minutes           REAL,
                rul_p5                REAL,
                rul_p95               REAL,
                mission_advisory      TEXT,

                -- Active fault (from fault_status.json)
                active_fault          TEXT,
                fault_severity        REAL
            )
        """)
        conn.commit()


# ── telemetry_log helpers (unchanged) ─────────────────────────────────────

def insert_record(record: dict[str, Any]) -> int:
    sql = """
        INSERT INTO telemetry_log (
            engine_id, timestamp,
            rpm, map_kpa, oat_c, egt_c, cht_c, dt_s,
            egt_expected, cht_expected,
            delta_egt, delta_cht,
            load_factor, mass_airflow, vol_efficiency, inlet_temp_c,
            advisory, root_cause, advisory_source
        ) VALUES (
            :engine_id, :timestamp,
            :rpm, :map_kpa, :oat_c, :egt_c, :cht_c, :dt_s,
            :egt_expected, :cht_expected,
            :delta_egt, :delta_cht,
            :load_factor, :mass_airflow, :vol_efficiency, :inlet_temp_c,
            :advisory, :root_cause, :advisory_source
        )
    """
    with _connect() as conn:
        cur = conn.execute(sql, record)
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]


def fetch_recent(engine_id: str, limit: int = 100) -> list[dict]:
    sql = """
        SELECT * FROM telemetry_log
        WHERE engine_id = ?
        ORDER BY id DESC LIMIT ?
    """
    with _connect() as conn:
        rows = conn.execute(sql, (engine_id, limit)).fetchall()
    return [dict(r) for r in rows]


# ── twin_log helpers ──────────────────────────────────────────────────────

def insert_twin_record(r: dict[str, Any]) -> int:
    """Insert a full twin_analyze record. Returns new row id."""
    sql = """
        INSERT INTO twin_log (
            timestamp,
            rpm, map_kpa, oat_c,
            egt_avg_c, cht_avg_c, oil_temp_c, oil_pressure_psi, vibration_rms_g,
            delta_egt, delta_cht, delta_oil_temp, delta_oil_pressure, delta_vibration,
            expected_egt, expected_cht, expected_oil_temp, expected_oil_pressure, expected_vibration,
            anomaly_score, fault_class, stress_coefficient, diag_status,
            current_health, rul_minutes, rul_p5, rul_p95, mission_advisory,
            active_fault, fault_severity
        ) VALUES (
            :timestamp,
            :rpm, :map_kpa, :oat_c,
            :egt_avg_c, :cht_avg_c, :oil_temp_c, :oil_pressure_psi, :vibration_rms_g,
            :delta_egt, :delta_cht, :delta_oil_temp, :delta_oil_pressure, :delta_vibration,
            :expected_egt, :expected_cht, :expected_oil_temp, :expected_oil_pressure, :expected_vibration,
            :anomaly_score, :fault_class, :stress_coefficient, :diag_status,
            :current_health, :rul_minutes, :rul_p5, :rul_p95, :mission_advisory,
            :active_fault, :fault_severity
        )
    """
    with _connect() as conn:
        cur = conn.execute(sql, r)
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]


def fetch_twin_recent(limit: int = 100) -> list[dict]:
    """Return most recent *limit* twin_log records."""
    sql = "SELECT * FROM twin_log ORDER BY id DESC LIMIT ?"
    with _connect() as conn:
        rows = conn.execute(sql, (limit,)).fetchall()
    return [dict(r) for r in rows]
