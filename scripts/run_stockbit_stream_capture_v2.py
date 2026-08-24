"""Cloud runner for Stockbit Stream routine capture V2."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from idx_trade.stockbit_stream_archive import StreamArchiveError, ZapiClient
from idx_trade.stockbit_stream_capture_v2 import archive_from_env, build_runtime_universe, capture_stream_v2


class _EnvelopeAwareResponse:
    """Preserve exact response bytes while exposing the nested finance payload to the parser."""

    def __init__(self, response: requests.Response):
        self._response = response
        self.status_code = response.status_code
        self.content = response.content
        self.headers = response.headers

    def json(self):
        payload = self._response.json()
        if (
            isinstance(payload, dict)
            and isinstance(payload.get("data"), dict)
            and "project" in payload
            and "timestamp" in payload
        ):
            return payload["data"]
        return payload


class _EnvelopeAwareSession:
    def __init__(self):
        self._session = requests.Session()

    def get(self, *args, **kwargs):
        return _EnvelopeAwareResponse(self._session.get(*args, **kwargs))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity-csv", type=Path, required=True)
    parser.add_argument("--slot", required=True)
    parser.add_argument("--top-n", type=int, default=200)
    parser.add_argument("--capture-date")
    args = parser.parse_args()

    capture_date = args.capture_date or datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()
    api_key = os.environ.get("ZAPI_API_KEY", "")
    if not api_key:
        print(json.dumps({"status": "BLOCKED", "detail": "ZAPI_API_KEY missing"}))
        return 2
    try:
        universe = build_runtime_universe(
            api_key=api_key,
            identity_csv=args.identity_csv,
            capture_date=capture_date,
            top_n=args.top_n,
            session=_EnvelopeAwareSession(),
        )
        result = capture_stream_v2(
            client=ZapiClient(api_key),
            archive=archive_from_env(),
            universe=universe,
            slot=args.slot,
            hmac_salt=os.environ.get("STOCKBIT_STREAM_HMAC_SALT", ""),
        )
        summary = {
            "status": result["status"],
            "run_id": result["run_id"],
            "slot": args.slot,
            "top_n": args.top_n,
            "source_session": universe.source_session,
            "universe_sha256": universe.universe_sha256,
            "planned_calls": result.get("planned_calls"),
            "completed_calls": result.get("completed_calls"),
            "successful_responses": result.get("successful_responses"),
            "normalized_post_rows": result.get("normalized_post_rows"),
            "response_classification_counts": result.get("response_classification_counts"),
            "manifest_sha256": result.get("manifest_sha256"),
            "model_accessed": False,
            "outcome_accessed": False,
            "counter_mutated": False,
        }
        print(json.dumps(summary, sort_keys=True))
        return 0 if result["status"] == "DATA_READY" else 2
    except (StreamArchiveError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED_OR_FAILED", "detail": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
