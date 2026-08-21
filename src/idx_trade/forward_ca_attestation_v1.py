from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

PROVIDER_REPOSITORY = "nichsedge/idx-bei"
PROVIDER_COMMIT = "75d6c0f74fa360d225794c70c383348977de6798"
UPSTREAM_BASE_URL = "https://www.idx.co.id/primary"
PHASE_SCHEMA = "idx_trade_forward_ca_phase_manifest_v1"
SOURCE_SCHEMA = "idx_trade_forward_ca_source_manifest_v1"
ATTESTATION_SCHEMA = "v4_x1_paper_ca_attestation_v1"
EXPECTED_CALENDAR_SCHEMA_FINGERPRINT: str | None = None
REQUIRED_PHASES = ("POST_EOD", "PREOPEN")
REQUIRED_LEGS = ("issued_history", "announcements", "calendar")
NO_EVENT = "NO_RELEVANT_EVENT"
RELEVANT = "RELEVANT_EVENT"

CA_KEYWORDS = (
    "dividen", "dividend", "cum date", "ex date", "recording date",
    "stock split", "reverse stock", "pemecahan saham", "penggabungan nilai nominal",
    "hmetd", "hak memesan efek terlebih dahulu", "rights issue", "right issue",
    "pmthmetd", "private placement", "tanpa hmetd",
    "saham bonus", "bonus share", "bonus shares", "dividen saham", "stock dividend",
    "buyback", "pembelian kembali saham", "merger", "penggabungan usaha",
    "konversi saham", "partial delisting", "delisting sebagian",
    "capital reduction", "pengurangan modal", "waran", "warrant",
)

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class ForwardCAError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm_ticker(value: object) -> str:
    ticker = str(value or "").strip().upper()
    if not ticker or not re.fullmatch(r"[A-Z0-9]{1,12}", ticker):
        raise ForwardCAError(f"FORWARD_CA_TICKER_INVALID:{value!r}")
    return ticker


def _iso_date(value: object, code: str) -> str:
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except Exception as exc:
        raise ForwardCAError(code) from exc


