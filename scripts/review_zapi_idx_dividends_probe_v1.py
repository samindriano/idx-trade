from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

MANIFEST_SCHEMA = "idx_trade_zapi_idx_dividends_probe_v1"
EXPECTED_ENDPOINT = "https://api.zpi.web.id/v1/finance:idx/dividends"
EXPECTED_CATALOG = "https://api.zpi.web.id/api/public/scrapers/idx/endpoints/dividends/schema"
REVIEW_SCHEMA = "idx_trade_zapi_idx_dividends_probe_review_v1"

TICKER_ALIASES = (
    "code", "ticker", "symbol", "stockCode", "StockCode", "companyCode",
    "issuerCode", "KodeEmiten", "kodeEmiten",
)
CASH_ALIASES = (
    "cashPerShare", "cash_per_share", "dividendPerShare", "dividend_per_share",
    "cashDividendPerShare", "cash_dividend_per_share", "dps",
)
CUM_ALIASES = (
    "cumDate", "cum_date", "cumTradingDate", "cum_date_regular_market",
    "cumDateRegular", "cumDateReguler", "cumRegularDate",
)
EX_ALIASES = (
    "exDate", "ex_date", "exTradingDate", "ex_date_regular_market",
    "exDateRegular", "exDateReguler", "exRegularDate",
)
RECORD_ALIASES = (
    "recordDate", "record_date", "recordingDate", "recording_date",
)
PAYMENT_ALIASES = (
    "paymentDate", "payment_date", "payDate", "pay_date",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _shape_fingerprint(value: Any) -> str:
    def shape(x: Any) -> Any:
        if isinstance(x, dict):
            return {"dict": {str(k): shape(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}}
        if isinstance(x, list):
            unique: dict[str, Any] = {}
            for item in x[:50]:
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
    blob = json.dumps(shape(value), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def _unwrap(value: Any) -> Any:
    if isinstance(value, dict) and "content" in value and value.get("content") is not None:
        return value["content"]
    return value


def _dict_lists(value: Any, path: str = "$", depth: int = 0) -> Iterable[tuple[str, list[dict[str, Any]]]]:
    if depth > 6:
        return
    if isinstance(value, list):
        rows = [x for x in value if isinstance(x, dict)]
        if rows:
            yield path, rows
        for i, item in enumerate(value[:5]):
            yield from _dict_lists(item, f"{path}[{i}]", depth + 1)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _dict_lists(item, f"{path}.{key}", depth + 1)


def _first(row: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for key in aliases:
        if key in row and row[key] not in (None, ""):
            return row[key]
    lower = {str(k).lower(): v for k, v in row.items()}
    for key in aliases:
        value = lower.get(key.lower())
        if value not in (None, ""):
            return value
    return None


def _positive_number(value: Any) -> float | None:
    try:
        if isinstance(value, str):
            cleaned = value.strip().replace("Rp", "").replace("IDR", "").replace(" ", "")
            if cleaned.count(",") == 1 and cleaned.count(".") == 0:
                cleaned = cleaned.replace(",", ".")
            elif cleaned.count(".") > 1 and "," not in cleaned:
                cleaned = cleaned.replace(".", "")
            value = cleaned
        x = float(value)
    except Exception:
        return None
    return x if x > 0 else None


def _date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    candidates = [text[:10], text]
    for candidate in candidates:
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


def _row_score(row: dict[str, Any]) -> int:
    groups = (TICKER_ALIASES, CASH_ALIASES, CUM_ALIASES, EX_ALIASES, RECORD_ALIASES, PAYMENT_ALIASES)
    return sum(_first(row, group) is not None for group in groups)


def _params_lower(params: dict[str, Any]) -> dict[str, Any]:
    return {str(k).lower(): v for k, v in params.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline reviewer for Zapi IDX dividends audit probe.")
    parser.add_argument("--probe-dir", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    root = Path(args.probe_dir).expanduser().resolve()
    manifest_path = root / "PROBE_MANIFEST.json"
    raw_path = root / "dividends_raw.json"
    catalog_path = root / "catalog_schema_raw.json"
    failures: list[str] = []
    warnings: list[str] = []

    if not manifest_path.is_file():
        raise SystemExit(f"ZAPI_DIVIDENDS_REVIEW_MANIFEST_MISSING:{manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        failures.append("MANIFEST_SCHEMA_CHANGED")
    if manifest.get("status") != "PROBE_COMPLETE_AWAITING_OFFLINE_REVIEW":
        failures.append(f"MANIFEST_NOT_COMPLETE:{manifest.get('status')}")
    if manifest.get("endpoint_url") != EXPECTED_ENDPOINT:
        failures.append("ENDPOINT_MISMATCH")
    if manifest.get("catalog_schema_url") != EXPECTED_CATALOG:
        failures.append("CATALOG_ENDPOINT_MISMATCH")
    if int(manifest.get("authenticated_request_count") or 0) != 1:
        failures.append("AUTHENTICATED_REQUEST_COUNT_NOT_ONE")
    if int(manifest.get("retry_count") or 0) != 0:
        failures.append("RETRIES_NOT_ZERO")
    if manifest.get("api_key_persisted") is not False:
        failures.append("API_KEY_PERSISTENCE_CONTRACT_VIOLATED")
    if int(manifest.get("http_status") or 0) != 200:
        failures.append(f"HTTP_STATUS_NOT_200:{manifest.get('http_status')}")

    params = manifest.get("params") if isinstance(manifest.get("params"), dict) else {}
    lower_params = _params_lower(params)
    preferred_target = str(manifest.get("preferred_target_code") or manifest.get("target_code") or "").strip().upper()
    scope_mode = str(manifest.get("scope_mode") or "")
    if scope_mode not in {"SERVER_TICKER_FILTER", "GLOBAL_FEED_CLIENT_SIDE_TICKER_FILTER"}:
        failures.append(f"UNKNOWN_SCOPE_MODE:{scope_mode}")

    # Every authenticated audit request must be explicitly bounded. Ticker
    # scoping is preferred but global-feed mode is valid if rows carry ticker
    # identity and can be filtered client-side.
    page_size = lower_params.get("length", lower_params.get("limit", lower_params.get("pagesize")))
    try:
        page_size_i = int(page_size)
    except Exception:
        page_size_i = 0
    if not (1 <= page_size_i <= 100):
        failures.append("REQUEST_NOT_BOUNDED_BY_SMALL_PAGE_SIZE")

    if scope_mode == "SERVER_TICKER_FILTER":
        scoped = str(lower_params.get("code") or lower_params.get("ticker") or lower_params.get("symbol") or "").strip().upper()
        if not preferred_target or scoped != preferred_target:
            failures.append("SERVER_TICKER_SCOPE_MISMATCH")

    if not raw_path.is_file():
        failures.append("RAW_RESPONSE_MISSING")
        raw_bytes = b""
        raw_payload: Any = None
    else:
        raw_bytes = raw_path.read_bytes()
        if _sha256(raw_bytes) != str(manifest.get("raw_sha256") or ""):
            failures.append("RAW_SHA_MISMATCH")
        try:
            raw_payload = json.loads(raw_bytes.decode("utf-8"))
        except Exception:
            raw_payload = None
            failures.append("RAW_RESPONSE_NOT_JSON")

    catalog_field_names: set[str] = set()
    if not catalog_path.is_file():
        failures.append("CATALOG_RAW_MISSING")
    else:
        catalog_bytes = catalog_path.read_bytes()
        if _sha256(catalog_bytes) != str(manifest.get("catalog_raw_sha256") or ""):
            failures.append("CATALOG_RAW_SHA_MISMATCH")
        if int(manifest.get("catalog_http_status") or 0) != 200:
            failures.append("CATALOG_HTTP_STATUS_NOT_200")
        catalog_field_names = {str(x).lower() for x in manifest.get("catalog_field_names", [])}
        if not ({"length", "limit", "pagesize"} & catalog_field_names):
            failures.append("CATALOG_HAS_NO_BOUNDED_PAGE_SIZE")
        if scope_mode == "GLOBAL_FEED_CLIENT_SIDE_TICKER_FILTER" and ({"code", "ticker", "symbol"} & catalog_field_names):
            warnings.append("GLOBAL_MODE_USED_DESPITE_AVAILABLE_TICKER_FILTER")

    response_headers = manifest.get("response_headers") if isinstance(manifest.get("response_headers"), dict) else {}
    content_type = str(response_headers.get("content-type") or "").lower()
    if content_type and "json" not in content_type:
        failures.append("CONTENT_TYPE_NOT_JSON")
    if not content_type:
        warnings.append("CONTENT_TYPE_HEADER_MISSING")

    core = _unwrap(raw_payload)
    candidates = sorted(_dict_lists(core), key=lambda item: max((_row_score(r) for r in item[1]), default=0), reverse=True)
    selected_path = None
    rows: list[dict[str, Any]] = []
    if candidates:
        selected_path, rows = candidates[0]
    if not rows:
        failures.append("NO_DIVIDEND_ROWS_FOUND")

    provider = None
    dataset = None
    search_objects = [raw_payload, core]
    for obj in search_objects:
        if isinstance(obj, dict):
            provider = provider or obj.get("provider")
            dataset = dataset or obj.get("dataset")
    if provider is not None and str(provider).lower() != "idx":
        failures.append(f"PROVIDER_NOT_IDX:{provider}")
    elif provider is None:
        warnings.append("PROVIDER_FIELD_ABSENT_HELPER_ONLY")
    if dataset is not None and str(dataset).lower() not in {"dividends", "dividend"}:
        failures.append(f"DATASET_NOT_DIVIDENDS:{dataset}")
    elif dataset is None:
        warnings.append("DATASET_FIELD_ABSENT_HELPER_ONLY")

    admissible: list[dict[str, Any]] = []
    row_keys = sorted({str(k) for row in rows[:100] for k in row})
    explicit_ticker_rows = 0
    for row in rows:
        ticker_raw = _first(row, TICKER_ALIASES)
        explicit_ticker = ticker_raw not in (None, "")
        if explicit_ticker:
            explicit_ticker_rows += 1
            ticker = str(ticker_raw).strip().upper()
        elif scope_mode == "SERVER_TICKER_FILTER":
            ticker = preferred_target
        else:
            ticker = ""

        if scope_mode == "SERVER_TICKER_FILTER" and ticker != preferred_target:
            continue
        if scope_mode == "GLOBAL_FEED_CLIENT_SIDE_TICKER_FILTER" and not ticker:
            continue

        cash = _positive_number(_first(row, CASH_ALIASES))
        cum = _date(_first(row, CUM_ALIASES))
        ex = _date(_first(row, EX_ALIASES))
        record = _date(_first(row, RECORD_ALIASES))
        payment = _date(_first(row, PAYMENT_ALIASES))
        if cash is None or not all((cum, ex, record, payment)):
            continue
        if not (cum < ex <= record <= payment):
            continue
        admissible.append({
            "ticker": ticker,
            "gross_dividend_per_share_idr": cash,
            "cum_date": cum,
            "ex_date": ex,
            "recording_date": record,
            "payment_date": payment,
        })

    if scope_mode == "GLOBAL_FEED_CLIENT_SIDE_TICKER_FILTER" and explicit_ticker_rows == 0:
        failures.append("GLOBAL_FEED_ROWS_HAVE_NO_TICKER_IDENTITY")
    if not admissible:
        failures.append("NO_ROW_WITH_REQUIRED_DIVIDEND_SEMANTICS")

    # Global-feed mode must expose enough paging semantics for production to
    # enumerate deterministically and filter relevant tickers client-side.
    pagination_metadata: dict[str, Any] = {}
    for obj in (raw_payload, core):
        if isinstance(obj, dict):
            for key in ("start", "length", "limit", "page", "total", "recordsTotal", "recordsFiltered", "count"):
                if key in obj and key not in pagination_metadata:
                    pagination_metadata[key] = obj[key]
    if scope_mode == "GLOBAL_FEED_CLIENT_SIDE_TICKER_FILTER" and not pagination_metadata:
        warnings.append("GLOBAL_FEED_RESPONSE_HAS_NO_EXPLICIT_PAGINATION_METADATA_ITERATE_UNTIL_SHORT_PAGE")

    cache_ttl_observation: dict[str, Any] = {}
    for key in ("cache-control", "age", "etag", "last-modified"):
        if key in response_headers:
            cache_ttl_observation[key] = response_headers[key]
    if "cache-control" not in cache_ttl_observation:
        warnings.append("CACHE_POLICY_NOT_EXPLICIT_IN_RESPONSE")

    report = {
        "schema_version": REVIEW_SCHEMA,
        "status": "PASS_ELIGIBLE_FOR_V1_1_STRUCTURED_HELPER" if not failures else "FAIL_NOT_ELIGIBLE_FOR_V1_1",
        "probe_dir": str(root),
        "endpoint_url": manifest.get("endpoint_url"),
        "scope_mode": scope_mode,
        "preferred_target_code": preferred_target,
        "params": params,
        "http_status": manifest.get("http_status"),
        "raw_sha256": _sha256(raw_bytes) if raw_bytes else None,
        "response_structural_fingerprint": _shape_fingerprint(raw_payload) if raw_payload is not None else None,
        "selected_rows_path": selected_path,
        "row_count": len(rows),
        "row_keys_union": row_keys,
        "explicit_ticker_rows": explicit_ticker_rows,
        "provider": provider,
        "dataset": dataset,
        "pagination_metadata": pagination_metadata,
        "admissible_semantic_rows": admissible[:20],
        "cache_observation": cache_ttl_observation,
        "failures": failures,
        "warnings": warnings,
        "v1_1_promotion_recommendation": (not failures),
        "authority_policy": "DIRECT_IDX_REMAINS_AUTHORITY_ZAPI_STRUCTURED_HELPER_ONLY_DISAGREEMENT_FAILS_CLOSED",
        "announcement_timestamp_required_from_zapi": False,
    }

    output = Path(args.output).expanduser().resolve() if args.output else root / "PROBE_REVIEW.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
