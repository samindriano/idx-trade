from __future__ import annotations

import json
import os
from typing import Any

import requests

BASE = "https://api.zpi.web.id/v1"
KEY = os.environ.get("ZAPI_API_KEY", "")
DATE = "2026-08-20"
WATCH = ("CNTX", "CNTB", "GOTOM")


def unwrap(value: Any) -> Any:
    if isinstance(value, dict) and "project" in value and "timestamp" in value and isinstance(value.get("data"), dict):
        return value["data"]
    return value


def get(path: str, params: dict[str, Any]) -> Any:
    response = requests.get(f"{BASE}/{path}", params=params, headers={"x-api-key": KEY}, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"{path} {params} HTTP {response.status_code}: {response.text[:200]}")
    return unwrap(response.json())


def selected_rows(payload: Any, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("unexpected payload")
    return [{field: row.get(field) for field in fields} for row in payload["data"] if isinstance(row, dict)]


def main() -> int:
    if not KEY:
        raise SystemExit("ZAPI_API_KEY missing")
    out: dict[str, Any] = {
        "schema_version": "stockbit_identity_delta_followup_v1",
        "date": DATE,
        "watch": {},
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
    print(json.dumps(out, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
