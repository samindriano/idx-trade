from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


class DecisionV3StructuralReplayError(RuntimeError):
    pass


EXPECTED_SOURCE_MANIFEST_SHA256 = (
    "6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205"
)
EXPECTED_SOURCE_SCORE_SHA256 = (
    "48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b"
)
EXPECTED_SCORE_SESSIONS = 600
EXPECTED_SCORE_ROWS = 172697
EXPECTED_NAIVE_TOP10_REPLACEMENTS = 3127
SCORE_FILENAME = "clean_challenger_validation_scores.parquet"

REPLAY_CONTRACT_RELATIVE_PATH = Path(
    "docs/specs/decision_v3_graded_evidence_structural_replay_contract_v2.json"
)
EXPECTED_REPLAY_CONTRACT_CANONICAL_SHA256 = (
    "4d16f2f8ca1a274e7d98cc8be24daaa0f4eb77bfc6e56ecf90c6f42f1b13239f"
)
ALLOWED_SCORE_COLUMNS = (
    "ticker",
    "date",
    "fold",
    "mode",
    "alpha_consensus",
)
SOURCE_GUARD_EXPECTATIONS = {
    "measurement_only": True,
    "provider_calls": False,
    "network_calls": False,
    "protected_forward_accessed": False,
    "fresh_forward_accessed": False,
}


@dataclass(frozen=True)
class PinnedReplaySource:
    frame: pd.DataFrame
    manifest_path: Path
    score_path: Path


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_frozen_replay_contract(repo_root: str | Path) -> Path:
    path = Path(repo_root).expanduser().resolve() / REPLAY_CONTRACT_RELATIVE_PATH
    if not path.is_file():
        raise DecisionV3StructuralReplayError(
            f"DECISION_V3_REPLAY_CONTRACT_MISSING:{path}"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_CONTRACT_INVALID_JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_CONTRACT_NOT_OBJECT"
        )
    actual = canonical_json_sha256(payload)
    if actual != EXPECTED_REPLAY_CONTRACT_CANONICAL_SHA256:
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_CONTRACT_CANONICAL_SHA_MISMATCH:"
            f"{actual}!={EXPECTED_REPLAY_CONTRACT_CANONICAL_SHA256}"
        )
    if payload.get("status") != "FROZEN_BEFORE_FIRST_REPLAY":
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_CONTRACT_STATUS_CHANGED"
        )
    if payload.get("execution_authorized") is not False:
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_CONTRACT_EXECUTION_FLAG_CHANGED"
        )
    return path


def _validate_source_manifest(path: Path) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_SOURCE_MANIFEST_INVALID"
        ) from exc
    if not isinstance(payload, dict):
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_SOURCE_MANIFEST_NOT_OBJECT"
        )
    for key, expected in SOURCE_GUARD_EXPECTATIONS.items():
        if payload.get(key) is not expected:
            raise DecisionV3StructuralReplayError(
                f"DECISION_V3_REPLAY_SOURCE_GUARD_CHANGED:{key}"
            )


def _read_projected_score_frame(
    score_path: Path,
    *,
    expected_rows: int = EXPECTED_SCORE_ROWS,
) -> pd.DataFrame:
    try:
        parquet = pq.ParquetFile(score_path)
    except Exception as exc:
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_SCORE_PARQUET_INVALID"
        ) from exc

    schema_names = set(parquet.schema.names)
    missing = set(ALLOWED_SCORE_COLUMNS) - schema_names
    if missing:
        raise DecisionV3StructuralReplayError(
            f"DECISION_V3_REPLAY_SCORE_COLUMNS_MISSING:{sorted(missing)}"
        )
    metadata_rows = int(parquet.metadata.num_rows)
    if metadata_rows != expected_rows:
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_SCORE_ROW_COUNT_CHANGED:"
            f"{metadata_rows}!={expected_rows}"
        )

    # Scientific boundary: only consensus-ranking reconstruction inputs are read.
    # Head-specific alpha values, labels, returns and any other parquet columns
    # remain unread. alpha_consensus is discarded from the policy projection after
    # deterministic rank_consensus reconstruction.
    return pd.read_parquet(score_path, columns=list(ALLOWED_SCORE_COLUMNS))


