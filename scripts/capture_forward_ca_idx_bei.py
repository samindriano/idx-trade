from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

PROVIDER_REPOSITORY = "nichsedge/idx-bei"
PROVIDER_COMMIT = "75d6c0f74fa360d225794c70c383348977de6798"
UPSTREAM_BASE_URL = "https://www.idx.co.id/primary"
PHASE_SCHEMA = "idx_trade_forward_ca_phase_manifest_v1"
CA_TYPES = (
    "tanpaHmetd", "hmetd", "stockSplit", "reverseStock", "sahamBonus",
    "dividenSaham", "BuybackSaham", "PrivatePlacement", "ipo", "waran",
    "gabungUsaha", "kurangModal", "konversiSaham", "companyListing",
    "partialDelisting",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _structural_fingerprint(value: Any) -> str:
    def shape(x: Any) -> Any:
        if isinstance(x, dict):
            return {"dict": {str(k): shape(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}}
        if isinstance(x, list):
            if not x:
                return {"list": []}
            unique = {}
            for item in x[:25]:
                sig = json.dumps(shape(item), sort_keys=True, separators=(",", ":"))
                unique[sig] = json.loads(sig)
            return {"list": [unique[k] for k in sorted(unique)]}
        if x is None:
            return "null"
        if isinstance(x, bool):
            return "bool"
        if isinstance(x, int):
            return "int"
        if isinstance(x, float):
            return "float"
        return "str"

    blob = json.dumps(shape(value), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _verify_provider_checkout(checkout: Path) -> None:
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


def _parse_session(value: str, code: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(code) from exc


def _calendar_month_anchors(from_session: str, through_session: str) -> list[str]:
    start = _parse_session(from_session, "invalid --from-session; expected YYYY-MM-DD")
    end = _parse_session(through_session, "invalid --through-session; expected YYYY-MM-DD")
    if end < start:
        raise SystemExit("--through-session precedes --from-session")
    current = date(start.year, start.month, 1)
    final = date(end.year, end.month, 1)
    anchors: list[str] = []
    while current <= final:
        anchors.append(current.strftime("%Y%m%d"))
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return anchors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-checkout", required=True)
    parser.add_argument("--phase", required=True, choices=("POST_EOD", "PREOPEN"))
    parser.add_argument("--from-session", required=True)
    parser.add_argument("--through-session", required=True)
    parser.add_argument("--tickers", required=True, help="comma-separated IDX tickers")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    from_session = _parse_session(
        args.from_session, "invalid --from-session; expected YYYY-MM-DD"
    ).isoformat()
    through_session = _parse_session(
        args.through_session, "invalid --through-session; expected YYYY-MM-DD"
    ).isoformat()
    if through_session < from_session:
        raise SystemExit("--through-session precedes --from-session")

    checkout = Path(args.provider_checkout).expanduser().resolve()
    _verify_provider_checkout(checkout)

    provider_src = checkout / "python" / "src"
    if not provider_src.is_dir():
        raise SystemExit(f"provider python/src missing: {provider_src}")
    sys.path.insert(0, str(provider_src))
    from idx.core.client import IDXClient  # type: ignore

    tickers = sorted({x.strip().upper() for x in args.tickers.split(",") if x.strip()})
    if not tickers:
        raise SystemExit("no tickers")

    out = Path(args.output_dir).expanduser().resolve()
    if out.exists():
        raise SystemExit(f"output dir already exists: {out}")
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True)

    client = IDXClient(base_url=UPSTREAM_BASE_URL, max_retries=3, delay_seconds=1.0)
    artifacts = []
    leg_status = {
        "issued_history": "COMPLETE",
        "announcements": "COMPLETE",
        "calendar": "COMPLETE",
    }
    calendar_fingerprints = set()

    def capture(*, leg: str, name: str, endpoint: str, params: dict[str, Any]) -> Any:
        captured_at = datetime.now(timezone.utc).isoformat()
        response = client.get(endpoint, params=params, impersonate="chrome", timeout=30)
        if response is None:
            leg_status[leg] = "ERROR"
            raise RuntimeError(f"no response: {endpoint}")
        body = bytes(response.content)
        path = raw_dir / f"{name}.json"
        path.write_bytes(body)
        artifacts.append({
            "phase": args.phase,
            "leg": leg,
            "name": name,
            "endpoint": endpoint,
            "params": params,
            "captured_at_utc": captured_at,
            "http_status": int(response.status_code),
            "content_type": str(response.headers.get("content-type", "")),
            "path": str(path.relative_to(out)),
            "sha256": _sha256_bytes(body),
        })
        if response.status_code != 200:
            leg_status[leg] = "ERROR"
            raise RuntimeError(f"http {response.status_code}: {endpoint}")
        try:
            return response.json()
        except Exception as exc:
            leg_status[leg] = "ERROR"
            raise RuntimeError(f"invalid json: {endpoint}") from exc

    for ca_type in CA_TYPES:
        payload = capture(
            leg="issued_history",
            name=f"issued_{ca_type}",
            endpoint="/ListingActivity/GetIssuedHistory",
            params={
                "caType": ca_type,
                "dateFrom": from_session,
                "dateTo": through_session,
                "start": 0,
                "length": 9999,
            },
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            leg_status["issued_history"] = "ERROR"
            raise RuntimeError(f"issued history schema invalid: {ca_type}")
        filtered = payload.get("recordsFiltered")
        if isinstance(filtered, int) and filtered != len(payload["data"]):
            leg_status["issued_history"] = "ERROR"
            raise RuntimeError(f"issued history pagination incomplete: {ca_type}")

    for ticker in tickers:
        first = capture(
            leg="announcements",
            name=f"announcement_{ticker}_p1",
            endpoint="/NewsAnnouncement/GetAllAnnouncement",
            params={
                "keywords": ticker,
                "pageNumber": 1,
                "pageSize": 100,
                "lang": "id",
                "dateFrom": from_session,
                "dateTo": through_session,
            },
        )
        if not isinstance(first, dict) or not isinstance(first.get("Items"), list):
            leg_status["announcements"] = "ERROR"
            raise RuntimeError(f"announcement schema invalid: {ticker}")
        pages = int(first.get("PageCount") or 1)
        if pages < 1:
            leg_status["announcements"] = "ERROR"
            raise RuntimeError(f"announcement page count invalid: {ticker}")
        for page in range(2, pages + 1):
            payload = capture(
                leg="announcements",
                name=f"announcement_{ticker}_p{page}",
                endpoint="/NewsAnnouncement/GetAllAnnouncement",
                params={
                    "keywords": ticker,
                    "pageNumber": page,
                    "pageSize": 100,
                    "lang": "id",
                    "dateFrom": from_session,
                    "dateTo": through_session,
                },
            )
            if not isinstance(payload, dict) or not isinstance(payload.get("Items"), list):
                leg_status["announcements"] = "ERROR"
                raise RuntimeError(f"announcement schema invalid: {ticker}:p{page}")

    # Calendar is captured all-market, not once per ticker. The official endpoint
    # supports d/w/m ranges; monthly all-market capture is small (~hundreds of rows)
    # and avoids an empty-result schema fingerprint changing by ticker. Capture each
    # distinct calendar month touched by the decision->execution window so long
    # weekends/month boundaries remain covered, then classify only required tickers
    # offline inside IDX-Trade.
    for anchor in _calendar_month_anchors(from_session, through_session):
        calendar = capture(
            leg="calendar",
            name=f"calendar_month_{anchor[:6]}",
            endpoint="/Home/GetCalendar",
            params={
                "range": "m",
                "date": anchor,
                "start": 0,
                "length": 9999,
                "code": "",
                "language": "id-id",
                "search": "",
            },
        )
        if not isinstance(calendar, dict) or not isinstance(calendar.get("Results"), list):
            leg_status["calendar"] = "ERROR"
            raise RuntimeError(f"calendar schema invalid: {anchor[:6]}")
        if not calendar["Results"]:
            leg_status["calendar"] = "ERROR"
            raise RuntimeError(f"calendar unexpectedly empty: {anchor[:6]}")
        calendar_fingerprints.add(_structural_fingerprint(calendar))

    if len(calendar_fingerprints) != 1:
        leg_status["calendar"] = "ERROR"
        raise RuntimeError(
            f"calendar schema drift within capture: {sorted(calendar_fingerprints)}"
        )

    manifest = {
        "schema_version": PHASE_SCHEMA,
        "status": "COMPLETE" if all(x == "COMPLETE" for x in leg_status.values()) else "ERROR",
        "phase": args.phase,
        "provider_repository": PROVIDER_REPOSITORY,
        "provider_commit": PROVIDER_COMMIT,
        "provider_module": "idx.core.client.IDXClient",
        "transport": "curl_cffi",
        "impersonate": "chrome",
        "upstream_base_url": UPSTREAM_BASE_URL,
        "from_session_date": from_session,
        "through_session_date": through_session,
        "required_tickers": tickers,
        "calendar_capture_scope": "ALL_MARKET_MONTHS_TOUCHING_WINDOW",
        "legs": {name: {"status": status} for name, status in leg_status.items()},
        "calendar_schema_fingerprints": sorted(calendar_fingerprints),
        "raw_artifacts": artifacts,
    }
    manifest_path = out / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
