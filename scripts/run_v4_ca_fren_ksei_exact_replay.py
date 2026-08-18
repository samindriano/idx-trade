"""Final offline FREN remediation using pinned official KSEI rights evidence.

Inputs are immutable accepted material-six/ADRO parents plus a saved evidence
root produced by the bounded FREN probes.  No network call is made here.

Certification basis:
- issuer-official Smartfren archives establish the frozen mechanical-event
  census: PMHMETD V in 2024 and merger/security cessation in 2025;
- the pinned KSEI Rights Distribution PDF explicitly states the 2024-04-17
  Regular/Negotiated Market ex-right date, together with cum, record,
  distribution, trading dates and the 178:75 ratio;
- the already accepted parent merger evidence supplies the exact 2025-04-16
  terminal transition.

Record-date subtraction, price inference, EXCL stitching, model fitting,
prediction generation and protected-forward access remain forbidden.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = Path(__file__).resolve().parent
for value in (SRC_ROOT, SCRIPTS_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import pandas as pd

import run_v4_ca_fren_official_archive_replay as base
from idx_trade.v4_ca_fren_archive_semantics import (
    FREN_MERGER_DATE,
    FREN_RIGHT_EX_DATE,
    SMARTFREN_CORPORATE_ACTION_2024_URL,
    combined_evidence_sha,
    verify_smartfren_archive_pages,
)
from idx_trade.v4_ca_fren_ksei_schedule_semantics import (
    EXPECTED_KSEI_RIGHTS_INDEX_SHA256,
    EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256,
    KSEI_RIGHTS_SCHEDULE_URL,
    synthetic_fren_rights_event_ksei,
    verify_ksei_fren_rights_schedule_pdf,
)
from idx_trade.v4_ksei_coverage_gap import sha256_file


EXPECTED_FREN_ROWS = 604
EXPECTED_COVERAGE_CERTIFIED = 602
EXPECTED_COVERAGE_UNRESOLVED = 9
EXPECTED_PROBE_SCHEMA = "fren_ksei_official_rights_schedule_probe_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--material-six-root", type=Path, required=True)
    parser.add_argument("--adro-root", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--prior-event-evidence", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def verify_saved_evidence(root: Path) -> dict[str, object]:
    paths = {
        "corporate_action_2024": root / "raw" / "official_archive" / "corporate_action_2024.html",
        "disclosure_2024": root / "raw" / "official_archive" / "disclosure_2024.html",
        "merger_archive": root / "raw" / "official_archive" / "merger_archive.html",
        "investor_about": root / "raw" / "official_archive" / "investor_about.html",
        "ksei_index": root / "raw" / "ksei_rights_schedule_probe" / "ksei_rights_april_2024.html",
        "ksei_pdf": root / "raw" / "ksei_rights_schedule_probe" / "fren_ksei_schedule_01.pdf",
        "probe": root / "fren_ksei_rights_schedule_probe.json",
    }
    missing = [f"{label}:{path}" for label, path in paths.items() if not path.is_file()]
    if missing:
        raise RuntimeError(f"FREN_FINAL_SAVED_EVIDENCE_MISSING:{missing}")

    if sha256_file(paths["ksei_index"]) != EXPECTED_KSEI_RIGHTS_INDEX_SHA256:
        raise RuntimeError("FREN_FINAL_KSEI_RIGHTS_INDEX_SHA_CHANGED")
    if sha256_file(paths["ksei_pdf"]) != EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256:
        raise RuntimeError("FREN_FINAL_KSEI_RIGHTS_PDF_SHA_CHANGED")

    probe = json.loads(paths["probe"].read_text(encoding="utf-8"))
    if probe.get("schema_version") != EXPECTED_PROBE_SCHEMA or probe.get("verified") is not True:
        raise RuntimeError("FREN_FINAL_KSEI_PROBE_NOT_VERIFIED")
    verified_pdf = probe.get("verified_pdf") or {}
    if str(verified_pdf.get("sha256") or "") != EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256:
        raise RuntimeError("FREN_FINAL_KSEI_PROBE_PDF_SHA_MISMATCH")
    if str(verified_pdf.get("url") or "") != KSEI_RIGHTS_SCHEDULE_URL:
        raise RuntimeError("FREN_FINAL_KSEI_PROBE_URL_MISMATCH")

    issuer = dict(
        verify_smartfren_archive_pages(
            paths["corporate_action_2024"].read_bytes(),
            paths["disclosure_2024"].read_bytes(),
            paths["merger_archive"].read_bytes(),
            paths["investor_about"].read_bytes(),
        )
    )
    issuer["mechanical_census_method"] = (
        "ISSUER_OFFICIAL_ARCHIVE_MECHANICAL_CENSUS_PLUS_KSEI_OFFICIAL_RIGHTS_SCHEDULE"
    )
    rights = verify_ksei_fren_rights_schedule_pdf(paths["ksei_pdf"].read_bytes())

    probe_semantics = verified_pdf.get("semantics") or {}
    for key in (
        "transition_date",
        "transition_semantic",
        "cum_regular_negotiated",
        "record_date",
        "distribution_date",
        "trading_start",
        "trading_end",
        "ratio",
        "reference_no",
    ):
        if str(probe_semantics.get(key)) != str(rights.get(key)):
            raise RuntimeError(f"FREN_FINAL_PROBE_SEMANTIC_MISMATCH:{key}")

    evidence_payloads = [
        paths["corporate_action_2024"].read_bytes(),
        paths["disclosure_2024"].read_bytes(),
        paths["merger_archive"].read_bytes(),
        paths["investor_about"].read_bytes(),
        paths["ksei_index"].read_bytes(),
        paths["ksei_pdf"].read_bytes(),
    ]
    evidence_sha = combined_evidence_sha(evidence_payloads)
    return {
        "paths": paths,
        "issuer_semantics": issuer,
        "rights_semantics": rights,
        "combined_evidence_sha256": evidence_sha,
        "probe_sha256": sha256_file(paths["probe"]),
        "source_hashes": {label: sha256_file(path) for label, path in paths.items()},
    }


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    if not args.prior_event_evidence.is_file() or not args.official_calendar.is_file():
        raise RuntimeError("FREN_FINAL_REQUIRED_FROZEN_INPUT_MISSING")

    parent = base.verify_parent_roots(args.material_six_root, args.adro_root)
    evidence = verify_saved_evidence(args.evidence_root)
    issuer_semantics = dict(evidence["issuer_semantics"])
    rights_semantics = dict(evidence["rights_semantics"])
    evidence_sha = str(evidence["combined_evidence_sha256"])

    args.output_dir.mkdir(parents=True)
    attestation = {
        "schema_version": "v4_ca_fren_ksei_exact_attestation_v1",
        "status": "FREN_OFFICIAL_ARCHIVE_PLUS_KSEI_EXACT_MECHANICAL_HISTORY_CERTIFIED",
        "outcome_blind": True,
        "offline_replay": True,
        "network_calls": False,
        "static_ksei_registered_security_recovered": False,
        "source_substitution_disclosed": True,
        "coverage_basis": issuer_semantics["mechanical_census_method"],
        "mechanical_events": [
            {
                "family": "RIGHT_DISTRIBUTION_PMHMETD_V",
                "transition_date": FREN_RIGHT_EX_DATE.date().isoformat(),
                "source": "OFFICIAL_KSEI_RIGHTS_DISTRIBUTION_SCHEDULE",
                "transition_semantic": rights_semantics["transition_semantic"],
                "source_url": rights_semantics["source_url"],
                "source_sha256": rights_semantics["source_sha256"],
            },
            {
                "family": "MERGER_SECURITY_CESSATION",
                "transition_date": FREN_MERGER_DATE.date().isoformat(),
                "source": "PINNED_PARENT_ISSUER_OFFICIAL_MERGER_EVIDENCE",
            },
        ],
        "issuer_archive": issuer_semantics,
        "rights_semantics": rights_semantics,
        "ksei_rights_index_sha256": EXPECTED_KSEI_RIGHTS_INDEX_SHA256,
        "ksei_rights_pdf_sha256": EXPECTED_KSEI_RIGHTS_SCHEDULE_SHA256,
        "probe_sha256": evidence["probe_sha256"],
        "saved_source_hashes": evidence["source_hashes"],
        "combined_evidence_sha256": evidence_sha,
        "no_price_inference": True,
        "no_record_date_inference": True,
        "no_excl_price_stitching": True,
    }
    attestation_path = args.output_dir / "fren_ksei_exact_attestation.json"
    attestation_path.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    census = args.output_dir / "fren_ksei_exact_census_611"
    census.mkdir()
    coverage = pd.read_csv(parent["coverage"])
    mask = coverage["ticker"].astype(str).str.upper().eq("FREN")
    if int(mask.sum()) != 1:
        raise RuntimeError("FREN_FINAL_PARENT_COVERAGE_ROW_IDENTITY_CHANGED")
    if str(coverage.loc[mask, "coverage_certified"].iloc[0]).casefold() != "false":
        raise RuntimeError("FREN_FINAL_PARENT_ALREADY_CERTIFIED_UNEXPECTEDLY")

    coverage.loc[mask, "coverage_status"] = "OFFICIAL_ARCHIVE_PLUS_KSEI_EXACT_MECHANICAL_HISTORY_CERTIFIED"
    coverage.loc[mask, "coverage_certified"] = True
    coverage.loc[mask, "attempt_count"] = 0
    coverage.loc[mask, "final_http_status"] = 200
    coverage.loc[mask, "source_url"] = KSEI_RIGHTS_SCHEDULE_URL
    coverage.loc[mask, "source_sha256"] = evidence_sha
    coverage.loc[mask, "ca_rows"] = 2
    coverage.loc[mask, "active_ca_rows"] = 2
    coverage.loc[mask, "active_mechanical_rows"] = 2
    coverage.loc[mask, "active_unknown_rows"] = 0
    coverage.loc[mask, "earliest_ca_date"] = FREN_RIGHT_EX_DATE.date().isoformat()
    coverage.loc[mask, "latest_ca_date"] = FREN_MERGER_DATE.date().isoformat()
    coverage.loc[mask, "failure_reason"] = ""

    coverage_path = census / "ticker_coverage.csv"
    coverage.to_csv(coverage_path, index=False, lineterminator="\n")
    history_path = census / "ksei_ca_history.jsonl"
    shutil.copyfile(parent["history"], history_path)

    census_summary = {
        "schema_version": "v4_ca_fren_ksei_exact_census_v1",
        "status": "COMPLETE",
        "outcome_blind": True,
        "offline_replay": True,
        "tickers": int(coverage["ticker"].nunique()),
        "coverage_certified_tickers": int(
            coverage["coverage_certified"].astype(str).str.casefold().eq("true").sum()
        ),
        "fren_source_method": issuer_semantics["mechanical_census_method"],
        "fren_attestation_sha256": sha256_file(attestation_path),
        "parent_ksei_history_unchanged": sha256_file(history_path) == base.EXPECTED_MATERIAL_HISTORY,
        "output_hashes": {
            "ticker_coverage": sha256_file(coverage_path),
            "ksei_ca_history": sha256_file(history_path),
        },
    }
    census_summary_path = census / "summary.json"
    census_summary_path.write_text(json.dumps(census_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    census_manifest = {
        "schema_version": "v4_ca_fren_ksei_exact_census_manifest_v1",
        "status": "COMPLETE",
        "outcome_blind": True,
        "summary_sha256": sha256_file(census_summary_path),
        "output_hashes": census_summary["output_hashes"],
    }
    census_manifest_path = census / "MANIFEST.json"
    census_manifest_path.write_text(json.dumps(census_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    material_summary = json.loads(parent["material_summary"].read_text(encoding="utf-8"))
    fren_merger_sha = str((material_summary.get("fren_official_evidence") or {}).get("source_sha256") or "")
    mega_sha = str((material_summary.get("mega_official_evidence") or {}).get("source_sha256") or "")
    if not fren_merger_sha or not mega_sha:
        raise RuntimeError("FREN_FINAL_PARENT_SYNTHETIC_EVIDENCE_SHA_MISSING")
    adro_evidence = base.verify_adro_official_documents(
        parent["adro_prospectus"].read_bytes(), parent["adro_egms"].read_bytes()
    )

    frozen = base.frozen
    frozen.PINNED = dict(frozen.PINNED)
    frozen.PINNED["continuity_ledger"] = sha256_file(parent["ledger"])
    frozen.PINNED["ksei_manifest"] = sha256_file(census_manifest_path)
    frozen.PINNED["ksei_summary"] = sha256_file(census_summary_path)
    frozen.PINNED["ksei_coverage"] = sha256_file(coverage_path)
    frozen.PINNED["ksei_history"] = sha256_file(history_path)
    frozen.EXPECTED_TICKERS = base.EXPECTED_TICKERS
    frozen.EXPECTED_ROWS = base.EXPECTED_ROWS
    frozen.EXPECTED_DATES = base.EXPECTED_DATES
    frozen.classify_event = base.make_classifier(adro_evidence, fren_merger_sha)

    original_prior = frozen.prior_candidate_tickers
    original_build = frozen.build_events

    def prior_candidate_tickers_fren(prior_frame, *, period_start, period_end):
        result = set(original_prior(prior_frame, period_start=period_start, period_end=period_end))
        if "SCMA" in result:
            base.material_base.validate_scma_halo_only(prior_frame, max_terminal=pd.Timestamp(period_end))
            result.remove("SCMA")
        return result

    rights_event = synthetic_fren_rights_event_ksei(str(rights_semantics["source_sha256"]))

    def build_events_fren(*inner_args, **inner_kwargs):
        by_ticker, audit = original_build(*inner_args, **inner_kwargs)
        rows = audit.to_dict("records")
        additions = (
            (base.material_base.synthetic_mega_event(mega_sha), "MEGA_ISSUER_OFFICIAL"),
            (base.material_base.synthetic_fren_event(fren_merger_sha), "FREN_ISSUER_OFFICIAL_MERGER"),
            (rights_event, "FREN_KSEI_OFFICIAL_PMHETD_V_EX_RIGHT"),
        )
        for event, marker in additions:
            by_ticker.setdefault(event.ticker, []).append(event)
            rows.append(
                {
                    "event_id": event.event_id,
                    "ticker": event.ticker,
                    "source_type": event.source_type,
                    "family": event.family,
                    "semantic_class": event.semantic_class,
                    "transition_date": event.transition_date.date().isoformat() if event.transition_date is not None else "",
                    "transition_source": event.transition_source or "",
                    "reason": event.reason,
                    "source_dates": "|".join(v.date().isoformat() for v in event.source_dates),
                    "material_six_source_marker": marker,
                }
            )
        result = pd.DataFrame(rows).fillna("")
        return by_ticker, result.sort_values(
            ["ticker", "source_dates", "source_type", "event_id"], kind="mergesort"
        ).reset_index(drop=True)

    frozen.prior_candidate_tickers = prior_candidate_tickers_fren
    frozen.build_events = build_events_fren

    replay_root = args.output_dir / "final_continuity_611_fren_ksei_exact"
    original_argv = list(sys.argv)
    try:
        sys.argv = [
            original_argv[0],
            "--continuity-ledger", str(parent["ledger"]),
            "--prior-event-evidence", str(args.prior_event_evidence),
            "--official-calendar", str(args.official_calendar),
            "--ksei-census-root", str(census),
            "--schedule-evidence", str(parent["schedule"]),
            "--output-dir", str(replay_root),
        ]
        replay_result = int(frozen.main() or 0)
    finally:
        sys.argv = original_argv

    final_summary_path = replay_root / "summary.json"
    final_summary = json.loads(final_summary_path.read_text(encoding="utf-8"))
    window_path = replay_root / "v4_frozen_continuity_ledger_event_window.csv"
    window = pd.read_csv(window_path)
    fren = window[window["ticker"].astype(str).str.upper().eq("FREN")].copy()
    if len(fren) != EXPECTED_FREN_ROWS:
        raise RuntimeError(f"FREN_FINAL_WINDOW_ROW_COUNT_CHANGED:{len(fren)}")
    for col in ("entry_date", "terminal_date"):
        fren[col] = pd.to_datetime(fren[col], errors="raise").dt.normalize()

    resolved = fren["continuity_status"].eq("RESOLVED_NO_MECHANICAL_DISCONTINUITY")
    crossing = fren["continuity_reason"].eq("TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION")
    unexpected = fren.loc[~resolved & ~crossing]
    if not unexpected.empty:
        raise RuntimeError(
            "FREN_FINAL_NON_MECHANICAL_UNRESOLVED_REASON:"
            + str(sorted(unexpected["continuity_reason"].astype(str).unique()))
        )

    right_cross = (fren["entry_date"] < FREN_RIGHT_EX_DATE) & (fren["terminal_date"] >= FREN_RIGHT_EX_DATE)
    merger_cross = (fren["entry_date"] < FREN_MERGER_DATE) & (fren["terminal_date"] >= FREN_MERGER_DATE)
    if int(right_cross.sum()) <= 0 or int(merger_cross.sum()) <= 0:
        raise RuntimeError("FREN_FINAL_EXPECTED_MECHANICAL_CROSSINGS_NOT_OBSERVED")

    if int(final_summary.get("coverage_certified_tickers") or 0) != EXPECTED_COVERAGE_CERTIFIED:
        raise RuntimeError("FREN_FINAL_CERTIFIED_TICKER_COUNT_UNEXPECTED")
    if int(final_summary.get("coverage_unresolved_tickers") or 0) != EXPECTED_COVERAGE_UNRESOLVED:
        raise RuntimeError("FREN_FINAL_UNRESOLVED_TICKER_COUNT_UNEXPECTED")

    event_audit_path = replay_root / "event_semantics_audit.csv"
    event_audit = pd.read_csv(event_audit_path, dtype=str, keep_default_na=False)
    fren_events = event_audit[event_audit["ticker"].eq("FREN")].to_dict("records")
    exact = {
        row.get("transition_date"): row
        for row in fren_events
        if row.get("semantic_class") == "EXACT_TRANSITION"
    }
    if "2024-04-17" not in exact or "2025-04-16" not in exact:
        raise RuntimeError(f"FREN_FINAL_EXACT_TRANSITIONS_MISSING:{sorted(exact)}")
    right_audit = exact["2024-04-17"]
    if right_audit.get("transition_source") != "OFFICIAL_KSEI_REGULAR_NEGOTIATED_MARKET_EX_RIGHT_DATE":
        raise RuntimeError("FREN_FINAL_RIGHT_TRANSITION_SOURCE_NOT_KSEI_EXPLICIT")

    overlay = {
        "schema_version": "v4_ca_fren_ksei_exact_replay_v1",
        "status": "V4_CA_FREN_KSEI_EXACT_REPLAY_COMPLETE",
        "outcome_blind": True,
        "offline_replay": True,
        "network_calls": False,
        "provider_calls": False,
        "coverage_certified": True,
        "coverage_source_method": issuer_semantics["mechanical_census_method"],
        "static_ksei_registered_security_recovered": False,
        "rights_transition_date": FREN_RIGHT_EX_DATE.date().isoformat(),
        "rights_transition_source": rights_semantics["transition_semantic"],
        "rights_reference_no": rights_semantics["reference_no"],
        "rights_pdf_sha256": rights_semantics["source_sha256"],
        "merger_transition_date": FREN_MERGER_DATE.date().isoformat(),
        "fren_window_rows": int(len(fren)),
        "fren_resolved_window_rows": int(resolved.sum()),
        "fren_crossing_window_rows": int(crossing.sum()),
        "fren_right_crossing_rows": int(right_cross.sum()),
        "fren_merger_crossing_rows": int(merger_cross.sum()),
        "fren_resolved_window_rate": float(resolved.mean()),
        "fren_event_semantics": fren_events,
        "final_continuity": {
            "verdict": final_summary.get("verdict"),
            "corporate_action_continuity_certified": final_summary.get("corporate_action_continuity_certified"),
            "coverage_certified_tickers": final_summary.get("coverage_certified_tickers"),
            "coverage_unresolved_tickers": final_summary.get("coverage_unresolved_tickers"),
            "cross_source_conflict_tickers": final_summary.get("cross_source_conflict_tickers"),
            "schedule_required_events": final_summary.get("schedule_required_events"),
            "schedule_required_tickers": final_summary.get("schedule_required_tickers"),
            "per_date": final_summary.get("per_date"),
        },
        "attestation_sha256": sha256_file(attestation_path),
        "census_manifest_sha256": sha256_file(census_manifest_path),
        "continuity_summary_sha256": sha256_file(final_summary_path),
        "continuity_window_sha256": sha256_file(window_path),
        "event_semantics_sha256": sha256_file(event_audit_path),
        "parent_material_manifest_sha256": base.EXPECTED_MATERIAL_MANIFEST,
        "parent_adro_manifest_sha256": base.EXPECTED_ADRO_MANIFEST,
        "model_fit": False,
        "performance_computed": False,
        "prediction_generated": False,
        "target_or_rank_materialized": False,
        "protected_forward_accessed": False,
        "price_inference": False,
        "record_date_inference": False,
        "excl_price_stitching": False,
    }
    overlay_path = args.output_dir / "fren_ksei_exact_overlay.json"
    overlay_path.write_text(json.dumps(overlay, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": "v4_ca_fren_ksei_exact_manifest_v1",
        "status": overlay["status"],
        "outcome_blind": True,
        "offline_replay": True,
        "overlay_sha256": sha256_file(overlay_path),
        "attestation_sha256": sha256_file(attestation_path),
        "census_manifest_sha256": sha256_file(census_manifest_path),
        "continuity_summary_sha256": sha256_file(final_summary_path),
        "continuity_window_sha256": sha256_file(window_path),
        "event_semantics_sha256": sha256_file(event_audit_path),
        "parent_material_manifest_sha256": base.EXPECTED_MATERIAL_MANIFEST,
        "parent_adro_manifest_sha256": base.EXPECTED_ADRO_MANIFEST,
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({**overlay, "manifest_sha256": sha256_file(manifest_path)}, indent=2, sort_keys=True))
    return replay_result


if __name__ == "__main__":
    raise SystemExit(main())
