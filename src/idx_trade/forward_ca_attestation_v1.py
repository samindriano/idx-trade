from __future__ import annotations

from datetime import date, datetime, timezone
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
ATTESTATION_SCHEMA_V1_2 = "v4_x1_paper_ca_attestation_v1_2"
CALENDAR_CAPTURE_SCOPE = "ALL_MARKET_MONTHS_TOUCHING_WINDOW"
EXPECTED_CALENDAR_SCHEMA_FINGERPRINT: str | None = "09a2f81aaa291b27232ca610b228a28470cbe11d5599fa66f55a3b75030060f3"
REQUIRED_PHASES = ("POST_EOD", "PREOPEN")
REQUIRED_LEGS = ("issued_history", "announcements", "calendar")
EXPECTED_ENDPOINT_BY_LEG = {
    "issued_history": "/ListingActivity/GetIssuedHistory",
    "announcements": "/NewsAnnouncement/GetAllAnnouncement",
    "calendar": "/Home/GetCalendar",
}
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


def _structural_fingerprint(value: Any) -> str:
    def shape(x: Any) -> Any:
        if isinstance(x, dict):
            return {
                "dict": {
                    str(k): shape(v)
                    for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))
                }
            }
        if isinstance(x, list):
            if not x:
                return {"list": []}
            unique: dict[str, Any] = {}
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


