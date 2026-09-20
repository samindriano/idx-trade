"""Read-only probe of ticker-alias collisions in the pinned runtime universe.

The probe imports the exact pinned runtime from its separate worktree and uses
only synthetic prices/security metadata. It never writes runtime or research
data. The purpose is to test whether identity normalization is also a
uniqueness boundary at the universe layer.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
from typing import Any

import pandas as pd


RUNTIME_ROOT = Path(
    r"C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational"
).resolve()
EXPECTED_RUNTIME_HEAD = "402fca4b27e91cf8c82d21ff1394ba2d6da73656"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _runtime_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=RUNTIME_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def run_probe() -> dict[str, Any]:
    if _runtime_head() != EXPECTED_RUNTIME_HEAD:
        raise RuntimeError("PINNED_RUNTIME_HEAD_CHANGED")
    sys.path.insert(0, str(RUNTIME_ROOT / "src"))
    from idx_trade.data import canonicalize_ohlcv
    from idx_trade.security_master import (
        build_security_master,
        canonicalize_coverage_windows,
        canonicalize_tradability_anchors,
        canonicalize_tradability_intervals,
    )
    from idx_trade.universe import build_dynamic_liquidity_universe
    from idx_trade.decision_v2_minimal import DecisionV2Error
    from idx_trade.v4_x1_decision_v1_contract import (
        EXPECTED_ALPHA_MODEL_FINGERPRINT,
        EXPECTED_ALPHA_MODEL_ID,
        VerifiedScoreSession,
        _VERIFIED_TOKEN,
    )
    from idx_trade.v4_x1_decision_v2_minimal import rank_session_from_v4_x1_verified

    active = pd.DataFrame({
        "ticker": ["ABCD"],
        "company_name": ["ABCD Tbk"],
        "listed_from": ["2020-01-01"],
        "listed_to": [None],
        "source": ["IDX_SYNTHETIC"],
    })
    master = build_security_master(active, pd.DataFrame())
    sessions = pd.bdate_range("2026-01-02", periods=60)
    coverage = canonicalize_coverage_windows(pd.DataFrame({
        "market": ["REGULAR"],
        "effective_from": ["2020-01-01"],
        "effective_to": ["2026-12-31"],
        "source": ["SYNTHETIC_COMPLETE"],
        "is_complete": [True],
        "discovery_basis": ["SYNTHETIC"],
        "left_boundary_basis": ["SYNTHETIC"],
    }))
    intervals = canonicalize_tradability_intervals(pd.DataFrame())
    anchors = canonicalize_tradability_anchors(pd.DataFrame([
        {
            "ticker": "ABCD",
            "market": "REGULAR",
            "as_of_date": session.date().isoformat(),
            "state": "ACTIVE",
            "source": "IDX_SYNTHETIC",
            "source_ref": f"synthetic://ABCD/{session.date().isoformat()}",
            "evidence_type": "OFFICIAL_ACTIVE_STATUS",
        }
        for session in sessions
    ]))
    raw = pd.DataFrame({
        "date": sessions,
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.0,
        "volume": 1_000_000.0,
    })
    frame = canonicalize_ohlcv(raw)
    price_frames = {"ABCD": frame, "ABCD.JK": frame.copy()}
    output = build_dynamic_liquidity_universe(
        pd.Timestamp("2026-03-27"),
        sessions,
        price_frames,
        master,
        intervals,
        coverage,
        tradability_anchors=anchors,
        top_n=2,
        lookback_sessions=60,
        minimum_warmup_sessions=60,
    )
    duplicate_key = bool(output["ticker"].duplicated(keep=False).any())
    report = {
        "status": "IDENTITY_COLLISION_REPRODUCED" if duplicate_key else "NO_COLLISION",
        "runtime_head": _runtime_head(),
        "runtime_source_sha256": {
            "universe.py": _sha256(RUNTIME_ROOT / "src/idx_trade/universe.py"),
            "security_master.py": _sha256(RUNTIME_ROOT / "src/idx_trade/security_master.py"),
        },
        "synthetic_input_keys": ["ABCD", "ABCD.JK"],
        "normalized_identity": "ABCD",
        "output_rows": int(len(output)),
        "unique_tickers": int(output["ticker"].nunique()),
        "selected_rows": int(output["selected"].sum()),
        "duplicate_ticker_key": duplicate_key,
        "selected_rank_values": [
            int(value) for value in output.loc[output["selected"], "liquidity_rank"]
        ],
        "writes_performed": False,
    }
    if report["output_rows"] != 2 or report["unique_tickers"] != 1:
        raise AssertionError("SYNTHETIC_COLLISION_FIXTURE_NOT_OBSERVED")
    if report["selected_rows"] != 2 or not duplicate_key:
        raise AssertionError("UNIVERSE_COLLISION_DID_NOT_REPRODUCE")
    downstream_rejection = None
    scores = pd.DataFrame({
        "ticker": ["ABCD", "ABCD.JK", *[f"X{i:02d}" for i in range(1, 29)]],
        "rank_consensus": list(range(1, 31)),
    })
    verified = VerifiedScoreSession(
        session_date="2026-03-27",
        model_id=EXPECTED_ALPHA_MODEL_ID,
        model_fingerprint=EXPECTED_ALPHA_MODEL_FINGERPRINT,
        artifact_path=Path("synthetic.parquet"),
        artifact_sha256="synthetic-artifact",
        manifest_path=Path("synthetic.json"),
        manifest_sha256="synthetic-manifest",
        scores=scores,
        alpha_tie_rows=0,
        _verification_token=_VERIFIED_TOKEN,
    )
    try:
        rank_session_from_v4_x1_verified(verified)
    except DecisionV2Error as exc:
        downstream_rejection = str(exc)
    if downstream_rejection != "DECISION_V2_V4_X1_DUPLICATE_TICKER":
        raise AssertionError("DOWNSTREAM_IDENTITY_GUARD_NOT_OBSERVED")
    report["downstream_decision_guard"] = downstream_rejection
    return report


if __name__ == "__main__":
    import json

    print(json.dumps(run_probe(), indent=2, sort_keys=True))
