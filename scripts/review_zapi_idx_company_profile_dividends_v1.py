from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA = "idx_trade_zapi_idx_company_profile_dividend_probe_v1"
REVIEW_SCHEMA = "idx_trade_zapi_idx_company_profile_dividend_review_v1"
EXPECTED_ENDPOINT = "https://api.zpi.web.id/v1/finance:idx/company-profile"
EXPECTED_PARITY = {
    "ticker": "BBCA",
    "gross_dividend_per_share_idr": 20.0,
    "cum_date": "2026-06-15",
    "ex_date": "2026-06-17",
    "recording_date": "2026-06-18",
    "payment_date": "2026-06-26",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _unwrap(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("data", "content"):
            inner = value.get(key)
            if isinstance(inner, dict):
                return inner
    return value


def _positive_number(value: Any) -> float | None:
    try:
        x = float(value)
    except Exception:
        return None
    return x if x > 0 else None


def _parse_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    for candidate in (text[:10], text):
        try:
            return date.fromisoformat(candidate).isoformat()
        except Exception:
            pass
    for fmt in ("%Y%m%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except Exception:
            pass
    return None


def _semantic_rows(core: dict[str, Any], ticker: str) -> list[dict[str, Any]]:
    raw = core.get("dividends")
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        cash = _positive_number(item.get("cashPerShare"))
        cum = _parse_date(item.get("cumDate"))
        ex = _parse_date(item.get("exDate"))
        record = _parse_date(item.get("recordDate"))
        payment = _parse_date(item.get("paymentDate"))
        if cash is None or not all((cum, ex, record, payment)):
            continue
        if not (cum < ex <= record <= payment):
            continue
        rows.append({
            "ticker": ticker,
            "gross_dividend_per_share_idr": cash,
            "cum_date": cum,
            "ex_date": ex,
            "recording_date": record,
            "payment_date": payment,
            "type": item.get("type"),
            "book_year": item.get("bookYear"),
        })
    return rows


def _matches_expected(row: dict[str, Any]) -> bool:
    return all(row.get(k) == v for k, v in EXPECTED_PARITY.items())


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Zapi company-profile dividend parity reviewer.")
    parser.add_argument("--probe-dir", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    root = Path(args.probe_dir).expanduser().resolve()
    manifest_path = root / "PROBE_MANIFEST.json"
    raw_path = root / "company_profile_raw.json"
    failures: list[str] = []
    warnings: list[str] = []

    if not manifest_path.is_file():
        raise SystemExit(f"COMPANY_PROFILE_REVIEW_MANIFEST_MISSING:{manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        failures.append("MANIFEST_SCHEMA_CHANGED")
    if manifest.get("status") != "PROBE_COMPLETE_AWAITING_OFFLINE_REVIEW":
        failures.append("MANIFEST_NOT_COMPLETE")
    if manifest.get("endpoint_url") != EXPECTED_ENDPOINT:
        failures.append("ENDPOINT_MISMATCH")
    if int(manifest.get("authenticated_request_count") or 0) != 1:
        failures.append("AUTH_REQUEST_COUNT_NOT_ONE")
    if int(manifest.get("retry_count") or 0) != 0:
        failures.append("RETRIES_NOT_ZERO")
    if manifest.get("api_key_persisted") is not False:
        failures.append("API_KEY_PERSISTENCE_CONTRACT_VIOLATED")
    if int(manifest.get("http_status") or 0) != 200:
        failures.append(f"HTTP_STATUS_NOT_200:{manifest.get('http_status')}")

    target = str(manifest.get("target_code") or "").strip().upper()
    params = manifest.get("params") if isinstance(manifest.get("params"), dict) else {}
    if str(params.get("code") or "").strip().upper() != target or target != "BBCA":
        failures.append("TARGET_SCOPE_MISMATCH")

    raw_bytes = b""
    payload: Any = None
    if not raw_path.is_file():
        failures.append("RAW_RESPONSE_MISSING")
    else:
        raw_bytes = raw_path.read_bytes()
        if _sha256(raw_bytes) != str(manifest.get("raw_sha256") or ""):
            failures.append("RAW_SHA_MISMATCH")
        try:
            payload = json.loads(raw_bytes.decode("utf-8"))
        except Exception:
            failures.append("RAW_RESPONSE_NOT_JSON")

    core = _unwrap(payload)
    if not isinstance(core, dict):
        failures.append("PROFILE_NOT_OBJECT")
        core = {}

    code = str(core.get("code") or "").strip().upper()
    provider = core.get("provider")
    dataset = core.get("dataset")
    if code != target:
        failures.append(f"PROFILE_CODE_MISMATCH:{code}")
    if str(provider or "").lower() != "idx":
        failures.append(f"PROVIDER_NOT_IDX:{provider}")
    if str(dataset or "").lower() != "company-profile":
        failures.append(f"DATASET_NOT_COMPANY_PROFILE:{dataset}")

    raw_dividends = core.get("dividends")
    if not isinstance(raw_dividends, list):
        failures.append("DIVIDENDS_NOT_LIST")
        raw_dividends = []
    elif not raw_dividends:
        failures.append("DIVIDENDS_EMPTY")

    rows = _semantic_rows(core, target)
    if not rows:
        failures.append("NO_COMPLETE_DIVIDEND_SEMANTIC_ROW")
    parity_rows = [row for row in rows if _matches_expected(row)]
    if not parity_rows:
        failures.append("OFFICIAL_BBCA_2026_Q2_PARITY_EVENT_NOT_FOUND")

    headers = manifest.get("response_headers") if isinstance(manifest.get("response_headers"), dict) else {}
    content_type = str(headers.get("content-type") or "").lower()
    if content_type and "json" not in content_type:
        failures.append("CONTENT_TYPE_NOT_JSON")
    if "cache-control" not in headers:
        warnings.append("CACHE_POLICY_HEADER_MISSING")

    report = {
        "schema_version": REVIEW_SCHEMA,
        "status": "PASS_ELIGIBLE_FOR_V1_1_COMPANY_PROFILE_HELPER" if not failures else "FAIL_NOT_ELIGIBLE_FOR_V1_1_COMPANY_PROFILE_HELPER",
        "probe_dir": str(root),
        "target_code": target,
        "endpoint_url": manifest.get("endpoint_url"),
        "http_status": manifest.get("http_status"),
        "raw_sha256": _sha256(raw_bytes) if raw_bytes else None,
        "provider": provider,
        "dataset": dataset,
        "dividend_row_count": len(raw_dividends),
        "complete_semantic_rows": rows,
        "official_parity_expected": EXPECTED_PARITY,
        "official_parity_matches": parity_rows,
        "cache_observation": {k: headers[k] for k in ("cache-control", "age", "etag", "last-modified") if k in headers},
        "failures": failures,
        "warnings": warnings,
        "v1_1_structured_helper_recommendation": (not failures),
        "authority_policy": "DIRECT_IDX_REMAINS_AUTHORITY_ZAPI_COMPANY_PROFILE_STRUCTURED_HELPER_ONLY_DISAGREEMENT_FAILS_CLOSED",
    }

    output = Path(args.output).expanduser().resolve() if args.output else root / "PROBE_REVIEW.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
