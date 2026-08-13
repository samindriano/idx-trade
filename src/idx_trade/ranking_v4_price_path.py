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
from .research_v4_price_path import V4_B1_FEATURE_COLUMNS, V4_B2_FEATURE_COLUMNS


V4_B_HYPOTHESIS_ID = "V4-B-PRICE-PATH-V1"
V4_B_CONTROL = "V4-B-PRICE-PATH-V1-CONTROL-015"
V4_B1_CANDIDATE = "V4-B-PRICE-PATH-V1-COHERENCE-016"
V4_B2_CANDIDATE = "V4-B-PRICE-PATH-V1-RANGE-ACCEPTANCE-017"
V4_B_FIRST_PASS_CANDIDATES = (
    V4_B_CONTROL,
    V4_B1_CANDIDATE,
    V4_B2_CANDIDATE,
)

V4_B_CONTROL_FEATURE_COLUMNS = tuple(V3_B_FEATURE_COLUMNS)
V4_B1_MODEL_FEATURE_COLUMNS = (*V3_B_FEATURE_COLUMNS, *V4_B1_FEATURE_COLUMNS)
V4_B2_MODEL_FEATURE_COLUMNS = (*V3_B_FEATURE_COLUMNS, *V4_B2_FEATURE_COLUMNS)

MAX_V4_B_HISTORICAL_SIGNAL_INDEX = 1224
SEALED_V4_B_SIGNAL_INDEX = 1225
V4_B_SPEC_GIT_BLOB = "a750c28831b95b1c88640c5879289da5f2c05446"


def candidate_feature_columns(candidate: str) -> tuple[str, ...]:
    if candidate == V4_B_CONTROL:
        return tuple(V4_B_CONTROL_FEATURE_COLUMNS)
    if candidate == V4_B1_CANDIDATE:
        return tuple(V4_B1_MODEL_FEATURE_COLUMNS)
    if candidate == V4_B2_CANDIDATE:
        return tuple(V4_B2_MODEL_FEATURE_COLUMNS)
    raise ValueError(f"unknown V4-B candidate: {candidate}")


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
    if actual != V4_B_SPEC_GIT_BLOB:
        raise RuntimeError(
            "V4-B price-path spec Git blob mismatch: "
            f"expected={V4_B_SPEC_GIT_BLOB} actual={actual}"
        )
    return actual


def assert_historical_boundary(frame: pd.DataFrame) -> None:
    if "signal_session_index" not in frame.columns:
        raise ValueError("V4-B frame missing signal_session_index")
    values = pd.to_numeric(frame["signal_session_index"], errors="raise").astype(int)
    if values.empty:
        raise ValueError("V4-B frame is empty")
    if int(values.max()) >= SEALED_V4_B_SIGNAL_INDEX:
        raise PermissionError(
            "V4-B historical-development implementation must not materialize session 1225+"
        )


def assert_first_pass_candidate_set(candidates: Sequence[str]) -> None:
    actual = tuple(candidates)
    if actual != V4_B_FIRST_PASS_CANDIDATES:
        raise RuntimeError(
            "V4-B first-pass candidate set/order is frozen as control+B1+B2; "
            f"got {actual}"
        )
    if any("INTEGR" in candidate.upper() for candidate in actual):
        raise RuntimeError("V4-B first pass must not include a B1+B2 integration candidate")