def _normalize_ticker(value: object) -> str:
    ticker = str(value).upper().replace(".JK", "").strip()
    if not ticker:
        raise DecisionV3StructuralReplayError("DECISION_V3_REPLAY_EMPTY_TICKER")
    return ticker


def _naive_top10_replacements(frame: pd.DataFrame) -> int:
    dates = sorted(pd.Timestamp(x) for x in frame["date"].drop_duplicates())
    total = 0
    previous: set[str] | None = None
    for day in dates:
        block = frame.loc[frame["date"].eq(day)]
        current = set(
            block.loc[block["rank_consensus"].le(10), "ticker"].astype(str)
        )
        if previous is not None:
            total += max(len(previous - current), len(current - previous))
        previous = current
    return total


def load_pinned_v4_x1_source_strict(root: str | Path) -> PinnedReplaySource:
    root_path = Path(root).expanduser().resolve()
    manifest_path = root_path / "MANIFEST.json"
    score_path = root_path / SCORE_FILENAME
    if not manifest_path.is_file() or not score_path.is_file():
        raise DecisionV3StructuralReplayError("DECISION_V3_REPLAY_SOURCE_MISSING")

    manifest_sha = sha256_file(manifest_path)
    score_sha = sha256_file(score_path)
    if manifest_sha != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise DecisionV3StructuralReplayError(
            f"DECISION_V3_REPLAY_SOURCE_MANIFEST_SHA_MISMATCH:{manifest_sha}"
        )
    if score_sha != EXPECTED_SOURCE_SCORE_SHA256:
        raise DecisionV3StructuralReplayError(
            f"DECISION_V3_REPLAY_SOURCE_SCORE_SHA_MISMATCH:{score_sha}"
        )
    _validate_source_manifest(manifest_path)

    frame = _read_projected_score_frame(score_path)
    frame["ticker"] = frame["ticker"].map(_normalize_ticker)
    frame["date"] = (
        pd.to_datetime(frame["date"], errors="raise")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    frame["alpha_consensus"] = pd.to_numeric(
        frame["alpha_consensus"], errors="raise"
    ).astype(float)
    if not np.isfinite(frame["alpha_consensus"]).all():
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_NONFINITE:alpha_consensus"
        )
    if frame.duplicated(["date", "ticker"]).any():
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_DUPLICATE_DATE_TICKER"
        )
    if frame["date"].nunique() != EXPECTED_SCORE_SESSIONS:
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_SCORE_SESSION_COUNT_CHANGED:"
            f"{frame['date'].nunique()}!={EXPECTED_SCORE_SESSIONS}"
        )
    if int(frame.groupby("date")["fold"].nunique().max()) != 1:
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_MULTIPLE_FOLDS_PER_SESSION"
        )
    if int(frame.groupby("date")["mode"].nunique().max()) != 1:
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_MULTIPLE_MODES_PER_SESSION"
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
            1, len(ranked) + 1, dtype=int
        )
        ranked["rank_consensus"] = ranked["rank_consensus"].astype(int)
        ranked_parts.append(ranked)

    ranked_frame = pd.concat(ranked_parts, ignore_index=True)
    naive_replacements = _naive_top10_replacements(ranked_frame)
    if naive_replacements != EXPECTED_NAIVE_TOP10_REPLACEMENTS:
        raise DecisionV3StructuralReplayError(
            "DECISION_V3_REPLAY_NAIVE_COMPARATOR_CHANGED:"
            f"{naive_replacements}!={EXPECTED_NAIVE_TOP10_REPLACEMENTS}"
        )

    return PinnedReplaySource(
        frame=ranked_frame,
        manifest_path=manifest_path,
        score_path=score_path,
    )
