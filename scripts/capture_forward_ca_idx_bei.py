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
import os
from pathlib import Path
import subprocess
import sys
import uuid
from typing import Any
from urllib.parse import urlencode

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

TRANSPORT_WARMUP_URLS = (
    "https://www.idx.co.id/",
    "https://www.idx.co.id/id/perusahaan-tercatat/ringkasan-perusahaan/",
)
TRANSPORT_API_REFERER = TRANSPORT_WARMUP_URLS[1]
ZAPI_RAW_URL = "https://api.zpi.web.id/v1/finance:idx/raw"
ZAPI_PROJECT = "finance:idx:raw"
ZAPI_TRANSPORT = forward_ca.ZAPI_RAW_TRANSPORT
DIRECT_TRANSPORT = forward_ca.DIRECT_TRANSPORT
TRANSPORT_POLICY = forward_ca.TRANSPORT_POLICY


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


def _recover_interrupted_publication(
    out: Path,
    attestation: Path,
    *,
    expected_phase: str,
    expected_from_session: str,
    expected_through_session: str,
    required_tickers: list[str],
) -> bool:
    """Complete one interrupted two-artifact publication without provider access."""

    marker = out / "PUBLISH.json"
    if not marker.is_file():
        return False
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
        final_manifest = out / "MANIFEST.json"
        pending = Path(str(payload["pending_attestation"])).expanduser().resolve()
        if Path(str(payload["output_dir"])).expanduser().resolve() != out.resolve():
            raise ValueError("output directory mismatch")
        if Path(str(payload["attestation"])).expanduser().resolve() != attestation.resolve():
            raise ValueError("attestation path mismatch")
        if not final_manifest.is_file():
            raise ValueError("final manifest missing")
        phase = forward_ca.verify_phase_manifest(final_manifest)
        if (
            phase.get("phase") != expected_phase
            or phase.get("from_session_date") != expected_from_session
            or phase.get("through_session_date") != expected_through_session
            or sorted(phase.get("required_tickers") or []) != sorted(required_tickers)
        ):
            raise ValueError("phase scope mismatch")
        if str(payload["manifest_sha256"]) != hashlib.sha256(final_manifest.read_bytes()).hexdigest():
            raise ValueError("manifest hash mismatch")
        if not pending.is_file():
            if not attestation.is_file():
                raise ValueError("pending attestation missing")
        else:
            pending_sha = hashlib.sha256(pending.read_bytes()).hexdigest()
            if pending_sha != str(payload["pending_attestation_sha256"]):
                raise ValueError("pending attestation hash mismatch")
            if attestation.exists():
                if attestation.read_bytes() != pending.read_bytes():
                    raise ValueError("final attestation conflict")
                pending.unlink()
            else:
                pending.replace(attestation)
        if not attestation.is_file():
            raise ValueError("final attestation missing")
        attestation_doc = json.loads(attestation.read_text(encoding="utf-8"))
        if (
            attestation_doc.get("phase_manifest_path")
            != str(final_manifest.resolve())
            or attestation_doc.get("phase_manifest_sha256")
            != str(payload["manifest_sha256"])
        ):
            raise ValueError("attestation binding mismatch")
        from idx_trade.forward_dividend_execution_v1_1 import (
            _load_and_verify_post_eod_attestation_v1_2,
        )

        _load_and_verify_post_eod_attestation_v1_2(
            path=attestation,
            expected_from_session_date=expected_from_session,
            expected_through_session_date=expected_through_session,
            required_tickers=required_tickers,
        )
        marker.unlink()
        return True
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit("FORWARD_CA_INTERRUPTED_PUBLICATION_INVALID") from exc


def _build_transport_client(checkout: Path, raw_dir: Path) -> tuple[Any, list[dict[str, Any]]]:
    """Build the pinned IDX client over one warmed curl_cffi browser session.

    The provider checkout remains pinned and owns the request/client contract;
    this local adapter only supplies the persistent session and the previously
    proven public-page warm-up. No User-Agent is manually supplied, so the
    impersonation profile remains the authority for browser headers.
    """

    from curl_cffi import requests as curl_requests
    from idx.core import client as provider_client_module  # type: ignore

    session = curl_requests.Session(impersonate="chrome")
    session.headers.update(
        {"Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"}
    )
    raw_dir.mkdir(parents=True, exist_ok=True)
    transport_preflight: list[dict[str, Any]] = []
    stage = raw_dir.parent
    for index, url in enumerate(TRANSPORT_WARMUP_URLS, start=1):
        raw_path = raw_dir / f"warmup_{index}.bin"
        captured_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            response = session.get(url, timeout=30)
            body = bytes(response.content)
            raw_path.write_bytes(body)
            transport_preflight.append(
                {
                    "kind": f"IDX_WARMUP_{index}",
                    "requested_url": url,
                    "final_url": str(getattr(response, "url", url)),
                    "captured_at_utc": captured_at,
                    "http_status": int(response.status_code),
                    "content_type": str(response.headers.get("content-type", "")),
                    "path": str(raw_path.relative_to(stage)),
                    "bytes": len(body),
                    "sha256": _sha256_bytes(body),
                }
            )
        except Exception as exc:
            transport_preflight.append(
                {
                    "kind": f"IDX_WARMUP_{index}",
                    "requested_url": url,
                    "captured_at_utc": captured_at,
                    "http_status": 0,
                    "content_type": "",
                    "path": "",
                    "bytes": 0,
                    "sha256": "",
                    "error": f"{type(exc).__name__}:{exc}",
                }
            )

    # IDXClient.get() calls its module-level requests.get(). Point that call at
    # the warmed Session without changing the pinned provider checkout.
    provider_client_module.requests = session
    client = provider_client_module.IDXClient(
        base_url=UPSTREAM_BASE_URL,
        headers={
            "accept": "application/json, text/plain, */*",
            "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "referer": TRANSPORT_API_REFERER,
        },
        max_retries=3,
        delay_seconds=1.0,
    )
    return client, transport_preflight


