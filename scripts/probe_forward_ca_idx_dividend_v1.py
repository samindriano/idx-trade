from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

PROVIDER_REPOSITORY = "nichsedge/idx-bei"
PROVIDER_COMMIT = "75d6c0f74fa360d225794c70c383348977de6798"
UPSTREAM_BASE_URL = "https://www.idx.co.id/primary"
ENDPOINT = "/DigitalStatistic/GetApiDataPaginated"
SCHEMA = "idx_trade_forward_ca_direct_idx_dividend_probe_v1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verify_provider(checkout: Path) -> None:
    if not checkout.is_dir():
        raise SystemExit(f"provider checkout missing: {checkout}")
    proc = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    head = proc.stdout.strip()
    if head != PROVIDER_COMMIT:
        raise SystemExit(f"provider commit mismatch: {head} != {PROVIDER_COMMIT}")


def main() -> int:
    parser = argparse.ArgumentParser(description="One bounded direct-IDX LINK_DIVIDEND probe.")
    parser.add_argument("--provider-checkout", required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--page-size", type=int, default=100)
    args = parser.parse_args()

    if not 1990 <= args.year <= 2100:
        raise SystemExit("year out of range")
    if not 1 <= args.month <= 12:
        raise SystemExit("month out of range")
    if not 1 <= args.page_size <= 200:
        raise SystemExit("page size out of range")

    checkout = Path(args.provider_checkout).expanduser().resolve()
    _verify_provider(checkout)
    provider_src = checkout / "python" / "src"
    if not provider_src.is_dir():
        raise SystemExit(f"provider python/src missing: {provider_src}")
    sys.path.insert(0, str(provider_src))
    from idx.core.client import IDXClient  # type: ignore

    out = Path(args.output_dir).expanduser().resolve()
    if out.exists():
        raise SystemExit(f"output dir already exists: {out}")
    out.mkdir(parents=True)

    params: dict[str, Any] = {
        "urlName": "LINK_DIVIDEND",
        "periodYear": args.year,
        "periodMonth": args.month,
        "periodType": "monthly",
        "isPrint": "False",
        "cumulative": "false",
        "pageSize": args.page_size,
        "pageNumber": 1,
        "orderBy": "",
        "search": "",
    }

    client = IDXClient(base_url=UPSTREAM_BASE_URL, max_retries=0, delay_seconds=0.0)
    captured_at = datetime.now(timezone.utc).isoformat()
    response = client.get(ENDPOINT, params=params, impersonate="chrome", timeout=30)
    if response is None:
        raise SystemExit("DIRECT_IDX_DIVIDEND_NO_RESPONSE")

    raw = bytes(response.content)
    raw_path = out / "dividend_raw.json"
    raw_path.write_bytes(raw)
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA,
        "status": "PROBE_COMPLETE_AWAITING_OFFLINE_REVIEW",
        "provider_repository": PROVIDER_REPOSITORY,
        "provider_commit": PROVIDER_COMMIT,
        "provider_module": "idx.core.client.IDXClient",
        "transport": "curl_cffi",
        "impersonate": "chrome",
        "upstream_base_url": UPSTREAM_BASE_URL,
        "endpoint": ENDPOINT,
        "params": params,
        "captured_at_utc": captured_at,
        "http_status": int(response.status_code),
        "content_type": str(response.headers.get("content-type", "")),
        "raw_path": str(raw_path),
        "raw_sha256": _sha256(raw),
        "authenticated_request_count": 0,
        "direct_idx_request_count": 1,
        "retry_count": 0,
    }

    try:
        payload = response.json()
    except Exception:
        payload = None
        manifest["status"] = "PROBE_RESPONSE_NOT_JSON"

    if isinstance(payload, dict):
        manifest["top_level_keys"] = sorted(str(k) for k in payload)
        data = payload.get("data")
        manifest["data_count"] = len(data) if isinstance(data, list) else None
        manifest["records_total"] = payload.get("recordsTotal")
        if isinstance(data, list):
            manifest["row_keys_union"] = sorted(
                {str(k) for row in data[:100] if isinstance(row, dict) for k in row}
            )

    manifest_path = out / "PROBE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(manifest_path)
    print(f"http_status={response.status_code}")
    print(f"raw_sha256={manifest['raw_sha256']}")
    return 0 if response.status_code == 200 else 2


if __name__ == "__main__":
    raise SystemExit(main())
