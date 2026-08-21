from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

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
        "ticker", "date", "raw_h5", "raw_h10", "alpha_h5", "alpha_h10", "alpha_consensus"
    }
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"MISSING_SCORE_COLUMNS:{sorted(missing)}")

    frame = frame[list(required)].copy()
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.tz_localize(None).dt.normalize()
    if frame.duplicated(["ticker", "date"]).any():
        raise RuntimeError("DUPLICATE_IDENTITY")
    if frame["date"].nunique() != 600:
        raise RuntimeError("DATE_COUNT_CHANGED")

    parts: list[pd.DataFrame] = []
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
    return pd.concat(parts, ignore_index=True), manifest, scores


def _run_length(flags: pd.Series) -> pd.Series:
    out = np.zeros(len(flags), dtype=int)
    streak = 0
    for i, value in enumerate(flags.astype(bool).to_numpy()):
        streak = streak + 1 if value else 0
        out[i] = streak
    return pd.Series(out, index=flags.index, dtype=int)


def build_panel(frame: pd.DataFrame) -> pd.DataFrame:
    x = frame.sort_values(["ticker", "date"], kind="mergesort").copy()
    g = x.groupby("ticker", sort=False)

    for rank in ("rank_consensus", "rank_h5", "rank_h10"):
        x[f"prev_{rank}"] = g[rank].shift(1)
        for k in (1, 2, 3):
            x[f"next{k}_{rank}"] = g[rank].shift(-k)

    x["top10_run"] = g["rank_consensus"].transform(lambda s: _run_length(s <= 10))
    x["top20_run"] = g["rank_consensus"].transform(lambda s: _run_length(s <= 20))
    x["both_heads_le10"] = (x["rank_h5"] <= 10) & (x["rank_h10"] <= 10)
    x["both_heads_le20"] = (x["rank_h5"] <= 20) & (x["rank_h10"] <= 20)
    x["prev_consensus_le10"] = x["prev_rank_consensus"] <= 10
    x["prev_consensus_le20"] = x["prev_rank_consensus"] <= 20
    x["fresh_from_gt20_or_absent"] = x["prev_rank_consensus"].isna() | (x["prev_rank_consensus"] > 20)
    x["prev_consensus_11_20"] = (x["prev_rank_consensus"] > 10) & (x["prev_rank_consensus"] <= 20)
    return x


def _rate(series: pd.Series) -> float | None:
    return None if len(series) == 0 else float(series.astype(bool).mean())


def _summary(block: pd.DataFrame) -> dict[str, object]:
    if block.empty:
        return {"n": 0}

    n1 = block["next1_rank_consensus"].notna()
    next1 = block.loc[n1].copy()
    n3 = block[["next1_rank_consensus", "next2_rank_consensus", "next3_rank_consensus"]].notna().all(axis=1)
    next3 = block.loc[n3].copy()
    any_gt20_3 = (
        (next3["next1_rank_consensus"] > 20)
        | (next3["next2_rank_consensus"] > 20)
        | (next3["next3_rank_consensus"] > 20)
    )

    return {
        "n": int(len(block)),
        "next1_available_n": int(len(next1)),
        "next1_top10_survival_rate": _rate(next1["next1_rank_consensus"] <= 10),
        "next1_top20_survival_rate": _rate(next1["next1_rank_consensus"] <= 20),
        "next1_gt20_rate": _rate(next1["next1_rank_consensus"] > 20),
        "next1_rank_median": None if next1.empty else float(next1["next1_rank_consensus"].median()),
        "next1_rank_delta_median": None if next1.empty else float((next1["next1_rank_consensus"] - next1["rank_consensus"]).median()),
        "next3_available_n": int(len(next3)),
        "any_gt20_within3_rate": _rate(any_gt20_3),
    }


