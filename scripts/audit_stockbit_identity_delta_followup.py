from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import requests

BASE = "https://api.zpi.web.id/v1"
KEY = os.environ.get("ZAPI_API_KEY", "")
DATE = "2026-08-20"
WATCH = ("CNTX", "CNTB", "GOTOM")
TIMEOUT = 30


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def unwrap(value: Any) -> Any:
    if isinstance(value, dict) and "project" in value and "timestamp" in value and isinstance(value.get("data"), dict):
        return value["data"]
    return value


def compact_shape(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"type": type(payload).__name__}
    result: dict[str, Any] = {"keys": sorted(str(k) for k in payload)}
    for key in ("dataset", "provider", "recordsTotal", "recordsFiltered", "total", "count", "length", "start", "page", "year", "month", "hasMore", "nextPage"):
        if key in payload:
            result[key] = payload.get(key)
    containers: list[dict[str, Any]] = []
    for key in ("data", "items", "Results", "results"):
        rows = payload.get(key)
        if isinstance(rows, list):
            containers.append({
                "container": key,
                "count": len(rows),
                "fields": sorted({str(f) for row in rows[:30] if isinstance(row, dict) for f in row}),
                "sample_first_3": rows[:3],
            })
    result["containers"] = containers
    return result


def matching_dicts(value: Any, needles: tuple[str, ...]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            text_values = {str(item).strip().upper() for item in node.values() if isinstance(item, (str, int, float))}
            if any(needle in text_values for needle in needles):
                out.append(node)
            for item in node.values():
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(value)
    dedup: dict[str, dict[str, Any]] = {}
    for row in out:
        raw = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        dedup[raw] = row
    return [dedup[key] for key in sorted(dedup)]


def probe(path: str, params: dict[str, Any]) -> dict[str, Any]:
    response = requests.get(f"{BASE}/{path}", params=params, headers={"x-api-key": KEY}, timeout=TIMEOUT)
    result: dict[str, Any] = {
        "path": path,
        "params": params,
        "http_status": response.status_code,
        "raw_sha256": sha256_bytes(bytes(response.content)),
    }
    if response.status_code != 200:
        result["body_prefix"] = response.text[:160]
        return result
    payload = unwrap(response.json())
    result["shape"] = compact_shape(payload)
    result["watch_matches"] = matching_dicts(payload, WATCH)
    return result


def main() -> int:
    if not KEY:
        raise SystemExit("ZAPI_API_KEY missing")

    probes = {
        "delistings_default_2026": probe("finance:idx/delistings", {"year": 2026}),
        "delistings_2026_07": probe("finance:idx/delistings", {"year": 2026, "month": 7, "page": 1}),
        "delistings_2026_08": probe("finance:idx/delistings", {"year": 2026, "month": 8, "page": 1}),
        "new_listings_default_2026": probe("finance:idx/new-listings", {"year": 2026}),
        "new_listings_2026_07": probe("finance:idx/new-listings", {"year": 2026, "month": 7, "page": 1}),
        "new_listings_2026_08": probe("finance:idx/new-listings", {"year": 2026, "month": 8, "page": 1}),
        "ipo_2026": probe("finance:idx/ipo", {"year": 2026, "length": 200, "start": 0}),
    }
    for name, item in probes.items():
        print("EVENT_SCHEMA " + name + " " + json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False))

    print("AUDIT_FLAGS " + json.dumps({"outcome_accessed": False, "model_accessed": False, "roster_mutated": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
