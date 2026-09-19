"""Build a read-only field-level contract for the staged panel-depth source."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FIELDS = (
    "date", "open", "high", "low", "close", "previous", "change", "volume",
    "value", "frequency", "bid", "offer", "listedShares", "foreignBuyShares",
    "foreignSellShares", "netForeignShares", "foreignBuyValue", "foreignSellValue",
    "netForeignValue",
)

FIELD_CONTRACTS: dict[str, dict[str, Any]] = {
    "date": {"semantic": "session/date key", "unit": "calendar date", "status": "PARTIAL", "basis": "source date only; no knowledge-time"},
    "open": {"semantic": "opening price", "unit": "UNKNOWN", "status": "UNKNOWN", "basis": "price adjustment/currency not established"},
    "high": {"semantic": "session high price", "unit": "UNKNOWN", "status": "UNKNOWN", "basis": "price adjustment/currency not established"},
    "low": {"semantic": "session low price", "unit": "UNKNOWN", "status": "UNKNOWN", "basis": "price adjustment/currency not established"},
    "close": {"semantic": "closing price", "unit": "UNKNOWN", "status": "UNKNOWN", "basis": "price adjustment/currency not established"},
    "previous": {"semantic": "previous/reference price", "unit": "UNKNOWN", "status": "UNKNOWN", "basis": "price adjustment/currency not established"},
    "change": {"semantic": "reported price change", "unit": "UNKNOWN", "status": "UNKNOWN", "basis": "price adjustment/currency not established"},
    "volume": {"semantic": "traded volume", "unit": "shares per top-level metadata only", "status": "PARTIAL", "basis": "aggregation/session semantics not independently defined"},
    "value": {"semantic": "traded value", "unit": "UNKNOWN currency", "status": "UNKNOWN", "basis": "field-level monetary unit/currency absent"},
    "frequency": {"semantic": "frequency/trade-count-like field; exact meaning unknown", "unit": "UNKNOWN", "status": "UNKNOWN", "basis": "field definition absent"},
    "bid": {"semantic": "bid quote state", "unit": "UNKNOWN price units", "status": "PARTIAL", "basis": "quote timestamp/age/depth/zero semantics absent"},
    "offer": {"semantic": "offer quote state", "unit": "UNKNOWN price units", "status": "PARTIAL", "basis": "quote timestamp/age/depth/zero semantics absent"},
    "listedShares": {"semantic": "listed/outstanding-share-like field", "unit": "shares", "status": "PARTIAL", "basis": "issuer/CA transition and observation timing absent"},
    "foreignBuyShares": {"semantic": "foreign buy flow", "unit": "shares", "status": "PARTIAL", "basis": "actor scope/aggregation/publication/revision absent"},
    "foreignSellShares": {"semantic": "foreign sell flow", "unit": "shares", "status": "PARTIAL", "basis": "actor scope/aggregation/publication/revision absent"},
    "netForeignShares": {"semantic": "net foreign flow", "unit": "shares", "status": "PARTIAL", "basis": "derived arithmetic exact; PIT/actor scope absent"},
    "foreignBuyValue": {"semantic": "foreign buy flow value", "unit": "UNKNOWN currency", "status": "UNKNOWN", "basis": "monetary unit/currency/publication/revision absent"},
    "foreignSellValue": {"semantic": "foreign sell flow value", "unit": "UNKNOWN currency", "status": "UNKNOWN", "basis": "monetary unit/currency/publication/revision absent"},
    "netForeignValue": {"semantic": "net foreign flow value", "unit": "UNKNOWN currency", "status": "UNKNOWN", "basis": "derived arithmetic exact; monetary unit/PIT absent"},
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def numeric_summary(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values: list[float] = []
    missing = zero = negative = positive = 0
    for row in rows:
        value = row.get(field)
        if value is None:
            missing += 1
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            missing += 1
            continue
        if not math.isfinite(number):
            missing += 1
        elif number == 0:
            zero += 1
            values.append(number)
        elif number < 0:
            negative += 1
            values.append(number)
        else:
            positive += 1
            values.append(number)
    return {
        "rows": len(rows),
        "missing_or_non_finite": missing,
        "zero": zero,
        "negative": negative,
        "positive": positive,
        "distinct_values": len({str(row.get(field)) for row in rows if row.get(field) is not None}),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = load_json(args.manifest)
    files = sorted(args.root.glob("*.json"))
    if len(files) != 12:
        raise ValueError(f"expected 12 normalized symbol files, got {len(files)}")
    all_rows: list[dict[str, Any]] = []
    symbol_rows: dict[str, int] = {}
    source_hashes: dict[str, str] = {"manifest": sha256_file(args.manifest)}
    for path in files:
        payload = load_json(path)
        data = payload.get("data", payload)
        rows = data.get("items", []) if isinstance(data, dict) else []
        if not isinstance(rows, list):
            raise ValueError(f"missing items list: {path}")
        symbol = path.stem
        symbol_rows[symbol] = len(rows)
        source_hashes[symbol] = sha256_file(path)
        all_rows.extend(row for row in rows if isinstance(row, dict))

    field_observations = {field: numeric_summary(all_rows, field) for field in FIELDS if field != "date"}
    field_observations["date"] = {
        "rows": len(all_rows),
        "missing_or_non_finite": sum(not isinstance(row.get("date"), str) or len(str(row.get("date"))) < 10 for row in all_rows),
        "distinct_values": len({str(row.get("date"))[:10] for row in all_rows}),
    }
    foreign_arithmetic = {
        "netForeignShares_exact_rows": sum(row.get("netForeignShares") == (row.get("foreignBuyShares") - row.get("foreignSellShares")) for row in all_rows),
        "netForeignValue_exact_rows": sum(row.get("netForeignValue") == (row.get("foreignBuyValue") - row.get("foreignSellValue")) for row in all_rows),
    }
    bid_offer = {
        "both_positive_rows": sum(float(row.get("bid", 0)) > 0 and float(row.get("offer", 0)) > 0 for row in all_rows),
        "bid_positive_offer_zero_rows": sum(float(row.get("bid", 0)) > 0 and float(row.get("offer", 0)) == 0 for row in all_rows),
        "bid_gt_offer_when_both_positive_rows": sum(float(row.get("bid", 0)) > float(row.get("offer", 0)) > 0 for row in all_rows),
    }
    listed_changes: dict[str, int] = {}
    for path in files:
        data = load_json(path).get("data", {})
        rows = data.get("items", [])
        ascending = sorted(rows, key=lambda row: str(row.get("date", "")))
        listed_changes[path.stem] = sum(a.get("listedShares") != b.get("listedShares") for a, b in zip(ascending, ascending[1:]))
    result: dict[str, Any] = {
        "schema": "idx_trade_alpha_panel_depth_field_contract_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED",
        "scope": {
            "outcome_accessed": False,
            "model_scoring": False,
            "canonical_write": False,
            "cloud_or_r2_write": False,
            "network_used": False,
            "feature_or_candidate_created": False,
        },
        "source": {
            "manifest_path": str(args.manifest),
            "manifest_sha256": sha256_file(args.manifest),
            "manifest_run_id": manifest.get("run_id"),
            "symbol_file_count": len(files),
            "symbol_rows": symbol_rows,
            "total_rows": len(all_rows),
            "top_level_unit": "shares",
            "top_level_value_basis": "close",
            "row_level_identity_fields_present": False,
            "row_level_pit_fields_present": False,
            "row_level_revision_vintage_fields_present": False,
            "row_level_ca_issuer_fields_present": False,
        },
        "field_contract": {
            field: {**FIELD_CONTRACTS[field], "observed": field_observations[field]}
            for field in FIELDS
        },
        "structural_checks": {
            "foreign_arithmetic": foreign_arithmetic,
            "bid_offer": bid_offer,
            "listed_share_adjacent_transition_counts": listed_changes,
            "listed_share_transition_total": sum(listed_changes.values()),
        },
        "future_specification": {
            "id": "FUTURE_QUOTE_FLOW_INTERACTION_V1",
            "status": "FUTURE_DATA / SOURCE_ADMISSION_BLOCKED / NOVELTY_UNKNOWN",
            "mechanism": "EOD quote-state and foreign-pressure interaction",
            "newness_adjudication": "Bid/offer is a new raw-input surface; foreign-flow alone remains within H-FLOW/Foreign Flow family.",
            "required_contract": [
                "population-wide PIT/available-at and revision/vintage",
                "quote timestamp/age/depth and executable semantics",
                "foreign actor scope, aggregation, monetary unit/currency",
                "identity/ISIN continuity and corporate-action/share-basis authority",
                "complete universe coverage and missingness policy",
            ],
            "not_a_candidate": True,
        },
        "source_hashes": source_hashes,
        "code_sha256": sha256_file(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
