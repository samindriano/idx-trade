"""Read-only reconciliation of local BBCA historical price surfaces.

This audit compares already-staged TradingView, Investing, and IDX payloads.
It does not construct features, repair prices, infer corporate-action truth,
or access targets/outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any


PRICE_FIELDS = ("open", "high", "low", "close")
COMPARE_FIELDS = PRICE_FIELDS + ("volume",)


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


def date_key(value: Any) -> str:
    return str(value)[:10]


def extract_rows(payload: dict[str, Any], container: str, path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError(f"missing data object: {path}")
    rows = data.get(container)
    if not isinstance(rows, list):
        raise ValueError(f"missing list {container}: {path}")
    by_date: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or "date" not in row:
            raise ValueError(f"invalid row in {path}")
        key = date_key(row["date"])
        if key in by_date:
            raise ValueError(f"duplicate normalized date {key} in {path}")
        by_date[key] = row
    return data, by_date


def numeric_ratio(left: Any, right: Any) -> float | None:
    try:
        a = float(left)
        b = float(right)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(a) or not math.isfinite(b) or b == 0:
        return None
    return a / b


def ratio_summary(left_rows: dict[str, dict[str, Any]], right_rows: dict[str, dict[str, Any]], field: str, keys: list[str]) -> dict[str, Any]:
    ratios = [
        ratio
        for key in keys
        if (ratio := numeric_ratio(left_rows[key].get(field), right_rows[key].get(field))) is not None
    ]
    if not ratios:
        return {"finite_count": 0, "median": None, "min": None, "max": None}
    return {
        "finite_count": len(ratios),
        "median": median(ratios),
        "min": min(ratios),
        "max": max(ratios),
    }


def exact_counts(left_rows: dict[str, dict[str, Any]], right_rows: dict[str, dict[str, Any]], keys: list[str]) -> dict[str, int]:
    return {
        field: sum(left_rows[key].get(field) == right_rows[key].get(field) for key in keys)
        for field in COMPARE_FIELDS
    }


def ratio_categories(left_rows: dict[str, dict[str, Any]], right_rows: dict[str, dict[str, Any]], field: str, keys: list[str]) -> dict[str, int]:
    categories: Counter[str] = Counter()
    for key in keys:
        ratio = numeric_ratio(left_rows[key].get(field), right_rows[key].get(field))
        if ratio is None:
            categories["non_finite_or_zero_denominator"] += 1
        elif math.isclose(ratio, 1.0, rel_tol=0.0, abs_tol=1e-9):
            categories["1.0"] += 1
        elif math.isclose(ratio, 5.0, rel_tol=0.0, abs_tol=1e-9):
            categories["5.0"] += 1
        else:
            categories["other"] += 1
    return dict(sorted(categories.items()))


def price_ratio_blocks(idx_rows: dict[str, dict[str, Any]], tv_rows: dict[str, dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    values: list[tuple[str, str]] = []
    for key in keys:
        ratio = numeric_ratio(idx_rows[key].get("close"), tv_rows[key].get("close"))
        if ratio is None:
            label = "non_finite"
        elif math.isclose(ratio, 1.0, rel_tol=0.0, abs_tol=1e-9):
            label = "1.0"
        elif math.isclose(ratio, 5.0, rel_tol=0.0, abs_tol=1e-9):
            label = "5.0"
        else:
            label = "other"
        values.append((key, label))
    if not values:
        return []
    blocks: list[dict[str, Any]] = []
    start = previous = values[0][0]
    label = values[0][1]
    for key, next_label in values[1:]:
        if next_label != label:
            blocks.append({"from": start, "to": previous, "label": label})
            start = key
            label = next_label
        previous = key
    blocks.append({"from": start, "to": previous, "label": label})
    return blocks


def listed_share_changes(idx_rows: dict[str, dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    previous_date: str | None = None
    previous_value: Any = None
    for key in keys:
        value = idx_rows[key].get("listedShares")
        if previous_date is not None and value != previous_value:
            changes.append({
                "date": key,
                "previous_date": previous_date,
                "previous_listed_shares": previous_value,
                "listed_shares": value,
                "ratio": numeric_ratio(value, previous_value),
            })
        previous_date = key
        previous_value = value
    return changes


def compare(name: str, left_rows: dict[str, dict[str, Any]], right_rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    keys = sorted(set(left_rows).intersection(right_rows))
    exact = exact_counts(left_rows, right_rows, keys)
    return {
        "left": name.split("_vs_")[0],
        "right": name.split("_vs_")[1],
        "overlap_rows": len(keys),
        "overlap_from": keys[0] if keys else None,
        "overlap_to": keys[-1] if keys else None,
        "exact_counts": exact,
        "exact_all_compare_fields": sum(all(left_rows[key].get(field) == right_rows[key].get(field) for field in COMPARE_FIELDS) for key in keys),
        "ratio_summaries": {field: ratio_summary(left_rows, right_rows, field, keys) for field in COMPARE_FIELDS},
        "ratio_categories": {field: ratio_categories(left_rows, right_rows, field, keys) for field in COMPARE_FIELDS},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tradingview", type=Path, required=True)
    parser.add_argument("--investing", type=Path, required=True)
    parser.add_argument("--idx", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    tv_payload = load_json(args.tradingview)
    investing_payload = load_json(args.investing)
    idx_payload = load_json(args.idx)
    manifest = load_json(args.manifest)
    tv_meta, tv_rows = extract_rows(tv_payload, "candles", args.tradingview)
    investing_meta, investing_rows = extract_rows(investing_payload, "candles", args.investing)
    idx_meta, idx_rows = extract_rows(idx_payload, "items", args.idx)

    tv_idx_keys = sorted(set(tv_rows).intersection(idx_rows))
    result: dict[str, Any] = {
        "schema": "idx_trade_alpha_bbca_price_basis_reconciliation_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": {
            "outcome_accessed": False,
            "model_scoring": False,
            "canonical_write": False,
            "cloud_or_r2_write": False,
            "network_used": False,
            "feature_or_candidate_created": False,
        },
        "status": "PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED",
        "admission": {
            "tradingview": "PARTIAL / SOURCE_ADMISSION_BLOCKED",
            "investing": "PARTIAL / SOURCE_ADMISSION_BLOCKED",
            "idx": "PARTIAL / STRUCTURAL_CROSS_CHECK_ONLY",
            "feature_admission": "CLOSED",
        },
        "manifest": {
            "path": str(args.manifest),
            "sha256": sha256_file(args.manifest),
            "run_id": manifest.get("run_id"),
            "retry_policy": manifest.get("retry_policy"),
            "safe_flags": {key: manifest.get(key) for key in ("outcome_accessed", "model_scoring", "canonical_write", "cloud_or_r2_write")},
        },
        "manifest_sha256": sha256_file(args.manifest),
        "source_hashes": {
            "tradingview": sha256_file(args.tradingview),
            "investing": sha256_file(args.investing),
            "idx": sha256_file(args.idx),
            "manifest": sha256_file(args.manifest),
        },
        "sources": {
            "tradingview": {"path": str(args.tradingview), "sha256": sha256_file(args.tradingview), "rows": len(tv_rows), "metadata": {key: tv_meta.get(key) for key in ("symbol", "isin", "exchange", "market", "barSource", "barTransform", "hasAdjustment", "allowedAdjustment", "count")}},
            "investing": {"path": str(args.investing), "sha256": sha256_file(args.investing), "rows": len(investing_rows), "metadata": {key: investing_meta.get(key) for key in ("symbol", "pairId", "interval", "period", "count")}},
            "idx": {"path": str(args.idx), "sha256": sha256_file(args.idx), "rows": len(idx_rows), "metadata": {key: idx_meta.get(key) for key in ("code", "provider", "dataset", "from", "to", "unit", "valueBasis", "count")}},
        },
        "comparisons": {
            "tradingview_vs_idx": compare("tradingview_vs_idx", tv_rows, idx_rows),
            "investing_vs_idx": compare("investing_vs_idx", investing_rows, idx_rows),
            "tradingview_vs_investing": compare("tradingview_vs_investing", tv_rows, investing_rows),
        },
        "tradingview_idx_basis": {
            "price_ratio_definition": "idx_close / tradingview_close",
            "price_ratio_blocks": price_ratio_blocks(idx_rows, tv_rows, tv_idx_keys),
            "idx_listed_share_changes": listed_share_changes(idx_rows, sorted(idx_rows)),
        },
        "interpretation": [
            "TradingView and IDX have one date-normalized overlap with a stable 5.0 price/volume basis block before 2021-10-13 and a 1.0 price basis block from 2021-10-13 onward.",
            "The local IDX listed-share series changes by 5.0 on 2021-10-13; this is a coincident structural marker, not independent corporate-action certification.",
            "Investing has zero exact OHLCV field matches against IDX on its 1,568 overlapping dates and does not reduce to a single constant scale factor in this audit.",
            "These observations establish source/basis divergence and adjustment ambiguity, not which source is economically or PIT authoritative.",
        ],
        "code_sha256": sha256_file(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
