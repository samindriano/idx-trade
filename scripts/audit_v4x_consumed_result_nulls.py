"""Permutation/null attack for the already-consumed V4-3R validation scores.

This script is diagnostic only. It does not fit or score models, change any
scientific configuration, call providers, or access protected forward outcomes.
It verifies the immutable historical result manifest, reconstructs true
common-support Spearman IC from the stored validation scores/target ledger, and
compares the observed mean daily IC with within-date target permutations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


EXPECTED_MANIFEST_SHA256 = "05c00e5ab42adf34f9bffff4dd5237043d6d281b3e0abe1571f14a59eeb16fef"
HEAD_SPEC = {
    "h5": ("alpha_h5", "target_state_h5", "TARGET_H5_AVAILABLE", "target_rank_h5"),
    "h10": ("alpha_h10", "target_state_h10", "TARGET_H10_AVAILABLE", "target_rank_h10"),
    "consensus": ("alpha_consensus", "target_state_consensus", "TARGET_BOTH_AVAILABLE", "realized_consensus"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"NOT_JSON_OBJECT:{path}")
    return value


def normalized_rank(values: pd.Series) -> np.ndarray:
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise RuntimeError("NONFINITE_COMMON_SUPPORT_VALUE")
    n = len(numeric)
    if n < 2:
        raise RuntimeError("COMMON_SUPPORT_TOO_SMALL")
    ranks = pd.Series(numeric).rank(method="average", ascending=True).to_numpy(dtype=float)
    return (ranks - 1.0) / float(n - 1)


def standardize_for_corr(values: np.ndarray) -> np.ndarray:
    centered = values - float(values.mean())
    norm = float(np.sqrt(np.dot(centered, centered)))
    if not np.isfinite(norm) or norm <= 0.0:
        raise RuntimeError("ZERO_VARIANCE_COMMON_SUPPORT")
    return centered / norm


def build_blocks(root: Path, mode: str, head: str) -> tuple[list[tuple[np.ndarray, np.ndarray]], str, str]:
    alpha_col, state_col, available_state, target_col = HEAD_SPEC[head]
    score_path = root / f"v4_3r_{mode}_validation_scores.parquet"
    target_path = root / "v4_3r_target_ledger.parquet"
    scores = pd.read_parquet(score_path)
    targets = pd.read_parquet(target_path)
    for frame in (scores, targets):
        frame["ticker"] = frame["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
        frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.tz_localize(None).dt.normalize()
    if scores.duplicated(["ticker", "date"]).any():
        raise RuntimeError(f"DUPLICATE_SCORE_IDENTITY:{mode}")
    if targets.duplicated(["ticker", "date"]).any():
        raise RuntimeError("DUPLICATE_TARGET_IDENTITY")

    blocks: list[tuple[np.ndarray, np.ndarray]] = []
    for day, score_block in scores.groupby("date", sort=True):
        target_block = targets.loc[
            targets["date"].eq(day), ["ticker", "date", state_col, target_col]
        ]
        merged = score_block[["ticker", "date", alpha_col]].merge(
            target_block, on=["ticker", "date"], how="left", validate="one_to_one"
        )
        common = merged.loc[merged[state_col].eq(available_state), [alpha_col, target_col]].copy()
        if len(common) < 3:
            continue
        x = normalized_rank(common[alpha_col])
        y = normalized_rank(common[target_col])
        if np.ptp(x) == 0.0 or np.ptp(y) == 0.0:
            continue
        blocks.append((standardize_for_corr(x), standardize_for_corr(y)))
    if len(blocks) != 600:
        raise RuntimeError(f"EXPECTED_600_COMMON_SUPPORT_DATES:{mode}:{head}:{len(blocks)}")
    return blocks, sha256_file(score_path), sha256_file(target_path)


def observed_mean(blocks: list[tuple[np.ndarray, np.ndarray]]) -> float:
    return float(np.mean([float(np.dot(x, y)) for x, y in blocks]))


def permutation_distribution(
    blocks: list[tuple[np.ndarray, np.ndarray]], *, repetitions: int, seed: int
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    null = np.empty(repetitions, dtype=float)
    for rep in range(repetitions):
        total = 0.0
        for x, y in blocks:
            total += float(np.dot(x, rng.permutation(y)))
        null[rep] = total / float(len(blocks))
    return null


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-result-root", type=Path, required=True)
    parser.add_argument("--mode", choices=("control", "challenger"), default="challenger")
    parser.add_argument("--head", choices=("h5", "h10", "consensus", "all"), default="all")
    parser.add_argument("--repetitions", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260819)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repetitions < 100:
        raise RuntimeError("REPETITIONS_TOO_SMALL_FOR_AUDIT")
    root = args.historical_result_root.resolve()
    manifest_path = root / "MANIFEST.json"
    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError(f"MANIFEST_SHA_MISMATCH:{manifest_sha}!={EXPECTED_MANIFEST_SHA256}")
    manifest = read_json(manifest_path)
    if manifest.get("protected_forward_accessed") is not False or manifest.get("provider_calls") is not False:
        raise RuntimeError("HISTORICAL_GUARD_CHANGED")

    heads = tuple(HEAD_SPEC) if args.head == "all" else (args.head,)
    results: dict[str, Any] = {}
    for offset, head in enumerate(heads):
        blocks, score_sha, target_sha = build_blocks(root, args.mode, head)
        observed = observed_mean(blocks)
        null = permutation_distribution(
            blocks,
            repetitions=int(args.repetitions),
            seed=int(args.seed) + offset,
        )
        null_mean = float(null.mean())
        null_std = float(null.std(ddof=1)) if len(null) > 1 else float("nan")
        empirical_p_one_sided = float((1 + int((null >= observed).sum())) / (len(null) + 1))
        z_score = float((observed - null_mean) / null_std) if np.isfinite(null_std) and null_std > 0 else None
        results[head] = {
            "common_support_dates": len(blocks),
            "observed_mean_common_support_spearman_ic": observed,
            "null_repetitions": int(args.repetitions),
            "null_mean": null_mean,
            "null_std": null_std,
            "null_q001": float(np.quantile(null, 0.001)),
            "null_q01": float(np.quantile(null, 0.01)),
            "null_q05": float(np.quantile(null, 0.05)),
            "null_q95": float(np.quantile(null, 0.95)),
            "null_q99": float(np.quantile(null, 0.99)),
            "null_q999": float(np.quantile(null, 0.999)),
            "empirical_p_one_sided": empirical_p_one_sided,
            "z_score_vs_permutation_null": z_score,
            "score_sha256": score_sha,
            "target_ledger_sha256": target_sha,
        }

    output = {
        "schema_version": "v4x_consumed_score_permutation_null_v1",
        "status": "V4X_CONSUMED_SCORE_PERMUTATION_NULL_COMPLETE",
        "manifest_sha256": manifest_sha,
        "mode": args.mode,
        "seed": int(args.seed),
        "provider_calls": False,
        "model_fit": False,
        "model_scored": False,
        "protected_forward_accessed": False,
        "results": results,
        "interpretation_boundary": "This is a chance/metric-null diagnostic on already-consumed historical scores. It cannot remove researcher-selection bias and must not be used to retune V4-X1.",
    }
    print(json.dumps(output, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
