"""Offline adjudication for frozen residual-47 IDX Digital Statistic split corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from idx_trade.ranking_v4_3_ca_schedule_reuse import event_inventory_identity  # noqa: E402
from idx_trade.v4_3_ca_residual47_idx_digital_split import (  # noqa: E402
    ELIGIBLE_SOURCE_TYPES,
    clean,
    listing_date_linked,
    parse_source_dates,
    source_type_compatible,
    ticker,
    timestamp,
)

DEFAULT_CONFIG = REPO_ROOT / "config" / "v4_3_ca_training_domain_residual47_idx_digital_split_v1.json"


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label}_MISSING:{path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_NOT_OBJECT:{path}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--acquisition-root", type=Path, required=True)
    parser.add_argument("--expected-acquisition-manifest-sha", required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def verify_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "v4_3_ca_training_domain_residual47_idx_digital_split_v1":
        raise RuntimeError("CONFIG_SCHEMA_INVALID")
    if config.get("outcome_blind") is not True:
        raise RuntimeError("CONFIG_NOT_OUTCOME_BLIND")
    hard = config.get("hard_boundaries") or {}
    for key, value in hard.items():
        if value is not False:
            raise RuntimeError(f"HARD_BOUNDARY_CHANGED:{key}")


def verify_acquisition(root: Path, expected_sha: str) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    manifest_path = root / "MANIFEST.json"
    summary_path = root / "summary.json"
    scope_path = root / "frozen_residual_47_scope.csv"
    links_path = root / "event_idx_digital_split_candidate_links.csv"
    actual_manifest = sha256_file(manifest_path)
    if actual_manifest != clean(expected_sha):
        raise RuntimeError(f"ACQUISITION_MANIFEST_SHA_MISMATCH:{actual_manifest}!={clean(expected_sha)}")
    manifest = read_json(manifest_path, "ACQUISITION_MANIFEST")
    summary = read_json(summary_path, "ACQUISITION_SUMMARY")
    if manifest.get("status") != "V4_3_CA_RESIDUAL47_IDX_DIGITAL_SPLIT_ACQUISITION_COMPLETE":
        raise RuntimeError("ACQUISITION_STATUS_CHANGED")
    if summary.get("status") != manifest.get("status"):
        raise RuntimeError("ACQUISITION_SUMMARY_STATUS_CHANGED")
    if summary.get("semantic_admission_performed") is not False:
        raise RuntimeError("ACQUISITION_SEMANTIC_ADMISSION_ALREADY_PERFORMED")
    if summary.get("historical_target_loaded") is not False or summary.get("model_fit") is not False:
        raise RuntimeError("ACQUISITION_OUTCOME_GUARD_CHANGED")
    outputs = manifest.get("output_hashes") or {}
    for key, path in (("frozen_residual_scope", scope_path), ("candidate_links", links_path), ("summary", summary_path)):
        expected = clean(outputs.get(key))
        actual = sha256_file(path)
        if not expected or expected != actual:
            raise RuntimeError(f"ACQUISITION_CHILD_SHA_MISMATCH:{key}")
    scope = pd.read_csv(scope_path, dtype=str, keep_default_na=False)
    links = pd.read_csv(links_path, dtype=str, keep_default_na=False)
    if len(scope) != 47:
        raise RuntimeError("ACQUISITION_SCOPE_COUNT_CHANGED")
    scope["event_id"] = scope["event_id"].map(clean)
    scope["ticker"] = scope["ticker"].map(ticker)
    identity = event_inventory_identity(scope[["event_id", "ticker"]])
    if identity != summary.get("residual_event_identity_sha256"):
        raise RuntimeError("ACQUISITION_SCOPE_IDENTITY_CHANGED")
    return scope, links, {
        "acquisition_manifest": actual_manifest,
        "acquisition_scope": sha256_file(scope_path),
        "acquisition_links": sha256_file(links_path),
        "acquisition_summary": sha256_file(summary_path),
    }


def verify_calendar(artifact_root: Path, config: dict[str, Any]) -> tuple[set[pd.Timestamp], str]:
    cfg = config["official_calendar"]
    path = artifact_root / str(cfg["filename"])
    actual = sha256_file(path)
    if actual != cfg["sha256"]:
        raise RuntimeError(f"OFFICIAL_CALENDAR_SHA_MISMATCH:{actual}")
    frame = pd.read_csv(path)
    dates = set(pd.to_datetime(frame["date"], errors="raise").dt.normalize())
    return dates, actual


def main() -> int:
    args = parse_args()
    if args.output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_EXISTING_OUTPUT:{args.output_dir}")
    config = read_json(args.config, "CONFIG")
    verify_config(config)
    scope, links, acquisition_hashes = verify_acquisition(
        args.acquisition_root, args.expected_acquisition_manifest_sha
    )
    official_sessions, calendar_sha = verify_calendar(args.artifact_root, config)

    if not links.empty:
        links["event_id"] = links["event_id"].map(clean)
        links["ticker"] = links["ticker"].map(ticker)
    max_days = int(config["adjudication"]["max_listing_date_distance_days"])
    accepted_semantic = config["adjudication"]["accepted_transition_semantic"]

    evidence_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for event in scope.to_dict("records"):
        event_id = clean(event["event_id"])
        event_ticker = ticker(event["ticker"])
        source_type = clean(event.get("source_type"))
        source_dates = parse_source_dates(event.get("source_dates"))
        event_links = links[
            links["event_id"].eq(event_id) & links["ticker"].eq(event_ticker)
        ].copy() if not links.empty else pd.DataFrame()

        status = "UNRESOLVED"
        transition_date = ""
        official_reference = ""
        source_sha256 = ""
        linkage_basis = ""
        diagnostics: list[str] = []

        if source_type.casefold() not in ELIGIBLE_SOURCE_TYPES:
            diagnostics.append("NON_SPLIT_FAMILY_OUTSIDE_STRUCTURED_DATASET")
        else:
            admissible: list[dict[str, Any]] = []
            for row in event_links.to_dict("records") if not event_links.empty else []:
                compatible = source_type_compatible(source_type, row.get("action_type"))
                linked = listing_date_linked(
                    row.get("listing_date"), source_dates, max_distance_days=max_days
                )
                listing = timestamp(row.get("listing_date"))
                official_session = listing in official_sessions if listing is not None else False
                audit_rows.append({
                    "event_id": event_id,
                    "ticker": event_ticker,
                    "event_source_type": source_type,
                    "action_type": clean(row.get("action_type")),
                    "listing_date": clean(row.get("listing_date")),
                    "row_identity_sha256": clean(row.get("row_identity_sha256")),
                    "source_sha256": clean(row.get("source_sha256")),
                    "source_url": clean(row.get("source_url")),
                    "family_compatible": compatible,
                    "source_date_linked": linked,
                    "official_session": official_session,
                })
                if compatible and linked and official_session and clean(row.get("source_sha256")):
                    admissible.append(row)

            if not admissible:
                diagnostics.append("NO_COMPATIBLE_LINKED_OFFICIAL_SESSION_LISTING_DATE")
            else:
                distinct_dates = sorted({clean(row.get("listing_date")) for row in admissible if clean(row.get("listing_date"))})
                if len(distinct_dates) != 1:
                    diagnostics.append(f"MULTIPLE_DISTINCT_LISTING_DATES:{len(distinct_dates)}")
                else:
                    selected = [row for row in admissible if clean(row.get("listing_date")) == distinct_dates[0]]
                    status = "EXACT"
                    transition_date = distinct_dates[0]
                    official_reference = "|".join(sorted({
                        f"IDX_DIGITAL_STATISTIC_LINK_STOCK_SPLIT:{clean(row.get('period_year'))}-{int(clean(row.get('period_month'))):02d}:{clean(row.get('row_identity_sha256'))}"
                        for row in selected
                    }))
                    source_sha256 = "|".join(sorted({clean(row.get("source_sha256")) for row in selected if clean(row.get("source_sha256"))}))
                    linkage_basis = "EXACT_TICKER_COMPATIBLE_SPLIT_FAMILY_SOURCE_DATE_LINKED_OFFICIAL_IDX_LISTING_DATE"

        evidence_rows.append({
            "event_id": event_id,
            "ticker": event_ticker,
            "event_source_type": source_type,
            "linkage_status": status,
            "transition_date": transition_date,
            "transition_semantic": accepted_semantic if status == "EXACT" else "",
            "official_reference": official_reference,
            "source_sha256": source_sha256,
            "linkage_basis": linkage_basis,
            "diagnostics": "|".join(diagnostics),
        })

    evidence = pd.DataFrame(evidence_rows).sort_values(["ticker", "event_id"], kind="mergesort").reset_index(drop=True)
    if len(evidence) != 47 or evidence.duplicated(["event_id", "ticker"]).any():
        raise RuntimeError("ADJUDICATION_EVENT_IDENTITY_CHANGED")
    identity = event_inventory_identity(evidence[["event_id", "ticker"]])
    scope_identity = event_inventory_identity(scope[["event_id", "ticker"]])
    if identity != scope_identity:
        raise RuntimeError("ADJUDICATION_EVENT_IDENTITY_HASH_CHANGED")

    audit = pd.DataFrame(audit_rows)
    if audit.empty:
        audit = pd.DataFrame(columns=[
            "event_id", "ticker", "event_source_type", "action_type", "listing_date",
            "row_identity_sha256", "source_sha256", "source_url", "family_compatible",
            "source_date_linked", "official_session",
        ])
    else:
        audit = audit.sort_values(["ticker", "event_id", "listing_date"], kind="mergesort").reset_index(drop=True)

    exact = int(evidence["linkage_status"].eq("EXACT").sum())
    unresolved = int(evidence["linkage_status"].eq("UNRESOLVED").sum())
    args.output_dir.mkdir(parents=True)
    evidence_path = args.output_dir / "residual47_idx_digital_split_event_evidence.csv"
    audit_path = args.output_dir / "residual47_idx_digital_split_adjudication_audit.csv"
    summary_path = args.output_dir / "summary.json"
    manifest_path = args.output_dir / "MANIFEST.json"
    evidence.to_csv(evidence_path, index=False, lineterminator="\n")
    audit.to_csv(audit_path, index=False, lineterminator="\n")

    summary = {
        "schema_version": "v4_3_ca_training_domain_residual47_idx_digital_split_adjudication_result_v1",
        "status": "V4_3_CA_RESIDUAL47_IDX_DIGITAL_SPLIT_OFFLINE_ADJUDICATION_COMPLETE",
        "outcome_blind": True,
        "network_calls": False,
        "provider_calls": False,
        "residual_events": 47,
        "residual_event_identity_sha256": identity,
        "exact_transition_events": exact,
        "resolved_events": exact,
        "unresolved_events": unresolved,
        "conflict_events": 0,
        "historical_target_loaded": False,
        "model_fit": False,
        "performance_computed": False,
        "protected_forward_accessed": False,
        "next": "REPLAY_IF_MATERIAL_YIELD_ELSE_STOP_CA_LANE",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_hashes = {
        "event_evidence": sha256_file(evidence_path),
        "adjudication_audit": sha256_file(audit_path),
        "summary": sha256_file(summary_path),
    }
    manifest = {
        "schema_version": "v4_3_ca_training_domain_residual47_idx_digital_split_adjudication_manifest_v1",
        "status": summary["status"],
        "outcome_blind": True,
        "immutable_inputs": {
            **acquisition_hashes,
            "official_calendar": calendar_sha,
            "residual_event_identity_sha256": identity,
        },
        "output_hashes": output_hashes,
        "guardrails": config["hard_boundaries"],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": summary["status"],
        "residual_events": 47,
        "exact_transition_events": exact,
        "resolved_events": exact,
        "unresolved_events": unresolved,
        "conflict_events": 0,
        "historical_target_loaded": False,
        "model_fit": False,
        "performance_computed": False,
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "next": summary["next"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
