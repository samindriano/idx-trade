from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from .ranking_v3_structure_lite import V3_B_FEATURE_COLUMNS
from .research_baselines import (
    RANDOM_SEED,
    TREE_L2,
    TREE_LEARNING_RATE,
    TREE_MAX_ITER,
    TREE_MAX_LEAF_NODES,
)
from .research_features import assert_no_open_dependency
from .research_v2_models import pointwise_raw_score
from .research_v4_cross_sectional_context import V4_C_FEATURE_COLUMNS


V4_C_HYPOTHESIS_ID = "V4-C-CROSS-SECTIONAL-CONTEXT-V1"
V4_C_CONTROL = "V4-C-CROSS-SECTIONAL-CONTEXT-V1-CONTROL-018"
V4_C_CHALLENGER = "V4-C-CROSS-SECTIONAL-CONTEXT-V1-DISPERSION-019"
V4_C_FIRST_PASS_CANDIDATES = (V4_C_CONTROL, V4_C_CHALLENGER)

V4_C_CONTROL_FEATURE_COLUMNS = tuple(V3_B_FEATURE_COLUMNS)
V4_C_MODEL_FEATURE_COLUMNS = (*V3_B_FEATURE_COLUMNS, *V4_C_FEATURE_COLUMNS)

MAX_V4_C_HISTORICAL_SIGNAL_INDEX = 1224
SEALED_V4_C_SIGNAL_INDEX = 1225
V4_C_SPEC_GIT_BLOB = "43f222f31c7c0ea15e870d22b066aae95858c81f"


def candidate_feature_columns(candidate: str) -> tuple[str, ...]:
    if candidate == V4_C_CONTROL:
        return tuple(V4_C_CONTROL_FEATURE_COLUMNS)
    if candidate == V4_C_CHALLENGER:
        return tuple(V4_C_MODEL_FEATURE_COLUMNS)
    raise ValueError(f"unknown V4-C candidate: {candidate}")


def _numeric_preprocessor(columns: Sequence[str]) -> ColumnTransformer:
    assert_no_open_dependency(columns)
    numeric = Pipeline(
        [
            (
                "impute",
                SimpleImputer(
                    strategy="median",
                    add_indicator=True,
                    keep_empty_features=True,
                ),
            )
        ]
    )
    return ColumnTransformer(
        [("numeric", numeric, list(columns))],
        remainder="drop",
    )


def candidate_model(candidate: str) -> Pipeline:
    columns = candidate_feature_columns(candidate)
    return Pipeline(
        [
            ("preprocess", _numeric_preprocessor(columns)),
            (
                "model",
                HistGradientBoostingClassifier(
                    learning_rate=TREE_LEARNING_RATE,
                    max_iter=TREE_MAX_ITER,
                    max_leaf_nodes=TREE_MAX_LEAF_NODES,
                    l2_regularization=TREE_L2,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )


def candidate_raw_score(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    return pointwise_raw_score(model, frame)


def feature_order_sha256(columns: Sequence[str]) -> str:
    payload = json.dumps(
        list(columns), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalized_git_blob_sha1(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    payload = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def assert_spec_identity(spec_path: Path) -> str:
    actual = normalized_git_blob_sha1(spec_path)
    if actual != V4_C_SPEC_GIT_BLOB:
        raise RuntimeError(
            "V4-C context spec Git blob mismatch: "
            f"expected={V4_C_SPEC_GIT_BLOB} actual={actual}"
        )
    return actual


def assert_historical_boundary(frame: pd.DataFrame) -> None:
    if "signal_session_index" not in frame.columns:
        raise ValueError("V4-C frame missing signal_session_index")
    values = pd.to_numeric(frame["signal_session_index"], errors="raise").astype(int)
    if values.empty:
        raise ValueError("V4-C frame is empty")
    if int(values.max()) >= SEALED_V4_C_SIGNAL_INDEX:
        raise PermissionError(
            "V4-C historical-development implementation must not materialize session 1225+"
        )


def assert_first_pass_candidate_set(candidates: Sequence[str]) -> None:
    actual = tuple(candidates)
    if actual != V4_C_FIRST_PASS_CANDIDATES:
        raise RuntimeError(
            "V4-C first-pass candidate set/order is frozen as control+one dispersion challenger; "
            f"got {actual}"
        )
    if any("INTEGR" in candidate.upper() for candidate in actual):
        raise RuntimeError("V4-C has no within-family integration candidate")
