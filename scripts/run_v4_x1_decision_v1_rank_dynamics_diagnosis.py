from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.v4_x1_decision_v1 import plan_decision_v1  # noqa: E402
from idx_trade.v4_x1_decision_v1_contract import (  # noqa: E402
    EXPECTED_ALPHA_MODEL_FINGERPRINT,
    EXPECTED_ALPHA_MODEL_ID,
    REQUIRED_SCORE_COLUMNS,
    ShadowPortfolioState,
    VerifiedScoreSession,
    _VERIFIED_TOKEN,
)

EXPECTED_MANIFEST_SHA256 = "6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205"
EXPECTED_SCORE_SHA256 = "48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b"
DEFAULT_ROOT = Path(r"D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2")
SCORE_FILENAME = "clean_challenger_validation_scores.parquet"


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"MISSING:{path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _q(values) -> dict[str, float | None]:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if not len(arr):
        return {k: None for k in ("mean", "p25", "median", "p75", "p90", "p95", "max")}
    return {
        "mean": float(np.mean(arr)),
        "p25": float(np.quantile(arr, 0.25)),
        "median": float(np.median(arr)),
        "p75": float(np.quantile(arr, 0.75)),
        "p90": float(np.quantile(arr, 0.90)),
        "p95": float(np.quantile(arr, 0.95)),
        "max": float(np.max(arr)),
    }


def _corr(x, y) -> float | None:
    a = np.asarray(x, dtype=float)
    b = np.asarray(y, dtype=float)
    mask = np.isfinite(a) & np.isfinite(b)
    if mask.sum() < 3 or np.ptp(a[mask]) == 0 or np.ptp(b[mask]) == 0:
        return None
    return float(np.corrcoef(a[mask], b[mask])[0, 1])


def _safe_rate(num: int, den: int) -> float | None:
    return None if den == 0 else float(num / den)


def _json_safe(value: Any):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return value


