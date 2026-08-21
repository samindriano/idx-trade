from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

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
    TARGET_POSITIONS,
    ShadowPortfolioState,
    VerifiedScoreSession,
    _VERIFIED_TOKEN,
)

EXPECTED_HISTORICAL_MANIFEST_SHA256 = "6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205"
EXPECTED_HISTORICAL_SCHEMA = "ranking_v4_x1_clean_historical_oos_replay_manifest_v1"
EXPECTED_HISTORICAL_STATUS = "V4_X1_CLEAN_HISTORICAL_OOS_REPLAY_COMPLETE_REVIEW_REQUIRED"
EXPECTED_GENERATION_ID = "V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1"
DEFAULT_HISTORICAL_ROOT = Path(r"D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2")
SCORE_FILENAME = "clean_challenger_validation_scores.parquet"


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return value


def quantiles(values: list[float]) -> dict[str, float | None]:
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    if not len(a):
        return {"mean": None, "p25": None, "median": None, "p75": None, "p90": None, "p95": None, "max": None}
    return {
        "mean": float(np.mean(a)),
        "p25": float(np.quantile(a, 0.25)),
        "median": float(np.median(a)),
        "p75": float(np.quantile(a, 0.75)),
        "p90": float(np.quantile(a, 0.90)),
        "p95": float(np.quantile(a, 0.95)),
        "max": float(np.max(a)),
    }