def _load_json(path: Path, code: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ForwardCAError(code) from exc


def _resolve_artifact(manifest_path: Path, row: Mapping[str, Any]) -> Path:
    raw = Path(str(row.get("path") or ""))
    path = raw if raw.is_absolute() else (manifest_path.parent / raw).resolve()
    if not path.is_file():
        raise ForwardCAError(f"FORWARD_CA_RAW_ARTIFACT_MISSING:{path}")
    declared = str(row.get("sha256") or "")
    if not _SHA_RE.fullmatch(declared):
        raise ForwardCAError("FORWARD_CA_RAW_SHA_INVALID")
    actual = _sha256(path)
    if actual != declared:
        raise ForwardCAError(f"FORWARD_CA_RAW_SHA_MISMATCH:{path.name}")
    return path


def verify_phase_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path).expanduser().resolve()
    payload = _load_json(manifest_path, "FORWARD_CA_PHASE_MANIFEST_INVALID")
    if not isinstance(payload, dict) or payload.get("schema_version") != PHASE_SCHEMA:
        raise ForwardCAError("FORWARD_CA_PHASE_SCHEMA_CHANGED")
    if payload.get("provider_repository") != PROVIDER_REPOSITORY:
        raise ForwardCAError("FORWARD_CA_PROVIDER_REPOSITORY_MISMATCH")
    if payload.get("provider_commit") != PROVIDER_COMMIT:
        raise ForwardCAError("FORWARD_CA_PROVIDER_COMMIT_MISMATCH")
    if payload.get("upstream_base_url") != UPSTREAM_BASE_URL:
        raise ForwardCAError("FORWARD_CA_UPSTREAM_MISMATCH")
    phase = str(payload.get("phase") or "")
    if phase not in REQUIRED_PHASES:
        raise ForwardCAError("FORWARD_CA_PHASE_INVALID")
    if payload.get("status") != "COMPLETE":
        raise ForwardCAError(f"FORWARD_CA_PHASE_INCOMPLETE:{phase}")
    _iso_date(payload.get("from_session_date"), "FORWARD_CA_FROM_DATE_INVALID")
    _iso_date(payload.get("through_session_date"), "FORWARD_CA_THROUGH_DATE_INVALID")
    tickers = sorted({_norm_ticker(x) for x in payload.get("required_tickers", [])})
    if not tickers:
        raise ForwardCAError("FORWARD_CA_REQUIRED_TICKERS_EMPTY")
    legs = payload.get("legs")
    if not isinstance(legs, dict):
        raise ForwardCAError("FORWARD_CA_LEGS_MISSING")
    for leg in REQUIRED_LEGS:
        row = legs.get(leg)
        if not isinstance(row, dict) or row.get("status") != "COMPLETE":
            raise ForwardCAError(f"FORWARD_CA_LEG_INCOMPLETE:{phase}:{leg}")
    artifacts = payload.get("raw_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ForwardCAError("FORWARD_CA_RAW_ARTIFACTS_MISSING")
    seen_legs: set[str] = set()
    for row in artifacts:
        if not isinstance(row, dict):
            raise ForwardCAError("FORWARD_CA_RAW_ARTIFACT_ROW_INVALID")
        if row.get("http_status") != 200:
            raise ForwardCAError("FORWARD_CA_RAW_HTTP_STATUS_NOT_200")
        leg = str(row.get("leg") or "")
        if leg not in REQUIRED_LEGS:
            raise ForwardCAError("FORWARD_CA_RAW_LEG_INVALID")
        seen_legs.add(leg)
        _resolve_artifact(manifest_path, row)
    if not set(REQUIRED_LEGS).issubset(seen_legs):
        raise ForwardCAError("FORWARD_CA_RAW_LEG_COVERAGE_INCOMPLETE")
    fingerprints = payload.get("calendar_schema_fingerprints")
    if not isinstance(fingerprints, list) or not fingerprints:
        raise ForwardCAError("FORWARD_CA_CALENDAR_SCHEMA_FINGERPRINT_MISSING")
    if not all(isinstance(x, str) and _SHA_RE.fullmatch(x) for x in fingerprints):
        raise ForwardCAError("FORWARD_CA_CALENDAR_SCHEMA_FINGERPRINT_INVALID")
    payload["calendar_schema_fingerprints"] = sorted(set(fingerprints))
    payload["_manifest_path"] = str(manifest_path)
    payload["_manifest_sha256"] = _sha256(manifest_path)
    payload["required_tickers"] = tickers
    return payload


def merge_phase_manifests(
    *,
    post_eod_manifest_path: str | Path,
    preopen_manifest_path: str | Path,
    output_path: str | Path,
) -> Path:
    post = verify_phase_manifest(post_eod_manifest_path)
    pre = verify_phase_manifest(preopen_manifest_path)
    if post["phase"] != "POST_EOD" or pre["phase"] != "PREOPEN":
        raise ForwardCAError("FORWARD_CA_PHASE_ORDER_INVALID")
    for key in (
        "from_session_date", "through_session_date", "required_tickers",
        "calendar_schema_fingerprints",
    ):
        if post[key] != pre[key]:
            raise ForwardCAError(f"FORWARD_CA_PHASE_SCOPE_MISMATCH:{key}")
    out = Path(output_path).expanduser().resolve()
    if out.exists():
        raise ForwardCAError(f"FORWARD_CA_OUTPUT_EXISTS:{out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SOURCE_SCHEMA,
        "status": "COMPLETE",
        "provider_repository": PROVIDER_REPOSITORY,
        "provider_commit": PROVIDER_COMMIT,
        "upstream_base_url": UPSTREAM_BASE_URL,
        "from_session_date": post["from_session_date"],
        "through_session_date": post["through_session_date"],
        "required_tickers": post["required_tickers"],
        "calendar_schema_fingerprints": post["calendar_schema_fingerprints"],
        "capture_phases": [
            {
                "phase": "POST_EOD",
                "manifest_path": post["_manifest_path"],
                "manifest_sha256": post["_manifest_sha256"],
            },
            {
                "phase": "PREOPEN",
                "manifest_path": pre["_manifest_path"],
                "manifest_sha256": pre["_manifest_sha256"],
            },
        ],
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def verify_source_manifest(path: str | Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    source_path = Path(path).expanduser().resolve()
    payload = _load_json(source_path, "FORWARD_CA_SOURCE_MANIFEST_INVALID")
    if not isinstance(payload, dict) or payload.get("schema_version") != SOURCE_SCHEMA:
        raise ForwardCAError("FORWARD_CA_SOURCE_SCHEMA_CHANGED")
    if payload.get("status") != "COMPLETE":
        raise ForwardCAError("FORWARD_CA_SOURCE_INCOMPLETE")
    if payload.get("provider_repository") != PROVIDER_REPOSITORY:
        raise ForwardCAError("FORWARD_CA_PROVIDER_REPOSITORY_MISMATCH")
    if payload.get("provider_commit") != PROVIDER_COMMIT:
        raise ForwardCAError("FORWARD_CA_PROVIDER_COMMIT_MISMATCH")
    if payload.get("upstream_base_url") != UPSTREAM_BASE_URL:
        raise ForwardCAError("FORWARD_CA_UPSTREAM_MISMATCH")
    phases = payload.get("capture_phases")
    if not isinstance(phases, list) or len(phases) != 2:
        raise ForwardCAError("FORWARD_CA_SOURCE_PHASES_INVALID")
    loaded: dict[str, dict[str, Any]] = {}
    for row in phases:
        if not isinstance(row, dict):
            raise ForwardCAError("FORWARD_CA_SOURCE_PHASE_ROW_INVALID")
        phase = str(row.get("phase") or "")
        raw = Path(str(row.get("manifest_path") or ""))
        phase_path = raw if raw.is_absolute() else (source_path.parent / raw).resolve()
        declared = str(row.get("manifest_sha256") or "")
        if not phase_path.is_file() or not _SHA_RE.fullmatch(declared):
            raise ForwardCAError("FORWARD_CA_SOURCE_PHASE_MANIFEST_MISSING")
        if _sha256(phase_path) != declared:
            raise ForwardCAError("FORWARD_CA_SOURCE_PHASE_SHA_MISMATCH")
        phase_payload = verify_phase_manifest(phase_path)
        if phase_payload["phase"] != phase:
            raise ForwardCAError("FORWARD_CA_SOURCE_PHASE_ID_MISMATCH")
        loaded[phase] = phase_payload
    if set(loaded) != set(REQUIRED_PHASES):
        raise ForwardCAError("FORWARD_CA_SOURCE_PHASE_COVERAGE_INCOMPLETE")
    for phase in loaded.values():
        for key in (
            "from_session_date", "through_session_date", "required_tickers",
            "calendar_schema_fingerprints",
        ):
            if phase[key] != payload.get(key):
                raise ForwardCAError(f"FORWARD_CA_SOURCE_SCOPE_MISMATCH:{key}")
    payload["_source_path"] = str(source_path)
    payload["_source_sha256"] = _sha256(source_path)
    return payload, loaded


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)
    elif value is not None:
        yield str(value)


def _contains_ticker(value: Any, ticker: str) -> bool:
    pat = re.compile(rf"(?<![A-Z0-9]){re.escape(ticker)}(?![A-Z0-9])", re.I)
    return any(pat.search(text.strip()) for text in _walk_strings(value))


def _contains_ca_keyword(value: Any) -> bool:
    blob = " ".join(x.lower() for x in _walk_strings(value))
    return any(keyword in blob for keyword in CA_KEYWORDS)


def _date_in_open_closed_window(value: Any, from_date: str, through_date: str) -> bool:
    start = date.fromisoformat(from_date)
    end = date.fromisoformat(through_date)
    for text in _walk_strings(value):
        for match in re.finditer(r"\b(\d{4}-\d{2}-\d{2})", text):
            try:
                d = date.fromisoformat(match.group(1))
            except ValueError:
                continue
            if start < d <= end:
                return True
    return False


def _artifact_payloads(phase_manifest: Mapping[str, Any], leg: str) -> list[Any]:
    manifest_path = Path(str(phase_manifest["_manifest_path"]))
    out: list[Any] = []
    for row in phase_manifest["raw_artifacts"]:
        if row.get("leg") != leg:
            continue
        path = _resolve_artifact(manifest_path, row)
        out.append(_load_json(path, "FORWARD_CA_RAW_JSON_INVALID"))
    return out


def _ticker_has_relevant_event(
    ticker: str,
    *,
    from_date: str,
    through_date: str,
    phases: Mapping[str, Mapping[str, Any]],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for phase_name, phase in phases.items():
        for payload in _artifact_payloads(phase, "issued_history"):
            rows = payload.get("data", []) if isinstance(payload, dict) else []
            if not isinstance(rows, list):
                raise ForwardCAError("FORWARD_CA_ISSUED_HISTORY_SCHEMA_INVALID")
            for row in rows:
                if not isinstance(row, dict):
                    continue
                if str(row.get("KodeEmiten") or "").strip().upper() != ticker:
                    continue
                event_date = str(row.get("TanggalPencatatan") or "")[:10]
                if _date_in_open_closed_window(event_date, from_date, through_date):
                    reasons.append(
                        f"{phase_name}:ISSUED_HISTORY:{row.get('JenisTindakan') or 'UNKNOWN'}:{event_date}"
                    )
        for payload in _artifact_payloads(phase, "announcements"):
            items = payload.get("Items", []) if isinstance(payload, dict) else []
            if not isinstance(items, list):
                raise ForwardCAError("FORWARD_CA_ANNOUNCEMENT_SCHEMA_INVALID")
            for item in items:
                if not isinstance(item, dict) or not _contains_ticker(item, ticker):
                    continue
                if _contains_ca_keyword(item) and _date_in_open_closed_window(
                    item, from_date, through_date
                ):
                    reasons.append(
                        f"{phase_name}:ANNOUNCEMENT:"
                        f"{str(item.get('AnnouncementNo') or item.get('Id') or 'UNKNOWN')}"
                    )
        for payload in _artifact_payloads(phase, "calendar"):
            if _contains_ticker(payload, ticker) and _date_in_open_closed_window(
                payload, from_date, through_date
            ):
                reasons.append(f"{phase_name}:CALENDAR_EVENT")
    return bool(reasons), sorted(set(reasons))


def build_attestation(*, source_manifest_path: str | Path, output_path: str | Path) -> Path:
    source, phases = verify_source_manifest(source_manifest_path)
    if EXPECTED_CALENDAR_SCHEMA_FINGERPRINT is None:
        raise ForwardCAError("FORWARD_CA_CALENDAR_SCHEMA_NOT_FROZEN")
    fingerprints = source.get("calendar_schema_fingerprints", [])
    if fingerprints != [EXPECTED_CALENDAR_SCHEMA_FINGERPRINT]:
        raise ForwardCAError("FORWARD_CA_CALENDAR_SCHEMA_FINGERPRINT_MISMATCH")
    from_date = _iso_date(source["from_session_date"], "FORWARD_CA_FROM_DATE_INVALID")
    through_date = _iso_date(source["through_session_date"], "FORWARD_CA_THROUGH_DATE_INVALID")
    evidence_rows = []
    any_event = False
    for ticker in source["required_tickers"]:
        relevant, reasons = _ticker_has_relevant_event(
            ticker, from_date=from_date, through_date=through_date, phases=phases
        )
        any_event = any_event or relevant
        evidence_rows.append({
            "ticker": ticker,
            "status": RELEVANT if relevant else NO_EVENT,
            "reasons": reasons,
        })
    status = "RELEVANT_EVENT_DETECTED" if any_event else "NO_RELEVANT_EVENTS"
    out = Path(output_path).expanduser().resolve()
    if out.exists():
        raise ForwardCAError(f"FORWARD_CA_OUTPUT_EXISTS:{out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": ATTESTATION_SCHEMA,
        "from_session_date": from_date,
        "through_session_date": through_date,
        "status": status,
        "provider_repository": PROVIDER_REPOSITORY,
        "provider_commit": PROVIDER_COMMIT,
        "upstream_base_url": UPSTREAM_BASE_URL,
        "calendar_schema_fingerprint": EXPECTED_CALENDAR_SCHEMA_FINGERPRINT,
        "evidence_rows": evidence_rows,
        "source_path": source["_source_path"],
        "source_sha256": source["_source_sha256"],
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out
