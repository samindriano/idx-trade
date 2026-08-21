from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

import requests

API_BASE = "https://api.zpi.web.id/v1"
MCP = "https://mcp.zpi.web.id/mcp"
KEY = os.environ.get("ZAPI_API_KEY", "")
TIMEOUT = 30


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def outer_unwrap(payload: Any) -> tuple[Any, list[str]]:
    if isinstance(payload, dict):
        keys = sorted(payload)
        if "project" in payload and "timestamp" in payload and isinstance(payload.get("data"), dict):
            return payload["data"], keys
        return payload, keys
    return payload, [type(payload).__name__]


def safe_headers(r: requests.Response) -> dict[str, str]:
    keep = {}
    for k, v in r.headers.items():
        kl = k.lower()
        if kl.startswith("x-ratelimit-") or kl in {"content-type", "etag", "age", "cache-control"}:
            keep[kl] = v
    return keep


def mcp_call(tool_name: str) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    init = requests.post(
        MCP,
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "idx-trade-provider-acceptance", "version": "1"},
            },
        },
        timeout=TIMEOUT,
    )
    init.raise_for_status()
    if init.headers.get("mcp-session-id"):
        headers["Mcp-Session-Id"] = init.headers["mcp-session-id"]
    out = requests.post(
        MCP,
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": {}},
        },
        timeout=TIMEOUT,
    )
    out.raise_for_status()
    for line in out.text.splitlines():
        if line.startswith("data: "):
            obj = json.loads(line[6:])
            if isinstance(obj, dict):
                return obj
    raise RuntimeError(f"no MCP JSON payload for {tool_name}")


def structured(mcp: dict[str, Any]) -> dict[str, Any]:
    result = mcp.get("result", {})
    sc = result.get("structuredContent")
    if not isinstance(sc, dict):
        raise AssertionError("MCP structuredContent missing")
    return sc


def get_json(path: str, *, params: dict[str, Any], key: str | None = None) -> tuple[requests.Response, Any, list[str]]:
    r = requests.get(
        f"{API_BASE}/{path}",
        params=params,
        headers={"x-api-key": KEY if key is None else key},
        timeout=TIMEOUT,
    )
    payload: Any = None
    outer_keys: list[str] = []
    try:
        payload, outer_keys = outer_unwrap(r.json())
    except Exception:
        pass
    return r, payload, outer_keys


def validate_stock_summary(payload: Any, expected_date: str) -> dict[str, Any]:
    assert isinstance(payload, dict), "stock-summary payload not object"
    assert payload.get("provider") == "idx", payload.get("provider")
    assert payload.get("dataset") == "stock-summary", payload.get("dataset")
    rows = payload.get("data")
    assert isinstance(rows, list) and rows, "stock-summary rows empty"
    total = int(payload.get("recordsTotal"))
    filtered = int(payload.get("recordsFiltered"))
    assert total == filtered == len(rows), (total, filtered, len(rows))
    codes = []
    for row in rows:
        assert isinstance(row, dict)
        assert str(row.get("Date", ""))[:10] == expected_date, row.get("Date")
        code = str(row.get("StockCode", ""))
        assert code
        codes.append(code)
    assert len(codes) == len(set(codes)), "duplicate StockCode"
    return {
        "rows": len(rows),
        "recordsTotal": total,
        "first_codes": codes[:5],
        "last_codes": codes[-5:],
    }


def validate_stream(payload: Any, symbol: str) -> dict[str, Any]:
    assert isinstance(payload, dict), f"stream {symbol} payload not object"
    assert payload.get("provider") == "stockbit", payload.get("provider")
    assert payload.get("symbol") == symbol, payload.get("symbol")
    items = payload.get("items")
    assert isinstance(items, list), "stream items not list"
    declared = int(payload.get("count"))
    assert declared == len(items), (declared, len(items))
    ids = []
    tz_explicit = 0
    for item in items:
        assert isinstance(item, dict)
        assert item.get("id") not in {None, ""}
        assert isinstance(item.get("createdAt"), str)
        assert "content" in item
        ids.append(str(item["id"]))
        raw = item["createdAt"]
        if raw.endswith("Z") or "+" in raw[10:] or raw[-6:-5] in {"+", "-"}:
            tz_explicit += 1
    assert len(ids) == len(set(ids)), "duplicate stream post ids"
    return {
        "count": len(items),
        "ids": ids,
        "first_id": ids[0] if ids else None,
        "last_id": ids[-1] if ids else None,
        "explicit_timezone_rows": tz_explicit,
    }