def verify_historical_root(root: Path) -> tuple[Path, Path, str, str, dict]:
    manifest_path = root / "MANIFEST.json"
    score_path = root / SCORE_FILENAME
    manifest_sha = sha256_file(manifest_path)
    if manifest_sha != EXPECTED_HISTORICAL_MANIFEST_SHA256:
        raise RuntimeError(
            f"HISTORICAL_MANIFEST_SHA_MISMATCH:{manifest_sha}!={EXPECTED_HISTORICAL_MANIFEST_SHA256}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != EXPECTED_HISTORICAL_SCHEMA:
        raise RuntimeError("HISTORICAL_MANIFEST_SCHEMA_CHANGED")
    if manifest.get("status") != EXPECTED_HISTORICAL_STATUS:
        raise RuntimeError(f"HISTORICAL_MANIFEST_STATUS_CHANGED:{manifest.get('status')}")
    if manifest.get("generation_id") != EXPECTED_GENERATION_ID:
        raise RuntimeError("HISTORICAL_GENERATION_CHANGED")
    if manifest.get("measurement_only") is not True:
        raise RuntimeError("HISTORICAL_MEASUREMENT_ONLY_GUARD_CHANGED")
    for key in (
        "provider_calls",
        "network_calls",
        "protected_forward_accessed",
        "fresh_forward_accessed",
        "forward_counter_mutated",
        "deployed_model_mutated",
    ):
        if manifest.get(key) is not False:
            raise RuntimeError(f"HISTORICAL_GUARD_CHANGED:{key}")
    score_sha = sha256_file(score_path)
    expected_score_sha = str((manifest.get("output_hashes") or {}).get("scores_challenger") or "")
    if score_sha != expected_score_sha:
        raise RuntimeError(f"HISTORICAL_SCORE_SHA_MISMATCH:{score_sha}!={expected_score_sha}")
    return manifest_path, score_path, manifest_sha, score_sha, manifest


def prepare_scores(path: Path) -> pd.DataFrame:
    scores = pd.read_parquet(path)
    needed = {"ticker", "date", "alpha_h5", "alpha_h10", "alpha_consensus"}
    missing = needed - set(scores.columns)
    if missing:
        raise RuntimeError(f"HISTORICAL_SCORE_COLUMNS_MISSING:{sorted(missing)}")
    out = scores.loc[:, list(needed)].copy()
    out["ticker"] = (
        out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    )
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if out["ticker"].eq("").any() or out["date"].isna().any():
        raise RuntimeError("HISTORICAL_SCORE_IDENTITY_INVALID")
    if out.duplicated(["ticker", "date"]).any():
        raise RuntimeError("HISTORICAL_SCORE_DUPLICATE_TICKER_DATE")
    for col in ("alpha_h5", "alpha_h10", "alpha_consensus"):
        out[col] = pd.to_numeric(out[col], errors="coerce").astype(float)
        if not np.isfinite(out[col]).all():
            raise RuntimeError(f"HISTORICAL_SCORE_NONFINITE:{col}")
        if ((out[col] < 0.0) | (out[col] > 1.0)).any():
            raise RuntimeError(f"HISTORICAL_SCORE_OUT_OF_RANGE:{col}")
    expected = 0.5 * out["alpha_h5"] + 0.5 * out["alpha_h10"]
    if not np.allclose(out["alpha_consensus"], expected, rtol=0.0, atol=1e-12):
        raise RuntimeError("HISTORICAL_SCORE_CONSENSUS_MISMATCH")

    pieces: list[pd.DataFrame] = []
    for day, block in out.groupby("date", sort=True):
        block = block.sort_values(["alpha_consensus", "ticker"], ascending=[False, True], kind="mergesort").copy()
        if len(block) < TARGET_POSITIONS:
            raise RuntimeError(f"HISTORICAL_SCORE_DATE_TOO_SMALL:{day.date()}:{len(block)}")
        block["rank_consensus"] = np.arange(1, len(block) + 1, dtype=int)
        pieces.append(block)
    result = pd.concat(pieces, ignore_index=True)
    dates = result["date"].drop_duplicates().sort_values().tolist()
    if len(dates) != 600:
        raise RuntimeError(f"HISTORICAL_VALIDATION_DATE_COUNT_CHANGED:{len(dates)}!=600")
    return result


def make_verified_session(
    block: pd.DataFrame,
    score_path: Path,
    score_sha: str,
    manifest_path: Path,
    manifest_sha: str,
) -> VerifiedScoreSession:
    day = pd.Timestamp(block["date"].iloc[0]).date().isoformat()
    frame = block.loc[:, list(REQUIRED_SCORE_COLUMNS)].copy()
    frame = frame.sort_values("rank_consensus", kind="mergesort").reset_index(drop=True)
    tie_rows = int(frame["alpha_consensus"].duplicated(keep=False).sum())
    return VerifiedScoreSession(
        session_date=day,
        model_id=EXPECTED_ALPHA_MODEL_ID,
        model_fingerprint=EXPECTED_ALPHA_MODEL_FINGERPRINT,
        artifact_path=score_path,
        artifact_sha256=score_sha,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha,
        scores=frame,
        alpha_tie_rows=tie_rows,
        _verification_token=_VERIFIED_TOKEN,
    )


def longest_true_streak(values: list[bool]) -> int:
    best = cur = 0
    for value in values:
        if value:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def run_trajectory(scores: pd.DataFrame, manifest_path: Path, score_path: Path, manifest_sha: str, score_sha: str):
    state = ShadowPortfolioState.empty()
    previous_target: set[str] = set()
    previous_top10: set[str] = set()
    active_spells: dict[str, tuple[int, str]] = {}
    spell_rows: list[dict] = []
    daily_rows: list[dict] = []
    sell_reasons: Counter[str] = Counter()
    buy_reasons: Counter[str] = Counter()

    grouped = list(scores.groupby("date", sort=True))
    for index, (day, block) in enumerate(grouped, start=1):
        verified = make_verified_session(block, score_path, score_sha, manifest_path, manifest_sha)
        plan = plan_decision_v1(verified, state)
        target = set(plan.target_positions)
        ranks = dict(zip(block["ticker"], block["rank_consensus"], strict=True))
        top10 = set(block.loc[block["rank_consensus"].le(10), "ticker"].astype(str))

        if len(target) != TARGET_POSITIONS:
            raise RuntimeError(f"TARGET_SIZE_CHANGED:{day.date()}:{len(target)}")
        if any(int(ranks[t]) > 20 for t in target):
            raise RuntimeError(f"TARGET_HARD_EXIT_VIOLATION:{day.date()}")

        entered = target - previous_target
        exited = previous_target - target
        if index > 1:
            if entered != {x.ticker for x in plan.buy_intents}:
                raise RuntimeError(f"BUY_INTENT_TARGET_DELTA_MISMATCH:{day.date()}")
            if exited != {x.ticker for x in plan.sell_intents}:
                raise RuntimeError(f"SELL_INTENT_TARGET_DELTA_MISMATCH:{day.date()}")
        else:
            if len(plan.buy_intents) != TARGET_POSITIONS or plan.sell_intents:
                raise RuntimeError("BOOTSTRAP_INTENT_INVARIANT_CHANGED")

        for intent in plan.sell_intents:
            sell_reasons[intent.reason] += 1
        for intent in plan.buy_intents:
            buy_reasons[intent.reason] += 1

        for ticker in exited:
            start_index, start_date = active_spells.pop(ticker)
            spell_rows.append({
                "ticker": ticker,
                "entry_session_index": start_index,
                "entry_date": start_date,
                "exit_session_index": index,
                "exit_date": pd.Timestamp(day).date().isoformat(),
                "held_sessions": index - start_index,
                "right_censored": False,
            })
        for ticker in entered:
            active_spells[ticker] = (index, pd.Timestamp(day).date().isoformat())

        target_ranks = [int(ranks[t]) for t in target]
        overlap_top10 = len(target & top10)
        naive_buys = TARGET_POSITIONS if index == 1 else len(top10 - previous_top10)
        decision_buys = len(plan.buy_intents)
        decision_sells = len(plan.sell_intents)
        unchanged = index > 1 and decision_buys == 0 and decision_sells == 0

        daily_rows.append({
            "session_index": index,
            "date": pd.Timestamp(day).date().isoformat(),
            "universe_rows": int(len(block)),
            "decision_buys": decision_buys,
            "decision_sells": decision_sells,
            "decision_one_way_turnover_names": decision_buys,
            "decision_one_way_turnover_fraction": decision_buys / TARGET_POSITIONS,
            "naive_top10_buys": naive_buys,
            "naive_top10_one_way_turnover_fraction": naive_buys / TARGET_POSITIONS,
            "target_top10_overlap": overlap_top10,
            "target_buffer_11_20": TARGET_POSITIONS - overlap_top10,
            "target_mean_rank": float(np.mean(target_ranks)),
            "target_median_rank": float(np.median(target_ranks)),
            "target_worst_rank": int(max(target_ranks)),
            "target_best_rank": int(min(target_ranks)),
            "unchanged_from_prior": bool(unchanged),
            "alpha_tie_rows": int(verified.alpha_tie_rows),
            "fold_block": int((index - 1) // 100 + 1),
            "fold_boundary_start": bool(index in {1, 101, 201, 301, 401, 501}),
            "target_tickers": "|".join(plan.target_positions),
            "daily_top10_tickers": "|".join(block.nsmallest(10, "rank_consensus")["ticker"].astype(str).tolist()),
        })

        state = ShadowPortfolioState(
            as_of_session_date=pd.Timestamp(day).date().isoformat(),
            positions=plan.target_positions,
        )
        previous_target = target
        previous_top10 = top10

    last_index = len(grouped)
    last_date = pd.Timestamp(grouped[-1][0]).date().isoformat()
    for ticker, (start_index, start_date) in sorted(active_spells.items()):
        spell_rows.append({
            "ticker": ticker,
            "entry_session_index": start_index,
            "entry_date": start_date,
            "exit_session_index": None,
            "exit_date": None,
            "held_sessions": last_index - start_index + 1,
            "right_censored": True,
        })

    return pd.DataFrame(daily_rows), pd.DataFrame(spell_rows), sell_reasons, buy_reasons


def summarize(daily: pd.DataFrame, spells: pd.DataFrame, sell_reasons: Counter, buy_reasons: Counter) -> dict:
    post_bootstrap = daily.loc[daily["session_index"].gt(1)].copy()
    completed_spells = spells.loc[~spells["right_censored"].astype(bool)].copy()
    decision_total = int(post_bootstrap["decision_one_way_turnover_names"].sum())
    naive_total = int(post_bootstrap["naive_top10_buys"].sum())

    decision_counts = post_bootstrap["decision_one_way_turnover_names"].astype(int)
    naive_counts = post_bootstrap["naive_top10_buys"].astype(int)
    fold_summary = (
        post_bootstrap.groupby("fold_block", sort=True)
        .agg(
            sessions=("session_index", "size"),
            decision_buys=("decision_one_way_turnover_names", "sum"),
            naive_top10_buys=("naive_top10_buys", "sum"),
            mean_top10_overlap=("target_top10_overlap", "mean"),
            mean_target_rank=("target_mean_rank", "mean"),
            mean_worst_rank=("target_worst_rank", "mean"),
        )
        .reset_index()
        .to_dict(orient="records")
    )

    return {
        "schema_version": "v4_x1_decision_v1_structural_trajectory_audit_v1",
        "status": "COMPLETE_OUTCOME_BLIND_STRUCTURAL_ONLY",
        "sessions": int(len(daily)),
        "bootstrap_buys": int(daily.iloc[0]["decision_buys"]),
        "decision_rule": {
            "target_positions": 10,
            "entry_rank_max": 10,
            "hard_exit_rank_gt": 20,
            "replacement_rank_gap_min": 5,
        },
        "turnover": {
            "decision_total_replacements_ex_bootstrap": decision_total,
            "naive_daily_top10_total_replacements_ex_bootstrap": naive_total,
            "decision_vs_naive_ratio": None if naive_total == 0 else decision_total / naive_total,
            "decision_replacements_per_session": quantiles(decision_counts.tolist()),
            "naive_top10_replacements_per_session": quantiles(naive_counts.tolist()),
            "decision_zero_change_sessions": int(decision_counts.eq(0).sum()),
            "decision_zero_change_fraction": float(decision_counts.eq(0).mean()),
            "decision_sessions_3plus_replacements": int(decision_counts.ge(3).sum()),
            "decision_sessions_3plus_fraction": float(decision_counts.ge(3).mean()),
            "naive_sessions_3plus_replacements": int(naive_counts.ge(3).sum()),
            "longest_decision_no_change_streak": int(longest_true_streak(post_bootstrap["unchanged_from_prior"].tolist())),
        },
        "portfolio_rank_quality": {
            "top10_overlap": quantiles(daily["target_top10_overlap"].tolist()),
            "buffer_11_20_names": quantiles(daily["target_buffer_11_20"].tolist()),
            "target_mean_rank": quantiles(daily["target_mean_rank"].tolist()),
            "target_worst_rank": quantiles(daily["target_worst_rank"].tolist()),
            "hard_exit_rank_violations": int((daily["target_worst_rank"] > 20).sum()),
        },
        "holding_spells": {
            "all_spells": int(len(spells)),
            "completed_spells": int(len(completed_spells)),
            "right_censored_spells": int(spells["right_censored"].astype(bool).sum()),
            "all_held_sessions": quantiles(spells["held_sessions"].astype(float).tolist()),
            "completed_held_sessions": quantiles(completed_spells["held_sessions"].astype(float).tolist()),
        },
        "intent_reasons": {
            "sell": dict(sorted(sell_reasons.items())),
            "buy": dict(sorted(buy_reasons.items())),
        },
        "fold_blocks": fold_summary,
        "guards": {
            "target_or_return_loaded": False,
            "historical_return_loaded": False,
            "historical_pnl_computed": False,
            "protected_forward_accessed": False,
            "fresh_forward_accessed": False,
            "provider_calls": False,
            "network_calls": False,
            "model_fit": False,
            "model_retune": False,
            "decision_parameters_changed": False,
        },
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--historical-root", type=Path, default=DEFAULT_HISTORICAL_ROOT)
    p.add_argument("--output-dir", type=Path, required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = args.historical_root.expanduser().resolve()
    out = args.output_dir.expanduser().resolve()
    if out.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE:{out}")

    manifest_path, score_path, manifest_sha, score_sha, source_manifest = verify_historical_root(root)
    scores = prepare_scores(score_path)
    out.mkdir(parents=True, exist_ok=False)

    daily, spells, sell_reasons, buy_reasons = run_trajectory(
        scores, manifest_path, score_path, manifest_sha, score_sha
    )
    summary = summarize(daily, spells, sell_reasons, buy_reasons)
    summary["source"] = {
        "historical_root": str(root),
        "source_manifest_sha256": manifest_sha,
        "source_score_sha256": score_sha,
        "source_clean_historical_oos_ic": source_manifest.get("canonical_clean_historical_oos_ic"),
        "score_dates": int(scores["date"].nunique()),
        "score_rows": int(len(scores)),
    }

    daily_path = out / "decision_v1_trajectory_daily.csv"
    spells_path = out / "decision_v1_holding_spells.csv"
    summary_path = out / "summary.json"
    daily.to_csv(daily_path, index=False, lineterminator="\n")
    spells.to_csv(spells_path, index=False, lineterminator="\n")
    atomic_write_text(summary_path, json.dumps(json_safe(summary), indent=2, sort_keys=True) + "\n")

    output_hashes = {
        "daily": sha256_file(daily_path),
        "holding_spells": sha256_file(spells_path),
        "summary": sha256_file(summary_path),
    }
    result_manifest = {
        "schema_version": "v4_x1_decision_v1_structural_trajectory_manifest_v1",
        "status": summary["status"],
        "source_manifest_sha256": manifest_sha,
        "source_score_sha256": score_sha,
        "output_hashes": output_hashes,
        "guards": summary["guards"],
    }
    result_manifest_path = out / "MANIFEST.json"
    atomic_write_text(result_manifest_path, json.dumps(result_manifest, indent=2, sort_keys=True) + "\n")

    print(json.dumps(json_safe(summary), indent=2, sort_keys=True))
    print(f"manifest={result_manifest_path}")
    print(f"manifest_sha256={sha256_file(result_manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
