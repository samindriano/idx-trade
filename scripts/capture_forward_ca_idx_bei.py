"""Capture one immutable official IDX CA phase and its V1.2 attestation.

This is an operational source collector, not a model or outcome path.  It
uses the pinned ``nichsedge/idx-bei`` transport and fails closed on any
incomplete response, schema mismatch, or output conflict.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade import forward_ca_attestation_v1 as forward_ca  # noqa: E402


PROVIDER_REPOSITORY = forward_ca.PROVIDER_REPOSITORY
PROVIDER_COMMIT = forward_ca.PROVIDER_COMMIT
UPSTREAM_BASE_URL = forward_ca.UPSTREAM_BASE_URL
PHASE_SCHEMA = forward_ca.PHASE_SCHEMA
CA_TYPES = (
    "tanpaHmetd",
    "hmetd",
    "stockSplit",
    "reverseStock",
    "sahamBonus",
    "dividenSaham",
    "BuybackSaham",
    "PrivatePlacement",
    "ipo",
    "waran",
    "gabungUsaha",
    "kurangModal",
    "konversiSaham",
    "companyListing",
    "partialDelisting",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _structural_fingerprint(value: Any) -> str:
    def shape(x: Any) -> Any:
        if isinstance(x, dict):
            return {"dict": {str(k): shape(v) for k, v in sorted(x.items(), key=lambda item: str(item[0]))}}
        if isinstance(x, list):
            if not x:
                return {"list": []}
            unique: dict[str, Any] = {}
            for item in x[:25]:
                signature = json.dumps(shape(item), sort_keys=True, separators=(",", ":"))
                unique[signature] = json.loads(signature)
            return {"list": [unique[key] for key in sorted(unique)]}
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


def _parse_date(value: str, label: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise SystemExit(f"{label}: expected YYYY-MM-DD") from exc


def _month_anchors(from_session: str, through_session: str) -> list[str]:
    start = date.fromisoformat(from_session).replace(day=1)
    end = date.fromisoformat(through_session).replace(day=1)
    anchors: list[str] = []
    current = start
    while current <= end:
        anchors.append(current.strftime("%Y%m%d"))
        current = (
            date(current.year + 1, 1, 1)
            if current.month == 12
            else date(current.year, current.month + 1, 1)
        )
    return anchors


def _verify_provider_checkout(checkout: Path) -> None:
    if not checkout.is_dir() or not (checkout / "python" / "src").is_dir():
        raise SystemExit(f"FORWARD_CA_PROVIDER_CHECKOUT_MISSING:{checkout}")
    try:
        head = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit("FORWARD_CA_PROVIDER_CHECKOUT_ATTESTATION_FAILED") from exc
    if head != PROVIDER_COMMIT:
        raise SystemExit(f"FORWARD_CA_PROVIDER_COMMIT_MISMATCH:{head}")
    if dirty:
        raise SystemExit("FORWARD_CA_PROVIDER_WORKTREE_DIRTY")


def _count(value: object) -> int | None:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider-checkout", required=True)
    parser.add_argument("--phase", required=True, choices=("POST_EOD", "PREOPEN"))
    parser.add_argument("--from-session", required=True)
    parser.add_argument("--through-session", required=True)
    parser.add_argument("--tickers", required=True, help="comma-separated IDX tickers")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--attestation-output", required=True)
    args = parser.parse_args()

    from_session = _parse_date(args.from_session, "--from-session")
    through_session = _parse_date(args.through_session, "--through-session")
    if through_session < from_session:
        raise SystemExit("FORWARD_CA_SESSION_WINDOW_REVERSED")
    checkout = Path(args.provider_checkout).expanduser().resolve()
    _verify_provider_checkout(checkout)

    provider_src = checkout / "python" / "src"
    sys.path.insert(0, str(provider_src))
    try:
        from idx.core.client import IDXClient  # type: ignore
    except ImportError as exc:
        raise SystemExit("FORWARD_CA_PROVIDER_IMPORT_FAILED") from exc

    tickers = sorted({value.strip().upper() for value in args.tickers.split(",") if value.strip()})
    if not tickers:
        raise SystemExit("FORWARD_CA_REQUIRED_TICKERS_EMPTY")
    out = Path(args.output_dir).expanduser().resolve()
    if out.exists():
        raise SystemExit(f"FORWARD_CA_OUTPUT_EXISTS:{out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = out.parent / f".{out.name}.partial.{uuid.uuid4().hex}"
    stage.mkdir(parents=False, exist_ok=False)
    raw_dir = stage / "raw"
    raw_dir.mkdir(parents=False, exist_ok=False)
    artifacts: list[dict[str, Any]] = []
    leg_status = {leg: "COMPLETE" for leg in forward_ca.REQUIRED_LEGS}
    calendar_fingerprints: set[str] = set()

    client = IDXClient(base_url=UPSTREAM_BASE_URL, max_retries=3, delay_seconds=1.0)

    def capture(*, leg: str, name: str, endpoint: str, params: dict[str, Any]) -> Any:
        captured_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        response = client.get(endpoint, params=params, impersonate="chrome", timeout=30)
        if response is None:
            leg_status[leg] = "ERROR"
            raise SystemExit(f"FORWARD_CA_NO_RESPONSE:{endpoint}")
        body = bytes(response.content)
        raw_path = raw_dir / f"{name}.json"
        raw_path.write_bytes(body)
        artifacts.append(
            {
                "phase": args.phase,
                "leg": leg,
                "name": name,
                "endpoint": endpoint,
                "params": params,
                "captured_at_utc": captured_at,
                "http_status": int(response.status_code),
                "content_type": str(response.headers.get("content-type", "")),
        "path": str(raw_path.relative_to(stage)),
                "sha256": _sha256_bytes(body),
            }
        )
        if response.status_code != 200:
            leg_status[leg] = "ERROR"
            raise SystemExit(f"FORWARD_CA_HTTP_STATUS:{endpoint}:{response.status_code}")
        if "json" not in str(response.headers.get("content-type", "")).lower():
            leg_status[leg] = "ERROR"
            raise SystemExit(f"FORWARD_CA_CONTENT_TYPE_NOT_JSON:{endpoint}")
        try:
            return response.json()
        except Exception as exc:
            leg_status[leg] = "ERROR"
            raise SystemExit(f"FORWARD_CA_JSON_INVALID:{endpoint}") from exc

    request_from = from_session.replace("-", "")
    request_through = through_session.replace("-", "")
    for ca_type in CA_TYPES:
        payload = capture(
            leg="issued_history",
            name=f"issued_{ca_type}",
            endpoint="/ListingActivity/GetIssuedHistory",
            params={
                "caType": ca_type,
                "dateFrom": request_from,
                "dateTo": request_through,
                "start": 0,
                "length": 9999,
            },
        )
        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            leg_status["issued_history"] = "ERROR"
            raise SystemExit(f"FORWARD_CA_ISSUED_HISTORY_SCHEMA_INVALID:{ca_type}")
        expected = _count(payload.get("recordsFiltered") if isinstance(payload, dict) else None)
        if expected is not None and expected != len(rows):
            leg_status["issued_history"] = "ERROR"
            raise SystemExit(f"FORWARD_CA_ISSUED_HISTORY_INCOMPLETE:{ca_type}")

    for ticker in tickers:
        page = 1
        while True:
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
            items = payload.get("Items") if isinstance(payload, dict) else None
            if not isinstance(items, list):
                leg_status["announcements"] = "ERROR"
                raise SystemExit(f"FORWARD_CA_ANNOUNCEMENT_SCHEMA_INVALID:{ticker}:{page}")
            pages = _count(payload.get("PageCount") if isinstance(payload, dict) else None)
            if pages is None or pages < page:
                leg_status["announcements"] = "ERROR"
                raise SystemExit(f"FORWARD_CA_ANNOUNCEMENT_PAGECOUNT_INVALID:{ticker}:{page}")
            if page >= pages:
                break
            page += 1

    for anchor in _month_anchors(from_session, through_session):
        payload = capture(
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
        results = payload.get("Results") if isinstance(payload, dict) else None
        if not isinstance(results, list) or not results:
            leg_status["calendar"] = "ERROR"
            raise SystemExit(f"FORWARD_CA_CALENDAR_INVALID:{anchor[:6]}")
        calendar_fingerprints.add(_structural_fingerprint(payload))

    if sorted(calendar_fingerprints) != [forward_ca.EXPECTED_CALENDAR_SCHEMA_FINGERPRINT]:
        leg_status["calendar"] = "ERROR"
        raise SystemExit("FORWARD_CA_CALENDAR_SCHEMA_FINGERPRINT_MISMATCH")

    capture_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest = {
        "schema_version": PHASE_SCHEMA,
        "status": "COMPLETE",
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
        "calendar_capture_scope": forward_ca.CALENDAR_CAPTURE_SCOPE,
        "capture_timestamp_utc": capture_timestamp,
        "legs": {name: {"status": status} for name, status in leg_status.items()},
        "calendar_schema_fingerprints": sorted(calendar_fingerprints),
        "raw_artifacts": artifacts,
    }
    manifest_path = stage / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    forward_ca.verify_phase_manifest(manifest_path)

    attestation = Path(args.attestation_output).expanduser().resolve()
    stage.replace(out)
    final_manifest_path = out / "MANIFEST.json"
    try:
        forward_ca.build_phase_attestation_v1_2(
            phase_manifest_path=final_manifest_path,
            output_path=attestation,
        )
    except Exception:
        # Keep the failed evidence inspectable, but never leave a directory
        # that looks like a published phase capture.
        out.replace(stage)
        raise
    print(json.dumps({
        "status": "COMPLETE",
        "phase_manifest": str(final_manifest_path),
        "phase_manifest_sha256": hashlib.sha256(final_manifest_path.read_bytes()).hexdigest(),
        "attestation": str(attestation),
        "attestation_sha256": hashlib.sha256(attestation.read_bytes()).hexdigest(),
        "capture_timestamp_utc": capture_timestamp,
        "outcome_access": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
