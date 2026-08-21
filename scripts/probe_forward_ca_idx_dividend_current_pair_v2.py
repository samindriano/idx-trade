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
DIVIDEND_ENDPOINT = "/DigitalStatistic/GetApiDataPaginated"
ANNOUNCEMENT_ENDPOINT = "/ListedCompany/GetAnnouncement"
SCHEMA = "idx_trade_forward_ca_direct_idx_dividend_current_pair_probe_v2"

DEFAULT_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "referer": "https://www.idx.co.id/",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verify_provider(checkout: Path) -> Path:
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
    provider_src = checkout / "python" / "src"
    if not provider_src.is_dir():
        raise SystemExit(f"provider python/src missing: {provider_src}")
    return provider_src


def main() -> int:
    parser = argparse.ArgumentParser(description="Current-forward direct IDX dividend + issuer-announcement audit V2.")
    parser.add_argument("--provider-checkout", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--code", default="BBCA")
    args = parser.parse_args()

    code = str(args.code).strip().upper()
    if not code or not code.isalnum() or len(code) > 12:
        raise SystemExit("invalid code")

    checkout = Path(args.provider_checkout).expanduser().resolve()
    provider_src = _verify_provider(checkout)
    sys.path.insert(0, str(provider_src))
    from curl_cffi import requests  # type: ignore

    out = Path(args.output_dir).expanduser().resolve()
    if out.exists():
        raise SystemExit(f"output dir already exists: {out}")
    out.mkdir(parents=True)

    artifacts: list[dict[str, Any]] = []

    def capture(name: str, endpoint: str, params: dict[str, Any]) -> Any:
        captured_at = datetime.now(timezone.utc).isoformat()
        url = UPSTREAM_BASE_URL + endpoint
        response = requests.get(
            url,
            params=params,
            headers=DEFAULT_HEADERS,
            impersonate="chrome",
            timeout=30,
        )
        raw = bytes(response.content)
        path = out / f"{name}.json"
        path.write_bytes(raw)
        artifacts.append(
            {
                "name": name,
                "endpoint": endpoint,
                "params": params,
                "captured_at_utc": captured_at,
                "http_status": int(response.status_code),
                "content_type": str(response.headers.get("content-type", "")),
                "path": path.name,
                "sha256": _sha256(raw),
            }
        )
        if response.status_code != 200:
            raise RuntimeError(f"http {response.status_code}: {endpoint}")
        try:
            return response.json()
        except Exception as exc:
            raise RuntimeError(f"invalid json: {endpoint}") from exc

    dividend_params = {
        "urlName": "LINK_DIVIDEND",
        "periodYear": 2026,
        "periodMonth": 8,
        "periodType": "monthly",
        "isPrint": "False",
        "cumulative": "false",
        "pageSize": 100,
        "pageNumber": 1,
        "orderBy": "",
        "search": code,
    }
    dividend = capture("dividend", DIVIDEND_ENDPOINT, dividend_params)
    if not isinstance(dividend, dict) or not isinstance(dividend.get("data"), list):
        raise RuntimeError("direct IDX dividend schema invalid")
    records_total = dividend.get("recordsTotal")
    if isinstance(records_total, int) and records_total > 100:
        raise RuntimeError("direct IDX dividend pagination incomplete")

    announcement_params = {
        "kodeEmiten": code,
        "emitenType": "*",
        "indexFrom": 0,
        "pageSize": 100,
        "dateFrom": "20260818",
        "dateTo": "20260821",
        "lang": "id",
        "keyword": "",
    }
    announcements = capture("announcements", ANNOUNCEMENT_ENDPOINT, announcement_params)
    if not isinstance(announcements, dict) or not isinstance(announcements.get("Replies"), list):
        raise RuntimeError("direct IDX ListedCompany announcement schema invalid")
    result_count = announcements.get("ResultCount")
    if isinstance(result_count, int) and result_count > 100:
        raise RuntimeError("direct IDX announcement pagination incomplete")

    manifest = {
        "schema_version": SCHEMA,
        "status": "COMPLETE_AWAITING_OFFLINE_REVIEW",
        "provider_repository": PROVIDER_REPOSITORY,
        "provider_commit": PROVIDER_COMMIT,
        "provider_transport_dependency": "curl_cffi from pinned idx-bei environment",
        "upstream_base_url": UPSTREAM_BASE_URL,
        "target_code": code,
        "direct_idx_request_count": 2,
        "retry_count": 0,
        "request_policy": "DIRECT_ONE_SHOT_NO_RETRY_HELPER",
        "raw_artifacts": artifacts,
    }
    manifest_path = out / "PROBE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(manifest_path)
    for row in artifacts:
        print(f"{row['name']}: http={row['http_status']} sha256={row['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
