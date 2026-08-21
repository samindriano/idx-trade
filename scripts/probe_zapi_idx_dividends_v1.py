from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
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


def _select_params(fields: list[dict[str, Any]], code: str) -> dict[str, Any]:
    names = {str(row.get("name") or ""): row for row in fields}
    params: dict[str, Any] = {}
    if "code" in names:
        params["code"] = code
    elif "ticker" in names:
        params["ticker"] = code
    elif "symbol" in names:
        params["symbol"] = code
    else:
        raise RuntimeError("ZAPI_DIVIDENDS_CATALOG_NO_TICKER_FILTER")

    if "start" in names:
        params["start"] = 0
    if "length" in names:
        params["length"] = 20
    elif "limit" in names:
        params["limit"] = 20
    return params


def _parse_json(data: bytes, code: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(code) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded audit probe for Zapi IDX /dividends.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--code", default="BBCA")
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
        "target_code": code,
        "authenticated_request_count": 0,
        "retry_count": 0,
        "api_key_persisted": False,
    }

    # Public no-auth discovery first. If the endpoint contract does not expose a
    # ticker filter, stop before spending an authenticated request.
    try:
        cat_status, cat_headers, cat_body = _fetch(CATALOG_SCHEMA_URL, timeout=args.timeout)
    except URLError as exc:
        manifest["status"] = "CATALOG_NETWORK_ERROR_NO_AUTH_REQUEST_MADE"
        manifest["error"] = type(exc).__name__
        (root / "PROBE_MANIFEST.json").write_bytes(_json_bytes(manifest))
        raise SystemExit(2)

    (root / "catalog_schema_raw.json").write_bytes(cat_body)
    manifest["catalog_http_status"] = cat_status
    manifest["catalog_headers"] = cat_headers
    manifest["catalog_raw_sha256"] = _sha256(cat_body)

    try:
        catalog_payload = _parse_json(cat_body, "ZAPI_DIVIDENDS_CATALOG_JSON_INVALID")
        fields = _catalog_fields(catalog_payload)
        params = _select_params(fields, code)
    except Exception as exc:
        manifest["status"] = "CATALOG_SCHEMA_UNUSABLE_NO_AUTH_REQUEST_MADE"
        manifest["catalog_field_names"] = [str(x.get("name") or "") for x in _catalog_fields(_parse_json(cat_body, "ZAPI_DIVIDENDS_CATALOG_JSON_INVALID"))]
        manifest["error"] = str(exc)
        (root / "PROBE_MANIFEST.json").write_bytes(_json_bytes(manifest))
        print(root / "PROBE_MANIFEST.json")
        return 2

    manifest["catalog_field_names"] = [str(x.get("name") or "") for x in fields]
    manifest["params"] = params
    query_url = ENDPOINT_URL + "?" + urlencode(params)

    try:
        status, headers, body = _fetch(query_url, api_key=api_key, timeout=args.timeout)
    except URLError as exc:
        manifest["status"] = "AUTHENTICATED_NETWORK_ERROR"
        manifest["authenticated_request_count"] = 1
        manifest["error"] = type(exc).__name__
        (root / "PROBE_MANIFEST.json").write_bytes(_json_bytes(manifest))
        raise SystemExit(2)

    manifest["authenticated_request_count"] = 1
    manifest["http_status"] = status
    manifest["response_headers"] = headers
    manifest["raw_sha256"] = _sha256(body)
    manifest["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["status"] = "PROBE_COMPLETE_AWAITING_OFFLINE_REVIEW"
    (root / "dividends_raw.json").write_bytes(body)
    (root / "PROBE_MANIFEST.json").write_bytes(_json_bytes(manifest))

    print(root / "PROBE_MANIFEST.json")
    print(f"http_status={status}")
    print(f"raw_sha256={manifest['raw_sha256']}")
    print("API key was used only from process memory and was not written to the probe artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
