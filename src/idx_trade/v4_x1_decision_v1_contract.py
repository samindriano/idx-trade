from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Literal

import pandas as pd

EXPECTED_CONFIG_SHA256 = "f464f51bc6ffc3e0d9b513850ca20d638ebddd33e4b737ec5582a55c2811b0b8"
EXPECTED_ALPHA_MODEL_ID = "V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1"
EXPECTED_ALPHA_MODEL_FINGERPRINT = "30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf"
EXPECTED_GENERATION = "V4-X1-CLEAN"
TARGET_POSITIONS = 10
ENTRY_RANK_MAX = 10
HARD_EXIT_RANK_GT = 20
REPLACEMENT_RANK_GAP_MIN = 5
SHADOW_STATE_SOURCE = "DECISION_V1_SHADOW_ONLY"
EXECUTION_REFERENCE = "OFFICIAL_OPEN_T_PLUS_1"
EXPECTED_FREEZE_BOUNDARY = "2026-08-20T12:08:44+00:00"
EXPECTED_SCIENTIFIC_BLOBS = {
    "src/idx_trade/ranking_v4_3_features.py": "59ad05f815870ae00480dc7945fe18371d8eff9c",
    "src/idx_trade/ranking_v4_3_preregistration.py": "cc1308feb51bbed16606bf7bded1ca0111644326",
}
_VERIFIED_TOKEN = object()

REQUIRED_SCORE_COLUMNS = (
    "ticker",
    "date",
    "alpha_h5",
    "alpha_h10",
    "alpha_consensus",
    "rank_consensus",
)


class DecisionV1Error(RuntimeError):
    pass


@dataclass(frozen=True)
class VerifiedScoreSession:
    session_date: str
    model_id: str
    model_fingerprint: str
    artifact_path: Path
    artifact_sha256: str
    manifest_path: Path
    manifest_sha256: str
    scores: pd.DataFrame
    alpha_tie_rows: int
    _verification_token: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class ShadowPortfolioState:
    as_of_session_date: str | None
    positions: tuple[str, ...]
    source: str = SHADOW_STATE_SOURCE

    @classmethod
    def empty(cls) -> "ShadowPortfolioState":
        return cls(as_of_session_date=None, positions=())


@dataclass(frozen=True)
class TradeIntent:
    side: Literal["BUY_INTENT", "SELL_INTENT"]
    ticker: str
    rank_consensus: int | None
    reason: str
    replacement_peer: str | None = None


@dataclass(frozen=True)
class DecisionPlan:
    decision_session_date: str
    execution_reference: str
    current_shadow_positions: tuple[str, ...]
    target_positions: tuple[str, ...]
    buy_intents: tuple[TradeIntent, ...]
    sell_intents: tuple[TradeIntent, ...]
    hold_tickers: tuple[str, ...]
    alpha_tie_rows: int
    rule_id: str = "V4_X1_DECISION_V1"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_frozen_config(config_path: str | Path) -> dict[str, object]:
    path = Path(config_path).expanduser().resolve()
    if not path.is_file():
        raise DecisionV1Error(f"DECISION_V1_CONFIG_MISSING:{path}")
    actual = _sha256(path)
    if actual != EXPECTED_CONFIG_SHA256:
        raise DecisionV1Error(f"DECISION_V1_CONFIG_SHA_MISMATCH:{actual}!={EXPECTED_CONFIG_SHA256}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "alpha_model_id": EXPECTED_ALPHA_MODEL_ID,
        "alpha_model_fingerprint": EXPECTED_ALPHA_MODEL_FINGERPRINT,
        "target_positions": TARGET_POSITIONS,
        "entry_rank_max": ENTRY_RANK_MAX,
        "hard_exit_rank_gt": HARD_EXIT_RANK_GT,
        "replacement_rank_gap_min": REPLACEMENT_RANK_GAP_MIN,
        "investment_policy": "NO_DISCRETIONARY_CASH_OR_MARKET_TIMING",
        "full_nav_investment_required": False,
        "residual_cash_allowed": True,
        "residual_cash_reason": "LOT_ROUNDING_OR_EXECUTION_RESIDUAL_ONLY",
        "state_source": SHADOW_STATE_SOURCE,
        "output_semantics": "INTENTS_NOT_FILLS",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise DecisionV1Error(f"DECISION_V1_CONFIG_CONTRACT_CHANGED:{key}")
    return payload


def _normalize_ticker(value: object) -> str:
    ticker = str(value).upper().replace(".JK", "").strip()
    if not ticker:
        raise DecisionV1Error("DECISION_V1_EMPTY_TICKER")
    return ticker


def _read_manifest(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV1Error(f"DECISION_V1_MANIFEST_INVALID:{path}") from exc
    if not isinstance(payload, dict):
        raise DecisionV1Error("DECISION_V1_MANIFEST_NOT_OBJECT")
    return payload


def _resolve_artifact(manifest_path: Path, raw: object) -> Path:
    candidate = Path(str(raw or ""))
    if not str(candidate):
        raise DecisionV1Error("DECISION_V1_ARTIFACT_PATH_MISSING")
    if candidate.is_absolute():
        return candidate
    return (manifest_path.parent / candidate).resolve()