def main() -> None:
    if not KEY:
        raise SystemExit("ZAPI_API_KEY missing")

    hard_failures: list[str] = []
    soft_concerns: list[str] = []
    result: dict[str, Any] = {
        "schema_version": "zapi_stockbit_provider_acceptance_v1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "hard_failures": hard_failures,
        "soft_concerns": soft_concerns,
    }

    # Account + quota authority.
    before_usage = structured(mcp_call("get_usage"))
    before_account = structured(mcp_call("get_account"))
    quota_before = before_usage.get("quota", {})
    result["account"] = {
        "tier": before_account.get("tier"),
        "planStatus": before_account.get("planStatus"),
        "planExpiresAt": before_account.get("planExpiresAt"),
    }
    result["quota_before"] = {
        "tier": quota_before.get("tier"),
        "used": quota_before.get("used"),
        "limit": quota_before.get("limit"),
        "remaining": quota_before.get("remaining"),
        "resetAt": quota_before.get("resetAt"),
    }

    # Invalid auth must fail closed.
    bad, _, _ = get_json("finance:stockbit/stream", params={"symbol": "BBCA", "count": 1}, key="definitely-invalid")
    result["invalid_auth_status"] = bad.status_code
    if bad.status_code != 401:
        hard_failures.append(f"invalid auth returned HTTP {bad.status_code}, expected 401")

    # Historical stock-summary exactness and repeatability.
    stock_tests: dict[str, Any] = {}
    for target in ("2026-08-20", "2026-06-12"):
        try:
            r1, p1, ok1 = get_json("finance:idx/stock-summary", params={"length": 1000, "start": 0, "date": target})
            r2, p2, ok2 = get_json("finance:idx/stock-summary", params={"length": 1000, "start": 0, "date": target})
            assert r1.status_code == r2.status_code == 200
            v = validate_stock_summary(p1, target)
            validate_stock_summary(p2, target)
            inner1 = json.dumps(p1, sort_keys=True, separators=(",", ":")).encode()
            inner2 = json.dumps(p2, sort_keys=True, separators=(",", ":")).encode()
            stock_tests[target] = {
                **v,
                "outer_keys_first": ok1,
                "outer_keys_second": ok2,
                "inner_sha_first": sha(inner1),
                "inner_sha_second": sha(inner2),
                "repeat_inner_equal": inner1 == inner2,
                "headers": safe_headers(r1),
            }
            if inner1 != inner2:
                soft_concerns.append(f"stock-summary {target} changed across immediate repeat")
        except Exception as exc:
            hard_failures.append(f"stock-summary {target}: {type(exc).__name__}: {exc}")
    result["stock_summary"] = stock_tests

    # ISO and compact date should resolve to the same historical panel.
    try:
        a, pa, _ = get_json("finance:idx/stock-summary", params={"length": 1000, "start": 0, "date": "20260820"})
        b, pb, _ = get_json("finance:idx/stock-summary", params={"length": 1000, "start": 0, "date": "2026-08-20"})
        assert a.status_code == b.status_code == 200
        va = validate_stock_summary(pa, "2026-08-20")
        vb = validate_stock_summary(pb, "2026-08-20")
        canon_a = json.dumps(pa, sort_keys=True, separators=(",", ":"))
        canon_b = json.dumps(pb, sort_keys=True, separators=(",", ":"))
        result["date_format_equivalence"] = {
            "rows_compact": va["rows"],
            "rows_iso": vb["rows"],
            "equal": canon_a == canon_b,
        }
        if canon_a != canon_b:
            soft_concerns.append("compact and ISO stock-summary date formats returned non-identical panels")
    except Exception as exc:
        hard_failures.append(f"date format equivalence: {type(exc).__name__}: {exc}")

    # Weekend behavior is diagnostic, not a gate.
    try:
        rw, pw, okw = get_json("finance:idx/stock-summary", params={"length": 1000, "start": 0, "date": "2026-08-16"})
        weekend: dict[str, Any] = {"http_status": rw.status_code, "outer_keys": okw, "headers": safe_headers(rw)}
        if isinstance(pw, dict):
            weekend.update({
                "provider": pw.get("provider"),
                "dataset": pw.get("dataset"),
                "recordsTotal": pw.get("recordsTotal"),
                "recordsFiltered": pw.get("recordsFiltered"),
                "rows": len(pw.get("data", [])) if isinstance(pw.get("data"), list) else None,
                "distinct_dates": sorted({str(x.get("Date", ""))[:10] for x in pw.get("data", []) if isinstance(x, dict)})[:5] if isinstance(pw.get("data"), list) else [],
            })
        result["weekend_stock_summary"] = weekend
    except Exception as exc:
        soft_concerns.append(f"weekend diagnostic failed: {type(exc).__name__}: {exc}")

    # Stream contract across structural, large-platform, and speculative names.
    stream_results: dict[str, Any] = {}
    newest_post: tuple[str, str, str] | None = None
    for symbol in ("BBCA", "GOTO", "DADA"):
        try:
            r, p, outer = get_json("finance:stockbit/stream", params={"symbol": symbol, "count": 50})
            assert r.status_code == 200
            v = validate_stream(p, symbol)
            stream_results[symbol] = {
                "count_requested": 50,
                "count_returned": v["count"],
                "first_id": v["first_id"],
                "last_id": v["last_id"],
                "explicit_timezone_rows": v["explicit_timezone_rows"],
                "outer_keys": outer,
                "headers": safe_headers(r),
                "ids_sha256": sha("\n".join(v["ids"]).encode()),
            }
            if v["count"] and v["explicit_timezone_rows"] != v["count"]:
                soft_concerns.append(f"{symbol} createdAt lacks explicit timezone on some/all rows")
            if symbol == "BBCA" and v["count"]:
                first_item = p["items"][0]
                newest_post = (str(first_item["id"]), str(first_item.get("content", "")), symbol)
        except Exception as exc:
            hard_failures.append(f"stream {symbol}: {type(exc).__name__}: {exc}")
    result["stream_symbols"] = stream_results

    # Count semantics / page-depth probe on GOTO.
    count_probe: dict[str, Any] = {}
    id_sets: dict[int, list[str]] = {}
    for count in (1, 5, 10, 30, 50, 100):
        try:
            r, p, _ = get_json("finance:stockbit/stream", params={"symbol": "GOTO", "count": count})
            assert r.status_code == 200
            v = validate_stream(p, "GOTO")
            assert v["count"] <= count, (v["count"], count)
            id_sets[count] = v["ids"]
            count_probe[str(count)] = {
                "returned": v["count"],
                "first_id": v["first_id"],
                "last_id": v["last_id"],
                "headers": safe_headers(r),
            }
        except Exception as exc:
            hard_failures.append(f"stream count={count}: {type(exc).__name__}: {exc}")
    for small, large in ((1, 5), (5, 10), (10, 30), (30, 50), (50, 100)):
        if small in id_sets and large in id_sets and id_sets[small] != id_sets[large][: len(id_sets[small])]:
            soft_concerns.append(f"GOTO count prefix inconsistent between {small} and {large}; live page may have moved or query cache differs")
    result["stream_count_probe_goto"] = count_probe

    # Immediate identical request should at least remain contract-valid; body equality is diagnostic.
    try:
        r1, p1, _ = get_json("finance:stockbit/stream", params={"symbol": "BBCA", "count": 10})
        r2, p2, _ = get_json("finance:stockbit/stream", params={"symbol": "BBCA", "count": 10})
        assert r1.status_code == r2.status_code == 200
        v1 = validate_stream(p1, "BBCA")
        v2 = validate_stream(p2, "BBCA")
        result["stream_immediate_repeat"] = {
            "same_ids": v1["ids"] == v2["ids"],
            "first_count": v1["count"],
            "second_count": v2["count"],
            "first_headers": safe_headers(r1),
            "second_headers": safe_headers(r2),
        }
    except Exception as exc:
        hard_failures.append(f"stream immediate repeat: {type(exc).__name__}: {exc}")

    # Post-ID dereference integrity.
    if newest_post is not None:
        post_id, content, source_symbol = newest_post
        try:
            rp, pp, outer = get_json("finance:stockbit/post", params={"id": post_id})
            assert rp.status_code == 200
            assert isinstance(pp, dict)
            assert str(pp.get("id")) == post_id
            deref_content = str(pp.get("content", ""))
            result["post_dereference"] = {
                "source_symbol": source_symbol,
                "post_id": post_id,
                "id_match": True,
                "content_sha_match": sha(content.encode()) == sha(deref_content.encode()),
                "outer_keys": outer,
                "headers": safe_headers(rp),
            }
            if content != deref_content:
                hard_failures.append("post dereference content differs from stream observation")
        except Exception as exc:
            hard_failures.append(f"post dereference: {type(exc).__name__}: {exc}")

    # Unknown-symbol behavior should not be a provider 5xx.
    try:
        ru, pu, outer = get_json("finance:stockbit/stream", params={"symbol": "ZZZZZZ", "count": 5})
        result["unknown_symbol"] = {
            "http_status": ru.status_code,
            "outer_keys": outer,
            "payload_type": type(pu).__name__,
            "headers": safe_headers(ru),
        }
        if ru.status_code >= 500:
            hard_failures.append(f"unknown symbol causes provider HTTP {ru.status_code}")
    except Exception as exc:
        hard_failures.append(f"unknown symbol diagnostic: {type(exc).__name__}: {exc}")

    after_usage = structured(mcp_call("get_usage"))
    quota_after = after_usage.get("quota", {})
    result["quota_after"] = {
        "tier": quota_after.get("tier"),
        "used": quota_after.get("used"),
        "limit": quota_after.get("limit"),
        "remaining": quota_after.get("remaining"),
        "resetAt": quota_after.get("resetAt"),
    }
    try:
        result["quota_billed_delta"] = int(quota_after["used"]) - int(quota_before["used"])
    except Exception:
        result["quota_billed_delta"] = None
        soft_concerns.append("could not compute quota billing delta")

    result["verdict"] = "PASS_WITH_OBSERVED_LIMITATIONS" if not hard_failures else "FAIL_PROVIDER_ACCEPTANCE"
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    if hard_failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