def _capacity_by_date(frame: pd.DataFrame, mask: pd.Series) -> dict[str, float | int | None]:
    counts = frame.loc[mask].groupby("date").size().reindex(sorted(frame["date"].unique()), fill_value=0)
    if counts.empty:
        return {"dates": 0, "mean": None, "median": None, "p10": None, "min": None, "share_ge10": None}
    return {
        "dates": int(len(counts)),
        "mean": float(counts.mean()),
        "median": float(counts.median()),
        "p10": float(counts.quantile(0.10)),
        "min": int(counts.min()),
        "share_ge10": float((counts >= 10).mean()),
    }


def summarize(panel: pd.DataFrame) -> dict[str, object]:
    top10 = panel.loc[panel["rank_consensus"] <= 10].copy()
    top20 = panel.loc[panel["rank_consensus"] <= 20].copy()

    strata = {
        "ALL_CURRENT_TOP10": pd.Series(True, index=top10.index),
        "PREV_TOP10": top10["prev_consensus_le10"],
        "PREV_11_20": top10["prev_consensus_11_20"],
        "FRESH_FROM_GT20_OR_ABSENT": top10["fresh_from_gt20_or_absent"],
        "TOP10_RUN_GE2": top10["top10_run"] >= 2,
        "TOP10_RUN_GE3": top10["top10_run"] >= 3,
        "TOP20_RUN_GE2": top10["top20_run"] >= 2,
        "TOP20_RUN_GE3": top10["top20_run"] >= 3,
        "BOTH_HEADS_LE10": top10["both_heads_le10"],
        "BOTH_HEADS_LE20": top10["both_heads_le20"],
        "PREV_TOP20_AND_BOTH_HEADS_LE20": top10["prev_consensus_le20"] & top10["both_heads_le20"],
        "PREV_TOP10_AND_BOTH_HEADS_LE10": top10["prev_consensus_le10"] & top10["both_heads_le10"],
    }

    capacity = {
        "CURRENT_TOP20": _capacity_by_date(panel, panel["rank_consensus"] <= 20),
        "CURRENT_TOP20_WITH_TOP20_RUN_GE2": _capacity_by_date(panel, (panel["rank_consensus"] <= 20) & (panel["top20_run"] >= 2)),
        "CURRENT_TOP20_WITH_TOP20_RUN_GE3": _capacity_by_date(panel, (panel["rank_consensus"] <= 20) & (panel["top20_run"] >= 3)),
        "CURRENT_TOP20_PREV_TOP20_BOTH_HEADS_LE20": _capacity_by_date(
            panel,
            (panel["rank_consensus"] <= 20) & panel["prev_consensus_le20"] & panel["both_heads_le20"],
        ),
    }

    return {
        "schema_version": "v4_x1_decision_v1_temporal_persistence_diagnosis_v1",
        "status": "COMPLETE_OUTCOME_BLIND_TEMPORAL_PERSISTENCE_DIAGNOSIS",
        "top10_candidate_strata": {name: _summary(top10.loc[mask]) for name, mask in strata.items()},
        "persistent_candidate_capacity": capacity,
        "reference_counts": {
            "rows": int(len(panel)),
            "dates": int(panel["date"].nunique()),
            "current_top10_rows": int(len(top10)),
            "current_top20_rows": int(len(top20)),
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

    frame, _, _ = _load(args.historical_root.expanduser().resolve())
    panel = build_panel(frame)
    summary = summarize(panel)
    summary["source"] = {
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "score_sha256": EXPECTED_SCORE_SHA256,
    }

    out.mkdir(parents=True, exist_ok=False)
    p_panel = out / "temporal_candidate_panel.csv"
    p_summary = out / "summary.json"
    panel.to_csv(p_panel, index=False, lineterminator="\n")
    p_summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": "v4_x1_decision_v1_temporal_persistence_diagnosis_manifest_v1",
        "status": summary["status"],
        "source_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "source_score_sha256": EXPECTED_SCORE_SHA256,
        "output_sha256": {
            "panel": _sha256(p_panel),
            "summary": _sha256(p_summary),
        },
        "guards": summary["guards"],
    }
    p_manifest = out / "MANIFEST.json"
    p_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"manifest={p_manifest}")
    print(f"manifest_sha256={_sha256(p_manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
