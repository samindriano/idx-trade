from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.zpi.web.id"
CATALOG_SCHEMA_URL = f"{BASE_URL}/api/public/scrapers/idx/endpoints/dividends/schema"
ENDPOINT_URL = f"{BASE_URL}/v1/finance:idx/dividends"
USER_AGENT = "idx-trade-forward-ca-zapi-dividends-audit-v1"
MANIFEST_SCHEMA = "idx_trade_zapi_idx_dividends_probe_v1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _fetch(url: str, *, api_key: str | None = None, timeout: int = 30) -> tuple[int, dict[str, str], bytes]:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if api_key is not None:
        headers["x-api-key"] = api_key
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            selected = {
                k.lower(): v
                for k, v in response.headers.items()
                if k.lower() in {
                    "content-type",
                    "cache-control",
                    "age",
                    "etag",
                    "last-modified",
                    "x-ratelimit-limit",
                    "x-ratelimit-remaining",
                    "x-ratelimit-reset",
                }
            }
            return int(response.status), selected, body
    except HTTPError as exc:
        body = exc.read()
        selected = {
            k.lower(): v
            for k, v in exc.headers.items()
            if k.lower() in {
                "content-type",
                "cache-control",
                "age",
                "etag",
                "last-modified",
                "x-ratelimit-limit",
                "x-ratelimit-remaining",
                "x-ratelimit-reset",
            }
        }
        return int(exc.code), selected, body


def _unwrap_catalog_schema(payload: Any) -> Any:
    if isinstance(payload, dict) and isinstance(payload.get("content"), dict):
        return payload["content"]
    return payload


def _catalog_fields(payload: Any) -> list[dict[str, Any]]:
    core = _unwrap_catalog_schema(payload)
    if not isinstance(core, dict):
        return []
    fields = core.get("fields")
    return [x for x in fields if isinstance(x, dict)] if isinstance(fields, list) else []


def _field_map(fields: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in fields:
        name = str(row.get("name") or "").strip()
        if name:
            out[name.lower()] = name
    return out


def _select_params(fields: list[dict[str, Any]], code: str) -> tuple[dict[str, Any], str]:
    """Build a bounded request from the live public catalog.

    Dedicated corporate-action feeds are allowed to be global feeds. A ticker
    filter is preferred but is not required. In global-feed mode the response
    must be bounded by pagination and rows must carry ticker identity; the
    offline reviewer enforces that before V1.1 can pass.
    """
    names = _field_map(fields)
    params: dict[str, Any] = {}
    scope_mode = "GLOBAL_FEED_CLIENT_SIDE_TICKER_FILTER"

    for alias in ("code", "ticker", "symbol"):
        if alias in names:
            params[names[alias]] = code
            scope_mode = "SERVER_TICKER_FILTER"
            break

    # Hard bound: require a pagination control exposed by the live catalog.
    if "length" in names:
        params[names["length"]] = 20
    elif "limit" in names:
        params[names["limit"]] = 20
    elif "pagesize" in names:
        params[names["pagesize"]] = 20
    else:
        raise RuntimeError("ZAPI_DIVIDENDS_CATALOG_NO_BOUNDED_PAGE_SIZE")

    if "start" in names:
        params[names["start"]] = 0
    elif "offset" in names:
        params[names["offset"]] = 0
    elif "page" in names:
        params[names["page"]] = 1
    elif "pagenumber" in names:
        params[names["pagenumber"]] = 1

    # If the endpoint exposes a date range, keep the audit narrow and current.
    # This is not a semantic requirement; it is only a request-volume bound.
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=730)
    if "datefrom" in names:
        params[names["datefrom"]] = start_date.strftime("%Y%m%d")
    elif "from" in names:
        params[names["from"]] = start_date.isoformat()

    if "dateto" in names:
        params[names["dateto"]] = today.strftime("%Y%m%d")
    elif "to" in names:
        params[names["to"]] = today.isoformat()

    return params, scope_mode


