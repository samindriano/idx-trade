from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .decision_v2_structural_replay import (
    DecisionV2StructuralReplayError,
    EXPECTED_NAIVE_TOP10_REPLACEMENTS,
    EXPECTED_SCORE_ROWS,
    EXPECTED_SCORE_SESSIONS,
    EXPECTED_SOURCE_MANIFEST_SHA256,
    EXPECTED_SOURCE_SCORE_SHA256,
    PinnedReplaySource,
    SCORE_FILENAME,
    SOURCE_GUARD_EXPECTATIONS,
    _naive_top10_replacements,
    canonical_json_sha256,
    sha256_file,
)


REPLAY_CONTRACT_RELATIVE_PATH = Path(
    "docs/specs/decision_v2_minimal_structural_replay_contract_v1.json"
)
EXPECTED_REPLAY_CONTRACT_CANONICAL_SHA256 = (
    "2f4e04fe060b43da6d555717a5aab687c10f40fa114ee954ae24082f912d455f"
)
ALLOWED_SCORE_COLUMNS = (
    "ticker",
    "date",
    "fold",
    "mode",
    "alpha_h5",
    "alpha_h10",
    "alpha_consensus",
)


def verify_frozen_replay_contract(repo_root: str | Path) -> Path:
    path = Path(repo_root).expanduser().resolve() / REPLAY_CONTRACT_RELATIVE_PATH
    if not path.is_file():
        raise DecisionV2StructuralReplayError(
            f"DECISION_V2_REPLAY_CONTRACT_MISSING:{path}"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_CONTRACT_INVALID_JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_CONTRACT_NOT_OBJECT"
        )
    actual = canonical_json_sha256(payload)
    if actual != EXPECTED_REPLAY_CONTRACT_CANONICAL_SHA256:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_CONTRACT_CANONICAL_SHA_MISMATCH:"
            f"{actual}!={EXPECTED_REPLAY_CONTRACT_CANONICAL_SHA256}"
        )
    if payload.get("status") != "FROZEN_BEFORE_FIRST_REPLAY":
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_CONTRACT_STATUS_CHANGED"
        )
    return path


def _validate_source_manifest(path: Path) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_SOURCE_MANIFEST_INVALID"
        ) from exc
    if not isinstance(payload, dict):
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_SOURCE_MANIFEST_NOT_OBJECT"
        )
    for key, expected in SOURCE_GUARD_EXPECTATIONS.items():
        if payload.get(key) is not expected:
            raise DecisionV2StructuralReplayError(
                f"DECISION_V2_REPLAY_SOURCE_GUARD_CHANGED:{key}"
            )


def _read_projected_score_frame(
    score_path: Path,
    *,
    expected_rows: int = EXPECTED_SCORE_ROWS,
) -> pd.DataFrame:
    try:
        parquet = pq.ParquetFile(score_path)
    except Exception as exc:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_SCORE_PARQUET_INVALID"
        ) from exc

    schema_names = set(parquet.schema.names)
    missing = set(ALLOWED_SCORE_COLUMNS) - schema_names
    if missing:
        raise DecisionV2StructuralReplayError(
            f"DECISION_V2_REPLAY_SCORE_COLUMNS_MISSING:{sorted(missing)}"
        )
    metadata_rows = int(parquet.metadata.num_rows)
    if metadata_rows != expected_rows:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_SCORE_ROW_COUNT_CHANGED:"
            f"{metadata_rows}!={expected_rows}"
        )

    # Scientific boundary: read only the preregistered score/rank inputs.
    # Extra parquet columns (including any labels/returns if ever present)
    # remain unread.
    return pd.read_parquet(
        score_path,
        columns=list(ALLOWED_SCORE_COLUMNS),
    )


def _normalize_ticker(value: object) -> str:
    ticker = str(value).upper().replace(".JK", "").strip()
    if not ticker:
        raise DecisionV2StructuralReplayError("DECISION_V2_REPLAY_EMPTY_TICKER")
    return ticker


def load_pinned_v4_x1_source_strict(root: str | Path) -> PinnedReplaySource:
    root_path = Path(root).expanduser().resolve()
    manifest_path = root_path / "MANIFEST.json"
    score_path = root_path / SCORE_FILENAME
    if not manifest_path.is_file() or not score_path.is_file():
        raise DecisionV2StructuralReplayError("DECISION_V2_REPLAY_SOURCE_MISSING")

    manifest_sha = sha256_file(manifest_path)
    score_sha = sha256_file(score_path)
    if manifest_sha != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise DecisionV2StructuralReplayError(
            f"DECISION_V2_REPLAY_SOURCE_MANIFEST_SHA_MISMATCH:{manifest_sha}"
        )
    if score_sha != EXPECTED_SOURCE_SCORE_SHA256:
        raise DecisionV2StructuralReplayError(
            f"DECISION_V2_REPLAY_SOURCE_SCORE_SHA_MISMATCH:{score_sha}"
        )
    _validate_source_manifest(manifest_path)

    frame = _read_projected_score_frame(score_path)
    frame["ticker"] = frame["ticker"].map(_normalize_ticker)
    frame["date"] = (
        pd.to_datetime(frame["date"], errors="raise")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    for column in ("alpha_h5", "alpha_h10", "alpha_consensus"):
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype(float)
        if not np.isfinite(frame[column]).all():
            raise DecisionV2StructuralReplayError(
                f"DECISION_V2_REPLAY_NONFINITE:{column}"
            )

    if frame.duplicated(["date", "ticker"]).any():
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_DUPLICATE_DATE_TICKER"
        )
    if frame["date"].nunique() != EXPECTED_SCORE_SESSIONS:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_SCORE_SESSION_COUNT_CHANGED:"
            f"{frame['date'].nunique()}!={EXPECTED_SCORE_SESSIONS}"
        )
    if int(frame.groupby("date")["fold"].nunique().max()) != 1:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_MULTIPLE_FOLDS_PER_SESSION"
        )
    if int(frame.groupby("date")["mode"].nunique().max()) != 1:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_MULTIPLE_MODES_PER_SESSION"
        )

    ranked_parts: list[pd.DataFrame] = []
    for _, block in frame.groupby("date", sort=True):
        ranked = block.copy()
        order = ranked.sort_values(
            ["alpha_consensus", "ticker"],
            ascending=[False, True],
            kind="mergesort",
        ).index
        ranked.loc[order, "rank_consensus"] = np.arange(
            1,
            len(ranked) + 1,
            dtype=int,
        )
        ranked["rank_consensus"] = ranked["rank_consensus"].astype(int)
        ranked_parts.append(ranked)

    ranked_frame = pd.concat(ranked_parts, ignore_index=True)
    naive_replacements = _naive_top10_replacements(ranked_frame)
    if naive_replacements != EXPECTED_NAIVE_TOP10_REPLACEMENTS:
        raise DecisionV2StructuralReplayError(
            "DECISION_V2_REPLAY_NAIVE_COMPARATOR_CHANGED:"
            f"{naive_replacements}!={EXPECTED_NAIVE_TOP10_REPLACEMENTS}"
        )

    return PinnedReplaySource(
        frame=ranked_frame,
        manifest_path=manifest_path,
        score_path=score_path,
    )
