from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from idx_trade.forward_ca_attestation_v1 import (
    CALENDAR_CAPTURE_SCOPE,
    PROVIDER_COMMIT,
    PROVIDER_REPOSITORY,
    UPSTREAM_BASE_URL,
    _structural_fingerprint,
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verify_provider_checkout(checkout: Path) -> None:
    if not checkout.is_dir():
        raise SystemExit(f"provider checkout missing: {checkout}")
    head = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != PROVIDER_COMMIT:
        raise SystemExit(f"provider commit mismatch: {head} != {PROVIDER_COMMIT}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-request direct-IDX Home/GetCalendar schema probe."
    )
    parser.add_argument("--provider-checkout", required=True)
    parser.add_argument("--date", required=True, help="YYYYMMDD anchor date")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    if len(args.date) != 8 or not args.date.isdigit():
        raise SystemExit("--date must be YYYYMMDD")

    checkout = Path(args.provider_checkout).expanduser().resolve()
    _verify_provider_checkout(checkout)
    provider_src = checkout / "python" / "src"
    if not provider_src.is_dir():
        raise SystemExit(f"provider python/src missing: {provider_src}")
    sys.path.insert(0, str(provider_src))
    from idx.core.client import IDXClient  # type: ignore

    out = Path(args.output_dir).expanduser().resolve()
    if out.exists():
        raise SystemExit(f"output dir already exists: {out}")
    out.mkdir(parents=True)

    endpoint = "/Home/GetCalendar"
    params = {
        "range": "m",
        "date": args.date,
        "start": 0,
        "length": 9999,
        "code": "",
        "language": "id-id",
        "search": "",
    }
    client = IDXClient(base_url=UPSTREAM_BASE_URL, max_retries=0, delay_seconds=0)
    captured_at = datetime.now(timezone.utc).isoformat()
    response = client.get(endpoint, params=params, impersonate="chrome", timeout=30)
    if response is None:
        raise SystemExit("calendar probe returned no response")

    body = bytes(response.content)
    raw_path = out / "calendar_raw.json"
    raw_path.write_bytes(body)
    raw_sha = _sha256_bytes(body)

    if response.status_code != 200:
        raise SystemExit(f"calendar probe HTTP {response.status_code}; raw saved at {raw_path}")
    try:
        payload = response.json()
    except Exception as exc:
        raise SystemExit(f"calendar probe invalid JSON; raw saved at {raw_path}") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("Results"), list):
        raise SystemExit("calendar probe schema invalid: expected object with Results list")
    if not payload["Results"]:
        raise SystemExit("calendar probe unexpectedly empty; do not freeze schema")

    fingerprint = _structural_fingerprint(payload)
    result_keys = sorted(
        {
            str(key)
            for row in payload["Results"][:25]
            if isinstance(row, dict)
            for key in row.keys()
        }
    )
    manifest = {
        "schema_version": "idx_trade_forward_ca_calendar_probe_v1",
        "status": "PROBE_COMPLETE_NOT_YET_FROZEN",
        "provider_repository": PROVIDER_REPOSITORY,
        "provider_commit": PROVIDER_COMMIT,
        "upstream_base_url": UPSTREAM_BASE_URL,
        "calendar_capture_scope": CALENDAR_CAPTURE_SCOPE,
        "captured_at_utc": captured_at,
        "endpoint": endpoint,
        "params": params,
        "http_status": int(response.status_code),
        "content_type": str(response.headers.get("content-type", "")),
        "raw_path": str(raw_path),
        "raw_sha256": raw_sha,
        "top_level_keys": sorted(str(x) for x in payload.keys()),
        "results_count": len(payload["Results"]),
        "sample_result_keys_union": result_keys,
        "calendar_schema_fingerprint": fingerprint,
        "paper_execution_admission_changed": False,
    }
    manifest_path = out / "PROBE_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(manifest_path)
    print(f"calendar_schema_fingerprint={fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
