"""Build the outcome-blind INC-001 population-authority feasibility artifact.

This is an audit report builder, not a data-acquisition or admission path.  It
binds the already retained event, geometry, and source-authority manifests,
enumerates the exact dependency geometry, and records why the retained official
sources cannot currently certify historical population completeness.  It never
reads outcomes or targets, calls a provider, mutates canonical data, or writes
production state.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping


AUDIT_DATE = "2026-08-31"
V16_MANIFEST_SHA256 = "3ff25d77dd1d2d85d1ff7526fcef90525dfe60afed026f4c2738b8bfb2a57030"
CLOSURE_MANIFEST_SHA256 = "42a1e20f29ef4028ecfaae99f032dd138511c6fd1bf5242c66c057683cc4172c"
R31_MANIFEST_SHA256 = "9075b707db70cf7e2a6fce4b504bfdf8c16369b9de75420f90d9808f1b994c2b"
V8_MANIFEST_SHA256 = "556ab328b8f5663ce98450de46e8e7eed0f9e86d42d8d51506158b5fec323b71"
MERGER_MANIFEST_SHA256 = "747c83ac3bcf6dac15e73c1e71553a0ae80422b9da0f25deb57b3139dceff6c1"
CAPITAL_MANIFEST_SHA256 = "a4f4fd188d830088cdafbb1bbcd5716ae1f92cc6fcd8314181cf9dbefa832887"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {field: "" if row.get(field) is None else row.get(field, "") for field in fields}
            )


def as_bool(value: object) -> bool:
    return str(value or "").strip().upper() in {"TRUE", "1", "YES"}


def verify_manifest(root: Path, expected_sha256: str) -> dict[str, Any]:
    manifest_path = root / "MANIFEST.json"
    actual = sha256_file(manifest_path)
    if actual != expected_sha256:
        raise RuntimeError(f"manifest mismatch for {root}: {actual} != {expected_sha256}")
    manifest = read_json(manifest_path)
    entries = manifest.get("files", [])
    if entries:
        checks = ((item["path"], item["bytes"], item["sha256"]) for item in entries)
    else:
        checks = ((name, (root / name).stat().st_size, expected) for name, expected in manifest.get("output_hashes", {}).items())
    for relative, expected_bytes, expected_file_sha256 in checks:
        path = root / relative
        if (
            not path.is_file()
            or path.stat().st_size != expected_bytes
            or sha256_file(path) != expected_file_sha256
        ):
            raise RuntimeError(f"manifest-bound file mismatch: {path}")
    return manifest


def git_head(repo_root: Path) -> str:
    return subprocess.check_output(
        [
            "git",
            f"-c",
            f"safe.directory={repo_root}",
            "-C",
            str(repo_root),
            "rev-parse",
            "HEAD",
        ],
        text=True,
    ).strip()


def _expected_int(summary: Mapping[str, Any], path: tuple[str, ...]) -> int:
    value: Any = summary
    for key in path:
        value = value[key]
    return int(value)


def build_geometry(r31_root: Path, r31_summary: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ticker_rows = read_csv(r31_root / "r3_cross_section_ticker_summary.csv")
    closure_rows = read_csv(r31_root / "r3_backward_dependency_closure.csv")
    if len(ticker_rows) != 716:
        raise RuntimeError(f"unexpected R3.1 ticker summary size: {len(ticker_rows)}")
    if len(closure_rows) != 365968:
        raise RuntimeError(f"unexpected R3.1 closure size: {len(closure_rows)}")

    application_by_ticker = {row["ticker"].strip().upper(): row for row in ticker_rows}
    if len(application_by_ticker) != 716:
        raise RuntimeError("R3.1 ticker summary contains duplicate ticker identities")

    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "closure_rows": 0,
            "closure_start": "",
            "closure_end": "",
            "families": set(),
            "direct_rows": 0,
            "primary_membership_rows": 0,
            "fit_identity_rows": 0,
            "cross_section_only_rows": 0,
        }
    )
    for row in closure_rows:
        ticker = row["ticker"].strip().upper()
        date = row["date"].strip()
        group = grouped[ticker]
        group["closure_rows"] += 1
        group["closure_start"] = min(group["closure_start"] or date, date)
        group["closure_end"] = max(group["closure_end"], date)
        group["families"].update(
            value for value in row.get("dependency_families", "").split(";") if value
        )
        group["direct_rows"] += int(as_bool(row.get("is_direct_dependency")))
        group["primary_membership_rows"] += int(as_bool(row.get("is_primary_membership_dependency")))
        group["fit_identity_rows"] += int(as_bool(row.get("is_fit_identity")))
        group["cross_section_only_rows"] += int(as_bool(row.get("is_cross_section_only")))

    if set(grouped) != set(application_by_ticker):
        raise RuntimeError("R3.1 application and dependency-closure ticker sets differ")

    requirements: list[dict[str, Any]] = []
    for ticker in sorted(application_by_ticker):
        app = application_by_ticker[ticker]
        closure = grouped[ticker]
        requirements.append(
            {
                "ticker": ticker,
                "application_rows": int(app["application_rows"]),
                "fit_union_rows": int(app["fit_union_rows"]),
                "application_start": app["application_start"],
                "application_end": app["application_end"],
                "closure_rows": closure["closure_rows"],
                "closure_start": closure["closure_start"],
                "closure_end": closure["closure_end"],
                "dependency_families": ";".join(sorted(closure["families"])),
                "direct_dependency_rows": closure["direct_rows"],
                "primary_membership_dependency_rows": closure["primary_membership_rows"],
                "fit_identity_rows": closure["fit_identity_rows"],
                "cross_section_only_rows": closure["cross_section_only_rows"],
                "ksei_present_in_retained_census": app["ksei_present"],
                "retained_ksei_coverage_status": app["ksei_coverage_status"],
                "identity_geometry_status": "OBSERVED_DEPENDENCY_GEOMETRY_ONLY",
                "population_ca_authority": "UNKNOWN",
            }
        )

    expected = {
        "fit_rows": _expected_int(r31_summary, ("exact_final_fit", "union_rows")),
        "fit_tickers": _expected_int(r31_summary, ("exact_final_fit", "union_tickers")),
        "application_rows": _expected_int(r31_summary, ("cross_section_application", "application_rows")),
        "application_tickers": _expected_int(r31_summary, ("cross_section_application", "application_tickers")),
        "cross_section_only_rows": _expected_int(r31_summary, ("cross_section_application", "cross_section_only_rows")),
        "cross_section_only_tickers": _expected_int(r31_summary, ("cross_section_application", "cross_section_only_tickers")),
        "closure_rows": _expected_int(r31_summary, ("backward_dependency_closure", "closure_rows")),
        "closure_tickers": _expected_int(r31_summary, ("backward_dependency_closure", "closure_tickers")),
        "closure_start": r31_summary["backward_dependency_closure"]["closure_start"],
        "closure_end": r31_summary["backward_dependency_closure"]["closure_end"],
    }
    computed = {
        "fit_rows": sum(int(row["fit_union_rows"]) for row in ticker_rows),
        "fit_tickers": sum(int(int(row["fit_union_rows"]) > 0) for row in ticker_rows),
        "application_rows": sum(int(row["application_rows"]) for row in ticker_rows),
        "application_tickers": len(requirements),
        "cross_section_only_rows": sum(int(row["cross_section_only_rows"]) for row in requirements),
        "cross_section_only_tickers": sum(int(int(row["cross_section_only_rows"]) > 0) for row in requirements),
        "closure_rows": sum(int(row["closure_rows"]) for row in requirements),
        "closure_tickers": len(requirements),
        "closure_start": min(row["closure_start"] for row in requirements),
        "closure_end": max(row["closure_end"] for row in requirements),
    }
    if computed != expected:
        raise RuntimeError(f"R3.1 geometry summary mismatch: {computed} != {expected}")
    return requirements, {"expected": expected, "computed": computed}


def source_capability_matrix() -> list[dict[str, str]]:
    return [
        {
            "source": "IDX GetIssuedHistory category queries",
            "capability": "positive event enumeration",
            "status": "PARTIAL_POSITIVE_RESULT_SET_ONLY",
            "evidence": "v11_idx_negative_coverage_contract.csv; retained paginated/broad probe",
            "limitation": "A returned list is not an atomic historical universe and category-filter union omitted 498 rows from the comparable broad result.",
        },
        {
            "source": "IDX GetIssuedHistory category queries",
            "capability": "explicit exhaustive no-event authority",
            "status": "UNSUPPORTED",
            "evidence": "v11_idx_negative_coverage_contract.csv",
            "limitation": "All nine retained negative contracts say UNKNOWN_NO_EXHAUSTIVE_NO_EVENT_CONTRACT; an empty response is not a negative authority.",
        },
        {
            "source": "IDX retained broad unfiltered query",
            "capability": "captured positive pagination",
            "status": "PASS_FOR_CAPTURED_RESULT_ONLY",
            "evidence": "unfiltered/paginated probe checkpoint; 700 unique rows across the captured request",
            "limitation": "No atomic snapshot, historical as-of, revision, or no-event contract is established.",
        },
        {
            "source": "KSEI registered-security history pages",
            "capability": "positive parsed event facts",
            "status": "PASS_FOR_PARSED_ROWS_ONLY",
            "evidence": "retained KSEI page census; parser-consistent page rows",
            "limitation": "Pagination completeness, observed-through/as-of, global universe, and absence semantics are not certified; 610 of 716 required tickers are present.",
        },
        {
            "source": "KSEI registered-security history pages",
            "capability": "complete interval and no-event authority",
            "status": "UNKNOWN",
            "evidence": "retained source-authority V8 matrix",
            "limitation": "567 page-only ticker observations do not establish a source-defined complete interval or explicit no-event contract.",
        },
        {
            "source": "Security Master/listing interval evidence",
            "capability": "identity and listing continuity",
            "status": "PARTIAL_PASS_FOR_IDENTITY_ONLY",
            "evidence": "R3.1 PIT identity controls and clean Security Master hash",
            "limitation": "Listing presence cannot prove that no corporate action occurred for a session/family.",
        },
        {
            "source": "OJK corporate-action statistics",
            "capability": "aggregate supervisory cross-check",
            "status": "PARTIAL_CROSS_CHECK_ONLY",
            "evidence": "official statistical publications reviewed documentary-only",
            "limitation": "The retained publication form does not establish ticker-by-session exhaustive negative coverage, PIT knowledge state, or row-level transition authority.",
        },
    ]


def counterexamples() -> list[dict[str, str]]:
    return [
        {
            "finding_id": "IDX_FILTER_OMISSION",
            "observation": "The exact nine-category filtered query union contained 202 rows while the comparable broad query contained 700 unique rows; 498 broad rows were absent from the filter union, including 290 structural/action rows and 208 IPO rows.",
            "invalid_inference": "A zero or absent category result is not a no-event assertion for the missing scope.",
            "impact": "Family-complete negative authority is not established.",
        },
        {
            "finding_id": "IDX_RESULT_DISAPPEARANCE",
            "observation": "PACK was present in the retained comparable broad result and absent from a later comparable broad result.",
            "invalid_inference": "Current absence cannot be promoted to historical no-event or historical as-of evidence.",
            "impact": "The source result is observed to be mutable without a retained revision/as-of contract.",
        },
        {
            "finding_id": "KSEI_PARTIAL_CENSUS",
            "observation": "The retained KSEI census contains 610 of 716 dependency tickers; page parsing is internally consistent for observed pages but complete interval and date-level authority are unknown.",
            "invalid_inference": "Observed page rows cannot certify the unobserved ticker/session/family population.",
            "impact": "Population completeness and historical as-of remain UNKNOWN.",
        },
        {
            "finding_id": "UNRESOLVED_TRANSITION_SEMANTICS",
            "observation": "The V16 economic ledger contains 387 events: 163 RESOLVED, 178 UNRESOLVED, and 46 NOT_APPLICABLE_NON_BASIS; the current global gate is FAIL_STRUCTURAL_CA_COVERAGE_NOT_CERTIFIED.",
            "invalid_inference": "Population authority alone cannot make unresolved basis-changing transitions safe.",
            "impact": "Historical application remains blocked by both structural transition semantics and population authority.",
        },
        {
            "finding_id": "CALLER_BOUND_GATE_INPUT",
            "observation": "global_ca_population_gate() accepts structural_event_complete as a caller boolean and only reports scope_evidence diagnostics; the current gate is still fail-closed.",
            "invalid_inference": "A future TRUE boolean must not be treated as a manifest-bound certification without binding the V16 census and validating scope evidence.",
            "impact": "Future admission requires a separate implementation-hardening check; no source/runtime change is made in this audit.",
        },
    ]


def candidate_paths() -> list[dict[str, str]]:
    return [
        {
            "candidate_id": "IDX_DATA_REFERENCE_LICENSED",
            "authority": "IDX",
            "path": "IDX Data Reference / Layanan Data BEI licensed product",
            "official_reference": "https://www.idx.id/id/produk/layanan-data-bei/",
            "documentary_capability": "The official product page describes listed-company data including corporate actions delivered as a licensed system-to-system product.",
            "missing_contract_fields": "population universe; complete interval; explicit no-event; historical knowledge/as-of; revision/amendment semantics; immutable snapshot and raw evidence binding",
            "assessment": "HIGHEST_LIKELIHOOD_CANDIDATE_NOT_ACQUIRED",
            "action_taken": "DOCUMENTARY_REVIEW_ONLY_NO_ACQUISITION",
        },
        {
            "candidate_id": "KSEI_CIRT_INSTITUTIONAL_DATA",
            "authority": "KSEI",
            "path": "KSEI CIRT / institutional corporate-action data service",
            "official_reference": "https://www.ksei.co.id/Download/SDD_CIRT_KSEI_Version_v3.0.1_XCSD-English.pdf",
            "documentary_capability": "The official CIRT design material exposes corporate-action security identifiers and activation-related fields; retained issuer pages provide positive event examples.",
            "missing_contract_fields": "full historical archive; population and pagination completeness; explicit no-event; historical as-of/revision contract; session-level binding",
            "assessment": "PLAUSIBLE_CANDIDATE_NOT_PROVABLE_FROM_PUBLIC_RETAINED_EVIDENCE",
            "action_taken": "DOCUMENTARY_REVIEW_ONLY_NO_ACQUISITION",
        },
        {
            "candidate_id": "OJK_SUPERVISORY_STATISTICS_CROSSCHECK",
            "authority": "OJK",
            "path": "OJK corporate-action statistical publications",
            "official_reference": "https://www.ojk.go.id/id/kanal/pasar-modal/data-dan-statistik/statistik-pasar-modal/Documents/2.%20STATISTIK%20MINGGU%20KE-2%20MEI%202025.pdf",
            "documentary_capability": "Official publications provide supervisory aggregate/reference observations of issuers, action types, and effective dates.",
            "missing_contract_fields": "ticker-by-session exhaustive universe; explicit no-event; PIT knowledge state; row-level transition and revision authority",
            "assessment": "CROSS_CHECK_ONLY_NOT_PRIMARY_AUTHORITY",
            "action_taken": "DOCUMENTARY_REVIEW_ONLY_NO_ACQUISITION",
        },
    ]


def build(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = args.repo_root.resolve()
    v16_root = args.v16_root.resolve()
    closure_root = args.closure_root.resolve()
    r31_root = args.r31_root.resolve()
    v8_root = args.v8_root.resolve()
    merger_root = args.merger_root.resolve()
    capital_root = args.capital_root.resolve()
    output_root = args.output_root.resolve()

    input_manifests = {
        "v16": verify_manifest(v16_root, V16_MANIFEST_SHA256),
        "closure": verify_manifest(closure_root, CLOSURE_MANIFEST_SHA256),
        "r31": verify_manifest(r31_root, R31_MANIFEST_SHA256),
        "v8": verify_manifest(v8_root, V8_MANIFEST_SHA256),
        "merger": verify_manifest(merger_root, MERGER_MANIFEST_SHA256),
        "capital": verify_manifest(capital_root, CAPITAL_MANIFEST_SHA256),
    }
    if output_root.exists():
        raise FileExistsError(f"refuse overwrite feasibility artifact: {output_root}")
    staging = output_root.with_name(output_root.name + ".staging")
    if staging.exists():
        raise FileExistsError(f"staging feasibility artifact already exists: {staging}")
    staging.mkdir(parents=True)

    try:
        v16_summary = read_json(v16_root / "reconciliation_summary.json")
        v16_validation = read_json(v16_root / "validation_report.json")
        closure_summary = read_json(closure_root / "reconciliation_summary.json")
        closure_geometry = read_json(closure_root / "geometry_analysis.json")
        r31_summary = read_json(r31_root / "r3_summary.json")
        v8_summary = read_json(v8_root / "summary.json")

        events = read_csv(v16_root / "economic_event_ledger.csv")
        status_counts = Counter(row.get("transition_status", "") for row in events)
        expected_status = Counter(
            {"RESOLVED": 163, "UNRESOLVED": 178, "NOT_APPLICABLE_NON_BASIS": 46}
        )
        if len(events) != 387 or status_counts != expected_status:
            raise RuntimeError(f"unexpected V16 event status counts: {status_counts}")
        unresolved_by_family = Counter(
            row.get("economic_family", "")
            for row in events
            if row.get("transition_status") == "UNRESOLVED"
        )
        if unresolved_by_family["MERGER"] != 5 or unresolved_by_family["CAPITAL_RESTRUCTURING"] != 19 or unresolved_by_family["COMPOSITE_CASH_SHARE_DISTRIBUTION"] != 4:
            raise RuntimeError("V16 phase-specific unresolved counts do not match current closure")

        requirements, geometry_check = build_geometry(r31_root, r31_summary)
        ksei_present = sum(as_bool(row["ksei_present_in_retained_census"]) for row in requirements)
        ksei_status_counts = Counter(row["retained_ksei_coverage_status"] for row in requirements)
        if ksei_present != 610:
            raise RuntimeError(f"unexpected retained KSEI ticker count: {ksei_present}")

        source_matrix = source_capability_matrix()
        finding_rows = counterexamples()
        candidate_rows = candidate_paths()
        current_head = git_head(repo_root)

        authority_contract = {
            "schema_version": "INC001_POPULATION_AUTHORITY_CONTRACT_V1",
            "purpose": "minimum source contract required before historical CA-aware admission",
            "identity": [
                "stable security/listing identity with PIT-valid ticker mapping",
                "listing/delisting/relisting/symbol-change semantics bound to the identity",
            ],
            "scope": [
                "one explicit row for every required (security identity, official session) in fit, application, and dependency closure",
                "all 716 application/closure tickers and exact geometry date intervals are explicitly in scope",
            ],
            "event_and_negative_semantics": [
                "complete positive enumeration for every frozen structural family",
                "explicit source-defined exhaustive no-event result for every family and interval",
                "exact transition semantics or explicit unresolved state for every basis-changing event",
            ],
            "temporal_and_revision": [
                "knowledge/as-of timestamp no later than the decision cutoff",
                "observed-through and interval boundaries",
                "revision, correction, amendment, and snapshot/version identity semantics",
            ],
            "immutable_provenance": [
                "source contract/version and request scope",
                "raw response and normalized evidence SHA-256",
                "retrieval timestamp, source-defined knowledge date, and deterministic manifest",
            ],
            "admission_rule": "UNKNOWN, malformed, incomplete, ambiguous, or unbound evidence remains blocked; absence from a current page/query is never a no-event row",
        }
        prospective_contract = {
            "historical_application": "BLOCKED",
            "prospective_status": "CONDITIONALLY_POSSIBLE_NOT_CURRENTLY_PROVEN",
            "minimum_future_evidence": [
                "runtime emits immutable per-session population and family coverage attestations before canonical EOD",
                "explicit no-event and complete-interval semantics are source-defined",
                "knowledge/as-of is before the decision cutoff and revisions are append-only/versioned",
                "transition semantics are resolved or the row is fail-closed unknown",
                "the existing gate binds the event census, scope evidence, geometry, and all evidence hashes",
            ],
            "do_not_infer": "A future source response, current Security Master presence, or empty category query is not prospective proof by itself.",
        }
        input_manifest = {
            "schema_version": "INC001_POPULATION_AUTHORITY_FEASIBILITY_INPUT_MANIFEST_V1",
            "audit_date": AUDIT_DATE,
            "review_repository": str(repo_root),
            "review_repository_head": current_head,
            "inputs": {
                "v16": {"root": str(v16_root), "manifest_sha256": V16_MANIFEST_SHA256},
                "closure": {"root": str(closure_root), "manifest_sha256": CLOSURE_MANIFEST_SHA256},
                "r31": {"root": str(r31_root), "manifest_sha256": R31_MANIFEST_SHA256},
                "source_authority_v8": {"root": str(v8_root), "manifest_sha256": V8_MANIFEST_SHA256},
                "merger": {"root": str(merger_root), "manifest_sha256": MERGER_MANIFEST_SHA256},
                "capital": {"root": str(capital_root), "manifest_sha256": CAPITAL_MANIFEST_SHA256},
            },
            "embedded_artifact_repository_heads_are_historical_metadata": True,
        }
        summary = {
            "schema_version": "INC001_POPULATION_AUTHORITY_FEASIBILITY_V1",
            "audit_date": AUDIT_DATE,
            "status": "FEASIBILITY_REVIEW_COMPLETE_HISTORICAL_ADMISSION_BLOCKED",
            "review_repository": {"head": current_head, "outcome_blind": True},
            "red_team": {
                "known_event_closure_verdict": "PASS_WITH_NONBLOCKING_FINDINGS",
                "known_event_work_disposition": "MATERIAL_WORK_COMPLETE",
                "known_event_long_tail": "PARKED_FAIL_CLOSED",
                "qualification": "The work disposition is supported, but 'population authority is the sole blocker' is incomplete for admission because 178 transition semantics remain explicitly unresolved and the existing gate requires structural_event_complete.",
                "current_gate_verdict": "FAIL_STRUCTURAL_CA_COVERAGE_NOT_CERTIFIED",
            },
            "reconciliation": {
                "v16_manifest_sha256": V16_MANIFEST_SHA256,
                "v16_event_count": len(events),
                "transition_status_counts": dict(sorted(status_counts.items())),
                "unresolved_by_family": dict(sorted(unresolved_by_family.items())),
                "closure_manifest_sha256": CLOSURE_MANIFEST_SHA256,
                "closure_verdict_in_retained_artifact": closure_summary["closure_verdict"],
                "closure_geometry_is_existing_r31_not_current_event_census": closure_geometry["geometry_is_not_current_event_census"],
                "v16_deterministic_replay": bool(v16_validation["deterministic_frozen_replay"]),
            },
            "dependency_geometry": {
                "r31_manifest_sha256": R31_MANIFEST_SHA256,
                "fit_rows": geometry_check["computed"]["fit_rows"],
                "fit_tickers": geometry_check["computed"]["fit_tickers"],
                "application_rows": geometry_check["computed"]["application_rows"],
                "application_tickers": geometry_check["computed"]["application_tickers"],
                "cross_section_only_rows": geometry_check["computed"]["cross_section_only_rows"],
                "cross_section_only_tickers": geometry_check["computed"]["cross_section_only_tickers"],
                "dependency_closure_rows": geometry_check["computed"]["closure_rows"],
                "dependency_closure_tickers": geometry_check["computed"]["closure_tickers"],
                "closure_date_range": [geometry_check["computed"]["closure_start"], geometry_check["computed"]["closure_end"]],
                "ksei_present_tickers": ksei_present,
                "ksei_coverage_status_counts": dict(sorted(ksei_status_counts.items())),
                "subset_verdict": "NO_SAME_SCIENCE_CERTIFIABLE_SUBSET_ESTABLISHED",
                "subset_reason": "V4 cross-sectional ranks and market context are computed across the full primary-liquid application population; excluding uncertified tickers post hoc would change the frozen population and derived features.",
            },
            "authority_contract": authority_contract,
            "source_feasibility": {
                "retained_official_sources_verdict": "EXISTING_OFFICIAL_SOURCES_CANNOT_CERTIFY_POPULATION_COMPLETENESS",
                "population_completeness": "UNKNOWN",
                "historical_asof": "UNKNOWN",
                "idx_negative_authority": "UNSUPPORTED",
                "ksei_complete_interval_authority": "UNKNOWN",
                "source_authority_manifest_sha256": V8_MANIFEST_SHA256,
            },
            "official_candidate_assessment": {
                "phase": "DOCUMENTARY_ONLY_AFTER_RETAINED_SOURCE_INSUFFICIENCY",
                "candidate_count": len(candidate_rows),
                "no_candidate_acquired": True,
            },
            "historical_vs_prospective": {
                "historical_inc001": "BLOCKED_ON_POPULATION_AUTHORITY_AND_UNRESOLVED_TRANSITION_SEMANTICS",
                "prospective": prospective_contract["prospective_status"],
                "prospective_contract": prospective_contract,
            },
            "next_decision": {
                "recommendation": "Obtain the smallest authoritative population-wide complete-interval, explicit-no-event, historical-as-of, and revision contract; bind it to the existing fail-closed gate and V16 transition census before any admission.",
                "executed": False,
            },
            "guardrails": {
                "provider_calls": False,
                "outcomes_or_targets": False,
                "model_or_refit": False,
                "counter_or_paper_state": False,
                "canonical_historical_rewrite": False,
                "production_or_backfill": False,
                "source_credentials": False,
            },
        }
        validation = {
            "schema_version": "INC001_POPULATION_AUTHORITY_FEASIBILITY_VALIDATION_V1",
            "input_manifests_verified": all(bool(value) for value in input_manifests.values()),
            "v16_counts_verified": len(events) == 387 and status_counts == expected_status,
            "v16_phase_counts_verified": unresolved_by_family["MERGER"] == 5 and unresolved_by_family["CAPITAL_RESTRUCTURING"] == 19 and unresolved_by_family["COMPOSITE_CASH_SHARE_DISTRIBUTION"] == 4,
            "r31_geometry_recomputed_from_retained_csv": geometry_check["computed"] == geometry_check["expected"],
            "r31_geometry_expected_716_tickers": len(requirements) == 716,
            "ksei_retained_presence_verified_610": ksei_present == 610,
            "source_negative_contract_remains_unknown": v8_summary["phase_e_gate"]["negative_coverage"] is False,
            "historical_gate_remains_stop": v8_summary["phase_e_gate"]["verdict"] == "STOP",
            "no_provider_or_scientific_admission": True,
            "deterministic_serialization": True,
        }

        fields = list(requirements[0])
        write_csv(staging / "dependency_authority_requirements.csv", requirements, fields)
        write_json(staging / "authority_contract.json", authority_contract)
        write_csv(staging / "source_capability_matrix.csv", source_matrix, list(source_matrix[0]))
        write_csv(staging / "completeness_counterexamples.csv", finding_rows, list(finding_rows[0]))
        write_csv(staging / "official_candidate_paths.csv", candidate_rows, list(candidate_rows[0]))
        write_json(staging / "prospective_contract.json", prospective_contract)
        write_json(staging / "input_manifest.json", input_manifest)
        write_json(staging / "summary.json", summary)
        write_json(staging / "validation_report.json", validation)

        manifest = {
            "schema_version": "INC001_POPULATION_AUTHORITY_FEASIBILITY_MANIFEST_V1",
            "audit_date": AUDIT_DATE,
            "self_hash_policy": "MANIFEST.json excluded from its own hash",
            "files": [],
        }
        for path in sorted(staging.rglob("*")):
            if path.is_file() and path.name != "MANIFEST.json":
                manifest["files"].append(
                    {
                        "path": path.relative_to(staging).as_posix(),
                        "bytes": path.stat().st_size,
                        "sha256": sha256_file(path),
                    }
                )
        write_json(staging / "MANIFEST.json", manifest)
        staging.replace(output_root)
        return {
            "artifact_root": str(output_root),
            "artifact_manifest_sha256": sha256_file(output_root / "MANIFEST.json"),
            "repository_head": current_head,
            "validation": validation,
        }
    except Exception:
        for path in sorted(staging.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        staging.rmdir()
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--v16-root", type=Path, required=True)
    parser.add_argument("--closure-root", type=Path, required=True)
    parser.add_argument("--r31-root", type=Path, required=True)
    parser.add_argument("--v8-root", type=Path, required=True)
    parser.add_argument("--merger-root", type=Path, required=True)
    parser.add_argument("--capital-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(build(parse_args()), indent=2, sort_keys=True))
