"""Outcome-blind INC-001 population/coverage reconciliation.

This runner consumes only already accepted local artifacts.  It deliberately
does not load market prices, targets, labels, models, or provider clients.
The output is a deterministic forensic ledger for the A-D gates in the
CA-aware feature-basis remediation protocol.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence


EXPECTED = {
    "phase_a_manifest": "f6b73ebc9f092d1869166de125bbb7afd24a02d3597fa5fa9d6fea8853a70dda",
    "phase_a_h5": "c4768bf09956ec0599df2bcefe4aa26fba3608178110dc2a6d64f9f68e8b0049",
    "phase_a_h10": "b537d2ebea9610431522199e6221abe6b13cd96a6b1d487ad761ae4ba46a191b",
    "phase_b_manifest": "30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf",
    "ksei_manifest": "7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25a",
    "ksei_summary": "a046637fbcff69cbc42c09e4cac30d9181b2ce93a3cf7297a9a01cfc23a2f422",
    "ksei_coverage": "bb5414125862411e5d3ee760f8e7415b8418803c71d1cc1ef26fb0c55397bc70",
    "ksei_history": "3ea2f0a160300dd4d74c40281dbcbf680e03accc565487cf00b190630471c08d",
    "ksei_requests": "e68d60103cc3efc04299c1b330c4ef39e55ba1e44bbcf79f178b2f1ccff812e5",
    "ca_event_census": "10540f8f73e6a0cec3975ac189dc2ab2034a81c6610f81381009966848f95ed3",
}

STRUCTURAL_FAMILIES = (
    "BONUS_SHARES",
    "CAPITAL_RESTRUCTURING",
    "MANDATORY_CONVERSION",
    "REVERSE_SPLIT",
    "RIGHTS_HMETD",
    "STOCK_DIVIDEND",
    "STOCK_SPLIT",
    "VOLUNTARY_CONVERSION",
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def require_hash(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise RuntimeError(f"{label}: missing file {path}")
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f"{label}: SHA256 mismatch expected={expected} actual={actual}")
    return actual


def require_date(value: str, label: str) -> str:
    if not DATE_RE.fullmatch(value):
        raise RuntimeError(f"{label}: malformed ISO date {value!r}")
    return value


def validate_identity_rows(rows: Sequence[Mapping[str, str]], label: str) -> None:
    required = {"ticker", "date"}
    if not rows or not required.issubset(rows[0]):
        raise RuntimeError(f"{label}: required identity columns missing")
    keys: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        ticker = row["ticker"].strip().upper()
        date = require_date(row["date"].strip(), f"{label}[{index}].date")
        if not ticker:
            raise RuntimeError(f"{label}[{index}]: empty ticker")
        key = (ticker, date)
        if key in keys:
            raise RuntimeError(f"{label}: duplicate identity {key}")
        keys.add(key)


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def json_dump(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _timestamp_bounds(request_rows: Sequence[Mapping[str, str]]) -> tuple[str, str]:
    values = sorted(row["accessed_at_utc"] for row in request_rows if row.get("accessed_at_utc"))
    return (values[0], values[-1]) if values else ("", "")


def _family_verdict(family: str, count: int) -> tuple[str, str, str]:
    if family in {"MANDATORY_CONVERSION", "VOLUNTARY_CONVERSION"}:
        return (
            "FAIL_TAXONOMY_CONTRADICTION",
            "KSEI voluntary-conversion evidence is historically mapped into mandatory conversion; no family-safe promotion",
            "KSEI registered-security history plus strict census",
        )
    if family == "CAPITAL_RESTRUCTURING":
        return (
            "FAIL_SOURCE_TAXONOMY_CONFLICT",
            "kurangModal is represented as CAPITAL_RESTRUCTURING in one ledger and CAPITAL_REDUCTION in another",
            "IDX issued-history evidence",
        )
    if count == 0:
        return (
            "UNKNOWN_NO_POSITIVE_EVENT_PROOF",
            "absence in the bounded census does not certify no historical event",
            "IDX/KSEI family-specific source required",
        )
    return (
        "UNKNOWN_NO_EVENT_OR_TRANSITION_CERTIFICATION",
        "positive labels exist, but exact transition session and market-wide no-event coverage are not certified",
        "family-specific official IDX/KSEI evidence",
    )


def run(args: argparse.Namespace) -> Path:
    phase_a = Path(args.phase_a_root)
    phase_b = Path(args.phase_b_root)
    ksei = Path(args.ksei_root)
    ca_audit = Path(args.ca_audit_root)
    output = Path(args.output_dir)
    staging = output.with_name(output.name + ".staging")
    if output.exists() or staging.exists():
        raise RuntimeError("refusing to overwrite existing output or staging directory")

    phase_a_manifest = phase_a / "MANIFEST.json"
    h5_path = phase_a / "clean_h5_support_identities.csv"
    h10_path = phase_a / "clean_h10_support_identities.csv"
    phase_b_manifest = phase_b / "MANIFEST.json"
    ksei_manifest = ksei / "MANIFEST.json"
    ksei_summary = ksei / "summary.json"
    ksei_coverage = ksei / "ticker_coverage.csv"
    ksei_history = ksei / "ksei_ca_history.jsonl"
    ksei_requests = ksei / "request_records.jsonl"
    ca_events = ca_audit / "ca_event_census.csv"

    input_hashes = {
        "phase_a_manifest": require_hash(phase_a_manifest, EXPECTED["phase_a_manifest"], "phase_a_manifest"),
        "phase_a_h5": require_hash(h5_path, EXPECTED["phase_a_h5"], "phase_a_h5"),
        "phase_a_h10": require_hash(h10_path, EXPECTED["phase_a_h10"], "phase_a_h10"),
        "phase_b_manifest": require_hash(phase_b_manifest, EXPECTED["phase_b_manifest"], "phase_b_manifest"),
        "ksei_manifest": require_hash(ksei_manifest, EXPECTED["ksei_manifest"], "ksei_manifest"),
        "ksei_summary": require_hash(ksei_summary, EXPECTED["ksei_summary"], "ksei_summary"),
        "ksei_coverage": require_hash(ksei_coverage, EXPECTED["ksei_coverage"], "ksei_coverage"),
        "ksei_history": require_hash(ksei_history, EXPECTED["ksei_history"], "ksei_history"),
        "ksei_requests": require_hash(ksei_requests, EXPECTED["ksei_requests"], "ksei_requests"),
        "ca_event_census": require_hash(ca_events, EXPECTED["ca_event_census"], "ca_event_census"),
    }
    phase_manifest = read_json(phase_a_manifest)
    phase_b_data = read_json(phase_b_manifest)
    ksei_data = read_json(ksei_manifest)
    ksei_summary_data = read_json(ksei_summary)
    if not isinstance(phase_manifest, dict) or not isinstance(phase_b_data, dict):
        raise RuntimeError("phase manifests must be JSON objects")
    if phase_b_data.get("phase_a_output_hashes", {}).get("h5_support") != input_hashes["phase_a_h5"]:
        raise RuntimeError("Phase-B manifest is not bound to the accepted H5 support identity")
    if phase_b_data.get("phase_a_output_hashes", {}).get("h10_support") != input_hashes["phase_a_h10"]:
        raise RuntimeError("Phase-B manifest is not bound to the accepted H10 support identity")
    if not isinstance(ksei_data, dict) or ksei_data.get("ticker_count") not in (None, 610):
        raise RuntimeError("unexpected KSEI manifest ticker count")
    if not isinstance(ksei_summary_data, dict) or ksei_summary_data.get("ticker_count") != 610:
        raise RuntimeError("KSEI summary is not the pinned 610-ticker census")

    h5 = read_csv(h5_path)
    h10 = read_csv(h10_path)
    validate_identity_rows(h5, "H5")
    validate_identity_rows(h10, "H10")
    h5_keys = {(r["ticker"].strip().upper(), r["date"]) for r in h5}
    h10_keys = {(r["ticker"].strip().upper(), r["date"]) for r in h10}
    union_keys = h5_keys | h10_keys
    support_tickers = sorted({ticker for ticker, _ in union_keys})
    support_dates = sorted({date for _, date in union_keys})
    ksei_rows = read_csv(ksei_coverage)
    ksei_by_ticker = {row["ticker"].strip().upper(): row for row in ksei_rows}
    if len(ksei_by_ticker) != 610:
        raise RuntimeError(f"KSEI coverage ticker count mismatch: {len(ksei_by_ticker)}")
    request_rows = []
    with ksei_requests.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if isinstance(row, dict):
                request_rows.append(row)
    observed_start, observed_end = _timestamp_bounds(request_rows)

    by_ticker_h5: Counter[str] = Counter(ticker for ticker, _ in h5_keys)
    by_ticker_h10: Counter[str] = Counter(ticker for ticker, _ in h10_keys)
    by_ticker_union: Counter[str] = Counter(ticker for ticker, _ in union_keys)
    dates_h5: defaultdict[str, list[str]] = defaultdict(list)
    dates_h10: defaultdict[str, list[str]] = defaultdict(list)
    dates_union: defaultdict[str, list[str]] = defaultdict(list)
    for ticker, date in h5_keys:
        dates_h5[ticker].append(date)
    for ticker, date in h10_keys:
        dates_h10[ticker].append(date)
    for ticker, date in union_keys:
        dates_union[ticker].append(date)

    population_rows = []
    for ticker in support_tickers:
        ksei_row = ksei_by_ticker.get(ticker, {})
        dates = sorted(dates_union[ticker])
        ksei_status = ksei_row.get("coverage_status", "ABSENT_FROM_KSEI_CENSUS")
        if ksei_status == "COVERAGE_CERTIFIED":
            coverage_verdict = "UNKNOWN_MISSING_KSEI_TEMPORAL_ATTESTATION"
        elif ksei_status == "COVERAGE_UNRESOLVED":
            coverage_verdict = "UNKNOWN_KSEI_COVERAGE_UNRESOLVED"
        else:
            coverage_verdict = "UNKNOWN_TICKER_ABSENT_FROM_KSEI_POPULATION"
        population_rows.append(
            {
                "ticker": ticker,
                "h5_rows": by_ticker_h5[ticker],
                "h10_rows": by_ticker_h10[ticker],
                "union_rows": by_ticker_union[ticker],
                "h5_start": min(dates_h5[ticker]),
                "h5_end": max(dates_h5[ticker]),
                "h10_start": min(dates_h10[ticker]),
                "h10_end": max(dates_h10[ticker]),
                "union_start": dates[0],
                "union_end": dates[-1],
                "ksei_present": bool(ksei_row),
                "ksei_coverage_status": ksei_status,
                "ksei_source_sha256": ksei_row.get("source_sha256", ""),
                "ksei_earliest_ca_date": ksei_row.get("earliest_ca_date", ""),
                "ksei_latest_ca_date": ksei_row.get("latest_ca_date", ""),
                "coverage_start_session": "",
                "coverage_end_session": "",
                "coverage_observed_at_utc": "",
                "coverage_verdict": coverage_verdict,
            }
        )

    event_rows = read_csv(ca_events)
    event_min, event_max = support_dates[0], support_dates[-1]
    event_ledger = []
    family_counts = Counter(row.get("event_family", "") for row in event_rows)
    for row in event_rows:
        ticker = row.get("ticker", "").strip().upper()
        candidate_date = row.get("candidate_date", "")
        in_population = ticker in set(support_tickers)
        in_interval = bool(candidate_date and event_min <= candidate_date <= event_max)
        in_scope = in_population and in_interval
        event_ledger.append(
            {
                "ticker": ticker,
                "event_family": row.get("event_family", ""),
                "candidate_date": candidate_date,
                "source_kind": row.get("source_kind", ""),
                "source_action_id": row.get("source_action_id", ""),
                "source_ref": row.get("source_ref", ""),
                "source_sha256": row.get("source_sha256", ""),
                "effective_date_status": row.get("effective_date_status", ""),
                "continuity_status": row.get("continuity_status", ""),
                "in_exact_fit_population": in_population,
                "in_exact_fit_interval": in_interval,
                "in_exact_fit_scope": in_scope,
                "classification": "UNRESOLVED" if in_scope else "OUTSIDE_EXACT_SUPPORT_SCOPE",
                "resolution_reason": (
                    "transition_session_unresolved; no source-backed global no-event coverage"
                    if in_scope
                    else "not simultaneously in exact final-fit ticker population and support interval"
                ),
            }
        )

    family_rows = []
    for family in STRUCTURAL_FAMILIES:
        count = family_counts[family]
        verdict, reason, authority = _family_verdict(family, count)
        family_rows.append(
            {
                "event_family": family,
                "authoritative_source": authority,
                "strict_census_positive_rows": count,
                "strict_census_transition_states": ";".join(
                    sorted({row.get("effective_date_status", "") for row in event_rows if row.get("event_family") == family})
                ),
                "exact_fit_population_coverage": "UNKNOWN",
                "no_event_coverage_certified": False,
                "transition_semantics": "UNRESOLVED",
                "global_verdict": verdict,
                "reason": reason,
            }
        )
    family_rows.append(
        {
            "event_family": "MERGER",
            "authoritative_source": "IDX gabungUsaha source pool observed in prior frozen audit",
            "strict_census_positive_rows": 0,
            "strict_census_transition_states": "NOT_PRESENT_IN_STRICT_CENSUS",
            "exact_fit_population_coverage": "UNKNOWN",
            "no_event_coverage_certified": False,
            "transition_semantics": "UNRESOLVED",
            "global_verdict": "UNKNOWN_DISTINCT_FAMILY_OR_CERTIFIED_RESTRUCTURING_CONTRACT_REQUIRED",
            "reason": "absence from strict census is not no-merger proof; frozen restructuring mapping is not a universal merger contract",
        }
    )

    temporal_rows = [
        {
            "scope": "EXACT_FINAL_FIT_SUPPORT_UNION",
            "source": "accepted Phase-A H5/H10 identity artifacts",
            "start_session": event_min,
            "end_session": event_max,
            "observed_at_start_utc": "",
            "observed_at_end_utc": "",
            "certified": True,
            "verdict": "PASS_IDENTITY_INTERVAL_ONLY",
            "reason": "support identity interval is exact; it is not CA source coverage",
        },
        {
            "scope": "KSEI_SOURCE_SNAPSHOT",
            "source": "pinned KSEI request_records.jsonl",
            "start_session": "",
            "end_session": "",
            "observed_at_start_utc": observed_start,
            "observed_at_end_utc": observed_end,
            "certified": False,
            "verdict": "UNKNOWN_NO_PER_SESSION_COVERAGE_ATTESTATION",
            "reason": "ticker_coverage lacks coverage_start_session/coverage_end_session/coverage_observed_at; snapshot retrieval time is not historical no-event coverage",
        },
        {
            "scope": "KSEI_EVENT_DATE_FIELDS",
            "source": "pinned ksei_ca_history.jsonl",
            "start_session": "2001-04-10",
            "end_session": "2026-09-15",
            "observed_at_start_utc": observed_start,
            "observed_at_end_utc": observed_end,
            "certified": False,
            "verdict": "UNKNOWN_EVENT_DATE_NOT_MARKET_TRANSITION",
            "reason": "field span includes future scheduled dates and source-specific event dates; no generic transition session is inferred",
        },
    ]
    for feature, offset, count in (
        ("close_return_5", "-5..0", 5),
        ("close_return_20", "-20..0", 20),
        ("atr14_over_close", "-14..0", 14),
        ("rolling20_price_features", "-19..0", 20),
        ("rolling60_price_features", "-59..0", 59),
    ):
        temporal_rows.append(
            {
                "scope": f"DEPENDENCY_{feature.upper()}",
                "source": "frozen V4 feature geometry",
                "start_session": offset,
                "end_session": "0",
                "observed_at_start_utc": "",
                "observed_at_end_utc": "",
                "certified": True,
                "verdict": "PASS_GEOMETRY_DEFINITION_ONLY",
                "reason": f"direct exposure count after warmup = {count}; admission still requires CA coverage and transition semantics",
            }
        )

    classification_rows = []
    for row in population_rows:
        classification_rows.append(
            {
                "ticker": row["ticker"],
                "model_interval_start": event_min,
                "model_interval_end": event_max,
                "ksei_coverage_status": row["ksei_coverage_status"],
                "event_family_coverage": "PARTIAL_OR_UNCERTIFIED",
                "transition_semantics": "UNRESOLVED",
                "classification": "UNRESOLVED",
                "reason": row["coverage_verdict"] + "; global structural CA family/no-event certification absent",
            }
        )

    population_tickers = set(support_tickers)
    ksei_tickers = set(ksei_by_ticker)
    certified_support = {ticker for ticker in population_tickers if ksei_by_ticker.get(ticker, {}).get("coverage_status") == "COVERAGE_CERTIFIED"}
    unresolved_support = population_tickers - certified_support
    event_scope_rows = [row for row in event_ledger if row["in_exact_fit_scope"]]
    summary = {
        "schema_version": "ca_aware_feature_basis_reconciliation_v1",
        "status": "A_D_AUDIT_COMPLETE_PHASE_E_BLOCKED",
        "verdict": {
            "EXACT_FINAL_FIT_POPULATION": "PASS_IDENTITY_RECONCILED",
            "KSEI_POPULATION_COVERAGE": "FAIL_629_FIT_TICKERS_VS_610_KSEI_CENSUS",
            "TEMPORAL_COVERAGE": "UNKNOWN_NO_KSEI_PER_SESSION_AS_OF_ATTESTATION",
            "STRUCTURAL_CA_FAMILY_COVERAGE": "FAIL_PARTIAL_OR_CONFLICTING_FAMILY_EVIDENCE",
            "MERGER_POLICY_VERDICT": "UNKNOWN_DISTINCT_FAMILY_OR_CERTIFIED_RESTRUCTURING_CONTRACT_REQUIRED",
            "VOLUNTARY_CONVERSION_VERDICT": "FAIL_TAXONOMY_CONTRADICTION",
            "TRANSITION_SEMANTICS": "FAIL_OR_UNKNOWN_ALL_STRICT_EVENTS_UNRESOLVED",
            "BACKWARD_CA_FEATURE_WINDOW_RISK": "PRESENT_NO_GLOBAL_CA_AWARE_ADMISSION",
            "EXACT_CLEAN_INPUT_IMPACT": "NOT_RECOMPUTED_IN_THIS_LANE",
            "HISTORICAL_APPLICATION": "BLOCKED_PHASE_E_NOT_RUN",
            "DATA_ADMISSION": "FAIL",
            "RESEARCH_ADMISSION": "FAIL",
            "MODEL_PROMOTION": "NOT_EVALUATED",
            "REFIT_AUTHORIZED": False,
            "COUNTER_ACTION": "NONE",
            "REMEDIATION_REQUIRED": "YES_TARGETED_CA_SOURCE_AND_COVERAGE_REMEDIATION",
        },
        "exact_final_fit": {
            "H5_rows": len(h5),
            "H10_rows": len(h10),
            "union_rows": len(union_keys),
            "H5_tickers": len({ticker for ticker, _ in h5_keys}),
            "H10_tickers": len({ticker for ticker, _ in h10_keys}),
            "union_tickers": len(population_tickers),
            "support_start": event_min,
            "support_end": event_max,
            "h5_h10_overlap_rows": len(h5_keys & h10_keys),
        },
        "ksei_population": {
            "ticker_count": len(ksei_tickers),
            "coverage_certified": sum(row.get("coverage_status") == "COVERAGE_CERTIFIED" for row in ksei_rows),
            "coverage_unresolved": sum(row.get("coverage_status") == "COVERAGE_UNRESOLVED" for row in ksei_rows),
            "fit_tickers_overlap": len(population_tickers & ksei_tickers),
            "fit_tickers_absent": len(population_tickers - ksei_tickers),
            "ksei_tickers_not_in_fit": len(ksei_tickers - population_tickers),
            "fit_tickers_certified": len(certified_support),
            "fit_tickers_unresolved_or_absent": len(unresolved_support),
            "identity_sha256": ksei_summary_data.get("ticker_identity_sha256", ""),
        },
        "temporal_coverage": {
            "ksei_observed_retrieval_start_utc": observed_start,
            "ksei_observed_retrieval_end_utc": observed_end,
            "coverage_start_session_field_present": False,
            "coverage_end_session_field_present": False,
            "coverage_observed_at_field_present": False,
            "per_session_no_event_attestation": False,
            "dependencies": {"close_return_5": 5, "close_return_20": 20, "atr14_over_close": 14, "rolling20": 20, "rolling60": 59},
        },
        "structural_ca": {
            "strict_event_rows": len(event_rows),
            "strict_event_family_counts": dict(sorted(family_counts.items())),
            "events_in_exact_fit_scope": len(event_scope_rows),
            "all_in_scope_events_unresolved": all(row["classification"] == "UNRESOLVED" for row in event_scope_rows),
            "global_coverage_certified": False,
        },
        "guardrails": {
            "outcome_blind": True,
            "target_values_accessed": False,
            "outcomes_accessed": False,
            "model_fit": False,
            "model_scoring": False,
            "provider_calls": False,
            "canonical_artifacts_mutated": False,
            "historical_feature_recompute": False,
            "phase_e_run": False,
            "counter_mutated": False,
        },
        "inputs": input_hashes,
    }

    staging.mkdir(parents=True)
    try:
        write_csv(
            staging / "population_reconciliation.csv",
            (
                "ticker", "h5_rows", "h10_rows", "union_rows", "h5_start", "h5_end", "h10_start", "h10_end", "union_start", "union_end", "ksei_present", "ksei_coverage_status", "ksei_source_sha256", "ksei_earliest_ca_date", "ksei_latest_ca_date", "coverage_start_session", "coverage_end_session", "coverage_observed_at_utc", "coverage_verdict"
            ),
            population_rows,
        )
        write_csv(
            staging / "structural_ca_event_ledger.csv",
            tuple(event_ledger[0].keys()) if event_ledger else ("ticker",),
            event_ledger,
        )
        write_csv(staging / "ca_family_coverage.csv", tuple(family_rows[0].keys()), family_rows)
        write_csv(staging / "temporal_coverage.csv", tuple(temporal_rows[0].keys()), temporal_rows)
        write_csv(staging / "model_population_classification.csv", tuple(classification_rows[0].keys()), classification_rows)
        json_dump(staging / "summary.json", summary)
        output_hashes = {
            name: sha256(staging / name)
            for name in (
                "population_reconciliation.csv",
                "structural_ca_event_ledger.csv",
                "ca_family_coverage.csv",
                "temporal_coverage.csv",
                "model_population_classification.csv",
                "summary.json",
            )
        }
        manifest = {
            "schema_version": "ca_aware_feature_basis_reconciliation_manifest_v1",
            "status": "A_D_AUDIT_COMPLETE_PHASE_E_BLOCKED",
            "input_hashes": input_hashes,
            "output_hashes": output_hashes,
            "exact_final_fit": summary["exact_final_fit"],
            "ksei_population": summary["ksei_population"],
            "temporal_coverage": summary["temporal_coverage"],
            "structural_ca": summary["structural_ca"],
            "guardrails": summary["guardrails"],
            "deterministic": True,
        }
        json_dump(staging / "MANIFEST.json", manifest)
        staging.replace(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase-a-root", required=True)
    parser.add_argument("--phase-b-root", required=True)
    parser.add_argument("--ksei-root", required=True)
    parser.add_argument("--ca-audit-root", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    result = run(parse_args())
    print(f"CA_AWARE_RECONCILIATION_COMPLETE output={result}")
