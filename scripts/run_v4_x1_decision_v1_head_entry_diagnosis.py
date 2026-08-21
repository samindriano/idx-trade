from __future__ import annotations

import argparse
from collections import defaultdict
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
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _q(values) -> dict[str, float | None]:
    x = pd.to_numeric(pd.Series(list(values)), errors="coerce").dropna().to_numpy(dtype=float)
    if len(x) == 0:
        return {k: None for k in ("mean", "p25", "median", "p75", "p90", "p95", "max")}
    return {
        "mean": float(np.mean(x)),
        "p25": float(np.quantile(x, 0.25)),
        "median": float(np.median(x)),
        "p75": float(np.quantile(x, 0.75)),
        "p90": float(np.quantile(x, 0.90)),
        "p95": float(np.quantile(x, 0.95)),
        "max": float(np.max(x)),
    }


def _rate(mask: pd.Series) -> float | None:
    return None if len(mask) == 0 else float(mask.astype(bool).mean())


def _load(root: Path) -> tuple[pd.DataFrame, Path, Path]:
    manifest = root / "MANIFEST.json"
    scores = root / SCORE_FILENAME
    if not manifest.is_file() or not scores.is_file():
        raise RuntimeError("SOURCE_MISSING")
    if _sha256(manifest) != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("SOURCE_MANIFEST_SHA_MISMATCH")
    if _sha256(scores) != EXPECTED_SCORE_SHA256:
        raise RuntimeError("SOURCE_SCORE_SHA_MISMATCH")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    for key, expected in {
        "measurement_only": True,
        "provider_calls": False,
        "network_calls": False,
        "protected_forward_accessed": False,
        "fresh_forward_accessed": False,
    }.items():
        if payload.get(key) is not expected:
            raise RuntimeError(f"SOURCE_GUARD_CHANGED:{key}")

    frame = pd.read_parquet(scores)
    required = {
        "ticker", "date", "fold", "mode", "raw_h5", "raw_h10",
        "alpha_h5", "alpha_h10", "alpha_consensus",
    }
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"MISSING_SCORE_COLUMNS:{sorted(missing)}")
    frame = frame[list(required)].copy()
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.tz_localize(None).dt.normalize()
    for col in ("raw_h5", "raw_h10", "alpha_h5", "alpha_h10", "alpha_consensus"):
        frame[col] = pd.to_numeric(frame[col], errors="raise").astype(float)
        if not np.isfinite(frame[col]).all():
            raise RuntimeError(f"NONFINITE:{col}")
    if frame.duplicated(["ticker", "date"]).any():
        raise RuntimeError("DUPLICATE_IDENTITY")
    if frame["date"].nunique() != 600:
        raise RuntimeError("DATE_COUNT_CHANGED")

    parts = []
    for _, block in frame.groupby("date", sort=True):
        b = block.copy()
        for alpha, rank in (
            ("alpha_h5", "rank_h5"),
            ("alpha_h10", "rank_h10"),
            ("alpha_consensus", "rank_consensus"),
        ):
            order = b.sort_values([alpha, "ticker"], ascending=[False, True], kind="mergesort").index
            b.loc[order, rank] = np.arange(1, len(b) + 1, dtype=int)
            b[rank] = b[rank].astype(int)
        parts.append(b)
    out = pd.concat(parts, ignore_index=True)
    return out, manifest, scores


def _verified(block: pd.DataFrame, manifest: Path, scores: Path) -> VerifiedScoreSession:
    score_block = block.loc[:, list(REQUIRED_SCORE_COLUMNS)].sort_values("rank_consensus", kind="mergesort").reset_index(drop=True)
    return VerifiedScoreSession(
        session_date=pd.Timestamp(block["date"].iloc[0]).date().isoformat(),
        model_id=EXPECTED_ALPHA_MODEL_ID,
        model_fingerprint=EXPECTED_ALPHA_MODEL_FINGERPRINT,
        artifact_path=scores,
        artifact_sha256=EXPECTED_SCORE_SHA256,
        manifest_path=manifest,
        manifest_sha256=EXPECTED_MANIFEST_SHA256,
        scores=score_block,
        alpha_tie_rows=int(score_block["alpha_consensus"].duplicated(keep=False).sum()),
        _verification_token=_VERIFIED_TOKEN,
    )


def _row_map(block: pd.DataFrame) -> dict[str, dict[str, Any]]:
    return {
        str(r.ticker): {
            "rank_consensus": int(r.rank_consensus),
            "rank_h5": int(r.rank_h5),
            "rank_h10": int(r.rank_h10),
            "alpha_consensus": float(r.alpha_consensus),
            "alpha_h5": float(r.alpha_h5),
            "alpha_h10": float(r.alpha_h10),
        }
        for r in block.itertuples(index=False)
    }


def _support_class(r5: int, r10: int, threshold: int) -> str:
    a, b = r5 <= threshold, r10 <= threshold
    if a and b:
        return f"BOTH_LE{threshold}"
    if a:
        return f"H5_ONLY_LE{threshold}"
    if b:
        return f"H10_ONLY_LE{threshold}"
    return f"NEITHER_LE{threshold}"