def _capture_timestamp_utc(value: object) -> str:
    """Validate and normalize a source-capture timestamp.

    A phase attestation is only useful for the V1.2 knowledge cutoff when the
    source capture carries an explicit timezone-aware UTC timestamp.  Do not
    accept a naive local timestamp or silently assign a timezone here.
    """

    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ForwardCAError("FORWARD_CA_CAPTURE_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ForwardCAError("FORWARD_CA_CAPTURE_TIMESTAMP_INVALID")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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


def _verify_raw_leg_payload(leg: str, payload: Any) -> str | None:
    if leg == "issued_history":
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ForwardCAError("FORWARD_CA_ISSUED_HISTORY_SCHEMA_INVALID")
        return None
    if leg == "announcements":
        if not isinstance(payload, dict) or not isinstance(payload.get("Items"), list):
            raise ForwardCAError("FORWARD_CA_ANNOUNCEMENT_SCHEMA_INVALID")
        return None
    if leg == "calendar":
        if not isinstance(payload, dict) or not isinstance(payload.get("Results"), list):
            raise ForwardCAError("FORWARD_CA_CALENDAR_SCHEMA_INVALID")
        if not payload["Results"]:
            raise ForwardCAError("FORWARD_CA_CALENDAR_UNEXPECTEDLY_EMPTY")
        return _structural_fingerprint(payload)
    raise ForwardCAError(f"FORWARD_CA_RAW_LEG_INVALID:{leg}")


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
    if payload.get("calendar_capture_scope") != CALENDAR_CAPTURE_SCOPE:
        raise ForwardCAError("FORWARD_CA_CALENDAR_CAPTURE_SCOPE_MISMATCH")

    phase = str(payload.get("phase") or "")
    if phase not in REQUIRED_PHASES:
        raise ForwardCAError("FORWARD_CA_PHASE_INVALID")
    if payload.get("status") != "COMPLETE":
        raise ForwardCAError(f"FORWARD_CA_PHASE_INCOMPLETE:{phase}")

    from_date = _iso_date(payload.get("from_session_date"), "FORWARD_CA_FROM_DATE_INVALID")
    through_date = _iso_date(
        payload.get("through_session_date"), "FORWARD_CA_THROUGH_DATE_INVALID"
    )
    if through_date < from_date:
        raise ForwardCAError("FORWARD_CA_DATE_WINDOW_REVERSED")

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
    observed_calendar_fingerprints: set[str] = set()
    for row in artifacts:
        if not isinstance(row, dict):
            raise ForwardCAError("FORWARD_CA_RAW_ARTIFACT_ROW_INVALID")
        if row.get("http_status") != 200:
            raise ForwardCAError("FORWARD_CA_RAW_HTTP_STATUS_NOT_200")
        content_type = str(row.get("content_type") or "").lower()
        if "json" not in content_type:
            raise ForwardCAError("FORWARD_CA_RAW_CONTENT_TYPE_NOT_JSON")
        leg = str(row.get("leg") or "")
        if leg not in REQUIRED_LEGS:
            raise ForwardCAError("FORWARD_CA_RAW_LEG_INVALID")
        if row.get("endpoint") != EXPECTED_ENDPOINT_BY_LEG[leg]:
            raise ForwardCAError(f"FORWARD_CA_RAW_ENDPOINT_MISMATCH:{leg}")
        seen_legs.add(leg)
        raw_path = _resolve_artifact(manifest_path, row)
        raw_payload = _load_json(raw_path, "FORWARD_CA_RAW_JSON_INVALID")
        fingerprint = _verify_raw_leg_payload(leg, raw_payload)
        if fingerprint is not None:
            observed_calendar_fingerprints.add(fingerprint)

    if not set(REQUIRED_LEGS).issubset(seen_legs):
        raise ForwardCAError("FORWARD_CA_RAW_LEG_COVERAGE_INCOMPLETE")

    fingerprints = payload.get("calendar_schema_fingerprints")
    if not isinstance(fingerprints, list) or not fingerprints:
        raise ForwardCAError("FORWARD_CA_CALENDAR_SCHEMA_FINGERPRINT_MISSING")
    if not all(isinstance(x, str) and _SHA_RE.fullmatch(x) for x in fingerprints):
        raise ForwardCAError("FORWARD_CA_CALENDAR_SCHEMA_FINGERPRINT_INVALID")
    declared_fingerprints = sorted(set(fingerprints))
    observed_fingerprints = sorted(observed_calendar_fingerprints)
    if declared_fingerprints != observed_fingerprints:
        raise ForwardCAError("FORWARD_CA_CALENDAR_SCHEMA_FINGERPRINT_RAW_MISMATCH")
    if len(observed_fingerprints) != 1:
        raise ForwardCAError("FORWARD_CA_CALENDAR_SCHEMA_NOT_STABLE_WITHIN_PHASE")

    payload["calendar_schema_fingerprints"] = observed_fingerprints
    payload["_manifest_path"] = str(manifest_path)
    payload["_manifest_sha256"] = _sha256(manifest_path)
    payload["required_tickers"] = tickers
    payload["from_session_date"] = from_date
    payload["through_session_date"] = through_date
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
        "from_session_date",
        "through_session_date",
        "required_tickers",
        "calendar_capture_scope",
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
        "calendar_capture_scope": post["calendar_capture_scope"],
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


def verify_source_manifest(
    path: str | Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
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
    if payload.get("calendar_capture_scope") != CALENDAR_CAPTURE_SCOPE:
        raise ForwardCAError("FORWARD_CA_CALENDAR_CAPTURE_SCOPE_MISMATCH")

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
            "from_session_date",
            "through_session_date",
            "required_tickers",
            "calendar_capture_scope",
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


def _date_in_window(
    value: Any,
    from_date: str,
    through_date: str,
    *,
    include_from: bool,
) -> bool:
    start = date.fromisoformat(from_date)
    end = date.fromisoformat(through_date)
    for text in _walk_strings(value):
        for match in re.finditer(r"\b(\d{4}-\d{2}-\d{2})", text):
            try:
                d = date.fromisoformat(match.group(1))
            except ValueError:
                continue
            if (start <= d if include_from else start < d) and d <= end:
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
                if _date_in_window(
                    event_date, from_date, through_date, include_from=False
                ):
                    reasons.append(
                        f"{phase_name}:ISSUED_HISTORY:"
                        f"{row.get('JenisTindakan') or 'UNKNOWN'}:{event_date}"
                    )

        for payload in _artifact_payloads(phase, "announcements"):
            items = payload.get("Items", []) if isinstance(payload, dict) else []
            if not isinstance(items, list):
                raise ForwardCAError("FORWARD_CA_ANNOUNCEMENT_SCHEMA_INVALID")
            for item in items:
                if not isinstance(item, dict) or not _contains_ticker(item, ticker):
                    continue
                if _contains_ca_keyword(item) and _date_in_window(
                    item, from_date, through_date, include_from=True
                ):
                    reasons.append(
                        f"{phase_name}:ANNOUNCEMENT:"
                        f"{str(item.get('AnnouncementNo') or item.get('Id') or 'UNKNOWN')}"
                    )

        for payload in _artifact_payloads(phase, "calendar"):
            results = payload.get("Results", []) if isinstance(payload, dict) else []
            if not isinstance(results, list):
                raise ForwardCAError("FORWARD_CA_CALENDAR_SCHEMA_INVALID")
            for item in results:
                if not isinstance(item, dict):
                    continue
                if not _contains_ticker(item, ticker):
                    continue
                if not _contains_ca_keyword(item):
                    continue
                if _date_in_window(item, from_date, through_date, include_from=False):
                    event_type = str(
                        item.get("Jenis")
                        or item.get("JenisAgenda")
                        or item.get("type")
                        or "UNKNOWN"
                    )
                    reasons.append(f"{phase_name}:CALENDAR_EVENT:{event_type}")

    return bool(reasons), sorted(set(reasons))


def build_attestation(*, source_manifest_path: str | Path, output_path: str | Path) -> Path:
    source, phases = verify_source_manifest(source_manifest_path)
    if EXPECTED_CALENDAR_SCHEMA_FINGERPRINT is None:
        raise ForwardCAError("FORWARD_CA_CALENDAR_SCHEMA_NOT_FROZEN")
    fingerprints = source.get("calendar_schema_fingerprints", [])
    if fingerprints != [EXPECTED_CALENDAR_SCHEMA_FINGERPRINT]:
        raise ForwardCAError("FORWARD_CA_CALENDAR_SCHEMA_FINGERPRINT_MISMATCH")

    from_date = _iso_date(source["from_session_date"], "FORWARD_CA_FROM_DATE_INVALID")
    through_date = _iso_date(
        source["through_session_date"], "FORWARD_CA_THROUGH_DATE_INVALID"
    )
    evidence_rows = []
    any_event = False
    for ticker in source["required_tickers"]:
        relevant, reasons = _ticker_has_relevant_event(
            ticker,
            from_date=from_date,
            through_date=through_date,
            phases=phases,
        )
        any_event = any_event or relevant
        evidence_rows.append(
            {
                "ticker": ticker,
                "status": RELEVANT if relevant else NO_EVENT,
                "reasons": reasons,
            }
        )

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


def build_phase_attestation_v1_2(
    *, phase_manifest_path: str | Path, output_path: str | Path
) -> Path:
    """Build one current-phase V1.2 attestation from a verified raw capture.

    The live controller captures POST_EOD and PREOPEN separately.  A merged
    source manifest is intentionally not required for either phase: each
    attestation is bound to its own immutable phase manifest, exact window,
    required ticker set, calendar fingerprint, and capture cutoff.
    """

    phase = verify_phase_manifest(phase_manifest_path)
    if phase.get("calendar_schema_fingerprints") != [EXPECTED_CALENDAR_SCHEMA_FINGERPRINT]:
        raise ForwardCAError("FORWARD_CA_CALENDAR_SCHEMA_FINGERPRINT_MISMATCH")
    capture_timestamp = _capture_timestamp_utc(phase.get("capture_timestamp_utc"))
    phase_name = str(phase["phase"])
    evidence_rows: list[dict[str, Any]] = []
    any_event = False
    for ticker in phase["required_tickers"]:
        relevant, reasons = _ticker_has_relevant_event(
            ticker,
            from_date=phase["from_session_date"],
            through_date=phase["through_session_date"],
            phases={phase_name: phase},
        )
        any_event = any_event or relevant
        evidence_rows.append(
            {
                "ticker": ticker,
                "status": RELEVANT if relevant else NO_EVENT,
                "reasons": reasons,
            }
        )

    phase_path = Path(phase["_manifest_path"]).expanduser().resolve()
    payload: dict[str, Any] = {
        "schema_version": ATTESTATION_SCHEMA_V1_2,
        "capture_phase": phase_name,
        "from_session_date": phase["from_session_date"],
        "through_session_date": phase["through_session_date"],
        "capture_timestamp_utc": capture_timestamp,
        "status": "RELEVANT_EVENT_DETECTED" if any_event else "NO_RELEVANT_EVENTS",
        "provider_repository": PROVIDER_REPOSITORY,
        "provider_commit": PROVIDER_COMMIT,
        "upstream_base_url": UPSTREAM_BASE_URL,
        "calendar_schema_fingerprint": EXPECTED_CALENDAR_SCHEMA_FINGERPRINT,
        "required_tickers": phase["required_tickers"],
        "evidence_rows": evidence_rows,
        "phase_manifest_path": str(phase_path),
        "phase_manifest_sha256": str(phase["_manifest_sha256"]),
    }
    out = Path(output_path).expanduser().resolve()
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if out.exists():
        if out.read_bytes() != encoded:
            raise ForwardCAError(f"FORWARD_CA_OUTPUT_EXISTS:{out}")
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = out.with_name(
        f".{out.name}.{hashlib.sha256(encoded).hexdigest()[:12]}.tmp"
    )
    temporary.write_bytes(encoded)
    try:
        if out.exists():
            if out.read_bytes() != encoded:
                raise ForwardCAError(f"FORWARD_CA_OUTPUT_EXISTS:{out}")
        else:
            temporary.replace(out)
    finally:
        temporary.unlink(missing_ok=True)
    return out
