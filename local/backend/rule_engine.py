"""
rule_engine.py
==============
VajraTwin Local – Deterministic advisory rule engine.

Replaces Bedrock in the local environment.  All thresholds are derived
from the Rotax 914 F/UL field service manual and the physics surrogate
diagnostic guidance.

Decision tree (evaluated in priority order)
-------------------------------------------
1. |ΔEGT| > 40 °C  OR  |ΔCHT| > 30 °C  →  MAINTENANCE REQUIRED
2. |ΔEGT| > 40 °C  OR  |ΔCHT| > 30 °C
   combined with load_factor > 1.2      →  MAINTENANCE REQUIRED  (already above)
3. load_factor > 1.2                    →  GO WITH DERATE
4. |ΔEGT| > 25 °C  OR  |ΔCHT| > 20 °C  →  GO WITH MONITORING
5. |ΔEGT| > 10 °C  OR  |ΔCHT| > 10 °C  →  GO WITH MONITORING
6. otherwise                            →  GO
"""

from __future__ import annotations


def get_advisory(physics: dict) -> dict:
    """
    Return advisory dict with keys:
        advisory        : one of the four operational states
        root_cause      : human-readable 1-2 sentence explanation
        advisory_source : always "rule_engine"
    """
    d_egt = physics.get("delta_egt_c", 0.0)
    d_cht = physics.get("delta_cht_c", 0.0)
    load  = physics.get("load_factor", 0.0)
    m_dot = physics.get("mass_airflow_kg_s", 0.0)

    abs_egt = abs(d_egt)
    abs_cht = abs(d_cht)

    # ── Priority 1: Hard thermal limit exceeded ───────────────────────────
    if abs_egt > 40.0 and abs_cht > 30.0:
        return _make(
            "MAINTENANCE REQUIRED",
            f"Critical multi-channel thermal exceedance: ΔEGT={d_egt:+.1f} °C, "
            f"ΔCHT={d_cht:+.1f} °C.  Suspect detonation, turbocharger over-boost, "
            f"or severe cooling failure.  Land immediately.",
        )

    if abs_egt > 40.0:
        cause = (
            "lean mixture or wastegate stiction" if d_egt > 0
            else "fuel enrichment fault or flooded cylinder"
        )
        return _make(
            "MAINTENANCE REQUIRED",
            f"High EGT residual ΔEGT={d_egt:+.1f} °C indicates {cause}.  "
            f"Airflow={m_dot:.4f} kg/s, load={load:.3f}.  Do not continue mission.",
        )

    if abs_cht > 30.0:
        cause = (
            "cooling degradation or oil starvation" if d_cht > 0
            else "excessive cooling or cowl flap fault"
        )
        return _make(
            "MAINTENANCE REQUIRED",
            f"High CHT residual ΔCHT={d_cht:+.1f} °C indicates {cause}.  "
            f"Load factor={load:.3f}.  Land as soon as practical.",
        )

    # ── Priority 2: Over-boost / MAP anomaly ─────────────────────────────
    if load > 1.2:
        return _make(
            "GO WITH DERATE",
            f"Engine load factor {load:.3f} exceeds rated threshold (1.20).  "
            f"Possible MAP sensor drift or wastegate partially closed.  "
            f"Reduce throttle to restore rated MAP.",
        )

    # ── Priority 3: Moderate deviation ───────────────────────────────────
    if abs_egt > 25.0 or abs_cht > 20.0:
        return _make(
            "GO WITH MONITORING",
            f"Moderate thermal residual: ΔEGT={d_egt:+.1f} °C, ΔCHT={d_cht:+.1f} °C.  "
            f"Engine within marginal envelope.  Monitor closely and reduce power "
            f"if trend continues.",
        )

    # ── Priority 4: Minor scatter ─────────────────────────────────────────
    if abs_egt > 10.0 or abs_cht > 10.0:
        return _make(
            "GO WITH MONITORING",
            f"Minor thermal scatter: ΔEGT={d_egt:+.1f} °C, ΔCHT={d_cht:+.1f} °C.  "
            f"Within normal operating tolerance.  Continue mission with monitoring.",
        )

    # ── Nominal ───────────────────────────────────────────────────────────
    return _make(
        "GO",
        f"Engine operating within nominal thermodynamic envelope.  "
        f"ΔEGT={d_egt:+.1f} °C, ΔCHT={d_cht:+.1f} °C, load={load:.3f}.  "
        f"All residuals within normal scatter limits.",
    )


def _make(advisory: str, root_cause: str) -> dict:
    return {
        "advisory":        advisory,
        "root_cause":      root_cause,
        "advisory_source": "rule_engine",
    }
