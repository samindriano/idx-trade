from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

EXPECTED_PROVIDER_REPOSITORY = "nichsedge/idx-bei"
EXPECTED_PROVIDER_COMMIT = "75d6c0f74fa360d225794c70c383348977de6798"
EXPECTED_UPSTREAM = "https://www.idx.co.id/primary"
EXPECTED_ENDPOINT = "/Home/GetCalendar"
EXPECTED_PARAMS = {
    "range": "m",
    "start": 0,
    "length": 9999,
    "code": "",
    "language": "id-id",
    "search": "",
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _structural_fingerprint(value: Any) -> str:
    def shape(x: Any) -> Any:
        if isinstance(x, dict):
            return {"dict": {str(k): shape(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}}
        if isinstance(x, list):
            if not x:
                return {"list": []}
            unique = {}
            for item in x[:25]:
                sig = json.dumps(shape(item), sort_keys=True, separators=(",", ":"))
                unique[sig] = json.loads(sig)
            return {"list": [unique[k] for k in sorted(unique)]}
        if x is None:
            return "null"
        if isinstance(x, bool):
            return "bool"
        if isinstance(x, int):
            return "int"
        if isinstance(x, float):
            return "float"
        return "str"

    blob = json.dumps(shape(value), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _fail(code: str) -> None:
    raise SystemExit(code)


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently review Forward CA Home/GetCalendar probe evidence.")
    parser.add_argument("--probe-dir", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    root = Path(args.probe_dir).expanduser().resolve()
    manifest_path = root / "PROBE_MANIFEST.json"
    raw_path = root / "calendar_raw.json"
    if not manifest_path.is_file():
        _fail(f"PROBE_REVIEW_MANIFEST_MISSING:{manifest_path}")
    if not raw_path.is_file():
        _fail(f"PROBE_REVIEW_RAW_MISSING:{raw_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw_bytes = raw_path.read_bytes()
        payload = json.loads(raw_bytes.decode("utf-8"))
    except Exception as exc:
        _fail(f"PROBE_REVIEW_JSON_INVALID:{type(exc).__name__}")

    failures: list[str] = []
    warnings: list[str] = []

    if manifest.get("schema_version") != "idx_trade_forward_ca_calendar_probe_v1":
        failures.append("MANIFEST_SCHEMA_CHANGED")
    if manifest.get("status") != "PROBE_COMPLETE_NOT_YET_FROZEN":
        failures.append("MANIFEST_STATUS_INVALID")
    if manifest.get("provider_repository") != EXPECTED_PROVIDER_REPOSITORY:
        failures.append("PROVIDER_REPOSITORY_MISMATCH")
    if manifest.get("provider_commit") != EXPECTED_PROVIDER_COMMIT:
        failures.append("PROVIDER_COMMIT_MISMATCH")
    if manifest.get("upstream_base_url") != EXPECTED_UPSTREAM:
        failures.append("UPSTREAM_MISMATCH")
    if manifest.get("endpoint") != EXPECTED_ENDPOINT:
        failures.append("ENDPOINT_MISMATCH")
    if int(manifest.get("http_status") or 0) != 200:
        failures.append("HTTP_STATUS_NOT_200")

    params = manifest.get("params")
    if not isinstance(params, dict):
        failures.append("PARAMS_MISSING")
        params = {}
    else:
        for key, expected in EXPECTED_PARAMS.items():
            if params.get(key) != expected:
                failures.append(f"PARAM_MISMATCH:{key}")
        anchor = str(params.get("date") or "")
        if len(anchor) != 8 or not anchor.isdigit():
            failures.append("PARAM_DATE_INVALID")

    actual_raw_sha = _sha256_bytes(raw_bytes)
    declared_raw_sha = str(manifest.get("raw_sha256") or "")
    if actual_raw_sha != declared_raw_sha:
        failures.append("RAW_SHA_MISMATCH")

    if not isinstance(payload, dict):
        failures.append("RAW_NOT_OBJECT")
        results: list[Any] = []
    else:
        results = payload.get("Results")
        if not isinstance(results, list):
            failures.append("RESULTS_NOT_LIST")
            results = []
        elif not results:
            failures.append("RESULTS_EMPTY")

    actual_fp = _structural_fingerprint(payload)
    declared_fp = str(manifest.get("calendar_schema_fingerprint") or "")
    if actual_fp != declared_fp:
        failures.append("FINGERPRINT_MISMATCH")

    top_level_keys = sorted(str(k) for k in payload.keys()) if isinstance(payload, dict) else []
    declared_top = manifest.get("top_level_keys")
    if isinstance(declared_top, list) and top_level_keys != sorted(str(x) for x in declared_top):
        failures.append("TOP_LEVEL_KEYS_MISMATCH")

    sample_rows = [x for x in results[:25] if isinstance(x, dict)]
    sample_key_union = sorted({str(k) for row in sample_rows for k in row.keys()})
    declared_sample = manifest.get("sample_result_keys_union")
    if isinstance(declared_sample, list) and sample_key_union != sorted(str(x) for x in declared_sample):
        failures.append("SAMPLE_KEYS_MISMATCH")

    # Known/likely useful calendar semantics. Missing fields do not automatically fail because
    # upstream naming may evolve; the frozen structural fingerprint remains the hard guard.
    ticker_candidates = {"title", "KodeEmiten", "code", "Code"}
    date_candidates = {"start", "Tanggal", "date", "Date", "end"}
    event_candidates = {"Jenis", "JenisAgenda", "description", "Keterangan", "Agenda", "Step"}
    present = set(sample_key_union)
    if not (present & ticker_candidates):
        warnings.append("NO_RECOGNIZED_TICKER_FIELD_IN_SAMPLE")
    if not (present & date_candidates):
        warnings.append("NO_RECOGNIZED_DATE_FIELD_IN_SAMPLE")
    if not (present & event_candidates):
        warnings.append("NO_RECOGNIZED_EVENT_FIELD_IN_SAMPLE")

    # Pagination/completeness inspection. Home/GetCalendar commonly returns all matching
    # Results for length=9999; if explicit total/count metadata exists, require consistency.
    pagination_checks: dict[str, Any] = {}
    for key in ("recordsTotal", "recordsFiltered", "Total", "total", "Count", "count"):
        if isinstance(payload, dict) and key in payload:
            pagination_checks[key] = payload[key]
    numeric_totals = [
        int(v) for v in pagination_checks.values()
        if isinstance(v, int) and not isinstance(v, bool)
    ]
    if numeric_totals and max(numeric_totals) > len(results):
        failures.append("PAGINATION_INCOMPLETE")

    report = {
        "schema_version": "idx_trade_forward_ca_calendar_probe_review_v1",
        "status": "PASS_ELIGIBLE_FOR_SCHEMA_FREEZE" if not failures else "FAIL_DO_NOT_FREEZE",
        "probe_dir": str(root),
        "provider_repository": manifest.get("provider_repository"),
        "provider_commit": manifest.get("provider_commit"),
        "upstream_base_url": manifest.get("upstream_base_url"),
        "endpoint": manifest.get("endpoint"),
        "params": params,
        "http_status": manifest.get("http_status"),
        "raw_sha256": actual_raw_sha,
        "calendar_schema_fingerprint": actual_fp,
        "top_level_keys": top_level_keys,
        "results_count": len(results),
        "sample_result_keys_union": sample_key_union,
        "pagination_metadata": pagination_checks,
        "failures": failures,
        "warnings": warnings,
        "freeze_recommendation": (not failures),
    }

    output = Path(args.output).expanduser().resolve() if args.output else root / "PROBE_REVIEW.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if failures:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
