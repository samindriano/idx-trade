"""Outcome-blind V4 corporate-action price-basis continuity census.

This runner consumes only the frozen V4 decision/support identities and the
already captured official IDX/KSEI corporate-action evidence.  Missing event
coverage is deliberately not interpreted as no event.  No target, return,
rank, model, or protected outcome is loaded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from idx_trade.ranking_v4_3_features import build_v4_control_feature_table


PINNED = {
    "calendar": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "panel": "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76",
    "security_master": "c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240",
    "validation_folds": "91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915",
    "ca_manifest": "d44b9362909f5c05d8412ff07ca4c5616a74b43930bd1caf92242ed25b5e10cf",
    "ca_normalized_candidates": "d3a11d3e51887ebde4af5b6a2f37ab64d9ad1bfd1d70179b58fca79d18e9909e",
    "ca_idx_linkages": "e52442489f034c6737c576bf815b07d54985410757e5eeb7ca24017a8d786378",
    "ca_cross_source": "46018e496cb18c8007866e6ddbbbd84b15c8bd6d2441e935082bdec6aa66670a",
    "ca_ksei_actions": "afadd79e619a0ab4493d2d7b9c5b5d45b0f3b9ef445d570caa5cb4b7dc63a8e7",
}

MECHANICAL_FAMILIES = {
    "STOCK_SPLIT",
    "REVERSE_SPLIT",
    "STOCK_DIVIDEND",
    "BONUS_SHARES",
    "RIGHTS_HMETD",
    "MANDATORY_CONVERSION",
    "MERGER",
    "CAPITAL_RESTRUCTURING",
}

REPORT_FAMILIES = (
    "STOCK_SPLIT",
    "REVERSE_SPLIT",
    "STOCK_DIVIDEND",
    "BONUS_SHARES",
    "RIGHTS_HMETD",
    "MANDATORY_CONVERSION",
    "MERGER",
    "CAPITAL_RESTRUCTURING",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_git_bytes(repo_root: Path, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"HEAD:{relative}"],
        check=True,
        capture_output=True,
    )
    return result.stdout


def normalize_dates(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_datetime(frame[column], errors="coerce")
    values = values.dt.tz_localize(None).dt.normalize()
    if values.isna().any():
        raise RuntimeError(f"INVALID_DATE_COLUMN:{column}")
    return values


def normalize_tickers(values: pd.Series) -> pd.Series:
    return (
        values.astype(str)
        .str.upper()
        .str.replace(".JK", "", regex=False)
        .str.strip()
    )


def classify_ksei_event(event_family_source: str) -> str | None:
    """Map only mechanically relevant KSEI families; cash/proxy stay out."""

    return {
        "Stock Dividend": "STOCK_DIVIDEND",
        "Right Distribution": "RIGHTS_HMETD",
        "Mandatory Conversion": "MANDATORY_CONVERSION",
        "Voluntary Conversion": "MANDATORY_CONVERSION",
    }.get(str(event_family_source).strip())


def event_reason(event_family: str, *, effective_date_proven: bool) -> str:
    if event_family not in MECHANICAL_FAMILIES:
        raise ValueError(f"unsupported mechanical event family: {event_family}")
    if effective_date_proven:
        return ""
    return "PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_event_evidence(ca_root: Path) -> pd.DataFrame:
    normalized = load_jsonl(ca_root / "normalized_candidates.jsonl")
    idx_rows = load_jsonl(ca_root / "idx_announcement_linkages.jsonl")
    ksei_rows = load_jsonl(ca_root / "ksei_security_actions.jsonl")

    idx_by_action: dict[str, list[dict[str, Any]]] = {}
    for row in idx_rows:
        idx_by_action.setdefault(str(row.get("source_action_id")), []).append(row)

    rows: list[dict[str, Any]] = []
    for row in normalized:
        family = {
            "STOCK_SPLIT": "STOCK_SPLIT",
            "REVERSE_SPLIT": "REVERSE_SPLIT",
            "REVERSE_STOCK": "REVERSE_SPLIT",
            "RIGHTS_ISSUE": "RIGHTS_HMETD",
            "BONUS_SHARES": "BONUS_SHARES",
            "CAPITAL_REDUCTION": "CAPITAL_RESTRUCTURING",
        }.get(str(row.get("event_family", "")).upper())
        if family not in MECHANICAL_FAMILIES:
            continue
        action_id = str(row.get("source_id"))
        linked = idx_by_action.get(action_id, [])
        join_statuses = sorted({str(item.get("join_status", "")) for item in linked})
        rows.append(
            {
                "source_kind": "IDX_GET_ISSUED_HISTORY",
                "ticker": str(row.get("ticker", "")).upper().strip(),
                "event_family": family,
                "candidate_date": row.get("listing_action_date"),
                "effective_date_status": "UNRESOLVED_TANGGAL_PENCATATAN_NOT_GENERIC_EFFECTIVE_DATE",
                "continuity_status": "PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE",
                "source_action_id": action_id,
                "source_ref": ";".join(join_statuses) or "NO_EXACT_ANNOUNCEMENT_JOIN",
                "source_url": "IDX:GetIssuedHistory",
                "source_sha256": PINNED["ca_normalized_candidates"],
                "official_attachment_sha256s": ";".join(
                    sorted(
                        {
                            str(item.get("attachment_sha256"))
                            for item in linked
                            if item.get("attachment_sha256")
                        }
                    )
                ),
                "official_announcement_refs": ";".join(
                    sorted(
                        {
                            str(item.get("announcement_ref"))
                            for item in linked
                            if item.get("announcement_ref")
                        }
                    )
                ),
                "published_at_utc": ";".join(
                    sorted(
                        {
                            str(item.get("published_at_utc"))
                            for item in linked
                            if item.get("published_at_utc")
                        }
                    )
                ),
                "evidence_id": f"IDX:{action_id}",
            }
        )

    for row in ksei_rows:
        family = classify_ksei_event(str(row.get("event_family_source", "")))
        if family is None:
            continue
        rows.append(
            {
                "source_kind": "KSEI_REGISTERED_SECURITY",
                "ticker": str(row.get("ticker", "")).upper().strip(),
                "event_family": family,
                "candidate_date": row.get("distribution_date")
                or row.get("record_date")
                or row.get("cum_date"),
                "effective_date_status": "UNRESOLVED_KSEI_EVENT_DATE_NOT_PROVEN_MARKET_EFFECTIVE",
                "continuity_status": "PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE",
                "source_action_id": "",
                "source_ref": str(row.get("event_family_source", "")),
                "source_url": row.get("source_url", ""),
                "source_sha256": str(row.get("source_sha256", "")),
                "official_attachment_sha256s": "",
                "official_announcement_refs": "",
                "published_at_utc": "",
                "evidence_id": f"KSEI:{row.get('ticker')}:{row.get('event_family_source')}:{row.get('distribution_date') or row.get('record_date')}",
            }
        )

    evidence = pd.DataFrame(rows)
    if evidence.empty:
        raise RuntimeError("NO_MECHANICAL_CA_EVIDENCE_ROWS")
    evidence["candidate_date"] = pd.to_datetime(
        evidence["candidate_date"], errors="coerce"
    ).dt.normalize()
    if evidence["candidate_date"].isna().any():
        raise RuntimeError("CA_EVIDENCE_INVALID_CANDIDATE_DATE")
    if evidence.duplicated(["evidence_id"]).any():
        raise RuntimeError("CA_EVIDENCE_DUPLICATE_IDENTITY")
    return evidence.sort_values(
        ["ticker", "candidate_date", "event_family", "evidence_id"],
        kind="mergesort",
    ).reset_index(drop=True)


def make_frozen_decisions(
    artifact_root: Path,
    security_master_path: Path,
    repo_root: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    calendar = pd.read_csv(artifact_root / "official_exchange_sessions_1260.csv")
    calendar["date"] = normalize_dates(calendar, "date")
    calendar = calendar.sort_values("date", kind="mergesort").reset_index(drop=True)
    calendar["session_index"] = np.arange(len(calendar), dtype=np.int64)

    panel_path = (
        artifact_root
        / "unknown_state_diagnostic_1260_20260809"
        / "model_safe_signal_research_panel_1260.parquet"
    )
    panel = pd.read_parquet(panel_path)
    panel["ticker"] = normalize_tickers(panel["ticker"])
    panel["date"] = normalize_dates(panel, "date")
    security_master = pd.read_csv(security_master_path)
    features, _ = build_v4_control_feature_table(
        panel, calendar["date"], security_master
    )
    primary = features[features["universe_primary_liquid"].astype(bool)][
        ["ticker", "date"]
    ].copy()
    if primary.duplicated(["ticker", "date"]).any():
        raise RuntimeError("PRIMARY_DECISION_DUPLICATE_IDENTITY")

    validation = pd.read_csv(
        repo_root
        / "docs/artifacts/ranking_v4_3_primary_liquid_support_v1/v4_3_validation_folds.csv"
    )
    validation["date"] = normalize_dates(validation, "date")
    if len(validation) != 600 or validation["date"].duplicated().any():
        raise RuntimeError("FROZEN_600_IDENTITY_INVALID")
    frozen = primary.merge(
        validation[["fold", "validation_position", "session_index", "date"]],
        on="date",
        how="inner",
        validate="many_to_one",
    )
    if frozen["date"].nunique() != 600:
        raise RuntimeError("FROZEN_600_DATE_SUPPORT_MISSING")
    if primary["ticker"].nunique() != 739:
        raise RuntimeError(
            f"V4_DECISION_TICKER_COUNT_CHANGED:{primary['ticker'].nunique()}"
        )
    decision_tickers = sorted(primary["ticker"].unique().tolist())
    frozen = frozen.sort_values(["date", "ticker"], kind="mergesort").reset_index(
        drop=True
    )
    return (
        frozen,
        validation.sort_values("session_index", kind="mergesort"),
        calendar[["session_index", "date"]],
        decision_tickers,
    )


def build_continuity_ledger(
    frozen: pd.DataFrame,
    validation: pd.DataFrame,
    calendar: pd.DataFrame,
    evidence: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    date_to_index = dict(zip(calendar["date"], calendar["session_index"]))
    index_to_date = dict(zip(calendar["session_index"], calendar["date"]))
    all_evidence_by_ticker: dict[str, pd.DataFrame] = {
        ticker: group for ticker, group in evidence.groupby("ticker", sort=False)
    }
    ledger_rows: list[dict[str, Any]] = []
    for ticker, signal_date in frozen[["ticker", "date"]].itertuples(index=False):
        signal_index = int(date_to_index[signal_date])
        for horizon in (5, 10):
            entry_index = signal_index + 1
            terminal_index = signal_index + horizon
            entry_date = index_to_date.get(entry_index)
            terminal_date = index_to_date.get(terminal_index)
            group = all_evidence_by_ticker.get(str(ticker))
            matching: list[dict[str, Any]] = []
            if group is not None and entry_date is not None and terminal_date is not None:
                matching = group[
                    (group["candidate_date"] >= entry_date)
                    & (group["candidate_date"] <= terminal_date)
                ].to_dict("records")
            if matching:
                status = "PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE"
                reason = "EVENT_CANDIDATE_CROSSES_WINDOW_WITHOUT_PROVEN_EFFECTIVE_DATE"
                event_families = sorted({str(row["event_family"]) for row in matching})
                evidence_ids = sorted({str(row["evidence_id"]) for row in matching})
            else:
                status = "PRICE_CONTINUITY_UNRESOLVED_COVERAGE"
                reason = "NO_MARKET_WIDE_NO_EVENT_COVERAGE;ABSENCE_CANNOT_PROVE_NO_EVENT"
                event_families = []
                evidence_ids = []
            ledger_rows.append(
                {
                    "ticker": str(ticker),
                    "signal_date": signal_date,
                    "horizon": horizon,
                    "entry_date": entry_date,
                    "terminal_date": terminal_date,
                    "continuity_status": status,
                    "unresolved_reason": reason,
                    "event_families": "|".join(event_families),
                    "event_evidence_ids": "|".join(evidence_ids),
                    "event_evidence_count": len(matching),
                    "policy_id": "V4_GENERATION_1_OFFICIAL_CA_PRICE_BASIS_V1",
                }
            )
    ledger = pd.DataFrame(ledger_rows)
    coverage_rows: list[dict[str, Any]] = []
    for date, group in ledger.groupby("signal_date", sort=True):
        by_horizon = {int(h): sub for h, sub in group.groupby("horizon")}
        row: dict[str, Any] = {
            "date": date,
            "decision_rows": int(len(by_horizon[5])),
        }
        for horizon in (5, 10):
            sub = by_horizon[horizon]
            resolved = int(sub["continuity_status"].eq("RESOLVED_NO_MECHANICAL_DISCONTINUITY").sum())
            row[f"h{horizon}_continuity_rows"] = resolved
            row[f"h{horizon}_decision_rows"] = int(len(sub))
            row[f"h{horizon}_continuity_rate"] = resolved / len(sub) if len(sub) else np.nan
            row[f"h{horizon}_continuity_gate"] = bool(
                len(sub) > 0 and resolved / len(sub) >= 0.90
            )
        row["consensus_continuity_rows"] = int(
            min(row["h5_continuity_rows"], row["h10_continuity_rows"])
        )
        row["consensus_continuity_rate"] = (
            row["consensus_continuity_rows"] / row["decision_rows"]
            if row["decision_rows"]
            else np.nan
        )
        row["consensus_continuity_gate"] = bool(
            row["decision_rows"] > 0 and row["consensus_continuity_rate"] >= 0.90
        )
        coverage_rows.append(row)
    return ledger, pd.DataFrame(coverage_rows)


def verify_inputs(
    artifact_root: Path,
    security_master: Path,
    repo_root: Path,
    ca_root: Path,
) -> dict[str, str]:
    paths = {
        "calendar": artifact_root / "official_exchange_sessions_1260.csv",
        "panel": artifact_root / "unknown_state_diagnostic_1260_20260809" / "model_safe_signal_research_panel_1260.parquet",
        "security_master": security_master,
        "validation_folds": repo_root / "docs/artifacts/ranking_v4_3_primary_liquid_support_v1/v4_3_validation_folds.csv",
        "ca_manifest": ca_root / "MANIFEST.json",
        "ca_normalized_candidates": ca_root / "normalized_candidates.jsonl",
        "ca_idx_linkages": ca_root / "idx_announcement_linkages.jsonl",
        "ca_cross_source": ca_root / "cross_source_linkage.jsonl",
        "ca_ksei_actions": ca_root / "ksei_security_actions.jsonl",
    }
    actual: dict[str, str] = {}
    for name, path in paths.items():
        if not path.is_file():
            raise RuntimeError(f"REQUIRED_INPUT_MISSING:{name}:{path}")
        if name == "validation_folds":
            digest = sha256_bytes(
                canonical_git_bytes(
                    repo_root,
                    "docs/artifacts/ranking_v4_3_primary_liquid_support_v1/v4_3_validation_folds.csv",
                )
            )
        else:
            digest = sha256(path)
        actual[name] = digest
        if digest != PINNED[name]:
            raise RuntimeError(f"PINNED_INPUT_HASH_MISMATCH:{name}:{digest}")
    return actual


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--ca-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    args.output_dir.mkdir(parents=True)
    input_hashes = verify_inputs(
        args.artifact_root,
        args.security_master,
        args.repo_root,
        args.ca_root,
    )
    frozen, validation, calendar, decision_tickers = make_frozen_decisions(
        args.artifact_root,
        args.security_master,
        args.repo_root,
    )
    evidence = build_event_evidence(args.ca_root)
    ledger, coverage = build_continuity_ledger(
        frozen, validation, calendar, evidence
    )

    event_counts = (
        evidence.groupby(["event_family", "source_kind"], dropna=False)
        .size()
        .reset_index(name="evidence_rows")
    )
    family_inventory = {
        family: int(evidence["event_family"].eq(family).sum())
        for family in REPORT_FAMILIES
    }
    status_counts = Counter(ledger["continuity_status"])
    coverage = coverage.sort_values("date", kind="mergesort").reset_index(drop=True)
    outputs = {
        "event_evidence": args.output_dir / "event_family_evidence.csv",
        "continuity_ledger": args.output_dir / "v4_frozen_continuity_ledger.csv",
        "per_date": args.output_dir / "v4_frozen_continuity_per_date.csv",
        "event_counts": args.output_dir / "event_family_counts.csv",
    }
    evidence.to_csv(outputs["event_evidence"], index=False, lineterminator="\n")
    ledger.to_csv(outputs["continuity_ledger"], index=False, lineterminator="\n")
    coverage.to_csv(outputs["per_date"], index=False, lineterminator="\n")
    event_counts.to_csv(outputs["event_counts"], index=False, lineterminator="\n")

    summary = {
        "schema_version": "v4_corporate_action_price_basis_continuity_gate_v1",
        "verdict": "GO" if bool(coverage["consensus_continuity_gate"].all()) else "BLOCKED",
        "outcome_blind": True,
        "provider_calls": False,
        "target_or_rank_materialized": False,
        "model_fit": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "parent_freeze_commit": "b536c832730bd0c5e2dd6952b44cf9b11b4573f9",
        "decision_tickers": int(len(decision_tickers)),
        "decision_ticker_universe_sha256": sha256_bytes(
            ("\n".join(decision_tickers) + "\n").encode("utf-8")
        ),
        "frozen_decision_tickers": int(frozen["ticker"].nunique()),
        "frozen_validation_dates": int(validation["date"].nunique()),
        "frozen_decision_rows": int(len(frozen)),
        "event_evidence_rows": int(len(evidence)),
        "event_family_inventory": family_inventory,
        "event_family_counts": event_counts.to_dict(orient="records"),
        "continuity_status_counts": dict(sorted(status_counts.items())),
        "unresolved_reason_counts": dict(
            sorted(Counter(ledger["unresolved_reason"]).items())
        ),
        "per_date": {
            "h5_gate_dates": int(coverage["h5_continuity_gate"].sum()),
            "h10_gate_dates": int(coverage["h10_continuity_gate"].sum()),
            "consensus_gate_dates": int(coverage["consensus_continuity_gate"].sum()),
            "h5_min_rate": float(coverage["h5_continuity_rate"].min()),
            "h10_min_rate": float(coverage["h10_continuity_rate"].min()),
            "consensus_min_rate": float(coverage["consensus_continuity_rate"].min()),
        },
        "frozen_gate": {
            "required_rate": 0.90,
            "h5_pass": bool(coverage["h5_continuity_gate"].all()),
            "h10_pass": bool(coverage["h10_continuity_gate"].all()),
            "consensus_pass": bool(coverage["consensus_continuity_gate"].all()),
        },
        "policy": {
            "cash_dividend_is_not_blocker": True,
            "tanggal_pencatatan_is_not_generic_effective_date": True,
            "missing_evidence_does_not_prove_no_event": True,
            "only_passing_state": "RESOLVED_NO_MECHANICAL_DISCONTINUITY",
        },
        "input_hashes": input_hashes,
        "output_hashes": {},
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary["output_hashes"] = {
        name: sha256(path) for name, path in outputs.items()
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_corporate_action_price_basis_continuity_manifest_v1",
        "status": summary["verdict"],
        "outcome_blind": True,
        "input_hashes": input_hashes,
        "outputs": {name: sha256(path) for name, path in outputs.items()},
        "summary_sha256": sha256(summary_path),
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "manifest_sha256": sha256(manifest_path)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
