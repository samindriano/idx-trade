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
ANNOUNCEMENT_ENDPOINT = "/NewsAnnouncement/GetAllAnnouncement"
SCHEMA = "idx_trade_forward_ca_direct_idx_dividend_current_pair_probe_v1"


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
    parser = argparse.ArgumentParser(description="Paired current-forward direct IDX dividend + announcement probe.")
    parser.add_argument("--provider-checkout", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--code", default="BBCA")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month", type=int, default=8)
    parser.add_argument("--announcement-from", default="2026-08-18")
    parser.add_argument("--announcement-through", default="2026-08-21")
    args = parser.parse_args()

    code = str(args.code).strip().upper()
    if not code or not code.isalnum() or len(code) > 12:
        raise SystemExit("invalid code")
    if not 1990 <= args.year <= 2100 or not 1 <= args.month <= 12:
        raise SystemExit("invalid year/month")

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

    client = IDXClient(base_url=UPSTREAM_BASE_URL, max_retries=0, delay_seconds=0.0)
    artifacts: list[dict[str, Any]] = []

    def capture(name: str, endpoint: str, params: dict[str, Any]) -> Any:
        captured_at = datetime.now(timezone.utc).isoformat()
        response = client.get(endpoint, params=params, impersonate="chrome", timeout=30)
        if response is None:
            raise RuntimeError(f"no response: {endpoint}")
        raw = bytes(response.content)
        path = out / f"{name}.json"
        path.write_bytes(raw)
        row = {
            "name": name,
            "endpoint": endpoint,
            "params": params,
            "captured_at_utc": captured_at,
            "http_status": int(response.status_code),
            "content_type": str(response.headers.get("content-type", "")),
            "path": str(path.name),
            "sha256": _sha256(raw),
        }
        artifacts.append(row)
        if response.status_code != 200:
            raise RuntimeError(f"http {response.status_code}: {endpoint}")
        try:
            return response.json()
        except Exception as exc:
            raise RuntimeError(f"invalid json: {endpoint}") from exc

    dividend_params = {
        "urlName": "LINK_DIVIDEND",
        "periodYear": args.year,
        "periodMonth": args.month,
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
        "keywords": code,
        "pageNumber": 1,
        "pageSize": 100,
        "lang": "id",
        "dateFrom": args.announcement_from,
        "dateTo": args.announcement_through,
    }
    announcements = capture("announcements", ANNOUNCEMENT_ENDPOINT, announcement_params)
    if not isinstance(announcements, dict) or not isinstance(announcements.get("Items"), list):
        raise RuntimeError("direct IDX announcement schema invalid")
    page_count = int(announcements.get("PageCount") or 1)
    if page_count != 1:
        raise RuntimeError(f"announcement pagination unexpectedly exceeds one page: {page_count}")

    manifest = {
        "schema_version": SCHEMA,
        "status": "COMPLETE_AWAITING_OFFLINE_REVIEW",
        "provider_repository": PROVIDER_REPOSITORY,
        "provider_commit": PROVIDER_COMMIT,
        "provider_module": "idx.core.client.IDXClient",
        "transport": "curl_cffi",
        "impersonate": "chrome",
        "upstream_base_url": UPSTREAM_BASE_URL,
        "target_code": code,
        "target_year": args.year,
        "target_month": args.month,
        "announcement_from": args.announcement_from,
        "announcement_through": args.announcement_through,
        "direct_idx_request_count": 2,
        "retry_count": 0,
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
