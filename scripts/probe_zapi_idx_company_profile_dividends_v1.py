from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.zpi.web.id"
ENDPOINT_URL = f"{BASE_URL}/v1/finance:idx/company-profile"
USER_AGENT = "idx-trade-forward-ca-zapi-company-profile-dividend-audit-v1"
MANIFEST_SCHEMA = "idx_trade_zapi_idx_company_profile_dividend_probe_v1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _fetch(url: str, *, api_key: str, timeout: int) -> tuple[int, dict[str, str], bytes]:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT, "x-api-key": api_key}
    request = Request(url, headers=headers, method="GET")
    selected_names = {
        "content-type", "cache-control", "age", "etag", "last-modified",
        "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
    }
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            selected = {k.lower(): v for k, v in response.headers.items() if k.lower() in selected_names}
            return int(response.status), selected, body
    except HTTPError as exc:
        body = exc.read()
        selected = {k.lower(): v for k, v in exc.headers.items() if k.lower() in selected_names}
        return int(exc.code), selected, body


def main() -> int:
    parser = argparse.ArgumentParser(description="One-request Zapi IDX company-profile dividend parity probe.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--code", default="BBCA")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    code = str(args.code).strip().upper()
    if not code or not code.isalnum() or len(code) > 12:
        raise SystemExit("ZAPI_COMPANY_PROFILE_CODE_INVALID")
    api_key = os.environ.get("ZAPI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("ZAPI_COMPANY_PROFILE_API_KEY_MISSING")

    root = Path(args.output_dir).expanduser().resolve()
    if root.exists():
        raise SystemExit(f"ZAPI_COMPANY_PROFILE_OUTPUT_EXISTS:{root}")
    root.mkdir(parents=True)

    params = {"code": code}
    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA,
        "status": "STARTED",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint_url": ENDPOINT_URL,
        "params": params,
        "target_code": code,
        "authenticated_request_count": 0,
        "retry_count": 0,
        "api_key_persisted": False,
        "expected_parity_event": {
            "ticker": "BBCA",
            "gross_dividend_per_share_idr": 20.0,
            "cum_date": "2026-06-15",
            "ex_date": "2026-06-17",
            "recording_date": "2026-06-18",
            "payment_date": "2026-06-26",
            "official_reference": "BCA interim dividend Q2 FY2026 announced 2026-06-05",
        },
    }

    query_url = ENDPOINT_URL + "?" + urlencode(params)
    try:
        status, headers, body = _fetch(query_url, api_key=api_key, timeout=args.timeout)
    except URLError as exc:
        manifest["status"] = "NETWORK_ERROR"
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

    (root / "company_profile_raw.json").write_bytes(body)
    (root / "PROBE_MANIFEST.json").write_bytes(_json_bytes(manifest))

    print(root / "PROBE_MANIFEST.json")
    print(f"params={json.dumps(params, sort_keys=True)}")
    print(f"http_status={status}")
    print(f"raw_sha256={manifest['raw_sha256']}")
    print("API key was used only from process memory and was not written to probe artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