def diagnose(frame: pd.DataFrame, manifest: Path, scores: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = [pd.Timestamp(x) for x in sorted(frame["date"].unique())]
    blocks = {d: b.copy() for d, b in frame.groupby("date", sort=True)}
    maps = {d: _row_map(blocks[d]) for d in dates}

    state = ShadowPortfolioState.empty()
    open_entries: dict[str, dict[str, Any]] = {}
    entries: list[dict[str, Any]] = []
    hard_exits: list[dict[str, Any]] = []

    for i, d in enumerate(dates):
        block = blocks[d]
        current = maps[d]
        prior = maps[dates[i - 1]] if i > 0 else {}
        plan = plan_decision_v1(_verified(block, manifest, scores), state)

        for intent in plan.sell_intents:
            entry = open_entries.pop(intent.ticker, None)
            if entry is not None:
                entry["exit_index"] = i
                entry["exit_date"] = d.date().isoformat()
                entry["exit_reason"] = intent.reason
                entry["held_transition_count"] = i - int(entry["entry_index"])
            if intent.reason != "HARD_EXIT_RANK_GT20":
                continue
            now = current.get(intent.ticker)
            prev = prior.get(intent.ticker)
            if now is None:
                raise RuntimeError("HARD_EXIT_WITHOUT_CURRENT_SCORE")
            hard_exits.append({
                "date": d.date().isoformat(),
                "ticker": intent.ticker,
                "entry_index": None if entry is None else int(entry["entry_index"]),
                "holding_age": None if entry is None else i - int(entry["entry_index"]),
                "previous_rank_consensus": None if prev is None else prev["rank_consensus"],
                "previous_rank_h5": None if prev is None else prev["rank_h5"],
                "previous_rank_h10": None if prev is None else prev["rank_h10"],
                "current_rank_consensus": now["rank_consensus"],
                "current_rank_h5": now["rank_h5"],
                "current_rank_h10": now["rank_h10"],
                "current_support20": _support_class(now["rank_h5"], now["rank_h10"], 20),
                "delta_rank_h5": None if prev is None else now["rank_h5"] - prev["rank_h5"],
                "delta_rank_h10": None if prev is None else now["rank_h10"] - prev["rank_h10"],
                "h10_still_le20": now["rank_h10"] <= 20,
                "h5_still_le20": now["rank_h5"] <= 20,
                "both_heads_gt20": now["rank_h5"] > 20 and now["rank_h10"] > 20,
            })

        for intent in plan.buy_intents:
            now = current.get(intent.ticker)
            if now is None:
                raise RuntimeError("BUY_WITHOUT_CURRENT_SCORE")
            rec = {
                "entry_index": i,
                "entry_date": d.date().isoformat(),
                "ticker": intent.ticker,
                "buy_reason": intent.reason,
                "bootstrap": i == 0,
                "rank_consensus": now["rank_consensus"],
                "rank_h5": now["rank_h5"],
                "rank_h10": now["rank_h10"],
                "alpha_consensus": now["alpha_consensus"],
                "alpha_h5": now["alpha_h5"],
                "alpha_h10": now["alpha_h10"],
                "abs_head_rank_gap": abs(now["rank_h5"] - now["rank_h10"]),
                "abs_head_alpha_gap": abs(now["alpha_h5"] - now["alpha_h10"]),
                "support10": _support_class(now["rank_h5"], now["rank_h10"], 10),
                "support20": _support_class(now["rank_h5"], now["rank_h10"], 20),
                "exit_index": None,
                "exit_date": None,
                "exit_reason": None,
                "held_transition_count": None,
            }
            entries.append(rec)
            open_entries[intent.ticker] = rec

        state = ShadowPortfolioState(d.date().isoformat(), plan.target_positions)

    last_index = len(dates) - 1
    for entry in open_entries.values():
        entry["held_transition_count"] = last_index - int(entry["entry_index"])
        entry["exit_reason"] = "RIGHT_CENSORED"

    return pd.DataFrame(entries), pd.DataFrame(hard_exits)


def _group_entry(frame: pd.DataFrame, col: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, b in frame.groupby(col, sort=True):
        immediate = b["exit_reason"].eq("HARD_EXIT_RANK_GT20") & pd.to_numeric(b["held_transition_count"], errors="coerce").eq(1)
        hard3 = b["exit_reason"].eq("HARD_EXIT_RANK_GT20") & pd.to_numeric(b["held_transition_count"], errors="coerce").le(3)
        out[str(key)] = {
            "n": int(len(b)),
            "immediate_hard_exit_rate": _rate(immediate),
            "hard_exit_within3_rate": _rate(hard3),
            "head_rank_gap": _q(b["abs_head_rank_gap"]),
        }
    return out


def summarize(entries: pd.DataFrame, hard: pd.DataFrame) -> dict[str, Any]:
    non_boot = entries.loc[~entries["bootstrap"].astype(bool)].copy()
    immediate = non_boot["exit_reason"].eq("HARD_EXIT_RANK_GT20") & pd.to_numeric(non_boot["held_transition_count"], errors="coerce").eq(1)
    hard3 = non_boot["exit_reason"].eq("HARD_EXIT_RANK_GT20") & pd.to_numeric(non_boot["held_transition_count"], errors="coerce").le(3)
    immediate_b = non_boot.loc[immediate]
    not_immediate = non_boot.loc[~immediate]

    hard_one = hard.loc[pd.to_numeric(hard["holding_age"], errors="coerce").eq(1)].copy() if not hard.empty else hard

    return {
        "schema_version": "v4_x1_decision_v1_head_entry_diagnosis_v1",
        "status": "COMPLETE_OUTCOME_BLIND_HEAD_ENTRY_DIAGNOSIS",
        "entries": {
            "all": int(len(entries)),
            "non_bootstrap": int(len(non_boot)),
            "immediate_hard_exit_count": int(immediate.sum()),
            "immediate_hard_exit_rate": _rate(immediate),
            "hard_exit_within3_rate": _rate(hard3),
            "all_entry_head_rank_gap": _q(non_boot["abs_head_rank_gap"]),
            "immediate_exit_entry_head_rank_gap": _q(immediate_b["abs_head_rank_gap"]),
            "non_immediate_entry_head_rank_gap": _q(not_immediate["abs_head_rank_gap"]),
            "by_support10": _group_entry(non_boot, "support10"),
            "by_support20": _group_entry(non_boot, "support20"),
            "by_buy_reason": _group_entry(non_boot, "buy_reason"),
        },
        "hard_exit_head_state": {
            "n": int(len(hard)),
            "h10_still_le20_rate": _rate(hard["h10_still_le20"]) if not hard.empty else None,
            "h5_still_le20_rate": _rate(hard["h5_still_le20"]) if not hard.empty else None,
            "both_heads_gt20_rate": _rate(hard["both_heads_gt20"]) if not hard.empty else None,
            "current_rank_h5": _q(hard["current_rank_h5"]) if not hard.empty else _q([]),
            "current_rank_h10": _q(hard["current_rank_h10"]) if not hard.empty else _q([]),
            "delta_rank_h5": _q(hard["delta_rank_h5"]) if not hard.empty else _q([]),
            "delta_rank_h10": _q(hard["delta_rank_h10"]) if not hard.empty else _q([]),
            "by_current_support20": {
                str(k): int(v) for k, v in hard["current_support20"].value_counts().sort_index().items()
            } if not hard.empty else {},
        },
        "one_session_hard_exit_head_state": {
            "n": int(len(hard_one)),
            "h10_still_le20_rate": _rate(hard_one["h10_still_le20"]) if len(hard_one) else None,
            "h5_still_le20_rate": _rate(hard_one["h5_still_le20"]) if len(hard_one) else None,
            "both_heads_gt20_rate": _rate(hard_one["both_heads_gt20"]) if len(hard_one) else None,
            "delta_rank_h5": _q(hard_one["delta_rank_h5"]) if len(hard_one) else _q([]),
            "delta_rank_h10": _q(hard_one["delta_rank_h10"]) if len(hard_one) else _q([]),
        },
        "guards": {
            "realized_returns_loaded": False,
            "target_ledger_loaded": False,
            "historical_pnl_computed": False,
            "decision_v2_rule_simulated": False,
            "decision_v2_parameters_tested": False,
            "model_refit_or_retune": False,
            "provider_or_network_calls": False,
            "protected_or_fresh_forward_access": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--historical-root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    out = args.output_dir.expanduser().resolve()
    if out.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE:{out}")
    frame, manifest, scores = _load(args.historical_root.expanduser().resolve())
    entries, hard = diagnose(frame, manifest, scores)
    summary = summarize(entries, hard)
    summary["source"] = {
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "score_sha256": EXPECTED_SCORE_SHA256,
        "score_rows": int(len(frame)),
        "score_dates": int(frame["date"].nunique()),
    }
    out.mkdir(parents=True, exist_ok=False)
    p_entries = out / "entry_events.csv"
    p_hard = out / "hard_exit_head_events.csv"
    p_summary = out / "summary.json"
    entries.to_csv(p_entries, index=False, lineterminator="\n")
    hard.to_csv(p_hard, index=False, lineterminator="\n")
    p_summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    payload = {
        "schema_version": "v4_x1_decision_v1_head_entry_diagnosis_manifest_v1",
        "status": summary["status"],
        "source_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "source_score_sha256": EXPECTED_SCORE_SHA256,
        "output_sha256": {
            "entries": _sha256(p_entries),
            "hard_exits": _sha256(p_hard),
            "summary": _sha256(p_summary),
        },
        "guards": summary["guards"],
    }
    p_manifest = out / "MANIFEST.json"
    p_manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"manifest={p_manifest}")
    print(f"manifest_sha256={_sha256(p_manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
