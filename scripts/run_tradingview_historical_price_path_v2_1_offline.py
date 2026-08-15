"""Run the zero-network TradingView historical price-path V2.1 remediation audit."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any

import pandas as pd

from idx_trade.tradingview_price_path_v2_1 import (
    STATUS_AMBIGUOUS,
    STATUS_MAPPED,
    STATUS_OUTSIDE,
    artifact_manifest,
    boundary_report,
    build_expected_state_reconciliation,
    control_request_fixture,
    fidelity_report_v2_1,
    identity_audit_summary,
    load_identity_intervals,
    map_identity_frame,
    mismatch_top20,
    sha256_file,
    theoretical_ceilings,
)


EXPECTED_PANEL_SHA = "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-root", type=Path, default=Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_20260814"))
    parser.add_argument("--security-master", type=Path, default=Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\listings\security_master.csv"))
    parser.add_argument("--scope-exclusions", type=Path, default=Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\listings\security_scope_exclusions.csv"))
    parser.add_argument("--curated-identities", type=Path, default=Path(r"config\curated_security_identities.csv"))
    parser.add_argument("--config", type=Path, default=Path(r"config\tradingview_historical_price_path_v2.json"))
    parser.add_argument("--canonical-panel", type=Path, default=Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet"))
    parser.add_argument("--artifact-root", type=Path, default=Path(r"D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_1_remediation_20260816"))
    return parser.parse_args()


def _yearly_coverage(states: pd.DataFrame) -> dict[str, Any]:
    states = states.copy()
    states["year"] = states["session_date"].str[:4]
    result: dict[str, Any] = {}
    for year, group in states.groupby("year", sort=True):
        active = group[group["activity_state"].eq("ACTIVE")]
        covered = active[active["reconciliation_status"].eq("COVERED_ACTIVE")]
        result[str(year)] = {
            "active_sessions": int(len(active)),
            "covered_active_sessions": int(len(covered)),
            "true_provider_misses": int(len(active) - len(covered)),
            "coverage": float(len(covered) / len(active)) if len(active) else 0.0,
        }
    return result


def main() -> int:
    args = _args()
    legacy = args.legacy_root
    out = args.artifact_root
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty artifact root: {out}")
    out.mkdir(parents=True, exist_ok=True)

    config = json.loads(args.config.read_text(encoding="utf-8"))
    panel_sha_before = sha256_file(args.canonical_panel)
    if panel_sha_before != EXPECTED_PANEL_SHA:
        raise SystemExit(f"canonical panel SHA mismatch: {panel_sha_before}")

    paths = {
        "config": args.config,
        "canonical_panel": args.canonical_panel,
        "security_master": args.security_master,
        "scope_exclusions": args.scope_exclusions,
        "curated_identities": args.curated_identities,
        "official_sessions": legacy / "official_sessions.csv",
        "universe": legacy / "universe.csv",
        "expected_ticker_sessions": legacy / "expected_ticker_sessions.csv",
        "activity_reconciliation": legacy / "activity_reconciliation.csv",
        "request_manifest": legacy / "request_manifest.csv",
        "request_diagnostics": legacy / "normalized" / "request_diagnostics.csv",
        "intraday_bars": legacy / "normalized" / "intraday_bars.csv",
        "fidelity_rows": legacy / "normalized" / "fidelity_rows.csv",
        "corporate_action_events": legacy / "corporate_action_events.csv",
    }
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise SystemExit(f"missing immutable input artifacts: {missing}")
    input_hashes = {name: sha256_file(path) for name, path in paths.items()}

    # Freeze the new contract before any optional future network stage.  This
    # run intentionally never starts that stage.
    prereg = {
        "schema": "idx-trade/tradingview-historical-price-path-v2-1-preregistration",
        "created_before_network": True,
        "network_started": False,
        "network_calls": 0,
        "lineage": {
            "failed_v2_head": "f6716bb861eee396a8b57c42b207af31b4565db7",
            "prior_open_price_path_remediation": "97124d017de9533e1c84d7f84eab4b22edbfbda4",
            "activity_resolution": "c943a76fd56872d981a87519c2eb7072c413322c",
            "mathieu_adapter_commit": "5baea86c8c7e576f13464919c86c3b4c4b0ecf4c",
        },
        "input_paths": {name: str(path) for name, path in paths.items()},
        "input_hashes": input_hashes,
        "frozen_gate_contract": config["gates"],
        "future_depth_preflight": {
            "authorized_only_if_offline_gates_reachable": True,
            "max_calls": 5,
            "tickers": ["BBCA", "BBRI", "BMRI", "TLKM", "ASII"],
            "server": "prodata",
            "symbol_template": "IDX:<ticker>",
            "timeframe": "60",
            "session": "regular",
            "adjustment": "none",
            "initial_range": 10000,
            "fetch_more_steps": 0,
            "required_start": config["window"]["start"],
        },
        "boundaries": {
            "no_full_v2_rerun": True,
            "no_panel_write": True,
            "no_model": True,
            "no_path_risk": True,
            "no_o2_or_outcomes": True,
            "no_provider_search": True,
        },
    }
    _write_json(out / "preregistration.json", prereg)

    official = pd.read_csv(paths["official_sessions"])
    expected = pd.read_csv(paths["expected_ticker_sessions"], dtype={"ticker": str, "security_id": str})
    activity = pd.read_csv(paths["activity_reconciliation"], dtype={"ticker": str, "session_date": str})
    requests = pd.read_csv(paths["request_manifest"], dtype={"ticker": str})
    diagnostics = pd.read_csv(paths["request_diagnostics"], dtype={"ticker": str})
    bars = pd.read_csv(paths["intraday_bars"], dtype={"ticker": str, "security_id": str, "session_date": str})
    bars["session_admissible"] = bars["session_admissible"].astype(str).str.lower().eq("true")
    fidelity_rows = pd.read_csv(paths["fidelity_rows"], dtype={"ticker": str, "session_date": str})
    events = pd.read_csv(paths["corporate_action_events"], dtype={"ticker": str})
    intervals = load_identity_intervals(args.security_master, args.curated_identities, args.scope_exclusions)

    mapped_expected = map_identity_frame(expected, intervals)
    mapped_bars = map_identity_frame(bars, intervals)
    identity_summary = identity_audit_summary(expected, mapped_bars, intervals)
    _write_json(out / "identity_audit_summary.json", identity_summary)
    _write_csv(out / "identity_problem_rows.csv", mapped_expected[~mapped_expected["identity_status"].eq(STATUS_MAPPED)])
    _write_csv(out / "provider_bar_identity_problem_rows.csv", mapped_bars[~mapped_bars["identity_status"].eq(STATUS_MAPPED)])

    reconciliation = build_expected_state_reconciliation(expected, activity, mapped_bars)
    state_counts = reconciliation["reconciliation_status"].value_counts().sort_index().to_dict()
    activity_counts = activity["activity_state"].value_counts().sort_index().to_dict()
    _write_csv(out / "expected_state_reconciliation.csv", reconciliation)
    _write_json(out / "expected_state_summary.json", {"activity_state_counts": {str(k): int(v) for k, v in activity_counts.items()}, "reconciliation_status_counts": {str(k): int(v) for k, v in state_counts.items()}, "yearly_coverage": _yearly_coverage(reconciliation.merge(activity[["ticker", "session_date", "activity_state"]], on=["ticker", "session_date"], suffixes=("", "_activity")))})

    fidelity_checked, fidelity = fidelity_report_v2_1(fidelity_rows, events, official)
    _write_csv(out / "fidelity_rows_v2_1.csv", fidelity_checked)
    _write_json(out / "fidelity_summary_v2_1.json", fidelity)
    _write_csv(out / "fidelity_mismatch_top20_2022_2026.csv", mismatch_top20(fidelity_checked))
    quarantine_comparison = fidelity_checked[["ticker", "session_date", "old_calendar_quarantined", "calendar_radius_quarantined", "session_index_quarantined"]].copy()
    _write_csv(out / "corporate_action_quarantine_comparison.csv", quarantine_comparison)

    boundaries = boundary_report(requests, bars, diagnostics)
    _write_csv(out / "boundary_report.csv", boundaries)
    boundary_summary = {
        "requests": int(len(boundaries)),
        "required_start_reached": int(boundaries["required_start_reached"].sum()),
        "boundary_complete": int(boundaries["boundary_complete"].sum()),
        "boundary_incomplete": int((boundaries["boundary_status"] == "BOUNDARY_INCOMPLETE").sum()),
        "completion_reason_counts": {str(k): int(v) for k, v in diagnostics["completion_reason"].fillna("UNSET").value_counts().items()},
        "earliest_observed_session_by_request_start_year": {
            str(year): sorted(boundaries.loc[boundaries["required_start"].str[:4].eq(str(year)), "observed_first_session"].dropna().unique().tolist())[:5]
            for year in sorted(boundaries["required_start"].str[:4].unique())
        },
    }
    _write_json(out / "boundary_summary.json", boundary_summary)

    error_rows = diagnostics[diagnostics["status"].astype(str).str.contains("SYMBOL_ERROR|invalid symbol", case=False, na=False) | diagnostics["errors"].astype(str).str.contains("invalid symbol", case=False, na=False)]
    error_tickers = sorted(error_rows["ticker"].astype(str).str.upper().unique().tolist())
    identity_resolved = intervals.groupby("ticker").size()
    identity_resolved_tickers = identity_resolved[identity_resolved.eq(1)].index.tolist()
    ceilings = theoretical_ceilings(activity, diagnostics, reconciliation, error_tickers, identity_resolved_tickers)
    _write_json(out / "theoretical_ceilings.json", ceilings)

    controls = control_request_fixture({"window": {"start": config["window"]["start"], "end": config["window"]["end"]}, "acquisition": config["acquisition"]})
    _write_json(out / "v2_1_control_request_fixture.json", controls)

    yearly = _yearly_coverage(reconciliation.merge(activity[["ticker", "session_date", "activity_state"]], on=["ticker", "session_date"], suffixes=("", "_activity")))
    yearly_fidelity = {
        year: {
            **metrics,
            "hlc_gate_pass": bool(metrics["hlc_exact_rate"] >= config["gates"]["hlc_exact_year"]),
            "volume_gate_pass": bool(metrics["volume_within_5_rate"] >= config["gates"]["volume_within_5_year"]),
        }
        for year, metrics in fidelity["by_year"].items()
    }
    _write_json(out / "yearly_coverage_and_fidelity.json", {"coverage": yearly, "fidelity": yearly_fidelity})

    panel_sha_after = sha256_file(args.canonical_panel)
    if panel_sha_after != panel_sha_before:
        raise SystemExit("canonical panel changed during offline audit")

    active_total = int((activity["activity_state"] == "ACTIVE").sum())
    covered_active = int(state_counts.get("COVERED_ACTIVE", 0))
    gates = {
        "current_observed_active_coverage": float(covered_active / active_total) if active_total else 0.0,
        "symbol_error_identity_resolution_complete": not bool(ceilings["frozen_provider_symbol_contract_unresolved"]),
        "ordered_session_ca_recomputation_complete": fidelity["unmapped_event_count"] == 0,
        "fidelity_yearly_gates_pass": all(row["hlc_gate_pass"] and row["volume_gate_pass"] for row in yearly_fidelity.values()),
        "boundary_contract_complete_for_all_requests": boundary_summary["boundary_complete"] == boundary_summary["requests"],
        "identity_contract_clean": identity_summary["expected_ambiguous_rows"] == 0 and identity_summary["expected_security_id_mismatch_rows"] == 0 and identity_summary["provider_bar_ambiguous_rows"] == 0 and identity_summary["provider_bar_security_id_mismatch_rows"] == 0,
    }
    # No symbol substitutions or opportunistic exclusions are allowed.  Under
    # the frozen provider contract the unresolved invalid-symbol set is enough
    # to stop before the five-call depth preflight.
    if ceilings["frozen_provider_symbol_contract_unresolved"]:
        verdict = "V2_1_BLOCKED_SYMBOL_RESOLUTION_REQUIRED"
        depth_preflight = "NOT_RUN_OFFLINE_SYMBOL_CEILING_BLOCKS_NETWORK_STAGE"
    elif not gates["identity_contract_clean"]:
        verdict = "V2_1_BLOCKED_DATA_CONTRACT"
        depth_preflight = "NOT_RUN"
    elif not gates["boundary_contract_complete_for_all_requests"]:
        verdict = "V2_1_BLOCKED_DEPTH_CONTRACT"
        depth_preflight = "NOT_RUN"
    else:
        verdict = "V2_1_REMEDIATION_READY_FOR_FULL_PREREGISTRATION"
        depth_preflight = "AUTHORIZED_BOUNDARY_REACHED_BUT_NOT_EXECUTED_BY_THIS_OFFLINE_RUN"

    audit_summary = {
        "schema": "idx-trade/tradingview-historical-price-path-v2-1-offline-runtime",
        "verdict": verdict,
        "depth_preflight": depth_preflight,
        "network_calls": 0,
        "provider_status_counts": {str(k): int(v) for k, v in diagnostics["status"].value_counts().items()},
        "symbol_error_tickers": error_tickers,
        "identity": identity_summary,
        "activity_state_counts": {str(k): int(v) for k, v in activity_counts.items()},
        "reconciliation_status_counts": {str(k): int(v) for k, v in state_counts.items()},
        "fidelity": fidelity,
        "boundary": boundary_summary,
        "theoretical_ceilings": ceilings,
        "gates": gates,
        "canonical_panel_sha256_before": panel_sha_before,
        "canonical_panel_sha256_after": panel_sha_after,
        "frozen_failed_v2_verdict_unchanged": "TRADINGVIEW_PRICE_PATH_V2_REJECTED",
        "modeling_authorized": False,
        "protected_outcomes_accessed": False,
    }
    _write_json(out / "audit_summary.json", audit_summary)
    manifest = artifact_manifest(out, exclude={"artifact_manifest.json"})
    _write_json(out / "artifact_manifest.json", manifest)
    print(json.dumps({"verdict": verdict, "artifact_root": str(out), "manifest_sha256": manifest["manifest_sha256"], "panel_sha256": panel_sha_after, "network_calls": 0, "symbol_error_tickers": error_tickers, "reconciliation_status_counts": state_counts, "fidelity": fidelity, "theoretical_ceilings": ceilings}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
