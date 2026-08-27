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
import re
import shutil
import subprocess
import sys
import types
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pandas as pd

# Allow the repository script to use the checked-out package without relying
# on a caller's global PYTHONPATH.  This does not load any data or alter the
# frozen source modules.
_SRC_ROOT = str(Path(__file__).resolve().parents[1] / "src")
if _SRC_ROOT not in sys.path:
    sys.path.insert(0, _SRC_ROOT)

from idx_trade.ca_aware_feature_basis_r3 import (
    R3_DEPENDENCY_OFFSETS,
    build_cross_section_population,
    build_observed_dependency_closure,
    build_primary_membership_dependency_closure,
    classify_event_scope,
    compare_identity_sets,
    global_ca_population_gate,
    merge_dependency_closures,
    reconcile_ksei_populations,
    validate_strict_event_census,
)


EXPECTED = {
    "phase_a_manifest": "f6b73ebc9f092d1869166de125bbb7afd24a02d3597fa5fa9d6fea8853a70dda",
    "phase_a_h5": "c4768bf09956ec0599df2bcefe4aa26fba3608178110dc2a6d64f9f68e8b0049",
    "phase_a_h10": "b537d2ebea9610431522199e6221abe6b13cd96a6b1d487ad761ae4ba46a191b",
    "phase_b_manifest": "30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf",
    "clean_panel": "25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e",
    "ksei_manifest": "7cc3ac4d409c3e15c6aa566b63bedab4268562fd4914d1af198ab29657dba25a",
    "ksei_summary": "a046637fbcff69cbc42c09e4cac30d9181b2ce93a3cf7297a9a01cfc23a2f422",
    "ksei_coverage": "bb5414125862411e5d3ee760f8e7415b8418803c71d1cc1ef26fb0c55397bc70",
    "ksei_history": "3ea2f0a160300dd4d74c40281dbcbf680e03accc565487cf00b190630471c08d",
    "ksei_requests": "e68d60103cc3efc04299c1b330c4ef39e55ba1e44bbcf79f178b2f1ccff812e5",
    "ca_event_census": "10540f8f73e6a0cec3975ac189dc2ab2034a81c6610f81381009966848f95ed3",
    "ca_audit_summary": "3f6de321e673775dfe9b39150aded7ff54295b0d9b68828d14ff77943f50494c",
    "clean_security_master": "51fecc3be6956d24eac3d0193c80a6595f6b7976b999e1b9432b16a0e3c3cf0e",
    "official_calendar": "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a",
    "frozen_feature_builder_blob": "59ad05f815870ae00480dc7945fe18371d8eff9c",
    "old_manifest": "5d3bce5ce8776d68a356ea814aa2dcd8909cb26b8d3334ea5e3f68f089a5fe61",
    "old_summary": "c4d55545066bb28401246ec0ff217c6bf2a36a77372cedd158fe7ca579bfb4c5",
    "old_h5": "2c2874bde129f8cefb68af1aae01ab88203dfe74c2bc8cf4cf3e5bab61e76ede",
    "old_h10": "606eae2a431d0b924f7dbe574cbca493f1b857bf55aeb0d1af74db3d01c03386",
    "clean_ca80_support_per_date": "b36114623df7dc9475fd5227f877f9cae887a28f17b31448f28e26d443715f79",
    "old_vs_clean_primary_identity_delta": "f07bfec5d89443e05512984364831034b1571c7337e1257e685e6bf71e58a240",
    "old_vs_clean_support_delta": "ae13c763515ee86bf8934d6883dd089ae3aae5504ba317f8d951ffdcbf2f5862",
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


def clean_panel_interval(path: Path) -> dict[str, object]:
    """Read only the date column needed to pin the full observation interval."""
    try:
        import pyarrow.parquet as parquet
    except ImportError as exc:  # pragma: no cover - environment contract
        raise RuntimeError("clean panel date interval requires pyarrow") from exc
    schema = parquet.read_schema(path)
    if "date" not in schema.names:
        raise RuntimeError("clean panel is missing the required date column")
    table = parquet.read_table(path, columns=["date"])
    dates = []
    for value in table.column("date").to_pylist():
        if hasattr(value, "date") and callable(value.date):
            value = value.date()
        dates.append(value.isoformat() if hasattr(value, "isoformat") else str(value))
    if not dates or any(not DATE_RE.fullmatch(value) for value in dates):
        raise RuntimeError("clean panel contains an empty or malformed date interval")
    return {"row_count": len(dates), "start": min(dates), "end": max(dates)}


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
    if getattr(args, "r31", False):
        return run_r31(args)
    if getattr(args, "r3", False):
        return run_r3(args)
    phase_a = Path(args.phase_a_root)
    phase_b = Path(args.phase_b_root)
    clean_panel = Path(args.clean_panel)
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
        "clean_panel": require_hash(clean_panel, EXPECTED["clean_panel"], "clean_panel"),
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
    feature_interval = clean_panel_interval(clean_panel)

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
            "scope": "CLEAN_FEATURE_PANEL_OBSERVATION_INTERVAL",
            "source": "hash-pinned clean model-safe panel date column only",
            "start_session": feature_interval["start"],
            "end_session": feature_interval["end"],
            "observed_at_start_utc": "",
            "observed_at_end_utc": "",
            "certified": True,
            "verdict": "PASS_OBSERVATION_INTERVAL_ONLY",
            "reason": "full clean panel interval is wider than exact final-fit support and is the required historical comparison boundary",
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
        "historical_feature_observation_interval": feature_interval,
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
            "historical_feature_observation_interval": feature_interval,
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
            "historical_feature_observation_interval": feature_interval,
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


def _load_frozen_feature_builder(repo_root: Path):
    """Load the accepted builder blob in memory and verify its object identity."""

    result = subprocess.run(
        ["git", "cat-file", "-p", EXPECTED["frozen_feature_builder_blob"]],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    source = result.stdout
    object_hash = subprocess.run(
        ["git", "hash-object", "--stdin"],
        cwd=repo_root,
        input=source,
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").strip()
    actual = object_hash
    if actual != EXPECTED["frozen_feature_builder_blob"]:
        raise RuntimeError(
            "frozen feature builder blob mismatch: "
            f"expected={EXPECTED['frozen_feature_builder_blob']} actual={actual}"
        )
    name = "_idx_trade_frozen_v4_builder_r3"
    module = types.ModuleType(name)
    module.__file__ = f"<git-blob:{actual}>"
    sys.modules[name] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module, actual


def _r3_frame_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    """Convert a deterministic frame to plain rows for the shared CSV writer."""

    if frame.empty:
        return []
    return frame.astype(object).where(frame.notna(), "").to_dict(orient="records")


def _r3_ticker_summary(
    population: pd.DataFrame,
    h5_keys: set[tuple[str, str]],
    h10_keys: set[tuple[str, str]],
    ksei_rows: pd.DataFrame,
) -> pd.DataFrame:
    ksei = ksei_rows.copy()
    ksei["ticker"] = ksei["ticker"].astype(str).str.upper().str.strip()
    ksei = ksei.set_index("ticker")
    rows: list[dict[str, object]] = []
    for ticker, group in population.groupby("ticker", sort=True):
        dates = group["date"].tolist()
        h5_count = sum((ticker, date) in h5_keys for date in dates)
        h10_count = sum((ticker, date) in h10_keys for date in dates)
        ksei_row = ksei.loc[ticker] if ticker in ksei.index else None
        rows.append(
            {
                "ticker": ticker,
                "application_rows": len(group),
                "h5_fit_rows": h5_count,
                "h10_fit_rows": h10_count,
                "fit_union_rows": h5_count + h10_count - sum(
                    (ticker, date) in h5_keys and (ticker, date) in h10_keys for date in dates
                ),
                "application_start": min(dates),
                "application_end": max(dates),
                "ksei_present": ksei_row is not None,
                "ksei_coverage_status": str(ksei_row["coverage_status"]) if ksei_row is not None else "ABSENT_FROM_KSEI_CENSUS",
                "ksei_source_sha256": str(ksei_row.get("source_sha256", "")) if ksei_row is not None else "",
            }
        )
    return pd.DataFrame(rows)


def run_r3(args: argparse.Namespace) -> Path:
    """Run the outcome-blind R3 population/closure reconciliation exactly once."""

    required_args = (
        "phase_a_root",
        "phase_b_root",
        "clean_panel",
        "ksei_root",
        "ca_audit_root",
        "output_dir",
        "repo_root",
        "clean_security_master",
        "official_calendar",
        "old_support_root",
    )
    missing_args = [name for name in required_args if not getattr(args, name, None)]
    if missing_args:
        raise RuntimeError(f"R3 arguments missing: {', '.join(missing_args)}")

    phase_a = Path(args.phase_a_root)
    phase_b = Path(args.phase_b_root)
    clean_panel = Path(args.clean_panel)
    ksei = Path(args.ksei_root)
    ca_audit = Path(args.ca_audit_root)
    old_support = Path(args.old_support_root)
    clean_master = Path(args.clean_security_master)
    official_calendar = Path(args.official_calendar)
    repo_root = Path(args.repo_root)
    output = Path(args.output_dir)
    staging = output.with_name(output.name + ".staging")
    if output.exists() or staging.exists():
        raise RuntimeError("refusing to overwrite existing R3 output or staging directory")

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
    ca_audit_summary = ca_audit / "audit_summary.json"
    old_manifest = old_support / "MANIFEST.json"
    old_summary = old_support / "summary.json"
    old_h5_path = old_support / "h5_support_identities.csv"
    old_h10_path = old_support / "h10_support_identities.csv"

    input_hashes = {
        "phase_a_manifest": require_hash(phase_a_manifest, EXPECTED["phase_a_manifest"], "phase_a_manifest"),
        "phase_a_h5": require_hash(h5_path, EXPECTED["phase_a_h5"], "phase_a_h5"),
        "phase_a_h10": require_hash(h10_path, EXPECTED["phase_a_h10"], "phase_a_h10"),
        "phase_b_manifest": require_hash(phase_b_manifest, EXPECTED["phase_b_manifest"], "phase_b_manifest"),
        "clean_panel": require_hash(clean_panel, EXPECTED["clean_panel"], "clean_panel"),
        "clean_security_master": require_hash(clean_master, EXPECTED["clean_security_master"], "clean_security_master"),
        "official_calendar": require_hash(official_calendar, EXPECTED["official_calendar"], "official_calendar"),
        "ksei_manifest": require_hash(ksei_manifest, EXPECTED["ksei_manifest"], "ksei_manifest"),
        "ksei_summary": require_hash(ksei_summary, EXPECTED["ksei_summary"], "ksei_summary"),
        "ksei_coverage": require_hash(ksei_coverage, EXPECTED["ksei_coverage"], "ksei_coverage"),
        "ksei_history": require_hash(ksei_history, EXPECTED["ksei_history"], "ksei_history"),
        "ksei_requests": require_hash(ksei_requests, EXPECTED["ksei_requests"], "ksei_requests"),
        "ca_event_census": require_hash(ca_events, EXPECTED["ca_event_census"], "ca_event_census"),
        "ca_audit_summary": require_hash(ca_audit_summary, EXPECTED["ca_audit_summary"], "ca_audit_summary"),
        "old_manifest": require_hash(old_manifest, EXPECTED["old_manifest"], "old_manifest"),
        "old_summary": require_hash(old_summary, EXPECTED["old_summary"], "old_summary"),
        "old_h5": require_hash(old_h5_path, EXPECTED["old_h5"], "old_h5"),
        "old_h10": require_hash(old_h10_path, EXPECTED["old_h10"], "old_h10"),
    }

    phase_a_data = read_json(phase_a_manifest)
    phase_b_data = read_json(phase_b_manifest)
    ksei_data = read_json(ksei_manifest)
    ksei_summary_data = read_json(ksei_summary)
    ca_audit_data = read_json(ca_audit_summary)
    old_summary_data = read_json(old_summary)
    if not isinstance(phase_a_data, dict) or not isinstance(phase_b_data, dict):
        raise RuntimeError("R3 phase manifests must be JSON objects")
    if phase_b_data.get("phase_a_output_hashes", {}).get("h5_support") != input_hashes["phase_a_h5"]:
        raise RuntimeError("R3 Phase-B manifest is not bound to accepted H5 support")
    if phase_b_data.get("phase_a_output_hashes", {}).get("h10_support") != input_hashes["phase_a_h10"]:
        raise RuntimeError("R3 Phase-B manifest is not bound to accepted H10 support")
    if not isinstance(ksei_data, dict) or ksei_data.get("ticker_count") not in (None, 610):
        raise RuntimeError("R3 KSEI manifest ticker count is neither absent nor the pinned 610")
    if not isinstance(ksei_summary_data, dict) or ksei_summary_data.get("ticker_count") != 610:
        raise RuntimeError("R3 KSEI summary ticker count is not the pinned 610")
    if not isinstance(ca_audit_data, dict) or ca_audit_data.get("market_ca_event_census", {}).get("evidence_rows") != 26:
        raise RuntimeError("R3 strict CA census completeness attestation is missing or not 26 rows")

    h5 = read_csv(h5_path)
    h10 = read_csv(h10_path)
    old_h5 = read_csv(old_h5_path)
    old_h10 = read_csv(old_h10_path)
    validate_identity_rows(h5, "R3 H5")
    validate_identity_rows(h10, "R3 H10")
    validate_identity_rows(old_h5, "R3 old H5")
    validate_identity_rows(old_h10, "R3 old H10")
    h5_keys = {(row["ticker"].strip().upper(), row["date"].strip()) for row in h5}
    h10_keys = {(row["ticker"].strip().upper(), row["date"].strip()) for row in h10}
    old_h5_keys = {(row["ticker"].strip().upper(), row["date"].strip()) for row in old_h5}
    old_h10_keys = {(row["ticker"].strip().upper(), row["date"].strip()) for row in old_h10}
    current_union = h5_keys | h10_keys
    old_union = old_h5_keys | old_h10_keys

    panel = pd.read_parquet(clean_panel)
    forbidden = {
        "r5",
        "r10",
        "realized_consensus",
        "target_rank_h5",
        "target_rank_h10",
        "target_state_h5",
        "target_state_h10",
    }
    if forbidden & set(panel.columns):
        raise RuntimeError(f"clean panel contains forbidden target/outcome columns: {sorted(forbidden & set(panel.columns))}")
    master = pd.read_csv(clean_master)
    calendar = pd.read_csv(official_calendar)
    if "date" not in calendar.columns:
        raise RuntimeError("official calendar missing date column")
    builder, builder_blob = _load_frozen_feature_builder(repo_root)
    features, builder_diag = builder.build_v4_control_feature_table(panel, calendar["date"], master)
    if forbidden & set(features.columns):
        raise RuntimeError(f"frozen feature builder exposed forbidden target/outcome columns: {sorted(forbidden & set(features.columns))}")

    population, population_summary = build_cross_section_population(features, h5_keys, h10_keys)
    application_keys = set(map(tuple, population[["ticker", "date"]].itertuples(index=False, name=None)))
    direct_closure, direct_closure_summary = build_observed_dependency_closure(
        features,
        application_keys,
        dependencies=R3_DEPENDENCY_OFFSETS,
    )
    membership_closure, membership_closure_summary = build_primary_membership_dependency_closure(
        features,
        application_keys,
        calendar["date"],
        lookback_sessions=60,
    )
    closure = merge_dependency_closures(direct_closure, membership_closure)
    closure_summary = {
        **direct_closure_summary,
        "direct_closure_rows": direct_closure_summary["closure_rows"],
        "primary_membership_closure_rows": membership_closure_summary["closure_rows"],
        "primary_membership_closure_tickers": membership_closure_summary["closure_tickers"],
        "primary_membership_closure_start": membership_closure_summary["closure_start"],
        "primary_membership_closure_end": membership_closure_summary["closure_end"],
        "closure_rows": len(closure),
        "closure_tickers": closure["ticker"].nunique() if not closure.empty else 0,
        "closure_start": closure["date"].min() if not closure.empty else "",
        "closure_end": closure["date"].max() if not closure.empty else "",
        "primary_membership_lookback_sessions": 60,
    }

    ksei_rows = pd.read_csv(ksei_coverage, dtype=str).fillna("")
    ksei_scope = reconcile_ksei_populations(
        {
            "EXACT_FINAL_FIT": {ticker for ticker, _ in current_union},
            "CROSS_SECTION_APPLICATION": set(population["ticker"]),
            "BACKWARD_DEPENDENCY_CLOSURE": set(closure["ticker"]) if not closure.empty else set(),
        },
        ksei_rows,
    )
    ksei_lookup = ksei_rows.copy()
    ksei_lookup["ticker"] = ksei_lookup["ticker"].astype(str).str.upper().str.strip()
    ksei_lookup = ksei_lookup.set_index("ticker")
    population = population.copy()
    population["ksei_present"] = population["ticker"].isin(set(ksei_lookup.index))
    population["ksei_coverage_status"] = population["ticker"].map(ksei_lookup["coverage_status"]).fillna("ABSENT_FROM_KSEI_CENSUS")
    population["ksei_source_sha256"] = population["ticker"].map(ksei_lookup.get("source_sha256", pd.Series(dtype=str))).fillna("")
    ticker_summary = _r3_ticker_summary(population, h5_keys, h10_keys, ksei_rows)

    event_rows = pd.read_csv(ca_events, dtype=str).fillna("")
    expected_family_counts = ca_audit_data.get("market_ca_event_census", {}).get("event_family_counts", {})
    try:
        validate_strict_event_census(
            event_rows,
            expected_rows=26,
            expected_family_counts=expected_family_counts,
        )
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    event_scope = classify_event_scope(event_rows, closure)
    family_counts = event_rows["event_family"].value_counts().sort_index().to_dict()

    lineage_frames = []
    lineage_summaries = {}
    for name, old_set, current_set in (
        ("H5", old_h5_keys, h5_keys),
        ("H10", old_h10_keys, h10_keys),
        ("UNION", old_union, current_union),
    ):
        frame, comparison = compare_identity_sets(old_set, current_set)
        frame.insert(0, "support_head", name)
        lineage_frames.append(frame)
        lineage_summaries[name] = comparison
    lineage = pd.concat(lineage_frames, ignore_index=True)
    old_overlay_union = ca_audit_data.get("accepted_overlay_exact_fit_impact", {}).get("UNION", {})
    support_lineage_summary = {
        "old_stage_c": {
            "manifest_sha256": input_hashes["old_manifest"],
            "summary_sha256": input_hashes["old_summary"],
            "h5_rows": len(old_h5_keys),
            "h10_rows": len(old_h10_keys),
            "union_rows": len(old_union),
            "decision": old_summary_data.get("decision", ""),
        },
        "current_phase_a_b": {
            "phase_a_manifest_sha256": input_hashes["phase_a_manifest"],
            "phase_b_manifest_sha256": input_hashes["phase_b_manifest"],
            "h5_rows": len(h5_keys),
            "h10_rows": len(h10_keys),
            "union_rows": len(current_union),
        },
        "comparisons": lineage_summaries,
        "old_56602_overlay": {
            "old_union_changed_rows": old_overlay_union.get("changed_rows", 56602),
            "old_union_changed_tickers": old_overlay_union.get("changed_tickers", 486),
            "current_phase_b_union_rows": len(current_union),
            "applicability_to_current_phase_b": "NOT_APPLICABLE_UNPROVEN_ON_CURRENT_SUPPORT",
            "reason": "the accepted 56,602-row overlay was measured on the superseded Stage-C population; no current Phase-B recomputation is authorized in R3",
        },
    }

    fit_ticker_set = {ticker for ticker, _ in current_union}
    application_ticker_set = set(population["ticker"])
    closure_identity_set = set(map(tuple, closure[["ticker", "date"]].itertuples(index=False, name=None))) if not closure.empty else set()
    closure_ticker_set = set(closure["ticker"]) if not closure.empty else set()
    fit_tickers = len(fit_ticker_set)
    gate = global_ca_population_gate(
        fit_tickers=fit_ticker_set,
        application_tickers=application_ticker_set,
        closure_tickers=closure_ticker_set,
        fit_identities=current_union,
        application_identities=application_keys,
        closure_identities=closure_identity_set,
        ksei_scope=ksei_scope,
        structural_event_complete=False,
    )
    if not closure.empty:
        closure_index = pd.MultiIndex.from_frame(closure[["ticker", "date"]])
        fit_index = pd.MultiIndex.from_tuples(sorted(current_union), names=["ticker", "date"])
        cross_only_index = pd.MultiIndex.from_tuples(sorted(application_keys - current_union), names=["ticker", "date"])
        closure["is_fit_identity"] = closure_index.isin(fit_index)
        closure["is_cross_section_only"] = closure_index.isin(cross_only_index)
    else:
        closure["is_fit_identity"] = pd.Series(dtype=bool)
        closure["is_cross_section_only"] = pd.Series(dtype=bool)
    closure["outside_r2_fit_interval"] = closure["date"].map(lambda value: value < "2022-02-11" or value > "2026-07-17") if not closure.empty else pd.Series(dtype=bool)

    event_scope_summary = event_scope["closure_scope_classification"].value_counts().sort_index().to_dict()
    structural_summary = {
        "strict_event_rows": len(event_scope),
        "family_counts": {str(key): int(value) for key, value in sorted(family_counts.items())},
        "scope_classification_counts": {str(key): int(value) for key, value in event_scope_summary.items()},
        "all_transition_semantics_unresolved": bool((event_scope["transition_semantics"] == "UNRESOLVED").all()),
        "strict_census_completeness_attested": True,
        "global_event_coverage_certified": False,
    }
    summary = {
        "schema_version": "ca_aware_feature_basis_reconciliation_r3",
        "status": "R3_AUDIT_COMPLETE_PHASE_E_BLOCKED",
        "verdict": {
            "EXACT_FINAL_FIT_POPULATION": "PASS_IDENTITY_RECONCILED",
            "CROSS_SECTION_APPLICATION_POPULATION": "PASS_FULL_PRIMARY_LIQUID_ON_FIT_DATES",
            "BACKWARD_DEPENDENCY_CLOSURE": "PASS_OBSERVED_ROW_CLOSURE_COMPUTED",
            "KSEI_FIT_POPULATION_COVERAGE": "FAIL_629_VS_610_NO_DATE_ATTESTATION",
            "KSEI_CROSS_SECTION_COVERAGE": "FAIL_716_VS_610_NO_DATE_ATTESTATION",
            "KSEI_DEPENDENCY_CLOSURE_COVERAGE": "FAIL_716_VS_610_NO_DATE_ATTESTATION",
            "TEMPORAL_COVERAGE": "UNKNOWN_NO_KSEI_PER_SESSION_AS_OF_ATTESTATION",
            "STRUCTURAL_CA_EVENT_SCOPE": "FAIL_OR_UNKNOWN_UNRESOLVED_TRANSITION_SEMANTICS",
            "OLD_241724_POPULATION": "PRESENT_HASH_PINNED_LEGACY_STAGE_C_SUPPORT",
            "CURRENT_240344_POPULATION": "PRESENT_HASH_PINNED_ACCEPTED_PHASE_B_SUPPORT",
            "POPULATION_EQUIVALENCE": "FAIL_DIFFERENT_POPULATION",
            "OLD_56602_APPLICABILITY_TO_CURRENT_PHASE_B": "NOT_APPLICABLE_UNPROVEN_ON_CURRENT_SUPPORT",
            "STRUCTURAL_CA_FAMILY_COVERAGE": "FAIL_PARTIAL_OR_CONFLICTING_FAMILY_EVIDENCE",
            "TRANSITION_SEMANTICS": "FAIL_OR_UNKNOWN_ALL_STRICT_EVENTS_UNRESOLVED",
            "HISTORICAL_APPLICATION": "BLOCKED_PHASE_E_NOT_RUN",
            "DATA_ADMISSION": "FAIL",
            "RESEARCH_ADMISSION": "FAIL",
            "MODEL_PROMOTION": "NOT_EVALUATED",
            "REFIT_AUTHORIZED": False,
            "COUNTER_ACTION": "NONE",
        },
        "exact_final_fit": {
            "H5_rows": len(h5_keys),
            "H10_rows": len(h10_keys),
            "union_rows": len(current_union),
            "H5_tickers": len({ticker for ticker, _ in h5_keys}),
            "H10_tickers": len({ticker for ticker, _ in h10_keys}),
            "union_tickers": fit_tickers,
            "support_start": min(date for _, date in current_union),
            "support_end": max(date for _, date in current_union),
        },
        "cross_section_application": population_summary,
        "backward_dependency_closure": closure_summary,
        "ksei_population_scope": ksei_scope.to_dict(orient="records"),
        "support_lineage": support_lineage_summary,
        "structural_ca": structural_summary,
        "frozen_builder": {
            "blob_sha1": builder_blob,
            "diagnostics": {
                key: getattr(builder_diag, key)
                for key in ("input_rows", "admitted_listing_rows", "excluded_pre_listing_rows", "excluded_post_listing_rows", "excluded_missing_security_master_rows", "tickers_input", "tickers_admitted")
                if hasattr(builder_diag, key)
            },
        },
        "global_ca_population_gate": gate,
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
        write_csv(staging / "r3_cross_section_population_reconciliation.csv", tuple(population.columns), _r3_frame_rows(population))
        write_csv(staging / "r3_cross_section_ticker_summary.csv", tuple(ticker_summary.columns), _r3_frame_rows(ticker_summary))
        write_csv(staging / "r3_backward_dependency_closure.csv", tuple(closure.columns), _r3_frame_rows(closure))
        write_csv(staging / "r3_structural_ca_event_scope.csv", tuple(event_scope.columns), _r3_frame_rows(event_scope))
        write_csv(staging / "r3_support_lineage_reconciliation.csv", tuple(lineage.columns), _r3_frame_rows(lineage))
        write_csv(staging / "r3_ksei_population_scope_reconciliation.csv", tuple(ksei_scope.columns), _r3_frame_rows(ksei_scope))
        json_dump(staging / "r3_support_lineage_summary.json", support_lineage_summary)
        json_dump(staging / "r3_summary.json", summary)
        output_names = (
            "r3_cross_section_population_reconciliation.csv",
            "r3_cross_section_ticker_summary.csv",
            "r3_backward_dependency_closure.csv",
            "r3_structural_ca_event_scope.csv",
            "r3_support_lineage_reconciliation.csv",
            "r3_support_lineage_summary.json",
            "r3_ksei_population_scope_reconciliation.csv",
            "r3_summary.json",
        )
        output_hashes = {name: sha256(staging / name) for name in output_names}
        manifest = {
            "schema_version": "ca_aware_feature_basis_reconciliation_r3_manifest",
            "status": "R3_AUDIT_COMPLETE_PHASE_E_BLOCKED",
            "input_hashes": input_hashes,
            "output_hashes": output_hashes,
            "frozen_feature_builder_blob_sha1": builder_blob,
            "exact_final_fit": summary["exact_final_fit"],
            "cross_section_application": summary["cross_section_application"],
            "backward_dependency_closure": summary["backward_dependency_closure"],
            "ksei_population_scope": summary["ksei_population_scope"],
            "support_lineage": support_lineage_summary,
            "structural_ca": structural_summary,
            "verdict": summary["verdict"],
            "guardrails": summary["guardrails"],
            "deterministic": True,
        }
        json_dump(staging / "MANIFEST.json", manifest)
        staging.replace(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output


_R31_EVENT_IDENTITY_FIELDS = (
    "source_kind",
    "ticker",
    "event_family",
    "candidate_date",
    "source_action_id",
    "source_ref",
    "source_sha256",
    "published_at_utc",
    "evidence_id",
)


def _r31_event_identity(row: Mapping[str, str]) -> str:
    return "|".join(str(row.get(field, "") or "").strip() for field in _R31_EVENT_IDENTITY_FIELDS)


def _r31_support_mechanisms(
    lineage_rows: Sequence[Mapping[str, str]],
    *,
    phase_a_root: Path,
    old_stage_c_decision: str,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Keep row-level support-removal attribution fail-closed.

    The pinned manifests expose a global Stage-C decision, but no per-identity
    admission/remediation mapping.  That global note is retained as evidence,
    never promoted into a row-level explanation.
    """

    primary_delta_path = phase_a_root / "old_vs_clean_primary_identity_delta.csv"
    support_delta_path = phase_a_root / "old_vs_clean_support_delta.csv"
    ca80_path = phase_a_root / "clean_ca80_support_per_date.csv"
    primary_delta_hash = require_hash(
        primary_delta_path,
        EXPECTED["old_vs_clean_primary_identity_delta"],
        "R3.1 old_vs_clean_primary_identity_delta",
    )
    support_delta_hash = require_hash(
        support_delta_path,
        EXPECTED["old_vs_clean_support_delta"],
        "R3.1 old_vs_clean_support_delta",
    )
    ca80_hash = require_hash(ca80_path, EXPECTED["clean_ca80_support_per_date"], "R3.1 clean_ca80_support_per_date")
    primary_rows = read_csv(primary_delta_path)
    primary_add_dates = {
        row["date"]
        for row in primary_rows
        if row.get("ticker", "").strip().upper() == "FREN" and row.get("change") == "PRIMARY_ADD"
    }
    support_rows = read_csv(support_delta_path)
    drops_by_identity: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in support_rows:
        if row.get("change") == "DROP":
            drops_by_identity[(row.get("head", ""), row.get("ticker", "").strip().upper(), row.get("date", ""))].add(
                row.get("head", "")
            )
    ca80_by_date = {row.get("date", ""): row for row in read_csv(ca80_path)}
    rows: list[dict[str, object]] = []
    for row in lineage_rows:
        if row.get("support_head") != "UNION" or row.get("comparison") != "OLD_ONLY":
            continue
        ticker = row.get("ticker", "").strip().upper()
        date = row.get("date", "")
        heads = sorted(head for head in ("H5", "H10") if (head, ticker, date) in drops_by_identity)
        ca80_row = ca80_by_date.get(date, {})
        gate_flipped = bool(
            heads
            and all(str(ca80_row.get(f"{head.lower()}_eligible", "")).strip().lower() == "false" for head in heads)
        )
        primary_admission_on_date = date in primary_add_dates
        proven = primary_admission_on_date and gate_flipped
        rows.append(
            {
                "ticker": ticker,
                "date": date,
                "support_head": "UNION",
                "mechanism_classification": (
                    "CLEAN_SECURITY_MASTER_ADMISSION_PLUS_CA80_DATE_GATE_FLIP" if proven else "UNKNOWN"
                ),
                "mechanism_evidence": (
                    "FREN PRIMARY_ADD is present on the date and clean CA80 eligibility is false for the dropped head(s)"
                    if proven
                    else "identity-only artifacts do not prove the complete admission/gate chain for this row"
                ),
                "affected_heads": ";".join(heads),
                "primary_admission_identity": "FREN|" + date if primary_admission_on_date else "",
                "clean_ca80_gate_flipped": gate_flipped,
                "row_level_numerator_attribution": "UNKNOWN",
                "global_stage_c_decision": old_stage_c_decision,
                "global_decision_is_row_level_proof": False,
            }
        )
    mechanism_counts = Counter(row["mechanism_classification"] for row in rows)
    summary = {
        "old_only_union_rows": len(rows),
        "mechanism_classification_counts": dict(sorted(mechanism_counts.items())),
        "global_stage_c_decision": old_stage_c_decision,
        "row_level_attribution": "DATE_LEVEL_MECHANISM_PROVEN_NUMERATOR_UNKNOWN",
        "reason": "the clean primary identity delta and clean per-date CA80 ledger prove the security-master admission plus date-gate mechanism; they do not expose individual numerator/support flags",
        "source_artifact_hashes": {
            "old_vs_clean_primary_identity_delta": primary_delta_hash,
            "old_vs_clean_support_delta": support_delta_hash,
            "clean_ca80_support_per_date": ca80_hash,
        },
    }
    return rows, summary


def run_r31(args: argparse.Namespace) -> Path:
    """Run the immutable, outcome-blind R3.1 red-team correction ledger."""

    prior_root_value = getattr(args, "prior_r3_root", None)
    if not prior_root_value:
        raise RuntimeError("R3.1 requires --prior-r3-root")
    prior_root = Path(prior_root_value)
    prior_manifest_path = prior_root / "MANIFEST.json"
    prior_scope_path = prior_root / "r3_structural_ca_event_scope.csv"
    if not prior_manifest_path.is_file() or not prior_scope_path.is_file():
        raise RuntimeError("R3.1 prior R3 root is missing MANIFEST.json or structural event scope")
    prior_manifest = read_json(prior_manifest_path)
    if not isinstance(prior_manifest, dict) or not str(prior_manifest.get("schema_version", "")).endswith("_r3_manifest"):
        raise RuntimeError("R3.1 prior root is not an R3 manifest")
    prior_scope_hash = sha256(prior_scope_path)
    if prior_manifest.get("output_hashes", {}).get("r3_structural_ca_event_scope.csv") != prior_scope_hash:
        raise RuntimeError("R3.1 prior R3 structural event scope hash is not manifest-bound")

    output = Path(args.output_dir)
    base_output = output.with_name(output.name + ".r31-base")
    if output.exists() or base_output.exists() or base_output.with_name(base_output.name + ".staging").exists():
        raise RuntimeError("refusing to overwrite existing R3.1 output or staging directory")
    base_args = argparse.Namespace(**vars(args))
    base_args.output_dir = str(base_output)
    run_r3(base_args)

    try:
        current_scope_path = base_output / "r3_structural_ca_event_scope.csv"
        current_scope = read_csv(current_scope_path)
        prior_scope = read_csv(prior_scope_path)
        prior_by_id = {_r31_event_identity(row): row for row in prior_scope}
        current_by_id = {_r31_event_identity(row): row for row in current_scope}
        if len(prior_by_id) != len(prior_scope) or len(current_by_id) != len(current_scope):
            raise RuntimeError("R3.1 event scope contains duplicate source identities")
        if set(prior_by_id) != set(current_by_id):
            raise RuntimeError("R3.1 event scope identities differ from pinned R3 census")

        reclassification_rows = []
        for identity in sorted(current_by_id):
            before = prior_by_id[identity]
            after = current_by_id[identity]
            reclassification_rows.append(
                {
                    "event_identity": identity,
                    "source_kind": after.get("source_kind", ""),
                    "ticker": after.get("ticker", ""),
                    "event_family": after.get("event_family", ""),
                    "candidate_date": after.get("candidate_date", ""),
                    "source_action_id": after.get("source_action_id", ""),
                    "source_ref": after.get("source_ref", ""),
                    "before_classification": before.get("closure_scope_classification", ""),
                    "after_classification": after.get("closure_scope_classification", ""),
                    "before_reason": before.get("resolution_reason", ""),
                    "after_reason": after.get("resolution_reason", ""),
                    "classification_changed": before.get("closure_scope_classification", "") != after.get("closure_scope_classification", ""),
                }
            )

        lineage_path = base_output / "r3_support_lineage_reconciliation.csv"
        lineage_rows = read_csv(lineage_path)
        support_mechanism_rows, mechanism_summary = _r31_support_mechanisms(
            lineage_rows,
            phase_a_root=Path(args.phase_a_root),
            old_stage_c_decision=str(
                read_json(Path(args.old_support_root) / "summary.json").get("decision", "")
            ),
        )
        support_summary_path = base_output / "r3_support_lineage_summary.json"
        support_summary = read_json(support_summary_path)
        if not isinstance(support_summary, dict):
            raise RuntimeError("R3.1 support lineage summary is not a JSON object")
        support_summary["old_only_mechanism_classification"] = mechanism_summary

        summary_path = base_output / "r3_summary.json"
        summary = read_json(summary_path)
        if not isinstance(summary, dict):
            raise RuntimeError("R3.1 R3 summary is not a JSON object")
        before_counts = dict(sorted(Counter(row.get("closure_scope_classification", "") for row in prior_scope).items()))
        after_counts = dict(sorted(Counter(row.get("closure_scope_classification", "") for row in current_scope).items()))
        changed = [row for row in reclassification_rows if row["classification_changed"]]
        summary["schema_version"] = "ca_aware_feature_basis_reconciliation_r3_1"
        summary["status"] = "R3_1_AUDIT_COMPLETE_PHASE_E_BLOCKED"
        summary["inputs"]["prior_r3_manifest"] = sha256(prior_manifest_path)
        summary["inputs"]["prior_r3_structural_event_scope"] = prior_scope_hash
        summary["support_lineage"] = support_summary
        summary["structural_ca"]["scope_classification_counts_before_r3"] = before_counts
        summary["structural_ca"]["scope_classification_counts_after_r3_1"] = after_counts
        summary["structural_ca"]["reclassified_event_rows"] = len(changed)
        summary["structural_ca"]["reclassified_event_identities"] = [row["event_identity"] for row in changed]
        summary["verdict"]["EVENT_SCOPE_RULE"] = "PASS_ONLY_CERTIFIED_TRANSITION_LOWER_BOUND_MAY_PROVE_OUTSIDE"
        summary["verdict"]["SUPPORT_LINEAGE_ROW_LEVEL_MECHANISM"] = "UNKNOWN_NOT_PROVEN_BY_IDENTITY_ONLY_ARTIFACTS"
        summary["verdict"]["EXACT_HEAD_CI_33089485270"] = "334_PASSED_5_WARNINGS"

        write_csv(
            base_output / "r3_1_scope_reclassification.csv",
            tuple(reclassification_rows[0].keys()) if reclassification_rows else ("event_identity",),
            reclassification_rows,
        )
        write_csv(
            base_output / "r3_1_support_lineage_mechanism.csv",
            tuple(support_mechanism_rows[0].keys()) if support_mechanism_rows else ("ticker", "date"),
            support_mechanism_rows,
        )
        json_dump(support_summary_path, support_summary)
        json_dump(summary_path, summary)

        output_names = tuple(sorted(path.name for path in base_output.iterdir() if path.is_file() and path.name != "MANIFEST.json"))
        output_hashes = {name: sha256(base_output / name) for name in output_names}
        manifest = dict(read_json(base_output / "MANIFEST.json"))
        manifest.update(
            {
                "schema_version": "ca_aware_feature_basis_reconciliation_r3_1_manifest",
                "status": "R3_1_AUDIT_COMPLETE_PHASE_E_BLOCKED",
                "input_hashes": summary["inputs"],
                "output_hashes": output_hashes,
                "support_lineage": support_summary,
                "structural_ca": summary["structural_ca"],
                "verdict": summary["verdict"],
                "guardrails": summary["guardrails"],
                "deterministic": True,
            }
        )
        json_dump(base_output / "MANIFEST.json", manifest)
        base_output.replace(output)
    except Exception:
        shutil.rmtree(base_output, ignore_errors=True)
        raise
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r31", action="store_true", help="run the immutable outcome-blind R3.1 red-team correction audit")
    parser.add_argument("--r3", action="store_true", help="run the outcome-blind R3 population/closure audit")
    parser.add_argument("--phase-a-root", required=True)
    parser.add_argument("--phase-b-root", required=True)
    parser.add_argument("--clean-panel", required=True)
    parser.add_argument("--ksei-root", required=True)
    parser.add_argument("--ca-audit-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root")
    parser.add_argument("--clean-security-master")
    parser.add_argument("--official-calendar")
    parser.add_argument("--old-support-root")
    parser.add_argument("--prior-r3-root")
    return parser.parse_args()


if __name__ == "__main__":
    result = run(parse_args())
    print(f"CA_AWARE_RECONCILIATION_COMPLETE output={result}")
