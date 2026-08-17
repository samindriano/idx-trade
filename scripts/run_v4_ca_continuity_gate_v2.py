"""Outcome-blind V4 CA continuity gate remediation using complete KSEI history.

This runner never materializes future returns or model outputs.  It consumes:
1) the exact blocked V4 continuity ledger, 2) its bounded prior official event
candidates, and 3) the separately captured exact-610-ticker KSEI history
census.  A ticker is resolved only when KSEI history coverage is certified and
there is no active mechanical/unknown CA in the broad frozen V4 period.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from idx_trade.v4_ca_continuity_remediation import (
    HALO_CALENDAR_DAYS,
    RESOLVED,
    classify_ticker_period,
)


PINNED_CONTINUITY_LEDGER_SHA256 = (
    "52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb"
)
PINNED_PRIOR_EVENT_EVIDENCE_SHA256 = (
    "4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7"
)
EXPECTED_LEDGER_ROWS = 344_790
EXPECTED_FROZEN_TICKERS = 610
EXPECTED_FROZEN_DATES = 600
GATE_RATE = 0.90


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def normalize_ticker(values: pd.Series) -> pd.Series:
    return (
        values.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def normalize_date(values: pd.Series, *, label: str) -> pd.Series:
    result = pd.to_datetime(values, errors="coerce")
    if result.isna().any():
        raise RuntimeError(f"INVALID_DATE_COLUMN:{label}")
    return result.dt.tz_localize(None).dt.normalize()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise RuntimeError(f"REQUIRED_JSONL_MISSING:{path}")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def verify_prior_inputs(
    continuity_ledger: Path,
    prior_event_evidence: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not continuity_ledger.is_file():
        raise RuntimeError(f"CONTINUITY_LEDGER_MISSING:{continuity_ledger}")
    if sha256_file(continuity_ledger) != PINNED_CONTINUITY_LEDGER_SHA256:
        raise RuntimeError("CONTINUITY_LEDGER_SHA_MISMATCH")
    if not prior_event_evidence.is_file():
        raise RuntimeError(f"PRIOR_EVENT_EVIDENCE_MISSING:{prior_event_evidence}")
    if sha256_file(prior_event_evidence) != PINNED_PRIOR_EVENT_EVIDENCE_SHA256:
        raise RuntimeError("PRIOR_EVENT_EVIDENCE_SHA_MISMATCH")

    ledger = pd.read_csv(continuity_ledger)
    required = {
        "ticker",
        "signal_date",
        "horizon",
        "entry_date",
        "terminal_date",
    }
    missing = required - set(ledger.columns)
    if missing:
        raise RuntimeError(f"CONTINUITY_LEDGER_COLUMNS_MISSING:{sorted(missing)}")
    if len(ledger) != EXPECTED_LEDGER_ROWS:
        raise RuntimeError(f"CONTINUITY_LEDGER_ROW_COUNT_CHANGED:{len(ledger)}")
    ledger["ticker"] = normalize_ticker(ledger["ticker"])
    for column in ("signal_date", "entry_date", "terminal_date"):
        ledger[column] = normalize_date(ledger[column], label=column)
    ledger["horizon"] = pd.to_numeric(ledger["horizon"], errors="raise").astype(int)
    if set(ledger["horizon"].unique()) != {5, 10}:
        raise RuntimeError("CONTINUITY_LEDGER_HORIZON_SET_CHANGED")
    if ledger["ticker"].nunique() != EXPECTED_FROZEN_TICKERS:
        raise RuntimeError("CONTINUITY_LEDGER_TICKER_COUNT_CHANGED")
    if ledger["signal_date"].nunique() != EXPECTED_FROZEN_DATES:
        raise RuntimeError("CONTINUITY_LEDGER_DATE_COUNT_CHANGED")
    if ledger.duplicated(["ticker", "signal_date", "horizon"]).any():
        raise RuntimeError("CONTINUITY_LEDGER_DUPLICATE_IDENTITY")

    evidence = pd.read_csv(prior_event_evidence)
    if not {"ticker", "candidate_date", "event_family"}.issubset(evidence.columns):
        raise RuntimeError("PRIOR_EVENT_EVIDENCE_COLUMNS_MISSING")
    evidence["ticker"] = normalize_ticker(evidence["ticker"])
    evidence["candidate_date"] = pd.to_datetime(
        evidence["candidate_date"], errors="coerce"
    ).dt.normalize()
    if evidence["candidate_date"].isna().any():
        raise RuntimeError("PRIOR_EVENT_EVIDENCE_INVALID_DATE")
    return ledger, evidence


def verify_ksei_census(
    root: Path,
    expected_tickers: list[str],
) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, Any], dict[str, str]]:
    paths = {
        "coverage": root / "ticker_coverage.csv",
        "history": root / "ksei_ca_history.jsonl",
        "summary": root / "summary.json",
        "manifest": root / "MANIFEST.json",
    }
    for name, path in paths.items():
        if not path.is_file():
            raise RuntimeError(f"KSEI_CENSUS_INPUT_MISSING:{name}:{path}")

    summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if summary.get("outcome_blind") is not True:
        raise RuntimeError("KSEI_CENSUS_NOT_OUTCOME_BLIND")
    if int(summary.get("ticker_count", -1)) != EXPECTED_FROZEN_TICKERS:
        raise RuntimeError("KSEI_CENSUS_TICKER_COUNT_CHANGED")
    if summary.get("input", {}).get("continuity_ledger_sha256") != PINNED_CONTINUITY_LEDGER_SHA256:
        raise RuntimeError("KSEI_CENSUS_PARENT_LEDGER_MISMATCH")
    if manifest.get("summary_sha256") != sha256_file(paths["summary"]):
        raise RuntimeError("KSEI_CENSUS_SUMMARY_HASH_MISMATCH")
    for key, filename in (
        ("ticker_coverage", "coverage"),
        ("ksei_ca_history", "history"),
    ):
        expected = summary.get("output_hashes", {}).get(key)
        actual = sha256_file(paths[filename])
        if expected != actual:
            raise RuntimeError(f"KSEI_CENSUS_OUTPUT_HASH_MISMATCH:{key}")

    coverage = pd.read_csv(paths["coverage"])
    if not {"ticker", "coverage_certified"}.issubset(coverage.columns):
        raise RuntimeError("KSEI_COVERAGE_COLUMNS_MISSING")
    coverage["ticker"] = normalize_ticker(coverage["ticker"])
    if coverage["ticker"].duplicated().any():
        raise RuntimeError("KSEI_COVERAGE_DUPLICATE_TICKER")
    actual_tickers = sorted(coverage["ticker"].tolist())
    if actual_tickers != expected_tickers:
        raise RuntimeError("KSEI_COVERAGE_TICKER_IDENTITY_MISMATCH")
    coverage["coverage_certified"] = (
        coverage["coverage_certified"]
        .astype(str)
        .str.casefold()
        .map({"true": True, "false": False})
    )
    if coverage["coverage_certified"].isna().any():
        raise RuntimeError("KSEI_COVERAGE_BOOLEAN_INVALID")

    history = read_jsonl(paths["history"])
    for row in history:
        ticker = str(row.get("ticker", "")).upper().strip()
        if ticker not in set(expected_tickers):
            raise RuntimeError(f"KSEI_HISTORY_OUT_OF_SCOPE_TICKER:{ticker}")
    hashes = {name: sha256_file(path) for name, path in paths.items()}
    return coverage, history, summary, hashes


def candidate_tickers_in_period(
    evidence: pd.DataFrame,
    *,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
) -> set[str]:
    start = period_start - pd.Timedelta(days=HALO_CALENDAR_DAYS)
    end = period_end + pd.Timedelta(days=HALO_CALENDAR_DAYS)
    mask = evidence["candidate_date"].between(start, end, inclusive="both")
    return set(evidence.loc[mask, "ticker"].astype(str))


def build_ticker_classification(
    *,
    tickers: list[str],
    coverage: pd.DataFrame,
    history: list[dict[str, Any]],
    prior_candidates: set[str],
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
) -> pd.DataFrame:
    coverage_map = dict(
        zip(coverage["ticker"], coverage["coverage_certified"].astype(bool))
    )
    rows_by_ticker: dict[str, list[dict[str, Any]]] = {ticker: [] for ticker in tickers}
    for row in history:
        rows_by_ticker[str(row["ticker"]).upper().strip()].append(dict(row))

    classified: list[dict[str, Any]] = []
    for ticker in tickers:
        result = classify_ticker_period(
            coverage_certified=bool(coverage_map[ticker]),
            rows=rows_by_ticker[ticker],
            period_start=period_start,
            period_end=period_end,
            prior_official_candidate_in_period=ticker in prior_candidates,
        )
        classified.append(
            {
                "ticker": ticker,
                "continuity_status": result["continuity_status"],
                "reason": result["reason"],
                "risk_rows": int(result["risk_rows"]),
                "ksei_coverage_certified": bool(coverage_map[ticker]),
                "prior_official_candidate_in_period": ticker in prior_candidates,
                "ksei_history_rows": len(rows_by_ticker[ticker]),
            }
        )
    return pd.DataFrame(classified).sort_values("ticker", kind="mergesort").reset_index(drop=True)


def build_per_date_gate(ledger: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for date, block in ledger.groupby("signal_date", sort=True):
        row: dict[str, Any] = {"date": date}
        resolved_sets: dict[int, set[str]] = {}
        for horizon in (5, 10):
            sub = block[block["horizon"].eq(horizon)]
            resolved = sub[sub["continuity_status"].eq(RESOLVED)]
            rate = len(resolved) / len(sub) if len(sub) else np.nan
            row[f"h{horizon}_decision_rows"] = int(len(sub))
            row[f"h{horizon}_resolved_rows"] = int(len(resolved))
            row[f"h{horizon}_continuity_rate"] = rate
            row[f"h{horizon}_continuity_gate"] = bool(len(sub) and rate >= GATE_RATE)
            resolved_sets[horizon] = set(resolved["ticker"])
        h5 = block[block["horizon"].eq(5)]
        consensus_resolved = resolved_sets[5] & resolved_sets[10]
        consensus_rate = len(consensus_resolved) / len(h5) if len(h5) else np.nan
        row["consensus_resolved_rows"] = len(consensus_resolved)
        row["consensus_continuity_rate"] = consensus_rate
        row["consensus_continuity_gate"] = bool(
            len(h5) and consensus_rate >= GATE_RATE
        )
        rows.append(row)
    result = pd.DataFrame(rows).sort_values("date", kind="mergesort").reset_index(drop=True)
    if len(result) != EXPECTED_FROZEN_DATES:
        raise RuntimeError("PER_DATE_GATE_DATE_COUNT_CHANGED")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--continuity-ledger", type=Path, required=True)
    parser.add_argument("--prior-event-evidence", type=Path, required=True)
    parser.add_argument("--ksei-census-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    args.output_dir.mkdir(parents=True)

    ledger, prior_evidence = verify_prior_inputs(
        args.continuity_ledger, args.prior_event_evidence
    )
    tickers = sorted(ledger["ticker"].unique().tolist())
    coverage, history, ksei_summary, ksei_hashes = verify_ksei_census(
        args.ksei_census_root, tickers
    )

    period_start = ledger["entry_date"].min()
    period_end = ledger["terminal_date"].max()
    prior_candidates = candidate_tickers_in_period(
        prior_evidence, period_start=period_start, period_end=period_end
    )
    classification = build_ticker_classification(
        tickers=tickers,
        coverage=coverage,
        history=history,
        prior_candidates=prior_candidates,
        period_start=period_start,
        period_end=period_end,
    )

    remediated = ledger.drop(
        columns=[
            column
            for column in ("continuity_status", "unresolved_reason")
            if column in ledger.columns
        ]
    ).merge(
        classification[["ticker", "continuity_status", "reason", "risk_rows"]],
        on="ticker",
        how="left",
        validate="many_to_one",
    )
    if remediated["continuity_status"].isna().any():
        raise RuntimeError("REMEDIATED_LEDGER_CLASSIFICATION_MISSING")
    remediated = remediated.rename(columns={"reason": "continuity_reason"})
    per_date = build_per_date_gate(remediated)

    verdict = (
        "V4_CA_CONTINUITY_CERTIFIED"
        if bool(
            per_date["h5_continuity_gate"].all()
            and per_date["h10_continuity_gate"].all()
            and per_date["consensus_continuity_gate"].all()
        )
        else "V4_CA_CONTINUITY_STILL_BLOCKED"
    )
    certified = verdict == "V4_CA_CONTINUITY_CERTIFIED"

    classification_path = args.output_dir / "ticker_continuity_classification.csv"
    ledger_path = args.output_dir / "v4_frozen_continuity_ledger_v2.csv"
    per_date_path = args.output_dir / "v4_frozen_continuity_per_date_v2.csv"
    classification.to_csv(classification_path, index=False, lineterminator="\n")
    remediated.to_csv(ledger_path, index=False, lineterminator="\n")
    per_date.to_csv(per_date_path, index=False, lineterminator="\n")

    reason_counts = Counter(classification["reason"])
    status_counts = Counter(classification["continuity_status"])
    summary = {
        "schema_version": "v4_ca_continuity_gate_ksei_history_remediation_v1",
        "verdict": verdict,
        "corporate_action_continuity_certified": certified,
        "outcome_blind": True,
        "target_or_rank_materialized": False,
        "model_fit": False,
        "prediction_generated": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "policy": {
            "complete_ksei_history_can_certify_no_event": True,
            "effective_date_inference": False,
            "ticker_period_quarantine": True,
            "halo_calendar_days": HALO_CALENDAR_DAYS,
            "cash_dividend_is_not_blocker": True,
            "cancelled_ca_is_not_basis_change": True,
            "unknown_active_ca_is_blocker": True,
            "cross_source_missing_mechanical_representation_is_blocker": True,
            "required_per_date_rate": GATE_RATE,
        },
        "period": {
            "entry_start": str(period_start.date()),
            "terminal_end": str(period_end.date()),
        },
        "ticker_count": len(tickers),
        "resolved_tickers": int(classification["continuity_status"].eq(RESOLVED).sum()),
        "unresolved_tickers": int((~classification["continuity_status"].eq(RESOLVED)).sum()),
        "prior_candidate_tickers_in_period": len(prior_candidates),
        "ticker_status_counts": dict(sorted(status_counts.items())),
        "ticker_reason_counts": dict(sorted(reason_counts.items())),
        "frozen_dates": int(len(per_date)),
        "per_date": {
            "h5_gate_dates": int(per_date["h5_continuity_gate"].sum()),
            "h10_gate_dates": int(per_date["h10_continuity_gate"].sum()),
            "consensus_gate_dates": int(per_date["consensus_continuity_gate"].sum()),
            "h5_min_rate": float(per_date["h5_continuity_rate"].min()),
            "h10_min_rate": float(per_date["h10_continuity_rate"].min()),
            "consensus_min_rate": float(per_date["consensus_continuity_rate"].min()),
        },
        "inputs": {
            "blocked_continuity_ledger_sha256": sha256_file(args.continuity_ledger),
            "prior_event_evidence_sha256": sha256_file(args.prior_event_evidence),
            "ksei_census_hashes": ksei_hashes,
            "ksei_census_status": ksei_summary.get("status"),
        },
        "outputs": {},
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary["outputs"] = {
        "ticker_classification_sha256": sha256_file(classification_path),
        "continuity_ledger_v2_sha256": sha256_file(ledger_path),
        "per_date_v2_sha256": sha256_file(per_date_path),
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        "schema_version": "v4_ca_continuity_gate_ksei_history_manifest_v1",
        "status": verdict,
        "outcome_blind": True,
        "corporate_action_continuity_certified": certified,
        "summary_sha256": sha256_file(summary_path),
        "input_hashes": summary["inputs"],
        "output_hashes": summary["outputs"],
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {**summary, "manifest_sha256": sha256_file(manifest_path)},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
