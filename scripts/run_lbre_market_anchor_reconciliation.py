from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean, median
from typing import Any


MONTHLY_ROOT = Path(r"D:\Documents\Project\idx-lbre-monthly-free-float-history-20260815-v1")
SNAPSHOT_ROOT = Path(r"D:\Documents\Project\idx-historical-statutory-free-float-snapshot-20260815-v1")
OUTPUT_ROOT = Path(r"D:\Documents\Project\idx-lbre-market-anchor-reconciliation-20260816-v1")
EXPECTED_MONTHLY_MANIFEST = "e134809a1f1b745daf2f21c33ab7db78c38d1d5d520f5320564359d5b865bd86"
EXPECTED_SNAPSHOT_MANIFEST = "7e5d9cad904374d66b2ef69d25de5c974e06799cc617494619addde2fedb3a7e"
MARKET_PUBLISHED_AT = "2026-02-19T10:45:51+07:00"
PCT_TOLERANCE = 0.01
CLASSIFICATIONS = (
    "EXACT_AGREE",
    "SHARES_AGREE_PCT_DIFF",
    "SHARES_DIFF_PCT_AGREE",
    "SHARES_AND_PCT_DIFF",
    "LBRE_ONLY",
    "MARKET_ONLY",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_parents(output: Path) -> dict[str, Any]:
    checks = []
    for label, root, expected in (
        ("monthly_history", MONTHLY_ROOT, EXPECTED_MONTHLY_MANIFEST),
        ("historical_snapshot", SNAPSHOT_ROOT, EXPECTED_SNAPSHOT_MANIFEST),
    ):
        manifest = root / "artifact_manifest.json"
        actual = sha256_file(manifest)
        if actual != expected:
            raise RuntimeError(f"{label} manifest mismatch: expected {expected}, got {actual}")
        checks.append({"label": label, "root": str(root), "manifest": str(manifest), "sha256": actual, "valid": True})
    result = {"schema": "IDX_LBRE_MARKET_ANCHOR_PARENT_VERIFICATION_V1", "checks": checks}
    dump_json(output / "metadata/parent_manifest_verification.json", result)
    return result


def classify_overlap(lbre: dict[str, Any], market: dict[str, Any]) -> str:
    shares_same = int(lbre["free_float_shares"]) == int(market["free_float_shares"])
    pct_same = abs(float(lbre["free_float_pct"]) - float(market["free_float_pct"])) <= PCT_TOLERANCE
    if shares_same and pct_same:
        return "EXACT_AGREE"
    if shares_same:
        return "SHARES_AGREE_PCT_DIFF"
    if pct_same:
        return "SHARES_DIFF_PCT_AGREE"
    return "SHARES_AND_PCT_DIFF"


def diagnostic_row(ticker: str, lbre: dict[str, Any] | None, market: dict[str, Any] | None) -> dict[str, Any]:
    if lbre is None:
        return {"ticker": ticker, "classification": "MARKET_ONLY", "lbre_present": False, "market_present": True}
    if market is None:
        return {"ticker": ticker, "classification": "LBRE_ONLY", "lbre_present": True, "market_present": False}
    lbre_shares = int(lbre["free_float_shares"])
    market_shares = int(market["free_float_shares"])
    lbre_pct = float(lbre["free_float_pct"])
    market_pct = float(market["free_float_pct"])
    total = lbre.get("total_listed_shares")
    implied = (lbre_shares / int(total) * 100.0) if total not in (None, "", 0) else None
    lbre_published = datetime.fromisoformat(lbre["published_at"])
    market_published = datetime.fromisoformat(MARKET_PUBLISHED_AT)
    return {
        "ticker": ticker,
        "classification": classify_overlap(lbre, market),
        "lbre_present": True,
        "market_present": True,
        "lbre_free_float_shares": lbre_shares,
        "market_free_float_shares": market_shares,
        "share_delta": lbre_shares - market_shares,
        "share_delta_abs": abs(lbre_shares - market_shares),
        "share_delta_pct_of_lbre": (abs(lbre_shares - market_shares) / lbre_shares * 100.0) if lbre_shares else None,
        "lbre_free_float_pct": lbre_pct,
        "market_free_float_pct": market_pct,
        "pct_delta_pp": lbre_pct - market_pct,
        "lbre_total_listed_shares": int(total) if total not in (None, "") else None,
        "lbre_implied_pct": implied,
        "lbre_reported_minus_implied_pp": lbre_pct - implied if implied is not None else None,
        "lbre_published_at": lbre["published_at"],
        "market_published_at": MARKET_PUBLISHED_AT,
        "publication_delta_seconds_lbre_minus_market": (lbre_published - market_published).total_seconds(),
        "lbre_announcement_no": lbre["announcement_no"],
        "lbre_source_url": lbre["source_url"],
        "lbre_source_sha256": lbre["source_sha256"],
        "market_source_url": market.get("source_url"),
        "market_source_sha256": market.get("source_sha256"),
    }


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def numeric_summary(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = [float(row[field]) for row in rows if row.get(field) is not None]
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min": min(values),
        "q25": percentile(values, 0.25),
        "median": median(values),
        "mean": mean(values),
        "q75": percentile(values, 0.75),
        "max": max(values),
    }


def build(output: Path) -> dict[str, Any]:
    parent_verification = verify_parents(output)
    monthly = load_json(MONTHLY_ROOT / "normalized/lbre_current_observations.json")
    market_anchor = load_json(SNAPSHOT_ROOT / "normalized/market_anchor_2025_12_31.json")
    lbre_rows = {row["ticker"]: row for row in monthly if row.get("as_of_date") == "2025-12-31"}
    market_rows = {row["ticker"]: row for row in market_anchor["rows"]}
    rows = [diagnostic_row(ticker, lbre_rows.get(ticker), market_rows.get(ticker)) for ticker in sorted(set(lbre_rows) | set(market_rows))]
    overlap = [row for row in rows if row["lbre_present"] and row["market_present"]]
    observed_counts = Counter(row["classification"] for row in rows)
    class_counts = {classification: observed_counts.get(classification, 0) for classification in CLASSIFICATIONS}
    conflict_rows = [row for row in overlap if row["classification"] != "EXACT_AGREE"]
    delta_fields = {
        "share_delta": numeric_summary(overlap, "share_delta"),
        "share_delta_abs": numeric_summary(overlap, "share_delta_abs"),
        "share_delta_pct_of_lbre": numeric_summary(overlap, "share_delta_pct_of_lbre"),
        "pct_delta_pp": numeric_summary(overlap, "pct_delta_pp"),
        "lbre_reported_minus_implied_pp": numeric_summary(overlap, "lbre_reported_minus_implied_pp"),
    }
    shares_diff = [row for row in overlap if row["classification"] in {"SHARES_DIFF_PCT_AGREE", "SHARES_AND_PCT_DIFF"}]
    publication_deltas = [row["publication_delta_seconds_lbre_minus_market"] for row in overlap]
    publication = {
        "market_published_at": MARKET_PUBLISHED_AT,
        "overlap_count": len(overlap),
        "lbre_before_market_count": sum(value < 0 for value in publication_deltas),
        "same_timestamp_count": sum(value == 0 for value in publication_deltas),
        "lbre_after_market_count": sum(value > 0 for value in publication_deltas),
        "delta_seconds": numeric_summary([{"value": value} for value in publication_deltas], "value"),
    }
    evidence_sample = []
    for classification in sorted({row["classification"] for row in rows}):
        candidates = [row for row in rows if row["classification"] == classification]
        if classification in {"SHARES_DIFF_PCT_AGREE", "SHARES_AND_PCT_DIFF"}:
            candidates = sorted(candidates, key=lambda row: (row.get("share_delta_abs", 0), row["ticker"]), reverse=True)
        evidence_sample.extend(candidates[:5])
    denominator = {
        "lbre_overlap_rows": len(overlap),
        "lbre_total_listed_shares_available": sum(row.get("lbre_total_listed_shares") is not None for row in overlap),
        "share_identical_rows": sum(row["classification"] in {"EXACT_AGREE", "SHARES_AGREE_PCT_DIFF"} for row in overlap),
        "share_conflict_rows": len(shares_diff),
        "readiness": "PARTIAL_CONFLICT_REVIEW_REQUIRED" if shares_diff else "READY_WITH_EXPLICIT_GAPS",
    }
    result = {
        "schema": "IDX_LBRE_MARKET_ANCHOR_RECONCILIATION_V1",
        "position_date": "2025-12-31",
        "pct_tolerance": PCT_TOLERANCE,
        "parent_verification": parent_verification,
        "inputs": {
            "monthly_current_path": str(MONTHLY_ROOT / "normalized/lbre_current_observations.json"),
            "market_anchor_path": str(SNAPSHOT_ROOT / "normalized/market_anchor_2025_12_31.json"),
            "market_source": market_anchor["source"],
        },
        "class_counts": class_counts,
        "diagnostics": delta_fields,
        "publication_time": publication,
        "denominator_readiness": denominator,
        "evidence_review_sample": evidence_sample,
        "rows": rows,
    }
    dump_json(output / "normalized/classified_reconciliation_2025_12_31.json", result)
    dump_json(output / "reports/class_counts.json", {"class_counts": class_counts, "denominator_readiness": denominator})
    dump_json(output / "reports/delta_distributions.json", delta_fields)
    dump_json(output / "reports/publication_time_comparison.json", publication)
    dump_json(output / "reports/evidence_review_sample.json", {"sample_size": len(evidence_sample), "rows": evidence_sample})
    return result


def finalize(output: Path) -> str:
    files = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name not in {"artifact_manifest.json", "artifact_manifest.sha256"}:
            files.append({"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema": "IDX_LBRE_MARKET_ANCHOR_RECONCILIATION_V1",
        "position_date": "2025-12-31",
        "file_count": len(files),
        "files": files,
    }
    dump_json(output / "artifact_manifest.json", manifest)
    digest = sha256_file(output / "artifact_manifest.json")
    (output / "artifact_manifest.sha256").write_text(digest + "  artifact_manifest.json\n", encoding="utf-8")
    return digest


if __name__ == "__main__":
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    result = build(OUTPUT_ROOT)
    digest = finalize(OUTPUT_ROOT)
    print(json.dumps({"class_counts": result["class_counts"], "denominator_readiness": result["denominator_readiness"], "manifest_sha256": digest}, indent=2))