def _load(root: Path) -> tuple[pd.DataFrame, Path, Path]:
    manifest_path = root / "MANIFEST.json"
    score_path = root / SCORE_FILENAME
    if _sha256(manifest_path) != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("SOURCE_MANIFEST_SHA_MISMATCH")
    if _sha256(score_path) != EXPECTED_SCORE_SHA256:
        raise RuntimeError("SOURCE_SCORE_SHA_MISMATCH")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("measurement_only") is not True:
        raise RuntimeError("SOURCE_MEASUREMENT_ONLY_CHANGED")
    for key in ("provider_calls", "network_calls", "protected_forward_accessed", "fresh_forward_accessed"):
        if manifest.get(key) is not False:
            raise RuntimeError(f"SOURCE_GUARD_CHANGED:{key}")

    frame = pd.read_parquet(score_path)
    required = {
        "ticker", "date", "fold", "mode", "raw_h5", "raw_h10",
        "alpha_h5", "alpha_h10", "alpha_consensus",
    }
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"SCORE_COLUMNS_MISSING:{sorted(missing)}")
    frame = frame.loc[:, sorted(required)].copy()
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if frame["date"].isna().any() or frame["ticker"].eq("").any():
        raise RuntimeError("INVALID_IDENTITY")
    if frame.duplicated(["ticker", "date"]).any():
        raise RuntimeError("DUPLICATE_TICKER_DATE")
    if frame["date"].nunique() != 600:
        raise RuntimeError(f"DATE_COUNT_CHANGED:{frame['date'].nunique()}")
    if not frame["mode"].astype(str).eq("CHALLENGER").all():
        raise RuntimeError("MODE_CHANGED")
    for col in ("raw_h5", "raw_h10", "alpha_h5", "alpha_h10", "alpha_consensus"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce").astype(float)
        if not np.isfinite(frame[col]).all():
            raise RuntimeError(f"NONFINITE:{col}")
    expected = 0.5 * frame["alpha_h5"] + 0.5 * frame["alpha_h10"]
    if not np.allclose(frame["alpha_consensus"], expected, atol=1e-12, rtol=0.0):
        raise RuntimeError("CONSENSUS_CHANGED")

    pieces = []
    for _, block in frame.groupby("date", sort=True):
        block = block.sort_values(["alpha_consensus", "ticker"], ascending=[False, True], kind="mergesort").copy()
        block["rank_consensus"] = np.arange(1, len(block) + 1, dtype=int)
        pieces.append(block)
    return pd.concat(pieces, ignore_index=True), manifest_path, score_path


def _verified(block: pd.DataFrame, manifest_path: Path, score_path: Path) -> VerifiedScoreSession:
    day = pd.Timestamp(block["date"].iloc[0]).date().isoformat()
    cols = list(REQUIRED_SCORE_COLUMNS)
    scores = block.loc[:, cols].sort_values("rank_consensus", kind="mergesort").reset_index(drop=True)
    return VerifiedScoreSession(
        session_date=day,
        model_id=EXPECTED_ALPHA_MODEL_ID,
        model_fingerprint=EXPECTED_ALPHA_MODEL_FINGERPRINT,
        artifact_path=score_path,
        artifact_sha256=EXPECTED_SCORE_SHA256,
        manifest_path=manifest_path,
        manifest_sha256=EXPECTED_MANIFEST_SHA256,
        scores=scores,
        alpha_tie_rows=int(scores["alpha_consensus"].duplicated(keep=False).sum()),
        _verification_token=_VERIFIED_TOKEN,
    )


def _rank_bucket(rank: int) -> str:
    if rank <= 3:
        return "R1_3"
    if rank <= 6:
        return "R4_6"
    if rank <= 10:
        return "R7_10"
    if rank <= 20:
        return "R11_20"
    return "R21_PLUS"


def _future_first_rank_le(
    lookup: dict[pd.Timestamp, dict[str, int]], dates: list[pd.Timestamp], start_idx: int,
    ticker: str, threshold: int, max_horizon: int,
) -> int | None:
    for h in range(1, max_horizon + 1):
        j = start_idx + h
        if j >= len(dates):
            break
        rank = lookup[dates[j]].get(ticker)
        if rank is not None and rank <= threshold:
            return h
    return None


def diagnose(frame: pd.DataFrame, manifest_path: Path, score_path: Path):
    dates = sorted(frame["date"].drop_duplicates().tolist())
    blocks = {pd.Timestamp(d): b.copy() for d, b in frame.groupby("date", sort=True)}
    rank_lookup = {
        d: dict(zip(blocks[d]["ticker"].astype(str), blocks[d]["rank_consensus"].astype(int), strict=True))
        for d in dates
    }

    transition_rows: list[dict[str, Any]] = []
    top10_rows: list[dict[str, Any]] = []

    for i in range(len(dates) - 1):
        d0, d1 = pd.Timestamp(dates[i]), pd.Timestamp(dates[i + 1])
        a = blocks[d0]
        b = blocks[d1]
        fold0 = int(a["fold"].iloc[0])
        fold1 = int(b["fold"].iloc[0])
        boundary = fold0 != fold1
        merged = a.merge(b, on="ticker", how="inner", suffixes=("_0", "_1"), validate="one_to_one")
        top10_0 = set(a.loc[a["rank_consensus"].le(10), "ticker"])
        top10_1 = set(b.loc[b["rank_consensus"].le(10), "ticker"])
        top20_0 = set(a.loc[a["rank_consensus"].le(20), "ticker"])
        top20_1 = set(b.loc[b["rank_consensus"].le(20), "ticker"])

        merged["abs_rank_delta"] = (merged["rank_consensus_1"] - merged["rank_consensus_0"]).abs()
        merged["abs_alpha_delta"] = (merged["alpha_consensus_1"] - merged["alpha_consensus_0"]).abs()
        top_prev = merged[merged["rank_consensus_0"].le(10)].copy()

        ordered0 = a.sort_values("rank_consensus")
        alpha10 = float(ordered0.loc[ordered0["rank_consensus"].eq(10), "alpha_consensus"].iloc[0])
        alpha11 = float(ordered0.loc[ordered0["rank_consensus"].eq(11), "alpha_consensus"].iloc[0])
        alpha20 = float(ordered0.loc[ordered0["rank_consensus"].eq(20), "alpha_consensus"].iloc[0])
        alpha21 = float(ordered0.loc[ordered0["rank_consensus"].eq(21), "alpha_consensus"].iloc[0])

        transition_rows.append({
            "date_0": d0.date().isoformat(), "date_1": d1.date().isoformat(),
            "fold_0": fold0, "fold_1": fold1, "fold_boundary": boundary,
            "universe_0": len(a), "universe_1": len(b), "common": len(merged),
            "prev_universe_missing_next": len(a) - len(merged),
            "rank_spearman_common": _corr(merged["rank_consensus_0"], merged["rank_consensus_1"]),
            "alpha_consensus_corr_common": _corr(merged["alpha_consensus_0"], merged["alpha_consensus_1"]),
            "raw_h5_corr_common": _corr(merged["raw_h5_0"], merged["raw_h5_1"]),
            "raw_h10_corr_common": _corr(merged["raw_h10_0"], merged["raw_h10_1"]),
            "top10_overlap": len(top10_0 & top10_1),
            "top20_overlap": len(top20_0 & top20_1),
            "top10_jaccard": len(top10_0 & top10_1) / len(top10_0 | top10_1),
            "top20_jaccard": len(top20_0 & top20_1) / len(top20_0 | top20_1),
            "top10_prev_common": len(top_prev),
            "top10_to_top10": int(top_prev["rank_consensus_1"].le(10).sum()),
            "top10_to_11_20": int(top_prev["rank_consensus_1"].between(11, 20).sum()),
            "top10_to_gt20": int(top_prev["rank_consensus_1"].gt(20).sum()),
            "top10_abs_rank_delta_median": float(top_prev["abs_rank_delta"].median()),
            "top10_abs_rank_delta_p90": float(top_prev["abs_rank_delta"].quantile(0.90)),
            "common_abs_rank_delta_median": float(merged["abs_rank_delta"].median()),
            "common_abs_alpha_delta_median": float(merged["abs_alpha_delta"].median()),
            "abs_rank_vs_abs_alpha_corr": _corr(merged["abs_rank_delta"], merged["abs_alpha_delta"]),
            "alpha_gap_rank10_11": alpha10 - alpha11,
            "alpha_gap_rank20_21": alpha20 - alpha21,
        })

        curr_rank = dict(zip(b["ticker"], b["rank_consensus"], strict=True))
        curr_alpha = dict(zip(b["ticker"], b["alpha_consensus"], strict=True))
        for row in a.loc[a["rank_consensus"].le(10)].itertuples(index=False):
            ticker = str(row.ticker)
            r0 = int(row.rank_consensus)
            r1 = curr_rank.get(ticker)
            top10_rows.append({
                "date_0": d0.date().isoformat(), "date_1": d1.date().isoformat(),
                "fold_boundary": boundary, "ticker": ticker,
                "rank_0": r0, "rank_bucket_0": _rank_bucket(r0),
                "rank_1": None if r1 is None else int(r1),
                "state_1": "ABSENT" if r1 is None else ("TOP10" if r1 <= 10 else ("R11_20" if r1 <= 20 else "GT20")),
                "rank_delta": None if r1 is None else int(r1 - r0),
                "alpha_0": float(row.alpha_consensus),
                "alpha_1": None if ticker not in curr_alpha else float(curr_alpha[ticker]),
                "alpha_delta": None if ticker not in curr_alpha else float(curr_alpha[ticker] - row.alpha_consensus),
            })

    # Replay actual Decision V1 to isolate hard-exit mechanics and whipsaw.
    state = ShadowPortfolioState.empty()
    active_age: dict[str, int] = {}
    hard_exits: list[dict[str, Any]] = []
    buy_dates: defaultdict[str, list[int]] = defaultdict(list)

    for i, d in enumerate(dates):
        block = blocks[pd.Timestamp(d)]
        plan = plan_decision_v1(_verified(block, manifest_path, score_path), state)
        prev_ranks = rank_lookup[dates[i - 1]] if i > 0 else {}
        current_ranks = rank_lookup[pd.Timestamp(d)]

        for intent in plan.buy_intents:
            buy_dates[intent.ticker].append(i)
        for intent in plan.sell_intents:
            if intent.reason == "HARD_EXIT_RANK_GT20":
                ticker = intent.ticker
                prev_rank = prev_ranks.get(ticker)
                current_rank = current_ranks.get(ticker)
                first_le20 = _future_first_rank_le(rank_lookup, dates, i, ticker, 20, 10)
                first_top10 = _future_first_rank_le(rank_lookup, dates, i, ticker, 10, 10)
                hard_exits.append({
                    "event_index": i,
                    "date": pd.Timestamp(d).date().isoformat(),
                    "fold": int(block["fold"].iloc[0]),
                    "ticker": ticker,
                    "holding_age_before_exit": int(active_age.get(ticker, 0)),
                    "previous_rank": None if prev_rank is None else int(prev_rank),
                    "current_rank": None if current_rank is None else int(current_rank),
                    "one_day_rank_jump": None if prev_rank is None or current_rank is None else int(current_rank - prev_rank),
                    "rank_next_session": None if i + 1 >= len(dates) else rank_lookup[dates[i + 1]].get(ticker),
                    "first_return_le20_within10": first_le20,
                    "first_return_top10_within10": first_top10,
                })

        prev_target = set(state.positions)
        target = set(plan.target_positions)
        for ticker in prev_target & target:
            active_age[ticker] = active_age.get(ticker, 1) + 1
        for ticker in target - prev_target:
            active_age[ticker] = 1
        for ticker in prev_target - target:
            active_age.pop(ticker, None)
        state = ShadowPortfolioState(pd.Timestamp(d).date().isoformat(), plan.target_positions)

    # Add actual rebuy delay after each hard exit.
    for event in hard_exits:
        ticker = event["ticker"]
        i = int(event["event_index"])
        future_buys = [j for j in buy_dates.get(ticker, []) if j > i]
        event["first_actual_rebuy_delay"] = None if not future_buys else int(future_buys[0] - i)

    return pd.DataFrame(transition_rows), pd.DataFrame(top10_rows), pd.DataFrame(hard_exits)


def _transition_state_summary(top10: pd.DataFrame) -> dict[str, Any]:
    total = len(top10)
    counts = top10["state_1"].value_counts().to_dict()
    by_bucket = {}
    for bucket, block in top10.groupby("rank_bucket_0", sort=True):
        c = block["state_1"].value_counts().to_dict()
        by_bucket[str(bucket)] = {
            "n": len(block),
            "top10": int(c.get("TOP10", 0)),
            "r11_20": int(c.get("R11_20", 0)),
            "gt20": int(c.get("GT20", 0)),
            "absent": int(c.get("ABSENT", 0)),
            "gt20_rate": _safe_rate(int(c.get("GT20", 0)), len(block)),
        }
    return {
        "n": total,
        "top10": int(counts.get("TOP10", 0)),
        "r11_20": int(counts.get("R11_20", 0)),
        "gt20": int(counts.get("GT20", 0)),
        "absent": int(counts.get("ABSENT", 0)),
        "top10_survival_rate": _safe_rate(int(counts.get("TOP10", 0)), total),
        "top20_survival_rate": _safe_rate(int(counts.get("TOP10", 0)) + int(counts.get("R11_20", 0)), total),
        "gt20_rate": _safe_rate(int(counts.get("GT20", 0)), total),
        "absent_rate": _safe_rate(int(counts.get("ABSENT", 0)), total),
        "by_start_rank_bucket": by_bucket,
    }


def _hard_exit_summary(events: pd.DataFrame) -> dict[str, Any]:
    if events.empty:
        return {"n": 0}
    def rate_le(col: str, h: int) -> float:
        vals = pd.to_numeric(events[col], errors="coerce")
        return float(vals.le(h).fillna(False).mean())
    next_rank = pd.to_numeric(events["rank_next_session"], errors="coerce")
    rebuy = pd.to_numeric(events["first_actual_rebuy_delay"], errors="coerce")
    return {
        "n": int(len(events)),
        "previous_rank": _q(pd.to_numeric(events["previous_rank"], errors="coerce")),
        "current_rank": _q(pd.to_numeric(events["current_rank"], errors="coerce")),
        "one_day_rank_jump": _q(pd.to_numeric(events["one_day_rank_jump"], errors="coerce")),
        "holding_age_before_exit": _q(pd.to_numeric(events["holding_age_before_exit"], errors="coerce")),
        "next_session_back_le20_rate": float(next_rank.le(20).fillna(False).mean()),
        "next_session_back_top10_rate": float(next_rank.le(10).fillna(False).mean()),
        "rank_return_top10_within_2_rate": rate_le("first_return_top10_within10", 2),
        "rank_return_top10_within_3_rate": rate_le("first_return_top10_within10", 3),
        "rank_return_top10_within_5_rate": rate_le("first_return_top10_within10", 5),
        "rank_return_le20_within_2_rate": rate_le("first_return_le20_within10", 2),
        "rank_return_le20_within_3_rate": rate_le("first_return_le20_within10", 3),
        "actual_rebuy_within_2_rate": float(rebuy.le(2).fillna(False).mean()),
        "actual_rebuy_within_3_rate": float(rebuy.le(3).fillna(False).mean()),
        "actual_rebuy_within_5_rate": float(rebuy.le(5).fillna(False).mean()),
    }


def summarize(trans: pd.DataFrame, top10: pd.DataFrame, hard: pd.DataFrame) -> dict[str, Any]:
    within = trans.loc[~trans["fold_boundary"].astype(bool)]
    boundary = trans.loc[trans["fold_boundary"].astype(bool)]
    common_prev_missing = int(trans["prev_universe_missing_next"].sum())
    common_prev_total = int(trans["universe_0"].sum())

    return {
        "schema_version": "v4_x1_decision_v1_rank_dynamics_diagnosis_v1",
        "status": "COMPLETE_OUTCOME_BLIND_DIAGNOSIS",
        "sessions": 600,
        "transitions": int(len(trans)),
        "kill_test_diagnosis": {
            "old_tests_scope": "STATIC_SINGLE_SESSION_CONTRACT_AND_INVARIANT_CORRECTNESS",
            "missing_old_test_scope": "REAL_LONGITUDINAL_SCORE_RANK_TRANSITION_DYNAMICS",
        },
        "consecutive_session_stability": {
            "rank_spearman_common": _q(trans["rank_spearman_common"]),
            "alpha_consensus_corr_common": _q(trans["alpha_consensus_corr_common"]),
            "raw_h5_corr_common": _q(trans["raw_h5_corr_common"]),
            "raw_h10_corr_common": _q(trans["raw_h10_corr_common"]),
            "top10_overlap": _q(trans["top10_overlap"]),
            "top20_overlap": _q(trans["top20_overlap"]),
            "top10_abs_rank_delta": {
                "median_across_days_of_median": float(trans["top10_abs_rank_delta_median"].median()),
                "median_across_days_of_p90": float(trans["top10_abs_rank_delta_p90"].median()),
            },
        },
        "top10_next_session_transition": _transition_state_summary(top10),
        "hard_exit_whipsaw": _hard_exit_summary(hard),
        "relative_rank_geometry": {
            "alpha_gap_rank10_11": _q(trans["alpha_gap_rank10_11"]),
            "alpha_gap_rank20_21": _q(trans["alpha_gap_rank20_21"]),
            "common_abs_alpha_delta": _q(trans["common_abs_alpha_delta_median"]),
            "abs_rank_vs_abs_alpha_corr": _q(trans["abs_rank_vs_abs_alpha_corr"]),
        },
        "universe_churn": {
            "prev_rows_missing_next_total": common_prev_missing,
            "prev_rows_total_across_transitions": common_prev_total,
            "missing_next_rate": _safe_rate(common_prev_missing, common_prev_total),
        },
        "fold_boundary_forensics": {
            "boundary_transitions": int(len(boundary)),
            "within_fold_transitions": int(len(within)),
            "boundary_top10_overlap": _q(boundary["top10_overlap"]),
            "within_fold_top10_overlap": _q(within["top10_overlap"]),
            "boundary_rank_spearman": _q(boundary["rank_spearman_common"]),
            "within_fold_rank_spearman": _q(within["rank_spearman_common"]),
            "boundary_top10_to_gt20_rate": _safe_rate(int(boundary["top10_to_gt20"].sum()), int(boundary["top10_prev_common"].sum())),
            "within_fold_top10_to_gt20_rate": _safe_rate(int(within["top10_to_gt20"].sum()), int(within["top10_prev_common"].sum())),
        },
        "guards": {
            "realized_returns_loaded": False,
            "target_ledger_loaded": False,
            "historical_pnl_computed": False,
            "decision_v2_parameters_tested": False,
            "model_fit_or_retune": False,
            "provider_or_network_calls": False,
            "protected_or_fresh_forward_access": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--historical-root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    root = args.historical_root.expanduser().resolve()
    out = args.output_dir.expanduser().resolve()
    if out.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE:{out}")

    frame, manifest_path, score_path = _load(root)
    trans, top10, hard = diagnose(frame, manifest_path, score_path)
    summary = summarize(trans, top10, hard)
    summary["source"] = {
        "historical_root": str(root),
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "score_sha256": EXPECTED_SCORE_SHA256,
        "score_rows": int(len(frame)),
        "score_dates": int(frame["date"].nunique()),
    }

    out.mkdir(parents=True, exist_ok=False)
    paths = {
        "transition_metrics": out / "consecutive_transition_metrics.csv",
        "top10_transitions": out / "top10_next_session_transitions.csv",
        "hard_exits": out / "decision_v1_hard_exit_events.csv",
        "summary": out / "summary.json",
    }
    trans.to_csv(paths["transition_metrics"], index=False, lineterminator="\n")
    top10.to_csv(paths["top10_transitions"], index=False, lineterminator="\n")
    hard.drop(columns=["event_index"], errors="ignore").to_csv(paths["hard_exits"], index=False, lineterminator="\n")
    paths["summary"].write_text(json.dumps(_json_safe(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_x1_decision_v1_rank_dynamics_diagnosis_manifest_v1",
        "status": summary["status"],
        "source_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "source_score_sha256": EXPECTED_SCORE_SHA256,
        "output_sha256": {k: _sha256(v) for k, v in paths.items()},
        "guards": summary["guards"],
    }
    manifest_path_out = out / "MANIFEST.json"
    manifest_path_out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True))
    print(f"manifest={manifest_path_out}")
    print(f"manifest_sha256={_sha256(manifest_path_out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
