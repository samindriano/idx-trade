from __future__ import annotations

import argparse
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA = "idx_trade_forward_ca_direct_idx_dividend_probe_v1"
EXPECTED_PROVIDER = "nichsedge/idx-bei"
EXPECTED_PROVIDER_COMMIT = "75d6c0f74fa360d225794c70c383348977de6798"
EXPECTED_UPSTREAM = "https://www.idx.co.id/primary"
EXPECTED_ENDPOINT = "/DigitalStatistic/GetApiDataPaginated"
EXPECTED_BBCA = {
    "cash_dividend": Decimal("281"),
    "cum_date": "2026-03-27",
    "ex_date": "2026-03-30",
    "record_date": "2026-03-31",
    "payment_date": "2026-04-08",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    for candidate in (text[:10], text):
        try:
            return date.fromisoformat(candidate).isoformat()
        except Exception:
            pass
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y%m%d"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except Exception:
            pass
    return None


def _decimal(value: Any) -> Decimal | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline review for direct IDX LINK_DIVIDEND probe.")
    parser.add_argument("--probe-dir", required=True)
    args = parser.parse_args()

    root = Path(args.probe_dir).expanduser().resolve()
    manifest_path = root / "PROBE_MANIFEST.json"
    raw_path = root / "dividend_raw.json"
    failures: list[str] = []
    warnings: list[str] = []

    if not manifest_path.is_file():
        raise SystemExit(f"manifest missing: {manifest_path}")
    if not raw_path.is_file():
        raise SystemExit(f"raw missing: {raw_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = raw_path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        payload = None
        failures.append("RAW_NOT_JSON")

    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        failures.append("MANIFEST_SCHEMA_MISMATCH")
    if manifest.get("status") != "PROBE_COMPLETE_AWAITING_OFFLINE_REVIEW":
        failures.append(f"MANIFEST_STATUS_INVALID:{manifest.get('status')}")
    if manifest.get("provider_repository") != EXPECTED_PROVIDER:
        failures.append("PROVIDER_REPOSITORY_MISMATCH")
    if manifest.get("provider_commit") != EXPECTED_PROVIDER_COMMIT:
        failures.append("PROVIDER_COMMIT_MISMATCH")
    if manifest.get("upstream_base_url") != EXPECTED_UPSTREAM:
        failures.append("UPSTREAM_MISMATCH")
    if manifest.get("endpoint") != EXPECTED_ENDPOINT:
        failures.append("ENDPOINT_MISMATCH")
    if int(manifest.get("http_status") or 0) != 200:
        failures.append("HTTP_STATUS_NOT_200")
    if int(manifest.get("direct_idx_request_count") or 0) != 1:
        failures.append("DIRECT_IDX_REQUEST_COUNT_NOT_ONE")
    if int(manifest.get("retry_count") or 0) != 0:
        failures.append("RETRY_COUNT_NOT_ZERO")
    if _sha256(raw) != str(manifest.get("raw_sha256") or ""):
        failures.append("RAW_SHA_MISMATCH")

    params = manifest.get("params") if isinstance(manifest.get("params"), dict) else {}
    expected_params = {
        "urlName": "LINK_DIVIDEND",
        "periodYear": 2026,
        "periodMonth": 3,
        "periodType": "monthly",
        "isPrint": "False",
        "cumulative": "false",
        "pageNumber": 1,
        "orderBy": "",
        "search": "",
    }
    for key, expected in expected_params.items():
        if params.get(key) != expected:
            failures.append(f"PARAM_MISMATCH:{key}")
    try:
        page_size = int(params.get("pageSize") or 0)
    except Exception:
        page_size = 0
    if not 1 <= page_size <= 200:
        failures.append("PAGE_SIZE_INVALID")

    rows: list[dict[str, Any]] = []
    records_total = None
    if not isinstance(payload, dict):
        failures.append("PAYLOAD_NOT_OBJECT")
    else:
        data = payload.get("data")
        if not isinstance(data, list):
            failures.append("DATA_NOT_LIST")
        else:
            rows = [row for row in data if isinstance(row, dict)]
            if len(rows) != len(data):
                failures.append("NON_OBJECT_DIVIDEND_ROW")
        records_total = payload.get("recordsTotal")
        if isinstance(records_total, int) and records_total > page_size:
            failures.append("PAGINATION_INCOMPLETE_FOR_PROBE")

    required_fields = {
        "code", "cashDividend", "cumDividend", "exDividend", "recordDate", "paymentDate"
    }
    row_keys = sorted({str(k) for row in rows for k in row})
    if rows and not required_fields.issubset(set(row_keys)):
        failures.append("REQUIRED_FIELDS_MISSING")

    bbca_rows = [row for row in rows if str(row.get("code") or "").strip().upper() == "BBCA"]
    normalized_bbca: list[dict[str, Any]] = []
    parity_match = False
    for row in bbca_rows:
        normalized = {
            "cash_dividend": str(_decimal(row.get("cashDividend"))) if _decimal(row.get("cashDividend")) is not None else None,
            "cum_date": _parse_date(row.get("cumDividend")),
            "ex_date": _parse_date(row.get("exDividend")),
            "record_date": _parse_date(row.get("recordDate")),
            "payment_date": _parse_date(row.get("paymentDate")),
        }
        normalized_bbca.append(normalized)
        if (
            _decimal(row.get("cashDividend")) == EXPECTED_BBCA["cash_dividend"]
            and normalized["cum_date"] == EXPECTED_BBCA["cum_date"]
            and normalized["ex_date"] == EXPECTED_BBCA["ex_date"]
            and normalized["record_date"] == EXPECTED_BBCA["record_date"]
            and normalized["payment_date"] == EXPECTED_BBCA["payment_date"]
        ):
            parity_match = True

    if not bbca_rows:
        failures.append("KNOWN_POSITIVE_BBCA_ROW_MISSING")
    elif not parity_match:
        failures.append("KNOWN_POSITIVE_BBCA_TERMS_MISMATCH")

    report = {
        "schema_version": "idx_trade_forward_ca_direct_idx_dividend_probe_review_v1",
        "status": "PASS_DIRECT_IDX_DIVIDEND_SOURCE_ELIGIBLE_FOR_V1_1" if not failures else "FAIL_DIRECT_IDX_DIVIDEND_SOURCE_NOT_ADMITTED",
        "provider_repository": manifest.get("provider_repository"),
        "provider_commit": manifest.get("provider_commit"),
        "upstream_base_url": manifest.get("upstream_base_url"),
        "endpoint": manifest.get("endpoint"),
        "params": params,
        "raw_sha256": _sha256(raw),
        "row_count": len(rows),
        "records_total": records_total,
        "row_keys_union": row_keys,
        "bbca_rows": normalized_bbca,
        "known_positive_parity_match": parity_match,
        "failures": failures,
        "warnings": warnings,
        "v1_1_direct_idx_dividend_authority_recommendation": not failures,
        "zapi_required": False,
    }
    output = root / "PROBE_REVIEW.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
