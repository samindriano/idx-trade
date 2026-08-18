"""Outcome-blind ADRO-only replay over the accepted material-six 611 support.

Consumes the successful V4 material-six root as immutable input.  It performs
zero KSEI/provider recrawls.  The only new acquisition is two issuer-official
AlamTri PDFs whose joint text proves the exact ADRO PUPS entitlement boundary.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
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
import run_v4_ca_material_six_remediation as material_base
import run_v4_ca_material_six_remediation_v3 as material_v3
from idx_trade.v4_ca_adro_entitlement_semantics import (
    ADRO_EGMS_MINUTES_URL,
    ADRO_EVENT_ID,
    ADRO_PUPS_PROSPECTUS_URL,
    ADRO_TRANSITION_DATE,
    apply_adro_entitlement_evidence,
    verify_adro_official_documents,
)
from idx_trade.v4_ca_event_windows import EventSemantic
from idx_trade.v4_ksei_coverage_gap import sha256_file


EXPECTED_PARENT_MANIFEST_SHA256 = "c26b9e60f17b181016cd2ee4c30720ef4a4323b82603a5a0c9c01ea0fd175a4c"
EXPECTED_EXPANDED_LEDGER_SHA256 = "5139cbb39e34fd46b6214435b1bc6bb937ec1e5400ec268376e412bdd2225426"
EXPECTED_MERGED_COVERAGE_SHA256 = "44f7b9e9f7e02e5f2dacaf27f5ded3aa1d41d4ce61664725db096f7a28a93081"
EXPECTED_MERGED_HISTORY_SHA256 = "4dcdd9e44cc40e348079c1447aa3e1e20427b000247be5be91b6622fb03e997d"
EXPECTED_PARENT_FINAL_SUMMARY_SHA256 = "2fa85ca4b4025a651f4f1de4f317749723b1cd6280da2b277563450c066a0ca7"
EXPECTED_TICKERS = 611
EXPECTED_ROWS = 345_394
EXPECTED_DATES = 600


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--material-six-root", type=Path, required=True)
    parser.add_argument("--prior-event-evidence", type=Path, required=True)
    parser.add_argument("--official-calendar", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def download_exact_official_pdf(url: str, path: Path) -> tuple[bytes, dict[str, Any]]:
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 IDX-Trade-V4-ADRO-Entitlement/1.0"},
        timeout=45,
        allow_redirects=True,
    )
    payload = bytes(response.content or b"")
    if response.status_code != 200 or not payload:
        raise RuntimeError(
            f"ADRO_OFFICIAL_DOCUMENT_DOWNLOAD_FAILED:{response.status_code}:{len(payload)}:{url}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload, {
        "url": url,
        "final_url": str(response.url),
        "status_code": int(response.status_code),
        "bytes": len(payload),
        "sha256": sha256_file(path),
    }


def verify_parent_root(root: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    paths = {
        "manifest": root / "MANIFEST.json",
        "summary": root / "summary.json",
        "expanded_ledger": root / "expanded_continuity_ledger_611.csv",
        "merged_coverage": root / "merged_ksei_611" / "ticker_coverage.csv",
        "merged_history": root / "merged_ksei_611" / "ksei_ca_history.jsonl",
        "merged_ksei_manifest": root / "merged_ksei_611" / "MANIFEST.json",
        "merged_ksei_summary": root / "merged_ksei_611" / "summary.json",
        "schedule": root / "merged_schedule_evidence.csv",
        "parent_final_summary": root / "final_continuity_611" / "summary.json",
    }
    for label, path in paths.items():
        if not path.is_file():
            raise RuntimeError(f"ADRO_PARENT_REQUIRED_FILE_MISSING:{label}:{path}")
    if sha256_file(paths["manifest"]) != EXPECTED_PARENT_MANIFEST_SHA256:
        raise RuntimeError("ADRO_PARENT_MATERIAL_SIX_MANIFEST_CHANGED")
    if sha256_file(paths["expanded_ledger"]) != EXPECTED_EXPANDED_LEDGER_SHA256:
        raise RuntimeError("ADRO_PARENT_EXPANDED_LEDGER_CHANGED")
    if sha256_file(paths["merged_coverage"]) != EXPECTED_MERGED_COVERAGE_SHA256:
        raise RuntimeError("ADRO_PARENT_MERGED_COVERAGE_CHANGED")
    if sha256_file(paths["merged_history"]) != EXPECTED_MERGED_HISTORY_SHA256:
        raise RuntimeError("ADRO_PARENT_MERGED_HISTORY_CHANGED")
    if sha256_file(paths["parent_final_summary"]) != EXPECTED_PARENT_FINAL_SUMMARY_SHA256:
        raise RuntimeError("ADRO_PARENT_FINAL_CONTINUITY_SUMMARY_CHANGED")

    summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
    if summary.get("status") != "V4_CA_MATERIAL_SIX_REMEDIATION_COMPLETE":
        raise RuntimeError("ADRO_PARENT_MATERIAL_SIX_STATUS_INVALID")
    if summary.get("outcome_blind") is not True:
        raise RuntimeError("ADRO_PARENT_NOT_OUTCOME_BLIND")
    if (summary.get("expanded_support") or {}).get("tickers") != EXPECTED_TICKERS:
        raise RuntimeError("ADRO_PARENT_TICKER_COUNT_CHANGED")
    if (summary.get("final_continuity") or {}).get("corporate_action_continuity_certified") is not True:
        raise RuntimeError("ADRO_PARENT_CONTINUITY_NOT_CERTIFIED")
    return summary, paths


def make_adro_classifier(evidence, fren_source_sha: str):
    inherited_factory = material_v3.material_six_classifier_v3
    inherited = inherited_factory(fren_source_sha)

    def classify(row, *, official_sessions, schedule_evidence=()) -> EventSemantic:
        base_event = inherited(
            row,
            official_sessions=official_sessions,
            schedule_evidence=schedule_evidence,
        )
        return apply_adro_entitlement_evidence(
            row,
            base_event=base_event,
            evidence=evidence,
        )

    return classify


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    parent_summary, paths = verify_parent_root(args.material_six_root)
    if not args.prior_event_evidence.is_file() or not args.official_calendar.is_file():
        raise RuntimeError("ADRO_REPLAY_REQUIRED_FROZEN_INPUT_MISSING")

    args.output_dir.mkdir(parents=True)
    raw_docs = args.output_dir / "raw" / "official_docs"
    prospectus_payload, prospectus_download = download_exact_official_pdf(
        ADRO_PUPS_PROSPECTUS_URL,
        raw_docs / "adro_pups_prospectus_2024.pdf",
    )
    egms_payload, egms_download = download_exact_official_pdf(
        ADRO_EGMS_MINUTES_URL,
        raw_docs / "adro_egms_minutes_2024.pdf",
    )
    evidence = verify_adro_official_documents(prospectus_payload, egms_payload)

    frozen.PINNED = dict(frozen.PINNED)
    frozen.PINNED["continuity_ledger"] = sha256_file(paths["expanded_ledger"])
    frozen.PINNED["ksei_manifest"] = sha256_file(paths["merged_ksei_manifest"])
    frozen.PINNED["ksei_summary"] = sha256_file(paths["merged_ksei_summary"])
    frozen.PINNED["ksei_coverage"] = sha256_file(paths["merged_coverage"])
    frozen.PINNED["ksei_history"] = sha256_file(paths["merged_history"])
    frozen.EXPECTED_TICKERS = EXPECTED_TICKERS
    frozen.EXPECTED_ROWS = EXPECTED_ROWS
    frozen.EXPECTED_DATES = EXPECTED_DATES

    fren_sha = str((parent_summary.get("fren_official_evidence") or {}).get("source_sha256") or "")
    mega_sha = str((parent_summary.get("mega_official_evidence") or {}).get("source_sha256") or "")
    if not fren_sha or not mega_sha:
        raise RuntimeError("ADRO_PARENT_MATERIAL_SIX_OFFICIAL_EVIDENCE_SHA_MISSING")
    frozen.classify_event = make_adro_classifier(evidence, fren_sha)

    original_prior_candidate_tickers = frozen.prior_candidate_tickers
    original_build_events = frozen.build_events

    def prior_candidate_tickers_adro(prior_frame, *, period_start, period_end):
        result = set(
            original_prior_candidate_tickers(
                prior_frame, period_start=period_start, period_end=period_end
            )
        )
        if "SCMA" in result:
            material_base.validate_scma_halo_only(
                prior_frame, max_terminal=pd.Timestamp(period_end)
            )
            result.remove("SCMA")
        return result

    def build_events_adro(*inner_args, **inner_kwargs):
        by_ticker, audit = original_build_events(*inner_args, **inner_kwargs)
        rows = audit.to_dict("records")
        additions = (
            (material_base.synthetic_mega_event(mega_sha), "MEGA_ISSUER_OFFICIAL"),
            (material_base.synthetic_fren_event(fren_sha), "FREN_ISSUER_OFFICIAL"),
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
                    "transition_date": event.transition_date.date().isoformat(),
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

    frozen.prior_candidate_tickers = prior_candidate_tickers_adro
    frozen.build_events = build_events_adro

    replay_root = args.output_dir / "final_continuity_611_adro"
    original_argv = list(sys.argv)
    try:
        sys.argv = [
            original_argv[0],
            "--continuity-ledger", str(paths["expanded_ledger"]),
            "--prior-event-evidence", str(args.prior_event_evidence),
            "--official-calendar", str(args.official_calendar),
            "--ksei-census-root", str(args.material_six_root / "merged_ksei_611"),
            "--schedule-evidence", str(paths["schedule"]),
            "--output-dir", str(replay_root),
        ]
        replay_result = int(frozen.main() or 0)
    finally:
        sys.argv = original_argv

    continuity_summary_path = replay_root / "summary.json"
    continuity_summary = json.loads(continuity_summary_path.read_text(encoding="utf-8"))
    window = pd.read_csv(
        replay_root / "v4_frozen_continuity_ledger_event_window.csv",
        dtype=str,
        keep_default_na=False,
    )
    adro_window = window[window["ticker"].eq("ADRO")].copy()
    event_audit = pd.read_csv(
        replay_root / "event_semantics_audit.csv",
        dtype=str,
        keep_default_na=False,
    )
    adro_events = event_audit[event_audit["ticker"].eq("ADRO")]
    exact = adro_events[adro_events["event_id"].eq(ADRO_EVENT_ID)]
    if len(exact) != 1:
        raise RuntimeError(f"ADRO_FINAL_EVENT_IDENTITY_CHANGED:{len(exact)}")
    exact_row = exact.iloc[0].to_dict()
    if exact_row.get("semantic_class") != "EXACT_TRANSITION" or exact_row.get("transition_date") != "2024-11-28":
        raise RuntimeError(f"ADRO_FINAL_TRANSITION_NOT_EXACT:{exact_row}")

    resolved_mask = adro_window["continuity_status"].eq(
        "RESOLVED_NO_MECHANICAL_DISCONTINUITY"
    )
    crossing = adro_window[
        adro_window["continuity_reason"].eq(
            "TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION"
        )
    ]
    overlay = {
        "schema_version": "v4_ca_adro_exact_entitlement_replay_v1",
        "status": "V4_CA_ADRO_EXACT_ENTITLEMENT_REPLAY_COMPLETE",
        "outcome_blind": True,
        "ksei_provider_calls": False,
        "official_issuer_document_calls": True,
        "price_inference": False,
        "record_date_fallback": False,
        "distribution_date_fallback": False,
        "event_id": ADRO_EVENT_ID,
        "transition_date": ADRO_TRANSITION_DATE.date().isoformat(),
        "transition_semantic": evidence.semantic,
        "transition_source": "OFFICIAL_ISSUER_CROSS_DOCUMENT_ENTITLEMENT_EX_DATE",
        "evidence": {
            "prospectus": {**prospectus_download, "verified_sha256": evidence.prospectus_sha256},
            "egms_minutes": {**egms_download, "verified_sha256": evidence.egms_minutes_sha256},
            "linkage": (
                "PUPS participant set is explicitly shareholders obtaining the 2024-11-18 EGMS dividend; "
                "the same official EGMS minutes explicitly set Regular/Negotiated Market Ex Dividend to 2024-11-28."
            ),
        },
        "adro_window_rows": int(len(adro_window)),
        "adro_resolved_window_rows": int(resolved_mask.sum()),
        "adro_crossing_transition_window_rows": int(len(crossing)),
        "adro_resolved_window_rate": float(resolved_mask.mean()) if len(adro_window) else None,
        "adro_event_semantics": exact_row,
        "final_continuity": {
            "verdict": continuity_summary.get("verdict"),
            "corporate_action_continuity_certified": continuity_summary.get("corporate_action_continuity_certified"),
            "coverage_certified_tickers": continuity_summary.get("coverage_certified_tickers"),
            "coverage_unresolved_tickers": continuity_summary.get("coverage_unresolved_tickers"),
            "cross_source_conflict_tickers": continuity_summary.get("cross_source_conflict_tickers"),
            "schedule_required_events": continuity_summary.get("schedule_required_events"),
            "schedule_required_tickers": continuity_summary.get("schedule_required_tickers"),
            "per_date": continuity_summary.get("per_date"),
        },
        "parent_material_six_manifest_sha256": EXPECTED_PARENT_MANIFEST_SHA256,
        "continuity_summary_sha256": sha256_file(continuity_summary_path),
    }
    overlay_path = args.output_dir / "adro_exact_entitlement_overlay.json"
    overlay_path.write_text(json.dumps(overlay, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v4_ca_adro_exact_entitlement_manifest_v1",
        "status": overlay["status"],
        "outcome_blind": True,
        "parent_material_six_manifest_sha256": EXPECTED_PARENT_MANIFEST_SHA256,
        "overlay_sha256": sha256_file(overlay_path),
        "continuity_summary_sha256": sha256_file(continuity_summary_path),
        "prospectus_sha256": evidence.prospectus_sha256,
        "egms_minutes_sha256": evidence.egms_minutes_sha256,
    }
    manifest_path = args.output_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**overlay, "manifest_sha256": sha256_file(manifest_path)}, indent=2, sort_keys=True))
    return replay_result


if __name__ == "__main__":
    raise SystemExit(main())
