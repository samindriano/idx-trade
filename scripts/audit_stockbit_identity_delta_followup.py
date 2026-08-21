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


def get(path: str, params: dict[str, Any]) -> Any:
    response = requests.get(f"{BASE}/{path}", params=params, headers={"x-api-key": KEY}, timeout=TIMEOUT)
    if response.status_code != 200:
        raise RuntimeError(f"{path} {params} HTTP {response.status_code}: {response.text[:200]}")
    return unwrap(response.json())


def selected_rows(payload: Any, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("unexpected payload")
    return [{field: row.get(field) for field in fields} for row in payload["data"] if isinstance(row, dict)]


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


def row_container_summary(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"payload_type": type(payload).__name__}

    summary: dict[str, Any] = {
        "payload_type": "dict",
        "keys": sorted(str(key) for key in payload),
    }
    for key in (
        "dataset",
        "provider",
        "recordsTotal",
        "recordsFiltered",
        "total",
        "count",
        "length",
        "start",
        "page",
    ):
        if key in payload:
            summary[key] = payload.get(key)

    candidates: list[tuple[str, Any]] = []
    for key in ("data", "items", "Results", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            candidates.append((key, value))
    nested_data = payload.get("data")
    if isinstance(nested_data, dict):
        for key in ("items", "Results", "results", "data"):
            value = nested_data.get(key)
            if isinstance(value, list):
                candidates.append((f"data.{key}", value))

    summary["row_containers"] = []
    for name, rows in candidates:
        field_names = sorted(
            {
                str(field)
                for row in rows[:20]
                if isinstance(row, dict)
                for field in row.keys()
            }
        )
        summary["row_containers"].append(
            {
                "name": name,
                "count": len(rows),
                "field_names_first_20": field_names,
                "sample_first_3": rows[:3],
            }
        )
    return summary


def probe(path: str, param_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for params in param_candidates:
        response = requests.get(
            f"{BASE}/{path}",
            params=params,
            headers={"x-api-key": KEY},
            timeout=TIMEOUT,
        )
        raw = bytes(response.content)
        attempt: dict[str, Any] = {
            "params": params,
            "http_status": response.status_code,
            "raw_sha256": sha256_bytes(raw),
        }
        if response.status_code == 200:
            try:
                outer = response.json()
            except Exception:
                attempt["json"] = False
                attempt["body_prefix"] = response.text[:240]
                attempts.append(attempt)
                break
            payload = unwrap(outer)
            attempt["json"] = True
            attempt["shape"] = row_container_summary(payload)
            attempt["watch_matches"] = matching_dicts(payload, WATCH)
            attempts.append(attempt)
            break
        attempt["body_prefix"] = response.text[:240]
        attempts.append(attempt)
        if response.status_code in {401, 403, 429}:
            break
    return {"path": path, "attempts": attempts}


def main() -> int:
    if not KEY:
        raise SystemExit("ZAPI_API_KEY missing")
    out: dict[str, Any] = {
        "schema_version": "stockbit_identity_delta_followup_v2_listing_event_probe",
        "date": DATE,
        "watch": {},
        "listing_event_probes": {},
        "outcome_accessed": False,
        "model_accessed": False,
        "roster_mutated": False,
    }
    for code in WATCH:
        sec = get("finance:idx/securities", {"length": 20, "start": 0, "code": code})
        comp = get("finance:idx/companies", {"length": 20, "start": 0, "code": code})
        stock = get("finance:idx/stock-summary", {"length": 20, "start": 0, "date": DATE, "code": code})
        out["watch"][code] = {
            "securities_recordsTotal": sec.get("recordsTotal") if isinstance(sec, dict) else None,
            "securities_rows": selected_rows(sec, ("Code", "Name", "Shares", "ListingDate", "ListingBoard")),
            "companies_recordsTotal": comp.get("recordsTotal") if isinstance(comp, dict) else None,
            "companies_rows": selected_rows(comp, ("KodeEmiten", "NamaEmiten", "EfekEmiten_Saham", "TanggalPencatatan", "PapanPencatatan", "Status")),
            "stock_summary_recordsTotal": stock.get("recordsTotal") if isinstance(stock, dict) else None,
            "stock_summary_rows": selected_rows(
                stock,
                (
                    "StockCode",
                    "StockName",
                    "Date",
                    "Close",
                    "Value",
                    "Volume",
                    "Frequency",
                    "ListedShares",
                    "TradebleShares",
                    "DelistingDate",
                    "Remarks",
                ),
            ),
        }

    panel = get("finance:idx/stock-summary", {"length": 1000, "start": 0, "date": DATE})
    rows = panel.get("data", []) if isinstance(panel, dict) else []
    nonblank_delisting = []
    for row in rows:
        if isinstance(row, dict) and str(row.get("DelistingDate", "")).strip():
            nonblank_delisting.append(
                {
                    key: row.get(key)
                    for key in (
                        "StockCode",
                        "StockName",
                        "Date",
                        "DelistingDate",
                        "Close",
                        "Value",
                        "Volume",
                        "Frequency",
                        "ListedShares",
                    )
                }
            )
    out["stock_summary_nonblank_delisting"] = sorted(nonblank_delisting, key=lambda row: str(row.get("StockCode")))
    out["stock_summary_nonblank_delisting_count"] = len(nonblank_delisting)

    # Endpoint contracts were preregistered before this live structural probe.
    # Parameter variants are deliberately bounded so an undocumented envelope can
    # be observed without turning a 400 into a false statement that the dataset is absent.
    out["listing_event_probes"]["delistings"] = probe(
        "finance:idx/delistings",
        [
            {"year": 2026, "length": 200, "start": 0},
            {"length": 200, "start": 0},
            {},
        ],
    )
    out["listing_event_probes"]["new_listings"] = probe(
        "finance:idx/new-listings",
        [
            {"year": 2026, "length": 200, "start": 0},
            {"length": 200, "start": 0},
            {},
        ],
    )
    out["listing_event_probes"]["ipo"] = probe(
        "finance:idx/ipo",
        [
            {"year": 2026, "length": 200, "start": 0},
            {"length": 200, "start": 0},
        ],
    )

    print(json.dumps(out, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