def _parse_json(data: bytes, code: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(code) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded audit probe for Zapi IDX /dividends.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--code", default="BBCA", help="Preferred ticker when the endpoint exposes a server-side ticker filter")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    code = str(args.code).strip().upper()
    if not code or not code.isalnum() or len(code) > 12:
        raise SystemExit("ZAPI_DIVIDENDS_PROBE_CODE_INVALID")
    api_key = os.environ.get("ZAPI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("ZAPI_DIVIDENDS_PROBE_API_KEY_MISSING")

    root = Path(args.output_dir).expanduser().resolve()
    if root.exists():
        raise SystemExit(f"ZAPI_DIVIDENDS_PROBE_OUTPUT_EXISTS:{root}")
    root.mkdir(parents=True)

    started = datetime.now(timezone.utc).isoformat()
    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA,
        "status": "STARTED",
        "started_at_utc": started,
        "catalog_schema_url": CATALOG_SCHEMA_URL,
        "endpoint_url": ENDPOINT_URL,
        "preferred_target_code": code,
        "authenticated_request_count": 0,
        "retry_count": 0,
        "api_key_persisted": False,
    }

    # Public no-auth discovery first. Stop before spending an authenticated
    # request if the live endpoint cannot be bounded by page size.
    try:
        cat_status, cat_headers, cat_body = _fetch(CATALOG_SCHEMA_URL, timeout=args.timeout)
    except URLError as exc:
        manifest["status"] = "CATALOG_NETWORK_ERROR_NO_AUTH_REQUEST_MADE"
        manifest["error"] = type(exc).__name__
        (root / "PROBE_MANIFEST.json").write_bytes(_json_bytes(manifest))
        return 2

    (root / "catalog_schema_raw.json").write_bytes(cat_body)
    manifest["catalog_http_status"] = cat_status
    manifest["catalog_headers"] = cat_headers
    manifest["catalog_raw_sha256"] = _sha256(cat_body)

    try:
        catalog_payload = _parse_json(cat_body, "ZAPI_DIVIDENDS_CATALOG_JSON_INVALID")
        fields = _catalog_fields(catalog_payload)
        manifest["catalog_field_names"] = [str(x.get("name") or "") for x in fields]
        params, scope_mode = _select_params(fields, code)
    except Exception as exc:
        manifest["status"] = "CATALOG_SCHEMA_UNUSABLE_NO_AUTH_REQUEST_MADE"
        manifest["error"] = str(exc)
        (root / "PROBE_MANIFEST.json").write_bytes(_json_bytes(manifest))
        print(root / "PROBE_MANIFEST.json")
        return 2

    manifest["params"] = params
    manifest["scope_mode"] = scope_mode
    query_url = ENDPOINT_URL + ("?" + urlencode(params) if params else "")

    try:
        status, headers, body = _fetch(query_url, api_key=api_key, timeout=args.timeout)
    except URLError as exc:
        manifest["status"] = "AUTHENTICATED_NETWORK_ERROR"
        manifest["authenticated_request_count"] = 1
        manifest["error"] = type(exc).__name__
        (root / "PROBE_MANIFEST.json").write_bytes(_json_bytes(manifest))
        return 2

    manifest["authenticated_request_count"] = 1
    manifest["http_status"] = status
    manifest["response_headers"] = headers
    manifest["raw_sha256"] = _sha256(body)
    manifest["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["status"] = "PROBE_COMPLETE_AWAITING_OFFLINE_REVIEW"
    (root / "dividends_raw.json").write_bytes(body)
    (root / "PROBE_MANIFEST.json").write_bytes(_json_bytes(manifest))

    print(root / "PROBE_MANIFEST.json")
    print(f"scope_mode={scope_mode}")
    print(f"http_status={status}")
    print(f"raw_sha256={manifest['raw_sha256']}")
    print("API key was used only from process memory and was not written to the probe artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