def _fetch_zapi_raw(
    endpoint: str,
    params: dict[str, Any],
) -> bytes:
    """Fetch one exact IDX endpoint through Zapi's raw transport only."""

    api_key = os.environ.get("ZAPI_API_KEY")
    if not api_key:
        raise SystemExit("FORWARD_CA_ZAPI_API_KEY_MISSING")
    try:
        import requests

        response = requests.get(
            ZAPI_RAW_URL,
            params={
                "path": endpoint.lstrip("/"),
                "query": urlencode(params),
            },
            headers={"x-api-key": api_key, "Accept": "application/json"},
            timeout=30,
        )
    except Exception as exc:
        raise SystemExit("FORWARD_CA_ZAPI_RAW_REQUEST_ERROR") from exc
    if response.status_code != 200:
        raise SystemExit(f"FORWARD_CA_ZAPI_RAW_HTTP_STATUS:{response.status_code}")
    body = bytes(response.content)
    if not body:
        raise SystemExit("FORWARD_CA_ZAPI_RAW_EMPTY_RESPONSE")
    return body


def _normalize_zapi_raw_payload(raw: bytes, endpoint: str) -> dict[str, Any] | list[Any]:
    try:
        envelope = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise SystemExit("FORWARD_CA_ZAPI_RAW_JSON_INVALID") from exc
    if not isinstance(envelope, dict) or envelope.get("project") != ZAPI_PROJECT:
        raise SystemExit("FORWARD_CA_ZAPI_RAW_PROJECT_MISMATCH")
    inner = envelope.get("data")
    if not isinstance(inner, dict):
        raise SystemExit("FORWARD_CA_ZAPI_RAW_ENVELOPE_INVALID")
    if (
        inner.get("provider") != "idx"
        or str(inner.get("path") or "").lstrip("/") != endpoint.lstrip("/")
    ):
        raise SystemExit("FORWARD_CA_ZAPI_RAW_SOURCE_MISMATCH")
    payload = inner.get("data")
    if not isinstance(payload, (dict, list)):
        raise SystemExit("FORWARD_CA_ZAPI_RAW_DATA_MISSING")
    if isinstance(payload, dict):
        return payload
    normalized: dict[str, Any] = {"data": payload}
    for key in ("recordsTotal", "recordsFiltered"):
        if key in inner:
            normalized[key] = inner[key]
    return normalized


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
    tickers = sorted({value.strip().upper() for value in args.tickers.split(",") if value.strip()})
    if not tickers:
        raise SystemExit("FORWARD_CA_REQUIRED_TICKERS_EMPTY")
    out = Path(args.output_dir).expanduser().resolve()
    attestation = Path(args.attestation_output).expanduser().resolve()
    if out.exists():
        if _recover_interrupted_publication(
            out,
            attestation,
            expected_phase=args.phase,
            expected_from_session=from_session,
            expected_through_session=through_session,
            required_tickers=tickers,
        ):
            print(json.dumps({"status": "RECOVERED", "outcome_access": False}, sort_keys=True))
            return 0
        raise SystemExit(f"FORWARD_CA_OUTPUT_EXISTS:{out}")
    if attestation.exists():
        raise SystemExit(f"FORWARD_CA_ATTESTATION_EXISTS:{attestation}")
    checkout = Path(args.provider_checkout).expanduser().resolve()
    _verify_provider_checkout(checkout)

    provider_src = checkout / "python" / "src"
    sys.path.insert(0, str(provider_src))
    try:
        from idx.core.client import IDXClient  # type: ignore  # noqa: F401
    except ImportError as exc:
        raise SystemExit("FORWARD_CA_PROVIDER_IMPORT_FAILED") from exc

    out.parent.mkdir(parents=True, exist_ok=True)
    stage = out.parent / f".{out.name}.partial.{uuid.uuid4().hex}"
    stage.mkdir(parents=False, exist_ok=False)
    raw_dir = stage / "raw"
    raw_dir.mkdir(parents=False, exist_ok=False)
    artifacts: list[dict[str, Any]] = []
    transport_attempts: list[dict[str, Any]] = []
    selected_transports: set[str] = set()
    leg_status = {leg: "COMPLETE" for leg in forward_ca.REQUIRED_LEGS}
    calendar_fingerprints: set[str] = set()

    client, transport_preflight = _build_transport_client(checkout, raw_dir)

    def capture(*, leg: str, name: str, endpoint: str, params: dict[str, Any]) -> Any:
        captured_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        response = None
        direct_error = ""
        try:
            response = client.get(endpoint, params=params, impersonate="chrome", timeout=30)
        except Exception as exc:
            direct_error = f"{type(exc).__name__}:{exc}"
        if response is not None and response.status_code == 200:
            body = bytes(response.content)
            raw_path = raw_dir / f"{name}.json"
            raw_path.write_bytes(body)
            content_type = str(response.headers.get("content-type", ""))
            if "json" not in content_type.lower():
                leg_status[leg] = "ERROR"
                raise SystemExit(f"FORWARD_CA_CONTENT_TYPE_NOT_JSON:{endpoint}")
            try:
                payload = response.json()
            except Exception as exc:
                leg_status[leg] = "ERROR"
                raise SystemExit(f"FORWARD_CA_JSON_INVALID:{endpoint}") from exc
            artifacts.append(
                {
                    "phase": args.phase,
                    "leg": leg,
                    "name": name,
                    "endpoint": endpoint,
                    "params": params,
                    "captured_at_utc": captured_at,
                    "http_status": 200,
                    "content_type": content_type,
                    "path": str(raw_path.relative_to(stage)),
                    "sha256": _sha256_bytes(body),
                    "transport": DIRECT_TRANSPORT,
                }
            )
            selected_transports.add(DIRECT_TRANSPORT)
            return payload

        if response is not None:
            body = bytes(response.content)
            failed_path = raw_dir / f"{name}.direct-failure.bin"
            failed_path.write_bytes(body)
            direct_status = int(response.status_code)
            transport_attempts.append(
                {
                    "transport": DIRECT_TRANSPORT,
                    "endpoint": endpoint,
                    "params": params,
                    "captured_at_utc": captured_at,
                    "http_status": direct_status,
                    "content_type": str(response.headers.get("content-type", "")),
                    "path": str(failed_path.relative_to(stage)),
                    "sha256": _sha256_bytes(body),
                }
            )
        else:
            transport_attempts.append(
                {
                    "transport": DIRECT_TRANSPORT,
                    "endpoint": endpoint,
                    "params": params,
                    "captured_at_utc": captured_at,
                    "http_status": 0,
                    "content_type": "",
                    "path": "",
                    "sha256": "",
                    "error": direct_error or "NO_RESPONSE",
                }
            )

        zapi_raw = _fetch_zapi_raw(endpoint, params)
        zapi_envelope_path = raw_dir / f"{name}.zapi-envelope.json"
        zapi_envelope_path.write_bytes(zapi_raw)
        normalized_payload = _normalize_zapi_raw_payload(zapi_raw, endpoint)
        normalized_raw = json.dumps(
            normalized_payload, indent=2, sort_keys=True
        ).encode("utf-8")
        raw_path = raw_dir / f"{name}.json"
        raw_path.write_bytes(normalized_raw)
        artifacts.append(
            {
                "phase": args.phase,
                "leg": leg,
                "name": name,
                "endpoint": endpoint,
                "params": params,
                "captured_at_utc": captured_at,
                "http_status": 200,
                "content_type": "application/json",
                "path": str(raw_path.relative_to(stage)),
                "sha256": _sha256_bytes(normalized_raw),
                "transport": ZAPI_TRANSPORT,
                "transport_raw_path": str(zapi_envelope_path.relative_to(stage)),
                "transport_raw_sha256": _sha256_bytes(zapi_raw),
            }
        )
        selected_transports.add(ZAPI_TRANSPORT)
        return normalized_payload

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
        "transport_policy": TRANSPORT_POLICY,
        "selected_transports": sorted(selected_transports),
        "transport_attempts": transport_attempts,
        "transport_session": "curl_cffi.Session",
        "transport_warmup_urls": list(TRANSPORT_WARMUP_URLS),
        "transport_api_referer": TRANSPORT_API_REFERER,
        "transport_preflight": transport_preflight,
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

    final_manifest_path = out / "MANIFEST.json"
    pending_attestation = attestation.parent / (
        f".{attestation.name}.{out.name}.{uuid.uuid4().hex}.pending"
    )
    forward_ca.build_phase_attestation_v1_2(
        phase_manifest_path=manifest_path,
        output_path=pending_attestation,
        manifest_path_for_attestation=final_manifest_path,
    )
    pending_attestation_sha256 = hashlib.sha256(pending_attestation.read_bytes()).hexdigest()
    publish_marker = {
        "schema_version": "idx_trade_forward_ca_publication_v1",
        "output_dir": str(out),
        "attestation": str(attestation),
        "pending_attestation": str(pending_attestation),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "pending_attestation_sha256": pending_attestation_sha256,
    }
    (stage / "PUBLISH.json").write_text(
        json.dumps(publish_marker, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    stage.replace(out)
    pending_attestation.replace(attestation)
    (out / "PUBLISH.json").unlink()
    final_manifest_path = out / "MANIFEST.json"
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
