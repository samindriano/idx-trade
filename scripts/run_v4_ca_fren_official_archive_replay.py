"""FREN-only official-archive remediation over the accepted 611-ticker support.

This runner consumes the successful material-six and ADRO roots as immutable
parents. It does not recrawl the legacy FREN KSEI registered-security page.
Instead, it attempts a bounded issuer/KSEI archival mechanical-event census,
requires an issuer-official PMHMETD V PDF to state the exact Regular/Negotiated
Market ex-right date, preserves the already-proven 2025 merger boundary, marks
FREN coverage certified only if all archival checks pass, and replays the
unchanged 90% continuity gate outcome-blind.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any
from urllib.parse import urljoin, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = Path(__file__).resolve().parent
for value in (SRC_ROOT, SCRIPTS_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import pandas as pd
import requests

import run_v4_ca_event_window_support as frozen
import run_v4_ca_material_six_remediation as material_base
import run_v4_ca_material_six_remediation_v3 as material_v3
from idx_trade.v4_ca_adro_entitlement_semantics import (
    apply_adro_entitlement_evidence,
    verify_adro_official_documents,
)
from idx_trade.v4_ca_event_windows import EventSemantic
from idx_trade.v4_ca_fren_archive_semantics import (
    FREN_MERGER_DATE,
    FREN_RIGHT_EX_DATE,
    KSEI_MERGER_DISTRIBUTION_URL,
    KSEI_MERGER_RECORD_URL,
    KSEI_MERGER_REPORT_URL,
    KSEI_RIGHT_DISTRIBUTION_URL,
    KSEI_RIGHT_RECORD_URL,
    SMARTFREN_2024_ANNUAL_REPORT_PDF,
    SMARTFREN_ANNUAL_REPORT_URL,
    SMARTFREN_CORPORATE_ACTION_2024_URL,
    SMARTFREN_DISCLOSURE_2024_URL,
    SMARTFREN_INVESTOR_ABOUT_URL,
    SMARTFREN_MERGER_ARCHIVE_URL,
    SMARTFREN_PROSPECTUS_PAGE_URL,
    combined_evidence_sha,
    extract_official_pdf_urls,
    synthetic_fren_rights_event,
    verify_ksei_merger_pages,
    verify_ksei_right_pages,
    verify_rights_prospectus,
    verify_smartfren_archive_pages,
)
from idx_trade.v4_ksei_coverage_gap import sha256_file


EXPECTED_MATERIAL_MANIFEST = "c26b9e60f17b181016cd2ee4c30720ef4a4323b82603a5a0c9c01ea0fd175a4c"
EXPECTED_ADRO_MANIFEST = "8a952e0e94ed2b99a7fb3f6bcfb60d30e8be7df928f1bad6f8f9d46a01a600c9"
EXPECTED_EXPANDED_LEDGER = "5139cbb39e34fd46b6214435b1bc6bb937ec1e5400ec268376e412bdd2225426"
EXPECTED_MATERIAL_COVERAGE = "44f7b9e9f7e02e5f2dacaf27f5ded3aa1d41d4ce61664725db096f7a28a93081"
EXPECTED_MATERIAL_HISTORY = "4dcdd9e44cc40e348079c1447aa3e1e20427b000247be5be91b6622fb03e997d"
EXPECTED_TICKERS = 611
EXPECTED_ROWS = 345_394
EXPECTED_DATES = 600
EXPECTED_FREN_ROWS = 604


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--material-six-root", type=Path, required=True)
    parser.add_argument("--adro-root", type=Path, required=True)
    parser.add_argument("--prior-event-evidence", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def get(url: str, path: Path) -> tuple[bytes, dict[str, Any]]:
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 IDX-Trade-V4-FREN-Archive/1.0"},
        timeout=45,
        allow_redirects=True,
    )
    payload = bytes(response.content or b"")
    record = {
        "url": url,
        "final_url": str(response.url),
        "status_code": int(response.status_code),
        "bytes": len(payload),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    if payload:
        path.write_bytes(payload)
        record["sha256"] = sha256_file(path)
    if response.status_code != 200 or not payload:
        raise RuntimeError(f"FREN_OFFICIAL_FETCH_FAILED:{record}")
    return payload, record


def hrefs(payload: bytes, base_url: str) -> tuple[str, ...]:
    raw = payload.decode("utf-8", errors="ignore")
    output: set[str] = set()
    for match in re.finditer(r'''href\s*=\s*["']([^"']+)["']''', raw, re.I):
        url = urljoin(base_url, html.unescape(match.group(1)))
        parsed = urlparse(url)
        if parsed.scheme in {"http", "https"} and parsed.netloc.lower().endswith("smartfren.com"):
            output.add(url)
    return tuple(sorted(output))


def verify_parent_roots(material_root: Path, adro_root: Path) -> dict[str, Path]:
    paths = {
        "material_manifest": material_root / "MANIFEST.json",
        "material_summary": material_root / "summary.json",
        "ledger": material_root / "expanded_continuity_ledger_611.csv",
        "coverage": material_root / "merged_ksei_611" / "ticker_coverage.csv",
        "history": material_root / "merged_ksei_611" / "ksei_ca_history.jsonl",
        "schedule": material_root / "merged_schedule_evidence.csv",
        "adro_manifest": adro_root / "MANIFEST.json",
        "adro_overlay": adro_root / "adro_exact_entitlement_overlay.json",
        "adro_prospectus": adro_root / "raw" / "official_docs" / "adro_pups_prospectus_2024.pdf",
        "adro_egms": adro_root / "raw" / "official_docs" / "adro_egms_minutes_2024.pdf",
    }
    for label, path in paths.items():
        if not path.is_file():
            raise RuntimeError(f"FREN_PARENT_FILE_MISSING:{label}:{path}")
    if sha256_file(paths["material_manifest"]) != EXPECTED_MATERIAL_MANIFEST:
        raise RuntimeError("FREN_MATERIAL_PARENT_MANIFEST_CHANGED")
    if sha256_file(paths["adro_manifest"]) != EXPECTED_ADRO_MANIFEST:
        raise RuntimeError("FREN_ADRO_PARENT_MANIFEST_CHANGED")
    if sha256_file(paths["ledger"]) != EXPECTED_EXPANDED_LEDGER:
        raise RuntimeError("FREN_PARENT_LEDGER_CHANGED")
    if sha256_file(paths["coverage"]) != EXPECTED_MATERIAL_COVERAGE:
        raise RuntimeError("FREN_PARENT_COVERAGE_CHANGED")
    if sha256_file(paths["history"]) != EXPECTED_MATERIAL_HISTORY:
        raise RuntimeError("FREN_PARENT_HISTORY_CHANGED")
    adro_overlay = json.loads(paths["adro_overlay"].read_text(encoding="utf-8"))
    if adro_overlay.get("status") != "V4_CA_ADRO_EXACT_ENTITLEMENT_REPLAY_COMPLETE":
        raise RuntimeError("FREN_ADRO_PARENT_STATUS_INVALID")
    return paths


def discover_and_verify_rights_pdf(
    page_payloads: list[tuple[str, bytes]],
    raw_root: Path,
) -> tuple[bytes, dict[str, Any], dict[str, object]]:
    candidates: set[str] = {SMARTFREN_2024_ANNUAL_REPORT_PDF}
    detail_urls: set[str] = set()
    for base_url, payload in page_payloads:
        candidates.update(extract_official_pdf_urls(payload, base_url))
        for link in hrefs(payload, base_url):
            low = link.casefold()
            if "pmhmetd" in low or "prospektus" in low:
                detail_urls.add(link)

    # Follow only issuer-official PMHMETD/prospectus pages discovered from the
    # frozen archive pages; this is bounded discovery, not a web-wide search.
    detail_records: list[dict[str, Any]] = []
    for index, url in enumerate(sorted(detail_urls)[:12], start=1):
        try:
            payload, record = get(url, raw_root / f"detail_{index:02d}.html")
        except RuntimeError as exc:
            detail_records.append({"url": url, "error": str(exc)})
            continue
        detail_records.append(record)
        candidates.update(extract_official_pdf_urls(payload, url))

    attempts: list[dict[str, Any]] = []
    for index, url in enumerate(sorted(candidates)[:20], start=1):
        try:
            payload, record = get(url, raw_root / f"candidate_{index:02d}.pdf")
        except RuntimeError as exc:
            attempts.append({"url": url, "error": str(exc)})
            continue
        if not payload.startswith(b"%PDF"):
            attempts.append({**record, "error": "NOT_PDF_BYTES"})
            continue
        try:
            semantics = verify_rights_prospectus(payload)
        except Exception as exc:
            attempts.append({**record, "error": f"{type(exc).__name__}:{exc}"})
            continue
        return payload, record, {**semantics, "candidate_attempts": attempts, "detail_pages": detail_records}
    raise RuntimeError(
        "FREN_NO_ISSUER_PDF_PROVES_EX_RIGHT_DATE:"
        + json.dumps({"candidates": sorted(candidates), "attempts": attempts, "detail_pages": detail_records})
    )


def make_classifier(adro_evidence, fren_source_sha: str):
    inherited = material_v3.material_six_classifier_v3(fren_source_sha)

    def classify(row, *, official_sessions, schedule_evidence=()) -> EventSemantic:
        base_event = inherited(
            row,
            official_sessions=official_sessions,
            schedule_evidence=schedule_evidence,
        )
        return apply_adro_entitlement_evidence(
            row,
            base_event=base_event,
            evidence=adro_evidence,
        )

    return classify


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    paths = verify_parent_roots(args.material_six_root, args.adro_root)
    if not args.prior_event_evidence.is_file() or not args.official_calendar.is_file():
        raise RuntimeError("FREN_REQUIRED_FROZEN_INPUT_MISSING")
    args.output_dir.mkdir(parents=True)
    raw = args.output_dir / "raw" / "official_archive"

    page_specs = {
        "corporate_action_2024": SMARTFREN_CORPORATE_ACTION_2024_URL,
        "disclosure_2024": SMARTFREN_DISCLOSURE_2024_URL,
        "prospectus_page": SMARTFREN_PROSPECTUS_PAGE_URL,
        "annual_report_page": SMARTFREN_ANNUAL_REPORT_URL,
        "merger_archive": SMARTFREN_MERGER_ARCHIVE_URL,
        "investor_about": SMARTFREN_INVESTOR_ABOUT_URL,
        "ksei_right_record": KSEI_RIGHT_RECORD_URL,
        "ksei_right_distribution": KSEI_RIGHT_DISTRIBUTION_URL,
        "ksei_merger_record": KSEI_MERGER_RECORD_URL,
        "ksei_merger_report": KSEI_MERGER_REPORT_URL,
        "ksei_merger_distribution": KSEI_MERGER_DISTRIBUTION_URL,
    }
    payloads: dict[str, bytes] = {}
    fetch_records: dict[str, dict[str, Any]] = {}
    for label, url in page_specs.items():
        payload, record = get(url, raw / f"{label}.html")
        payloads[label] = payload
        fetch_records[label] = record

    archive_semantics = verify_smartfren_archive_pages(
        payloads["corporate_action_2024"],
        payloads["disclosure_2024"],
        payloads["merger_archive"],
        payloads["investor_about"],
    )
    verify_ksei_right_pages(
        payloads["ksei_right_record"], payloads["ksei_right_distribution"]
    )
    verify_ksei_merger_pages(
        payloads["ksei_merger_record"],
        payloads["ksei_merger_report"],
        payloads["ksei_merger_distribution"],
    )

    rights_payload, rights_record, rights_semantics = discover_and_verify_rights_pdf(
        [
            (SMARTFREN_CORPORATE_ACTION_2024_URL, payloads["corporate_action_2024"]),
            (SMARTFREN_DISCLOSURE_2024_URL, payloads["disclosure_2024"]),
            (SMARTFREN_PROSPECTUS_PAGE_URL, payloads["prospectus_page"]),
            (SMARTFREN_ANNUAL_REPORT_URL, payloads["annual_report_page"]),
        ],
        raw / "rights_pdf_discovery",
    )

    core_payloads = [
        payloads["corporate_action_2024"],
        payloads["disclosure_2024"],
        payloads["merger_archive"],
        payloads["investor_about"],
        payloads["ksei_right_record"],
        payloads["ksei_right_distribution"],
        payloads["ksei_merger_record"],
        payloads["ksei_merger_report"],
        payloads["ksei_merger_distribution"],
        rights_payload,
    ]
    evidence_sha = combined_evidence_sha(core_payloads)
    attestation = {
        "schema_version": "v4_ca_fren_official_archive_attestation_v1",
        "status": "FREN_OFFICIAL_ARCHIVE_MECHANICAL_HISTORY_CERTIFIED",
        "outcome_blind": True,
        "source_method": archive_semantics["mechanical_census_method"],
        "static_ksei_registered_security_recovered": False,
        "source_substitution_disclosed": True,
        "mechanical_events": [
            {
                "family": "RIGHT_DISTRIBUTION_PMHMETD_V",
                "transition_date": FREN_RIGHT_EX_DATE.date().isoformat(),
                "source": "SMARTFREN_OFFICIAL_PMHETD_V_PLUS_KSEI_CORROBORATION",
            },
            {
                "family": "MERGER_SECURITY_CESSATION",
                "transition_date": FREN_MERGER_DATE.date().isoformat(),
                "source": "SMARTFREN_OFFICIAL_MERGER_PLUS_KSEI_CORROBORATION",
            },
        ],
        "issuer_archive": archive_semantics,
        "rights_semantics": rights_semantics,
        "rights_pdf": rights_record,
        "official_page_fetches": fetch_records,
        "combined_evidence_sha256": evidence_sha,
        "no_price_inference": True,
        "no_record_date_inference": True,
        "no_excl_price_stitching": True,
    }
    attestation_path = args.output_dir / "fren_official_archive_attestation.json"
    attestation_path.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Build a mixed-source census root transparently: all parent KSEI history is
    # retained byte-for-byte, while only FREN's coverage row is replaced by the
    # official archival mechanical-history attestation.
    census = args.output_dir / "fren_archive_census_611"
    census.mkdir()
    coverage = pd.read_csv(paths["coverage"])
    mask = coverage["ticker"].astype(str).str.upper().eq("FREN")
    if int(mask.sum()) != 1 or str(coverage.loc[mask, "coverage_certified"].iloc[0]).casefold() != "false":
        raise RuntimeError("FREN_PARENT_COVERAGE_ROW_IDENTITY_CHANGED")
    coverage.loc[mask, "coverage_status"] = "OFFICIAL_ARCHIVE_MECHANICAL_HISTORY_CERTIFIED"
    coverage.loc[mask, "coverage_certified"] = True
    coverage.loc[mask, "attempt_count"] = 0
    coverage.loc[mask, "final_http_status"] = 200
    coverage.loc[mask, "source_url"] = SMARTFREN_CORPORATE_ACTION_2024_URL
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
    shutil.copyfile(paths["history"], history_path)
    census_summary = {
        "schema_version": "v4_ca_fren_mixed_official_archive_census_v1",
        "status": "COMPLETE",
        "outcome_blind": True,
        "tickers": int(coverage["ticker"].nunique()),
        "coverage_certified_tickers": int(
            coverage["coverage_certified"].astype(str).str.casefold().eq("true").sum()
        ),
        "fren_source_method": archive_semantics["mechanical_census_method"],
        "fren_attestation_sha256": sha256_file(attestation_path),
        "parent_ksei_history_unchanged": sha256_file(history_path) == EXPECTED_MATERIAL_HISTORY,
        "output_hashes": {
            "ticker_coverage": sha256_file(coverage_path),
            "ksei_ca_history": sha256_file(history_path),
        },
    }
    census_summary_path = census / "summary.json"
    census_summary_path.write_text(json.dumps(census_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    census_manifest = {
        "schema_version": "v4_ca_fren_mixed_official_archive_manifest_v1",
        "status": "COMPLETE",
        "outcome_blind": True,
        "summary_sha256": sha256_file(census_summary_path),
        "output_hashes": census_summary["output_hashes"],
    }
    census_manifest_path = census / "MANIFEST.json"
    census_manifest_path.write_text(json.dumps(census_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    material_summary = json.loads(paths["material_summary"].read_text(encoding="utf-8"))
    fren_merger_sha = str((material_summary.get("fren_official_evidence") or {}).get("source_sha256") or "")
    mega_sha = str((material_summary.get("mega_official_evidence") or {}).get("source_sha256") or "")
    if not fren_merger_sha or not mega_sha:
        raise RuntimeError("FREN_PARENT_SYNTHETIC_EVIDENCE_SHA_MISSING")
    adro_evidence = verify_adro_official_documents(
        paths["adro_prospectus"].read_bytes(), paths["adro_egms"].read_bytes()
    )

    frozen.PINNED = dict(frozen.PINNED)
    frozen.PINNED["continuity_ledger"] = sha256_file(paths["ledger"])
    frozen.PINNED["ksei_manifest"] = sha256_file(census_manifest_path)
    frozen.PINNED["ksei_summary"] = sha256_file(census_summary_path)
    frozen.PINNED["ksei_coverage"] = sha256_file(coverage_path)
    frozen.PINNED["ksei_history"] = sha256_file(history_path)
    frozen.EXPECTED_TICKERS = EXPECTED_TICKERS
    frozen.EXPECTED_ROWS = EXPECTED_ROWS
    frozen.EXPECTED_DATES = EXPECTED_DATES
    frozen.classify_event = make_classifier(adro_evidence, fren_merger_sha)

    original_prior = frozen.prior_candidate_tickers
    original_build = frozen.build_events

    def prior_candidate_tickers_fren(prior_frame, *, period_start, period_end):
        result = set(original_prior(prior_frame, period_start=period_start, period_end=period_end))
        if "SCMA" in result:
            material_base.validate_scma_halo_only(prior_frame, max_terminal=pd.Timestamp(period_end))
            result.remove("SCMA")
        return result

    rights_event = synthetic_fren_rights_event(str(rights_semantics["source_sha256"]))

    def build_events_fren(*inner_args, **inner_kwargs):
        by_ticker, audit = original_build(*inner_args, **inner_kwargs)
        rows = audit.to_dict("records")
        additions = (
            (material_base.synthetic_mega_event(mega_sha), "MEGA_ISSUER_OFFICIAL"),
            (material_base.synthetic_fren_event(fren_merger_sha), "FREN_ISSUER_OFFICIAL_MERGER"),
            (rights_event, "FREN_ISSUER_OFFICIAL_PMHETD_V"),
        )
        for event, marker in additions:
            by_ticker.setdefault(event.ticker, []).append(event)
            rows.append({
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
            })
        result = pd.DataFrame(rows).fillna("")
        return by_ticker, result.sort_values(
            ["ticker", "source_dates", "source_type", "event_id"], kind="mergesort"
        ).reset_index(drop=True)

    frozen.prior_candidate_tickers = prior_candidate_tickers_fren
    frozen.build_events = build_events_fren

    replay_root = args.output_dir / "final_continuity_611_fren"
    original_argv = list(sys.argv)
    try:
        sys.argv = [
            original_argv[0],
            "--continuity-ledger", str(paths["ledger"]),
            "--prior-event-evidence", str(args.prior_event_evidence),
            "--official-calendar", str(args.official_calendar),
            "--ksei-census-root", str(census),
            "--schedule-evidence", str(paths["schedule"]),
            "--output-dir", str(replay_root),
        ]
        replay_result = int(frozen.main() or 0)
    finally:
        sys.argv = original_argv

    final_summary_path = replay_root / "summary.json"
    final_summary = json.loads(final_summary_path.read_text(encoding="utf-8"))
    window = pd.read_csv(replay_root / "v4_frozen_continuity_ledger_event_window.csv")
    fren = window[window["ticker"].astype(str).str.upper().eq("FREN")].copy()
    if len(fren) != EXPECTED_FREN_ROWS:
        raise RuntimeError(f"FREN_WINDOW_ROW_COUNT_CHANGED:{len(fren)}")
    for col in ("entry_date", "terminal_date"):
        fren[col] = pd.to_datetime(fren[col], errors="raise").dt.normalize()
    resolved = fren["continuity_status"].eq("RESOLVED_NO_MECHANICAL_DISCONTINUITY")
    crossing = fren["continuity_reason"].eq("TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION")
    unexpected = fren.loc[~resolved & ~crossing]
    if not unexpected.empty:
        raise RuntimeError(
            "FREN_REMAINS_UNRESOLVED_FOR_NON_MECHANICAL_REASON:"
            + str(sorted(unexpected["continuity_reason"].astype(str).unique()))
        )
    right_cross = (fren["entry_date"] < FREN_RIGHT_EX_DATE) & (fren["terminal_date"] >= FREN_RIGHT_EX_DATE)
    merger_cross = (fren["entry_date"] < FREN_MERGER_DATE) & (fren["terminal_date"] >= FREN_MERGER_DATE)
    if int(right_cross.sum()) <= 0 or int(merger_cross.sum()) <= 0:
        raise RuntimeError("FREN_EXPECTED_MECHANICAL_CROSSING_WINDOWS_NOT_OBSERVED")
    if int(final_summary.get("coverage_certified_tickers") or 0) != 602:
        raise RuntimeError("FREN_FINAL_CERTIFIED_TICKER_COUNT_UNEXPECTED")
    if int(final_summary.get("coverage_unresolved_tickers") or 0) != 9:
        raise RuntimeError("FREN_FINAL_UNRESOLVED_TICKER_COUNT_UNEXPECTED")

    event_audit = pd.read_csv(replay_root / "event_semantics_audit.csv", dtype=str, keep_default_na=False)
    fren_events = event_audit[event_audit["ticker"].eq("FREN")].to_dict("records")
    transition_dates = {row.get("transition_date") for row in fren_events if row.get("semantic_class") == "EXACT_TRANSITION"}
    if not {"2024-04-17", "2025-04-16"}.issubset(transition_dates):
        raise RuntimeError(f"FREN_FINAL_EXACT_TRANSITIONS_MISSING:{transition_dates}")

    overlay = {
        "schema_version": "v4_ca_fren_official_archive_replay_v1",
        "status": "V4_CA_FREN_OFFICIAL_ARCHIVE_REPLAY_COMPLETE",
        "outcome_blind": True,
        "provider_calls": False,
        "official_archive_calls": True,
        "static_ksei_registered_security_recovered": False,
        "coverage_source_method": archive_semantics["mechanical_census_method"],
        "coverage_certified": True,
        "rights_transition_date": FREN_RIGHT_EX_DATE.date().isoformat(),
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
        "parent_material_manifest_sha256": EXPECTED_MATERIAL_MANIFEST,
        "parent_adro_manifest_sha256": EXPECTED_ADRO_MANIFEST,
        "model_fit": False,
        "performance_computed": False,
        "prediction_generated": False,
        "target_or_rank_materialized": False,
        "protected_forward_accessed": False,
        "price_inference": False,
        "record_date_inference": False,
        "excl_price_stitching": False,
    }
    overlay_path = args.output_dir / "fren_official_archive_overlay.json"
    overlay_path.write_text(json.dumps(overlay, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_ca_fren_official_archive_manifest_v1",
        "status": overlay["status"],
        "outcome_blind": True,
        "overlay_sha256": sha256_file(overlay_path),
        "attestation_sha256": sha256_file(attestation_path),
        "census_manifest_sha256": sha256_file(census_manifest_path),
        "continuity_summary_sha256": sha256_file(final_summary_path),
        "parent_material_manifest_sha256": EXPECTED_MATERIAL_MANIFEST,
        "parent_adro_manifest_sha256": EXPECTED_ADRO_MANIFEST,
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**overlay, "manifest_sha256": sha256_file(manifest_path)}, indent=2, sort_keys=True))
    return replay_result


if __name__ == "__main__":
    raise SystemExit(main())
