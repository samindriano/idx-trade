from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .decision_v2_structural_replay import (
    EXPECTED_NAIVE_TOP10_REPLACEMENTS,
    EXPECTED_SCORE_ROWS,
    EXPECTED_SCORE_SESSIONS,
    EXPECTED_SOURCE_MANIFEST_SHA256,
    EXPECTED_SOURCE_SCORE_SHA256,
    PinnedReplaySource,
    SCORE_FILENAME,
    SOURCE_GUARD_EXPECTATIONS,
    _naive_top10_replacements,
    sha256_file,
)


ALLOWED_KILL_DIAGNOSIS_SCORE_COLUMNS = (
    "ticker",
    "date",
    "fold",
    "mode",
    "alpha_consensus",
)


class DecisionV3KillSourceError(RuntimeError):
    pass


def _normalize_ticker(value: object) -> str:
    ticker = str(value).upper().replace(".JK", "").strip()
    if not ticker:
        raise DecisionV3KillSourceError("DECISION_V3_KILL_SOURCE_EMPTY_TICKER")
    return ticker


def _validate_manifest(path: Path) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV3KillSourceError(
            "DECISION_V3_KILL_SOURCE_MANIFEST_INVALID"
        ) from exc
    if not isinstance(payload, dict):
        raise DecisionV3KillSourceError(
            "DECISION_V3_KILL_SOURCE_MANIFEST_NOT_OBJECT"
        )
    for key, expected in SOURCE_GUARD_EXPECTATIONS.items():
        if payload.get(key) is not expected:
            raise DecisionV3KillSourceError(
                f"DECISION_V3_KILL_SOURCE_GUARD_CHANGED:{key}"
            )


def load_consensus_only_pinned_source(root: str | Path) -> PinnedReplaySource:
    root_path = Path(root).expanduser().resolve()
    manifest_path = root_path / "MANIFEST.json"
    score_path = root_path / SCORE_FILENAME
    if not manifest_path.is_file() or not score_path.is_file():
        raise DecisionV3KillSourceError("DECISION_V3_KILL_SOURCE_MISSING")

    manifest_sha = sha256_file(manifest_path)
    score_sha = sha256_file(score_path)
    if manifest_sha != EXPECTED_SOURCE_MANIFEST_SHA256:
        raise DecisionV3KillSourceError(
            "DECISION_V3_KILL_SOURCE_MANIFEST_SHA_MISMATCH:"
            f"{manifest_sha}!={EXPECTED_SOURCE_MANIFEST_SHA256}"
        )
    if score_sha != EXPECTED_SOURCE_SCORE_SHA256:
        raise DecisionV3KillSourceError(
            "DECISION_V3_KILL_SOURCE_SCORE_SHA_MISMATCH:"
            f"{score_sha}!={EXPECTED_SOURCE_SCORE_SHA256}"
        )
    _validate_manifest(manifest_path)

    try:
        parquet = pq.ParquetFile(score_path)
    except Exception as exc:
        raise DecisionV3KillSourceError(
            "DECISION_V3_KILL_SOURCE_PARQUET_INVALID"
        ) from exc
    schema_names = set(parquet.schema.names)
    missing = set(ALLOWED_KILL_DIAGNOSIS_SCORE_COLUMNS) - schema_names
    if missing:
        raise DecisionV3KillSourceError(
            f"DECISION_V3_KILL_SOURCE_COLUMNS_MISSING:{sorted(missing)}"
        )
    if int(parquet.metadata.num_rows) != EXPECTED_SCORE_ROWS:
        raise DecisionV3KillSourceError(
            "DECISION_V3_KILL_SOURCE_ROW_COUNT_CHANGED"
        )

    # Deliberately project only consensus-ranking inputs. H5/H10 columns,
    # returns, labels and any extra parquet columns remain unread.
    frame = pd.read_parquet(
        score_path,
        columns=list(ALLOWED_KILL_DIAGNOSIS_SCORE_COLUMNS),
    )
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
        raise DecisionV3KillSourceError(
            "DECISION_V3_KILL_SOURCE_NONFINITE_ALPHA_CONSENSUS"
        )
    if frame.duplicated(["date", "ticker"]).any():
        raise DecisionV3KillSourceError(
            "DECISION_V3_KILL_SOURCE_DUPLICATE_DATE_TICKER"
        )
    if frame["date"].nunique() != EXPECTED_SCORE_SESSIONS:
        raise DecisionV3KillSourceError(
            "DECISION_V3_KILL_SOURCE_SESSION_COUNT_CHANGED"
        )
    if int(frame.groupby("date")["fold"].nunique().max()) != 1:
        raise DecisionV3KillSourceError(
            "DECISION_V3_KILL_SOURCE_MULTIPLE_FOLDS_PER_SESSION"
        )
    if int(frame.groupby("date")["mode"].nunique().max()) != 1:
        raise DecisionV3KillSourceError(
            "DECISION_V3_KILL_SOURCE_MULTIPLE_MODES_PER_SESSION"
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
        raise DecisionV3KillSourceError(
            "DECISION_V3_KILL_SOURCE_NAIVE_COMPARATOR_CHANGED:"
            f"{naive_replacements}!={EXPECTED_NAIVE_TOP10_REPLACEMENTS}"
        )

    return PinnedReplaySource(
        frame=ranked_frame,
        manifest_path=manifest_path,
        score_path=score_path,
    )
