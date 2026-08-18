"""One-shot, outcome-blind remediation for six material V4 CA names.

The runner:
- retries official KSEI static history for AVIA/SMAR and refreshes MEGA/SCMA;
- probes FREN and ADRO with the identical strict KSEI parser;
- adds FREN back to the frozen validation support instead of silently omitting it;
- pins issuer-official FREN merger and MEGA bonus-share boundaries;
- removes SCMA's ticker-wide conflict only after proving its sole frozen prior
  candidate is halo-only, after every target terminal date;
- leaves ADRO fail-closed unless an exact official regular-market transition is
  already present in the accepted schedule evidence;
- replays the unchanged 90% continuity gate with zero model/target/outcome use.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = Path(__file__).resolve().parent
for value in (SRC_ROOT, SCRIPTS_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import pandas as pd
import requests

import run_v4_ca_event_window_support as frozen
import run_v4_ca_coverage_gap_continuity_replay as coverage_replay
import run_v4_ca_targeted_schedule_continuity_replay as targeted_replay
import run_v4_ca_icbp_single_ticker_coverage_remediation as icbp_cov
import run_v4_ca_icbp_single_ticker_continuity_replay as icbp_replay
import run_v4_ksei_coverage_gap_remediation as gap_runner

from idx_trade.ranking_v4_3_preregistration import build_primary_liquid_state
from idx_trade.v4_ca_event_windows import EventSemantic, event_identity, source_dates
from idx_trade.v4_ca_material_six_remediation import (
    EXPECTED_AFTER_AVIA_SMAR_UNRESOLVED,
    FREN_EFFECTIVE_DATE,
    FREN_OFFICIAL_DISCLOSURE_URL,
    KSEI_RETRY_TICKERS,
    MATERIAL_SIX,
    MEGA_OFFICIAL_BONUS_URL,
    new_fren_coverage_row,
    normalize_parent_coverage,
    normalize_ticker,
    parsed_history_stats,
    refreshed_coverage_row,
    replace_history_ticker,
    synthetic_fren_event,
    synthetic_mega_event,
    validate_scma_halo_only,
    verify_fren_official_disclosure,
    verify_mega_official_bonus,
)
from idx_trade.v4_ca_targeted_schedule_evidence import classify_event_with_targeted_evidence
from idx_trade.v4_ksei_coverage_gap import parse_bool_series, read_jsonl, sha256_file, write_jsonl


DEFAULT_CONFIG = Path("config/v4_ksei_coverage_gap_remediation_v1.json")
EXPECTED_FREN_VALIDATION_SIGNAL_ROWS = 302
EXPECTED_BASE_TICKERS = 610
EXPECTED_EXPANDED_TICKERS = 611


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--continuity-ledger", type=Path, required=True)
    parser.add_argument("--prior-event-evidence", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--icbp-remediation-root", type=Path, required=True)
    parser.add_argument("--residual-document-root", type=Path, required=True)
    parser.add_argument("--targeted-evidence-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def download_official(url: str, path: Path) -> tuple[bytes, dict[str, Any]]:
    headers = {"User-Agent": "Mozilla/5.0 IDX-Trade-V4-MaterialSix/1.0"}
    response = requests.get(url, headers=headers, timeout=45, allow_redirects=True)
    payload = bytes(response.content or b"")
    record = {
        "url": url,
        "final_url": str(response.url),
        "status_code": int(response.status_code),
        "bytes": len(payload),
    }
    if response.status_code != 200 or not payload:
        raise RuntimeError(f"OFFICIAL_DOCUMENT_DOWNLOAD_FAILED:{url}:{record}")
    path.write_bytes(payload)
    record["sha256"] = sha256_file(path)
    return payload, record


def update_existing_coverage(
    coverage: pd.DataFrame, replacement: dict[str, Any], ticker: str
) -> pd.DataFrame:
    target = normalize_ticker(ticker)
    result = coverage.copy()
    mask = result["ticker"].eq(target)
    if int(mask.sum()) != 1:
        raise RuntimeError(f"MATERIAL_SIX_EXISTING_COVERAGE_IDENTITY:{target}:{int(mask.sum())}")
    for column in result.columns:
        if column in replacement:
            result.loc[mask, column] = replacement[column]
    return result


def build_fren_ledger(
    *, artifact_root: Path, calendar: pd.DataFrame, base_ledger: pd.DataFrame
) -> pd.DataFrame:
    panel_path = (
        artifact_root
        / "unknown_state_diagnostic_1260_20260809"
        / "model_safe_signal_research_panel_1260.parquet"
    )
    if not panel_path.is_file():
        raise RuntimeError(f"FREN_SIGNAL_PANEL_MISSING:{panel_path}")
    panel = pd.read_parquet(panel_path)
    panel["ticker"] = panel["ticker"].map(normalize_ticker)
    panel["date"] = pd.to_datetime(panel["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    primary = build_primary_liquid_state(panel, calendar["date"])
    validation_dates = set(base_ledger["signal_date"])
    fren = primary[
        primary["ticker"].eq("FREN")
        & primary["universe_primary_liquid"].astype(bool)
        & primary["date"].isin(validation_dates)
    ].copy()
    if fren["date"].nunique() != EXPECTED_FREN_VALIDATION_SIGNAL_ROWS:
        raise RuntimeError(
            f"FREN_VALIDATION_PRIMARY_ROWS_CHANGED:{fren['date'].nunique()}"
        )
    date_to_index = {date: idx for idx, date in enumerate(calendar["date"])}
    index_to_date = {idx: date for date, idx in date_to_index.items()}
    rows: list[dict[str, Any]] = []
    for signal_date in sorted(fren["date"].unique()):
        signal = pd.Timestamp(signal_date)
        signal_idx = int(date_to_index[signal])
        for horizon in (5, 10):
            entry = index_to_date.get(signal_idx + 1)
            terminal = index_to_date.get(signal_idx + horizon)
            if entry is None or terminal is None:
                raise RuntimeError("FREN_VALIDATION_FUTURE_SESSION_MISSING")
            row = {column: "" for column in base_ledger.columns}
            row.update(
                {
                    "ticker": "FREN",
                    "signal_date": signal,
                    "horizon": horizon,
                    "entry_date": entry,
                    "terminal_date": terminal,
                    "continuity_status": "PRICE_CONTINUITY_UNRESOLVED_COVERAGE",
                }
            )
            if "unresolved_reason" in row:
                row["unresolved_reason"] = "FREN_PREVIOUSLY_OMITTED_FROM_CA_SUPPORT"
            if "continuity_reason" in row:
                row["continuity_reason"] = "FREN_PREVIOUSLY_OMITTED_FROM_CA_SUPPORT"
            rows.append(row)
    result = pd.DataFrame(rows, columns=base_ledger.columns)
    if len(result) != EXPECTED_FREN_VALIDATION_SIGNAL_ROWS * 2:
        raise RuntimeError("FREN_LEDGER_ROW_COUNT_CHANGED")
    return result


def material_six_classifier(fren_source_sha: str):
    def classify(
        row, *, official_sessions, schedule_evidence=()
    ) -> EventSemantic:
        base = classify_event_with_targeted_evidence(
            row,
            official_sessions=official_sessions,
            schedule_evidence=schedule_evidence,
        )
        if normalize_ticker(row.get("ticker")) != "FREN":
            return base
        dates = source_dates(row)
        close_to_merger = any(
            pd.Timestamp("2025-04-15") <= value <= pd.Timestamp("2025-04-17")
            for value in dates
        )
        source_type = str(row.get("event_family_source") or "").casefold()
        mechanical_source = any(
            token in source_type
            for token in ("conversion", "split", "merger", "restructur", "amort")
        )
        if not (close_to_merger and mechanical_source):
            return base
        exact = synthetic_fren_event(fren_source_sha)
        return EventSemantic(
            event_id=event_identity(row),
            ticker="FREN",
            source_type=str(row.get("event_family_source") or ""),
            family=exact.family,
            semantic_class="EXACT_TRANSITION",
            transition_date=FREN_EFFECTIVE_DATE,
            transition_source=exact.transition_source,
            reason=exact.reason,
            source_dates=dates,
        )

    return classify


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    args.output_dir.mkdir(parents=True)
    raw_ksei = args.output_dir / "raw" / "ksei"
    raw_docs = args.output_dir / "raw" / "official_docs"
    raw_ksei.mkdir(parents=True)
    raw_docs.mkdir(parents=True)

    parent_summary, parent_manifest_sha = icbp_replay.verify_icbp_root(
        args.icbp_remediation_root
    )
    config = icbp_cov.validate_provider_config(args.config)
    provider = config["provider"]
    parent_coverage = normalize_parent_coverage(
        pd.read_csv(args.icbp_remediation_root / "ticker_coverage.csv")
    )
    parent_history = read_jsonl(args.icbp_remediation_root / "ksei_ca_history.jsonl")

    merged_coverage = parent_coverage.copy()
    merged_history = list(parent_history)
    request_records: list[dict[str, Any]] = []
    retry_results: dict[str, Any] = {}

    for ticker in KSEI_RETRY_TICKERS:
        ticker_raw = raw_ksei / ticker
        ticker_raw.mkdir()
        success, records, parsed_rows = gap_runner.recover_ticker(
            ticker=ticker, provider=provider, raw_root=ticker_raw
        )
        request_records.extend(records)
        security_records = [r for r in records if r.get("request_kind") == "SECURITY_HISTORY"]
        item: dict[str, Any] = {
            "success": success is not None,
            "security_attempts": len(security_records),
            "request_count": len(records),
            "failure_class": "" if success is not None else gap_runner.failure_class(records),
        }
        if success is not None:
            stats = parsed_history_stats(parsed_rows, ticker)
            item["source_sha256"] = str(success.get("sha256") or "")
            item["parsed_history"] = stats
            if ticker in {"AVIA", "SMAR", "MEGA", "SCMA"}:
                parent_row = merged_coverage[merged_coverage["ticker"].eq(ticker)].iloc[0].to_dict()
                replacement = refreshed_coverage_row(
                    parent_row,
                    ticker=ticker,
                    success_record=success,
                    security_attempt_count=len(security_records),
                    stats=stats,
                )
                merged_coverage = update_existing_coverage(merged_coverage, replacement, ticker)
                merged_history = replace_history_ticker(merged_history, parsed_rows, ticker)
            elif ticker == "FREN":
                fren_row = new_fren_coverage_row(
                    merged_coverage.columns,
                    success_record=success,
                    security_attempt_count=len(security_records),
                    stats=stats,
                    failure_reason="",
                )
                merged_coverage = pd.concat(
                    [merged_coverage, pd.DataFrame([fren_row], columns=merged_coverage.columns)],
                    ignore_index=True,
                )
                merged_history = replace_history_ticker(merged_history, parsed_rows, "FREN")
            # ADRO is diagnostic-only here. Replacing its frozen history would
            # change the event identity while no exact ex-date has been proven.
        elif ticker == "FREN":
            fren_row = new_fren_coverage_row(
                merged_coverage.columns,
                success_record=None,
                security_attempt_count=len(security_records),
                stats=None,
                failure_reason=item["failure_class"],
            )
            merged_coverage = pd.concat(
                [merged_coverage, pd.DataFrame([fren_row], columns=merged_coverage.columns)],
                ignore_index=True,
            )
        retry_results[ticker] = item

    merged_coverage["ticker"] = merged_coverage["ticker"].map(normalize_ticker)
    if merged_coverage["coverage_certified"].dtype != bool:
        merged_coverage["coverage_certified"] = parse_bool_series(
            merged_coverage["coverage_certified"], label="material_six_merged_coverage"
        )
    if len(merged_coverage) != EXPECTED_EXPANDED_TICKERS or merged_coverage["ticker"].nunique() != EXPECTED_EXPANDED_TICKERS:
        raise RuntimeError("MATERIAL_SIX_EXPANDED_COVERAGE_NOT_611")
    unresolved_610 = set(
        merged_coverage.loc[
            (~merged_coverage["coverage_certified"]) & (~merged_coverage["ticker"].eq("FREN")),
            "ticker",
        ]
    )
    if not unresolved_610.issubset(EXPECTED_AFTER_AVIA_SMAR_UNRESOLVED):
        raise RuntimeError(f"MATERIAL_SIX_UNEXPECTED_610_UNRESOLVED:{sorted(unresolved_610)}")

    fren_pdf, fren_download = download_official(
        FREN_OFFICIAL_DISCLOSURE_URL, raw_docs / "fren_merger_effective_2025-04-16.pdf"
    )
    mega_pdf, mega_download = download_official(
        MEGA_OFFICIAL_BONUS_URL, raw_docs / "mega_bonus_shares_2026.pdf"
    )
    fren_official = verify_fren_official_disclosure(fren_pdf)
    mega_official = verify_mega_official_bonus(mega_pdf)

    base_ledger = pd.read_csv(args.continuity_ledger)
    base_ledger["ticker"] = base_ledger["ticker"].map(normalize_ticker)
    for column in ("signal_date", "entry_date", "terminal_date"):
        base_ledger[column] = pd.to_datetime(base_ledger[column], errors="coerce").dt.tz_localize(None).dt.normalize()
    if base_ledger["ticker"].nunique() != EXPECTED_BASE_TICKERS:
        raise RuntimeError("MATERIAL_SIX_BASE_LEDGER_NOT_610")

    calendar = pd.read_csv(args.official_calendar)
    calendar["date"] = pd.to_datetime(calendar["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    calendar = calendar.sort_values("date", kind="mergesort").reset_index(drop=True)
    fren_ledger = build_fren_ledger(
        artifact_root=args.artifact_root, calendar=calendar, base_ledger=base_ledger
    )
    expanded_ledger = pd.concat([base_ledger, fren_ledger], ignore_index=True, sort=False)
    if expanded_ledger.duplicated(["ticker", "signal_date", "horizon"]).any():
        raise RuntimeError("MATERIAL_SIX_EXPANDED_LEDGER_DUPLICATE")

    prior = pd.read_csv(args.prior_event_evidence)
    scma_halo = validate_scma_halo_only(
        prior, max_terminal=pd.Timestamp(expanded_ledger["terminal_date"].max())
    )

    merged_root = args.output_dir / "merged_ksei_611"
    merged_root.mkdir()
    coverage_path = merged_root / "ticker_coverage.csv"
    history_path = merged_root / "ksei_ca_history.jsonl"
    merged_coverage.sort_values("ticker", kind="mergesort").to_csv(
        coverage_path, index=False, lineterminator="\n"
    )
    write_jsonl(history_path, merged_history)
    merged_ksei_summary = {
        "schema_version": "v4_ca_material_six_ksei_611_v1",
        "status": "COMPLETE",
        "outcome_blind": True,
        "provider_calls": True,
        "ticker_count": 611,
        "certified_tickers": int(merged_coverage["coverage_certified"].sum()),
        "unresolved_tickers": sorted(
            merged_coverage.loc[~merged_coverage["coverage_certified"], "ticker"].tolist()
        ),
        "parent_icbp_manifest_sha256": parent_manifest_sha,
        "output_hashes": {
            "ticker_coverage": sha256_file(coverage_path),
            "ksei_ca_history": sha256_file(history_path),
        },
    }
    ksei_summary_path = merged_root / "summary.json"
    ksei_summary_path.write_text(
        json.dumps(merged_ksei_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    ksei_manifest = {
        "schema_version": "v4_ca_material_six_ksei_611_manifest_v1",
        "status": "COMPLETE",
        "outcome_blind": True,
        "summary_sha256": sha256_file(ksei_summary_path),
        "output_hashes": merged_ksei_summary["output_hashes"],
    }
    ksei_manifest_path = merged_root / "MANIFEST.json"
    ksei_manifest_path.write_text(
        json.dumps(ksei_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    requests_path = args.output_dir / "ksei_request_delta.jsonl"
    write_jsonl(requests_path, request_records)
    expanded_path = args.output_dir / "expanded_continuity_ledger_611.csv"
    expanded_ledger.to_csv(expanded_path, index=False, lineterminator="\n")

    residual_path, residual_manifest_sha = coverage_replay.verify_document_root(
        args.residual_document_root
    )
    targeted_summary, targeted_path, targeted_manifest_sha = targeted_replay.verify_targeted_root(
        args.targeted_evidence_root
    )
    residual = pd.read_csv(residual_path, dtype=str, keep_default_na=False)
    targeted = pd.read_csv(targeted_path, dtype=str, keep_default_na=False)
    schedule = pd.concat([residual, targeted], ignore_index=True, sort=False).fillna("")
    if schedule.duplicated().any():
        schedule = schedule.drop_duplicates().reset_index(drop=True)
    schedule_path = args.output_dir / "merged_schedule_evidence.csv"
    schedule.to_csv(schedule_path, index=False, lineterminator="\n")

    frozen.PINNED = dict(frozen.PINNED)
    frozen.PINNED["continuity_ledger"] = sha256_file(expanded_path)
    frozen.PINNED["ksei_manifest"] = sha256_file(ksei_manifest_path)
    frozen.PINNED["ksei_summary"] = sha256_file(ksei_summary_path)
    frozen.PINNED["ksei_coverage"] = sha256_file(coverage_path)
    frozen.PINNED["ksei_history"] = sha256_file(history_path)
    frozen.EXPECTED_TICKERS = EXPECTED_EXPANDED_TICKERS
    frozen.EXPECTED_ROWS = len(expanded_ledger)
    frozen.classify_event = material_six_classifier(fren_official["source_sha256"])

    original_prior_candidate_tickers = frozen.prior_candidate_tickers
    original_build_events = frozen.build_events

    def prior_candidate_tickers_material_six(prior_frame, *, period_start, period_end):
        result = set(
            original_prior_candidate_tickers(
                prior_frame, period_start=period_start, period_end=period_end
            )
        )
        # Narrow fix only: SCMA action 82840 is 2026-08-10, after every frozen
        # target terminal. The +/-60d halo is acquisition scope, not a reason to
        # poison every SCMA target window.
        if "SCMA" in result:
            validate_scma_halo_only(prior_frame, max_terminal=pd.Timestamp(period_end))
            result.remove("SCMA")
        return result

    def build_events_material_six(*inner_args, **inner_kwargs):
        by_ticker, audit = original_build_events(*inner_args, **inner_kwargs)
        additions: list[tuple[EventSemantic, str]] = []
        additions.append((synthetic_mega_event(mega_official["source_sha256"]), "MEGA_ISSUER_OFFICIAL"))
        additions.append((synthetic_fren_event(fren_official["source_sha256"]), "FREN_ISSUER_OFFICIAL"))
        rows = audit.to_dict("records")
        for event, source_marker in additions:
            by_ticker.setdefault(event.ticker, []).append(event)
            rows.append(
                {
                    "event_id": event.event_id,
                    "ticker": event.ticker,
                    "source_type": event.source_type,
                    "family": event.family,
                    "semantic_class": event.semantic_class,
                    "transition_date": event.transition_date.date().isoformat(),
                    "transition_source": event.transition_source or "",
                    "reason": event.reason,
                    "source_dates": "|".join(v.date().isoformat() for v in event.source_dates),
                    "material_six_source_marker": source_marker,
                }
            )
        new_audit = pd.DataFrame(rows).fillna("")
        return by_ticker, new_audit.sort_values(
            ["ticker", "source_dates", "source_type", "event_id"], kind="mergesort"
        ).reset_index(drop=True)

    frozen.prior_candidate_tickers = prior_candidate_tickers_material_six
    frozen.build_events = build_events_material_six

    final_root = args.output_dir / "final_continuity_611"
    original_argv = list(sys.argv)
    try:
        sys.argv = [
            original_argv[0],
            "--continuity-ledger", str(expanded_path),
            "--prior-event-evidence", str(args.prior_event_evidence),
            "--official-calendar", str(args.official_calendar),
            "--ksei-census-root", str(merged_root),
            "--schedule-evidence", str(schedule_path),
            "--output-dir", str(final_root),
        ]
        replay_result = frozen.main()
    finally:
        sys.argv = original_argv

    final_summary = json.loads((final_root / "summary.json").read_text(encoding="utf-8"))
    final_window = pd.read_csv(final_root / "v4_event_window_continuity_ledger.csv")
    final_window["ticker"] = final_window["ticker"].map(normalize_ticker)
    final_event = pd.read_csv(final_root / "event_semantics_audit.csv", dtype=str, keep_default_na=False)

    coverage_map = dict(zip(merged_coverage["ticker"], merged_coverage["coverage_certified"]))
    material_results: dict[str, Any] = {}
    for ticker in MATERIAL_SIX:
        rows = final_window[final_window["ticker"].eq(ticker)]
        resolved = int(rows["continuity_status"].eq("RESOLVED_NO_MECHANICAL_DISCONTINUITY").sum())
        reasons = sorted(set(rows.loc[~rows["continuity_status"].eq("RESOLVED_NO_MECHANICAL_DISCONTINUITY"), "continuity_reason"].astype(str)))
        item = {
            "coverage_certified": bool(coverage_map.get(ticker, False)),
            "window_rows": int(len(rows)),
            "resolved_window_rows": resolved,
            "resolved_window_rate": float(resolved / len(rows)) if len(rows) else None,
            "unresolved_reasons": reasons,
            "relevant_event_semantics": final_event[final_event["ticker"].eq(ticker)].to_dict("records"),
        }
        if ticker == "FREN":
            item["verdict"] = (
                "ADDRESSED_EXACT_MERGER_BOUNDARY_NO_EXCL_STITCHING"
                if item["coverage_certified"]
                else "UNRESOLVED_COMPLETE_KSEI_HISTORY_UNAVAILABLE"
            )
        elif ticker == "ADRO":
            item["verdict"] = "UNRESOLVED_PRIMARY_REGULAR_MARKET_EX_DATE_NOT_PROVEN"
        elif ticker == "MEGA":
            item["verdict"] = "RESOLVED_2026_EX_BONUS_2026-04-10"
        elif ticker == "SCMA":
            item["verdict"] = "RESOLVED_2026-08-10_CANDIDATE_HALO_ONLY_AFTER_FROZEN_TARGET_PERIOD"
        else:
            item["verdict"] = (
                "STRICT_KSEI_COVERAGE_RECOVERED"
                if item["coverage_certified"]
                else "STRICT_KSEI_COVERAGE_RETRY_FAILED_CLOSED"
            )
        material_results[ticker] = item

    summary = {
        "schema_version": "v4_ca_material_six_remediation_v1",
        "status": "V4_CA_MATERIAL_SIX_REMEDIATION_COMPLETE",
        "outcome_blind": True,
        "provider_calls": True,
        "provider_calls_in_final_replay": False,
        "model_fit": False,
        "performance_computed": False,
        "target_or_rank_materialized": False,
        "protected_forward_accessed": False,
        "material_six": list(MATERIAL_SIX),
        "ksei_retry_results": retry_results,
        "fren_official_evidence": fren_official,
        "mega_official_evidence": mega_official,
        "scma_halo_adjudication": scma_halo,
        "adro_policy": {
            "record_date_is_not_ex_date": True,
            "distribution_date_is_not_ex_date": True,
            "inferred_2024-11-28_forbidden": True,
            "verdict": "UNRESOLVED_PRIMARY_REGULAR_MARKET_EX_DATE_NOT_PROVEN",
        },
        "expanded_support": {
            "tickers": int(merged_coverage["ticker"].nunique()),
            "fren_validation_signal_rows": EXPECTED_FREN_VALIDATION_SIGNAL_ROWS,
            "fren_added_horizon_rows": int(len(fren_ledger)),
            "certified_tickers": int(merged_coverage["coverage_certified"].sum()),
            "unresolved_tickers": sorted(
                merged_coverage.loc[~merged_coverage["coverage_certified"], "ticker"].tolist()
            ),
        },
        "material_results": material_results,
        "final_continuity": {
            "verdict": final_summary.get("verdict"),
            "corporate_action_continuity_certified": final_summary.get("corporate_action_continuity_certified"),
            "cross_source_conflict_tickers": final_summary.get("cross_source_conflict_tickers"),
            "schedule_required_events": final_summary.get("schedule_required_events"),
            "schedule_required_tickers": final_summary.get("schedule_required_tickers"),
            "per_date": final_summary.get("per_date"),
        },
        "input_hashes": {
            "parent_icbp_manifest": parent_manifest_sha,
            "continuity_ledger": sha256_file(args.continuity_ledger),
            "prior_event_evidence": sha256_file(args.prior_event_evidence),
            "official_calendar": sha256_file(args.official_calendar),
            "residual_document_manifest": residual_manifest_sha,
            "targeted_evidence_manifest": targeted_manifest_sha,
        },
        "output_hashes": {},
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary["output_hashes"] = {
        "merged_coverage": sha256_file(coverage_path),
        "merged_history": sha256_file(history_path),
        "expanded_ledger": sha256_file(expanded_path),
        "request_delta": sha256_file(requests_path),
        "final_continuity_summary": sha256_file(final_root / "summary.json"),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_ca_material_six_remediation_manifest_v1",
        "status": summary["status"],
        "outcome_blind": True,
        "summary_sha256": sha256_file(summary_path),
        "output_hashes": summary["output_hashes"],
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**summary, "manifest_sha256": sha256_file(manifest_path)}, indent=2, sort_keys=True))
    return int(replay_result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
