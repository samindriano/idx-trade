from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests


ARTIFACT_ROOT = Path(
    r"D:\Documents\Project\idx-ca-zapi-coverage-contract-revalidation-20260902-v1"
)
BASE_URL = "https://api.zpi.web.id"
DOCS_URL = "https://zpi.web.id/api/finance/idx"
CONTROL_TRANSITIONS = {
    "SMDR": "2023-01-31",
    "DIVA": "2021-09-02",
    "TMAS": "2023-05-23",
    "TUGU": "2023-05-24",
    "BMRI": None,
    "BBRM": None,
    "SKRN": None,
}
FAMILIES = (
    "dividend",
    "rights",
    "additional-listing",
    "delisting",
    "new-listing",
)
INDIVIDUAL_ENDPOINTS = {
    "dividend": "/v1/finance:idx/dividends",
    "rights": "/v1/finance:idx/rights-offerings",
    "additional-listing": "/v1/finance:idx/additional-listings",
    "delisting": "/v1/finance:idx/delistings",
    "new-listing": "/v1/finance:idx/new-listings",
}
MONTHS = (
    (2025, 5),
    (2025, 6),
    (2025, 7),
    (2025, 8),
    (2025, 9),
    (2025, 10),
    (2025, 11),
    (2025, 12),
    (2026, 1),
    (2026, 2),
    (2026, 3),
    (2026, 4),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def unwrap_payload(payload: object) -> object:
    """Return the provider payload inside the stable ZAPI response envelope."""
    current = payload
    for _ in range(3):
        if not isinstance(current, dict):
            break
        nested = None
        for key in ("data", "content"):
            value = current.get(key)
            if isinstance(value, (dict, list)):
                nested = value
                break
        if nested is None:
            break
        current = nested
    return current


def response_items(payload: object) -> list[object]:
    payload = unwrap_payload(payload)
    if not isinstance(payload, dict):
        return []
    value = payload.get("items")
    if isinstance(value, list):
        return value
    value = payload.get("data")
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and isinstance(value.get("items"), list):
        return value["items"]
    return []


def item_identity(item: object) -> tuple[str, str]:
    if not isinstance(item, dict):
        return "NONE", stable_json(item)
    preferred = (
        "id",
        "eventId",
        "eventID",
        "sourceEventId",
        "sourceEventID",
        "recordId",
        "recordID",
        "itemId",
        "itemID",
    )
    for key in preferred:
        value = item.get(key)
        if value not in (None, ""):
            return key, str(value)
    return "NO_STABLE_ID", sha256(stable_json(item).encode("utf-8"))


def safe_headers(headers: requests.structures.CaseInsensitiveDict[str]) -> dict[str, str]:
    allowed = {"content-type", "etag", "cache-control", "date", "last-modified"}
    return {
        key: value
        for key, value in headers.items()
        if key.lower() in allowed or key.lower().startswith("x-ratelimit-")
    }


def months_between(start: str, end: str) -> list[str]:
    sy, sm = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    result: list[str] = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        result.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y += 1
            m = 1
    return result


def ensure_new_artifact_root() -> None:
    if ARTIFACT_ROOT.exists():
        raise RuntimeError(f"refusing to overwrite existing artifact root: {ARTIFACT_ROOT}")
    (ARTIFACT_ROOT / "raw").mkdir(parents=True)


class Audit:
    def __init__(self) -> None:
        self.api_key = os.environ.get("ZAPI_API_KEY", "")
        self.session = requests.Session()
        self.rows: list[dict[str, object]] = []
        self.by_key: dict[str, dict[str, object]] = {}
        self.sequence = 0

    def call(
        self,
        endpoint: str,
        params: dict[str, object],
        purpose: str,
        *,
        force: bool = False,
    ) -> dict[str, object]:
        normalized = urlencode(sorted((str(k), str(v)) for k, v in params.items()))
        key = f"{endpoint}?{normalized}"
        if key in self.by_key and not force:
            return self.by_key[key]
        self.sequence += 1
        request_id = f"r{self.sequence:04d}"
        retrieved = datetime.now(timezone.utc).isoformat(timespec="seconds")
        url = f"{BASE_URL}{endpoint}"
        print(f"CALL {request_id} {endpoint}?{normalized}", flush=True)
        row: dict[str, object] = {
            "request_id": request_id,
            "purpose": purpose,
            "endpoint": endpoint,
            "url": url,
            "query": normalized,
            "retrieved_at_utc": retrieved,
            "http_status": 0,
            "response_bytes": 0,
            "response_sha256": "",
            "payload_sha256": "",
            "raw_path": "",
            "response_headers": "{}",
            "json_valid": False,
            "top_level_keys": "",
            "payload_keys": "",
            "record_count": 0,
            "item_identity_quality": "NONE",
            "item_id_values": "",
            "total": "",
            "count": "",
            "page": "",
            "limit": "",
            "length": "",
            "has_more": "",
            "next_page": "",
            "coverage_start": "",
            "coverage_end": "",
            "coverage_key": "",
            "complete_for_query": "",
            "source": "",
            "segments_answered": "",
            "segments_requested": "",
            "unpublished_months": "",
            "error": "",
            "_payload": None,
        }
        try:
            response = self.session.get(
                url,
                params=params,
                headers={"x-api-key": self.api_key, "Accept": "application/json"},
                timeout=60,
            )
            raw = bytes(response.content)
            row["http_status"] = response.status_code
            row["response_bytes"] = len(raw)
            row["response_sha256"] = sha256(raw)
            row["response_headers"] = stable_json(safe_headers(response.headers))
            raw_path = ARTIFACT_ROOT / "raw" / f"{request_id}.json"
            raw_path.write_bytes(raw)
            row["raw_path"] = str(raw_path.relative_to(ARTIFACT_ROOT)).replace("\\", "/")
            try:
                payload = json.loads(raw.decode("utf-8"))
                row["json_valid"] = True
                row["_payload"] = payload
                if isinstance(payload, dict):
                    row["top_level_keys"] = ",".join(sorted(str(x) for x in payload))
                    normalized_payload = unwrap_payload(payload)
                    row["payload_sha256"] = sha256(stable_json(normalized_payload).encode("utf-8"))
                    if isinstance(normalized_payload, dict):
                        row["payload_keys"] = ",".join(sorted(str(x) for x in normalized_payload))
                    items = response_items(payload)
                    row["record_count"] = len(items)
                    identities = [item_identity(item) for item in items]
                    qualities = {kind for kind, _ in identities}
                    row["item_identity_quality"] = (
                        "STABLE_ID" if any(x != "NO_STABLE_ID" for x in qualities) else "NO_STABLE_ID"
                    )
                    row["item_id_values"] = "|".join(f"{kind}={value}" for kind, value in identities)
                    mapping = {
                        "total": "total",
                        "count": "count",
                        "page": "page",
                        "limit": "limit",
                        "length": "length",
                        "has_more": "hasMore",
                        "next_page": "nextPage",
                        "coverage_start": "coverageStart",
                        "coverage_end": "coverageEnd",
                        "coverage_key": "coverageKey",
                        "complete_for_query": "completeForQuery",
                        "source": "source",
                        "segments_answered": "segmentsAnswered",
                        "segments_requested": "segmentsRequested",
                        "unpublished_months": "unpublishedMonths",
                    }
                    for target, source in mapping.items():
                        value = normalized_payload.get(source, "") if isinstance(normalized_payload, dict) else ""
                        row[target] = stable_json(value) if isinstance(value, (list, dict)) else value
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                row["error"] = f"INVALID_JSON:{type(exc).__name__}"
        except requests.RequestException as exc:
            row["error"] = f"REQUEST_ERROR:{type(exc).__name__}"
        self.rows.append(row)
        self.by_key[key] = row
        return row

    def save_request_index(self) -> None:
        fields = [key for key in self.rows[0] if key != "_payload"] if self.rows else []
        with (ARTIFACT_ROOT / "request_index.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in self.rows:
                writer.writerow({key: row.get(key, "") for key in fields})

    @classmethod
    def from_existing_artifact(cls) -> "Audit":
        request_index = ARTIFACT_ROOT / "request_index.csv"
        raw_root = ARTIFACT_ROOT / "raw"
        if not request_index.is_file() or not raw_root.is_dir():
            raise RuntimeError(f"existing artifact is incomplete: {ARTIFACT_ROOT}")
        audit = cls()
        with request_index.open(newline="", encoding="utf-8") as handle:
            old_rows = list(csv.DictReader(handle))
        for old in old_rows:
            row = dict(old)
            row["_payload"] = None
            row.setdefault("payload_keys", "")
            row.setdefault("payload_sha256", "")
            raw_path = ARTIFACT_ROOT / str(row.get("raw_path", ""))
            raw = raw_path.read_bytes()
            if sha256(raw) != str(row.get("response_sha256", "")):
                raise RuntimeError(f"raw hash mismatch for {row.get('request_id')}")
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                row["json_valid"] = False
                row["error"] = f"INVALID_JSON:{type(exc).__name__}"
            else:
                row["json_valid"] = True
                row["_payload"] = payload
                if isinstance(payload, dict):
                    row["top_level_keys"] = ",".join(sorted(str(x) for x in payload))
                    normalized_payload = unwrap_payload(payload)
                    row["payload_sha256"] = sha256(stable_json(normalized_payload).encode("utf-8"))
                    row["payload_keys"] = (
                        ",".join(sorted(str(x) for x in normalized_payload))
                        if isinstance(normalized_payload, dict)
                        else ""
                    )
                    items = response_items(payload)
                    row["record_count"] = len(items)
                    identities = [item_identity(item) for item in items]
                    qualities = {kind for kind, _ in identities}
                    row["item_identity_quality"] = (
                        "STABLE_ID"
                        if any(x not in {"NO_STABLE_ID", "NONE"} for x in qualities)
                        else ("NO_STABLE_ID" if items else "NONE")
                    )
                    row["item_id_values"] = "|".join(f"{kind}={value}" for kind, value in identities)
                    mapping = {
                        "total": "total",
                        "count": "count",
                        "page": "page",
                        "limit": "limit",
                        "length": "length",
                        "has_more": "hasMore",
                        "next_page": "nextPage",
                        "coverage_start": "coverageStart",
                        "coverage_end": "coverageEnd",
                        "coverage_key": "coverageKey",
                        "complete_for_query": "completeForQuery",
                        "source": "source",
                        "segments_answered": "segmentsAnswered",
                        "segments_requested": "segmentsRequested",
                        "unpublished_months": "unpublishedMonths",
                    }
                    for target, source in mapping.items():
                        value = normalized_payload.get(source, "") if isinstance(normalized_payload, dict) else ""
                        row[target] = stable_json(value) if isinstance(value, (list, dict)) else value
            audit.rows.append(row)
            audit.by_key[f"{row.get('endpoint')}?{row.get('query')}"] = row
        audit.sequence = len(audit.rows)
        return audit


def values_from_row(row: dict[str, object]) -> list[dict[str, object]]:
    payload = row.get("_payload")
    return [item for item in response_items(payload) if isinstance(item, dict)]


def records_for(audit: Audit, purpose_prefix: str) -> list[dict[str, object]]:
    return [row for row in audit.rows if str(row["purpose"]).startswith(purpose_prefix)]


def write_csv(name: str, rows: list[dict[str, object]], fields: list[str]) -> None:
    with (ARTIFACT_ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def item_hash_set(row: dict[str, object], drop: tuple[str, ...] = ()) -> set[str]:
    result = set()
    for item in values_from_row(row):
        value = dict(item)
        for key in drop:
            value.pop(key, None)
        result.add(sha256(stable_json(value).encode("utf-8")))
    return result


def run_queries(audit: Audit) -> None:
    broad = {"code": "BBCA", "from": "2025-05", "to": "2026-04", "type": "dividend", "page": 1, "limit": 50}
    audit.call("/v1/finance:idx/corporate-actions", broad, "capability:combined:broad")
    for family in FAMILIES:
        audit.call(
            "/v1/finance:idx/corporate-actions",
            {"code": "BBCA", "from": "2025-05", "to": "2026-04", "type": family, "page": 1, "limit": 200},
            f"combined:full:{family}",
        )
    audit.call(
        "/v1/finance:idx/corporate-actions",
        {"code": "BBCA", "from": "2025-05", "to": "2026-04", "page": 1, "limit": 200},
        "combined:full:all",
    )

    for family, endpoint in INDIVIDUAL_ENDPOINTS.items():
        for year, month in MONTHS:
            audit.call(
                endpoint,
                {"year": year, "month": month, "page": 1, "length": 200, "search": "BBCA"},
                f"individual:full:{family}:{year:04d}-{month:02d}",
            )

    for family in FAMILIES:
        for start, end, label in (("2025-05", "2025-10", "first_half"), ("2025-11", "2026-04", "second_half")):
            audit.call(
                "/v1/finance:idx/corporate-actions",
                {"code": "BBCA", "from": start, "to": end, "type": family, "page": 1, "limit": 200},
                f"window:{family}:{label}",
            )

    for family in FAMILIES:
        page = 1
        while page <= 20:
            row = audit.call(
                "/v1/finance:idx/corporate-actions",
                {"code": "BBCA", "from": "2025-05", "to": "2026-04", "type": family, "page": page, "limit": 1},
                f"pagination:combined:{family}:page{page}",
            )
            has_more = row.get("has_more") is True or str(row.get("has_more")).lower() == "true"
            if not has_more:
                audit.call(
                    "/v1/finance:idx/corporate-actions",
                    {"code": "BBCA", "from": "2025-05", "to": "2026-04", "type": family, "page": page + 1, "limit": 1},
                    f"pagination:combined:{family}:after_final",
                )
                break
            page += 1

    for year, month, ticker in (
        (2023, 1, "SMDR"),
        (2021, 9, "DIVA"),
        (2023, 5, "TMAS"),
        (2023, 5, "TUGU"),
        (2023, 4, "BMRI"),
        (2023, 1, "SKRN"),
        (2026, 7, "BBCA"),
        (2022, 2, "BBRM"),
        (2025, 12, "GMFI"),
    ):
        audit.call(
            "/v1/finance:idx/stock-splits",
            {"year": year, "month": month, "page": 1, "length": 200, "search": ticker},
            f"transition:stock-splits:{ticker}:{year:04d}-{month:02d}",
        )

    for ticker in ("INDF", "SMDR", "DIVA", "TMAS", "TUGU", "BMRI", "BBRM", "SKRN"):
        audit.call(
            "/v1/finance:idx/issued-history",
            {"code": ticker, "page": 1, "limit": 500},
            f"identity:issued-history:{ticker}",
        )

    for ticker, window in (("BMRI", ("2023-04", "2023-04")), ("BBRM", ("2022-02", "2022-03")), ("SKRN", ("2023-01", "2023-02")), ("SMDR", ("2023-01", "2023-02")), ("DIVA", ("2021-09", "2021-10")), ("TMAS", ("2023-05", "2023-06")), ("TUGU", ("2023-05", "2023-06"))):
        audit.call(
            "/v1/finance:idx/corporate-actions",
            {"code": ticker, "from": window[0], "to": window[1], "page": 1, "limit": 200},
            f"transition:combined-control:{ticker}",
        )

    error_cases = (
        ("error:combined:over_12_months", "/v1/finance:idx/corporate-actions", {"code": "BBCA", "from": "2024-01", "to": "2025-01", "type": "dividend", "page": 1, "limit": 50}),
        ("error:combined:from_after_to", "/v1/finance:idx/corporate-actions", {"code": "BBCA", "from": "2026-04", "to": "2025-05", "type": "dividend", "page": 1, "limit": 50}),
        ("error:combined:invalid_month", "/v1/finance:idx/corporate-actions", {"code": "BBCA", "from": "2025-13", "to": "2026-01", "type": "dividend", "page": 1, "limit": 50}),
        ("error:combined:unsupported_type", "/v1/finance:idx/corporate-actions", {"code": "BBCA", "from": "2025-05", "to": "2026-04", "type": "stock-split", "page": 1, "limit": 50}),
        ("error:combined:unknown_code", "/v1/finance:idx/corporate-actions", {"code": "ZZZZ", "from": "2025-05", "to": "2026-04", "type": "dividend", "page": 1, "limit": 50}),
        ("error:combined:malformed_code", "/v1/finance:idx/corporate-actions", {"code": "!!!", "from": "2025-05", "to": "2026-04", "type": "dividend", "page": 1, "limit": 50}),
        ("error:combined:page_beyond_final", "/v1/finance:idx/corporate-actions", {"code": "BBCA", "from": "2025-05", "to": "2026-04", "type": "dividend", "page": 999, "limit": 50}),
        ("error:individual:invalid_month", "/v1/finance:idx/dividends", {"year": 2025, "month": 13, "page": 1, "length": 20, "search": "BBCA"}),
        ("error:individual:page_beyond_final", "/v1/finance:idx/dividends", {"year": 2025, "month": 12, "page": 999, "length": 20, "search": "BBCA"}),
        ("error:issued:page_beyond_final", "/v1/finance:idx/issued-history", {"code": "INDF", "page": 999, "limit": 500}),
    )
    for purpose, endpoint, params in error_cases:
        audit.call(endpoint, params, purpose)


def run_repeatability(audit: Audit) -> None:
    probes = (
        (
            "combined_bbca_dividend",
            "/v1/finance:idx/corporate-actions",
            {"code": "BBCA", "from": "2025-05", "to": "2026-04", "type": "dividend", "page": 1, "limit": 50},
        ),
        (
            "individual_bbca_dividend_2025_12",
            "/v1/finance:idx/dividends",
            {"year": 2025, "month": 12, "page": 1, "length": 200, "search": "BBCA"},
        ),
        (
            "issued_history_bmri",
            "/v1/finance:idx/issued-history",
            {"code": "BMRI", "page": 1, "limit": 500},
        ),
        (
            "unknown_code_zzzz",
            "/v1/finance:idx/corporate-actions",
            {"code": "ZZZZ", "from": "2025-05", "to": "2026-04", "type": "dividend", "page": 1, "limit": 50},
        ),
        (
            "stock_splits_smdr",
            "/v1/finance:idx/stock-splits",
            {"year": 2023, "month": 1, "page": 1, "length": 200, "search": "SMDR"},
        ),
    )
    for label, endpoint, params in probes:
        for attempt in range(1, 4):
            audit.call(
                endpoint,
                params,
                f"repeatability:{label}:attempt{attempt}",
                force=True,
            )


def run_transition_retries(audit: Audit) -> None:
    for year, month, ticker in (
        (2023, 1, "SMDR"),
        (2021, 9, "DIVA"),
        (2023, 5, "TMAS"),
        (2023, 5, "TUGU"),
        (2023, 4, "BMRI"),
        (2023, 1, "SKRN"),
        (2026, 7, "BBCA"),
        (2022, 2, "BBRM"),
        (2025, 12, "GMFI"),
    ):
        audit.call(
            "/v1/finance:idx/stock-splits",
            {"year": year, "month": month, "page": 1, "length": 200, "search": ticker},
            f"transition:stock-splits:{ticker}:retry1",
            force=True,
        )
    for ticker in ("INDF", "SMDR"):
        audit.call(
            "/v1/finance:idx/issued-history",
            {"code": ticker, "page": 1, "limit": 500},
            f"identity:issued-history:{ticker}:retry1",
            force=True,
        )


def build_tables(audit: Audit) -> dict[str, object]:
    endpoint_rows: dict[str, dict[str, object]] = {}
    for row in audit.rows:
        endpoint = str(row["endpoint"])
        target = endpoint_rows.setdefault(
            endpoint,
            {
                "endpoint": endpoint,
                "calls": 0,
                "statuses": set(),
                "top_level_keys": set(),
                "observed_fields": set(),
                "coverage_metadata_calls": 0,
                "complete_true": 0,
                "complete_false": 0,
                "stable_id_calls": 0,
                "source_values": set(),
            },
        )
        target["calls"] = int(target["calls"]) + 1
        target["statuses"].add(str(row["http_status"]))
        target["top_level_keys"].update(filter(None, str(row["top_level_keys"]).split(",")))
        target["observed_fields"].update(
            key
            for key in ("total", "count", "page", "limit", "length", "has_more", "next_page", "coverage_start", "coverage_end", "coverage_key", "complete_for_query", "source", "segments_answered", "segments_requested", "unpublished_months")
            if row.get(key, "") != ""
        )
        if row.get("coverage_start", "") != "" or row.get("coverage_end", "") != "":
            target["coverage_metadata_calls"] = int(target["coverage_metadata_calls"]) + 1
        if row.get("complete_for_query") is True or str(row.get("complete_for_query")).lower() == "true":
            target["complete_true"] = int(target["complete_true"]) + 1
        if row.get("complete_for_query") is False or str(row.get("complete_for_query")).lower() == "false":
            target["complete_false"] = int(target["complete_false"]) + 1
        if row.get("item_identity_quality") == "STABLE_ID":
            target["stable_id_calls"] = int(target["stable_id_calls"]) + 1
        if row.get("source", "") != "":
            target["source_values"].add(str(row["source"]))
    endpoint_matrix = []
    for endpoint in sorted(endpoint_rows):
        row = endpoint_rows[endpoint]
        endpoint_matrix.append(
            {
                "endpoint": endpoint,
                "calls": row["calls"],
                "http_statuses": "|".join(sorted(row["statuses"])),
                "top_level_keys": "|".join(sorted(row["top_level_keys"])),
                "observed_fields": "|".join(sorted(row["observed_fields"])),
                "coverage_metadata_calls": row["coverage_metadata_calls"],
                "complete_true_calls": row["complete_true"],
                "complete_false_calls": row["complete_false"],
                "stable_id_calls": row["stable_id_calls"],
                "source_values": "|".join(sorted(row["source_values"])),
                "docs_url": DOCS_URL,
            }
        )
    write_csv(
        "endpoint_capability_matrix.csv",
        endpoint_matrix,
        ["endpoint", "calls", "http_statuses", "top_level_keys", "observed_fields", "coverage_metadata_calls", "complete_true_calls", "complete_false_calls", "stable_id_calls", "source_values", "docs_url"],
    )

    pagination_rows = []
    for row in records_for(audit, "pagination:"):
        pagination_rows.append(
            {
                "request_id": row["request_id"],
                "purpose": row["purpose"],
                "endpoint": row["endpoint"],
                "query": row["query"],
                "http_status": row["http_status"],
                "record_count": row["record_count"],
                "total": row["total"],
                "page": row["page"],
                "limit": row["limit"],
                "has_more": row["has_more"],
                "next_page": row["next_page"],
                "complete_for_query": row["complete_for_query"],
                "item_id_values": row["item_id_values"],
                "response_sha256": row["response_sha256"],
            }
        )
    write_csv("pagination_audit.csv", pagination_rows, list(pagination_rows[0]) if pagination_rows else ["request_id"])

    window_rows = []
    for family in FAMILIES:
        full = audit.by_key.get(
            f"/v1/finance:idx/corporate-actions?code=BBCA&from=2025-05&limit=200&page=1&to=2026-04&type={family}"
        )
        first = audit.by_key.get(
            f"/v1/finance:idx/corporate-actions?code=BBCA&from=2025-05&limit=200&page=1&to=2025-10&type={family}"
        )
        second = audit.by_key.get(
            f"/v1/finance:idx/corporate-actions?code=BBCA&from=2025-11&limit=200&page=1&to=2026-04&type={family}"
        )
        if not (full and first and second):
            continue
        union = item_hash_set(first, ("type", "date")) | item_hash_set(second, ("type", "date"))
        broad = item_hash_set(full, ("type", "date"))
        window_rows.append(
            {
                "family": family,
                "broad_request_id": full["request_id"],
                "first_half_request_id": first["request_id"],
                "second_half_request_id": second["request_id"],
                "broad_count": full["record_count"],
                "partition_union_count": len(union),
                "event_hash_set_equal": broad == union,
                "broad_coverage": f"{full['coverage_start']}..{full['coverage_end']}",
                "first_coverage": f"{first['coverage_start']}..{first['coverage_end']}",
                "second_coverage": f"{second['coverage_start']}..{second['coverage_end']}",
                "coverage_key_consistent": first.get("coverage_key") == second.get("coverage_key") == full.get("coverage_key"),
                "complete_consistent": first.get("complete_for_query") == second.get("complete_for_query") == full.get("complete_for_query"),
                "identity_quality": full["item_identity_quality"],
            }
        )
    write_csv("window_partition_audit.csv", window_rows, list(window_rows[0]) if window_rows else ["family"])

    combined_rows = []
    for family in FAMILIES:
        combined = audit.by_key.get(
            f"/v1/finance:idx/corporate-actions?code=BBCA&from=2025-05&limit=200&page=1&to=2026-04&type={family}"
        )
        monthly = [
            row
            for row in audit.rows
            if str(row["purpose"]).startswith(f"individual:full:{family}:")
        ]
        monthly_hashes: set[str] = set()
        for row in monthly:
            monthly_hashes |= item_hash_set(row, ("type", "date"))
        combined_hashes = item_hash_set(combined, ("type", "date")) if combined else set()
        combined_rows.append(
            {
                "family": family,
                "combined_request_id": combined["request_id"] if combined else "",
                "monthly_request_count": len(monthly),
                "combined_count": combined["record_count"] if combined else "",
                "monthly_union_count": len(monthly_hashes),
                "normalized_event_hash_set_equal": bool(combined and combined_hashes == monthly_hashes),
                "combined_identity_quality": combined["item_identity_quality"] if combined else "",
                "monthly_stable_id_calls": sum(row["item_identity_quality"] == "STABLE_ID" for row in monthly),
                "interpretation": "comparison uses row-hash fallback when no stable event ID is exposed",
            }
        )
    write_csv("combined_vs_individual_audit.csv", combined_rows, list(combined_rows[0]) if combined_rows else ["family"])

    empty_rows = []
    for row in audit.rows:
        if int(row["record_count"] or 0) == 0:
            status = int(row["http_status"] or 0)
            try:
                total = int(row["total"])
            except (TypeError, ValueError):
                total = None
            if status != 200:
                empty_semantics = "HTTP_ERROR_OR_UNAVAILABLE_NOT_EMPTY_RESULT"
            elif total is not None and total > 0:
                empty_semantics = "PAGE_EMPTY_WITH_NONZERO_TOTAL_NOT_NO_EVENT"
            elif str(row.get("complete_for_query", "")).lower() == "false":
                empty_semantics = "DECLARED_INCOMPLETE_COVERAGE_NOT_NO_EVENT"
            else:
                empty_semantics = "NO_MATCH_IN_ZAPI_SOURCE_SCOPE_ONLY"
            empty_rows.append(
                {
                    "request_id": row["request_id"],
                    "purpose": row["purpose"],
                    "endpoint": row["endpoint"],
                    "query": row["query"],
                    "http_status": row["http_status"],
                    "total": row["total"],
                    "has_more": row["has_more"],
                    "coverage_start": row["coverage_start"],
                    "coverage_end": row["coverage_end"],
                    "coverage_key": row["coverage_key"],
                    "complete_for_query": row["complete_for_query"],
                    "source": row["source"],
                    "empty_semantics": empty_semantics,
                    "interpretation": "empty items are never real-world no-event authority",
                }
            )
    write_csv("empty_result_audit.csv", empty_rows, list(empty_rows[0]) if empty_rows else ["request_id"])

    coverage_rows = []
    for row in audit.rows:
        status = int(row["http_status"] or 0)
        try:
            total = int(row["total"])
        except (TypeError, ValueError):
            total = None
        if status != 200:
            semantic_observation = "HTTP_ERROR_OR_UNAVAILABLE_NOT_COVERAGE_EVIDENCE"
        elif str(row.get("complete_for_query", "")).lower() == "false":
            semantic_observation = "DECLARED_INCOMPLETE_COVERAGE; empty is not negative authority"
        elif total is not None and total > 0 and int(row["record_count"] or 0) == 0:
            semantic_observation = "PAGE_EMPTY_WITH_NONZERO_TOTAL; pagination probe only"
        elif total == 0:
            semantic_observation = "DECLARED_QUERY_SCOPE_EMPTY; not real-world no-event authority"
        else:
            semantic_observation = "DECLARED_QUERY_SCOPE_RESPONSE; field meaning remains contract-dependent"
        coverage_rows.append(
            {
                "request_id": row["request_id"],
                "purpose": row["purpose"],
                "endpoint": row["endpoint"],
                "query": row["query"],
                "coverage_start": row["coverage_start"],
                "coverage_end": row["coverage_end"],
                "coverage_key": row["coverage_key"],
                "complete_for_query": row["complete_for_query"],
                "segments_answered": row["segments_answered"],
                "segments_requested": row["segments_requested"],
                "unpublished_months": row["unpublished_months"],
                "semantic_observation": semantic_observation,
            }
        )
    write_csv("coverage_semantics_audit.csv", coverage_rows, list(coverage_rows[0]) if coverage_rows else ["request_id"])

    identity_rows = []
    for row in records_for(audit, "identity:issued-history:") + records_for(audit, "transition:stock-splits:"):
        identity_rows.append(
            {
                "request_id": row["request_id"],
                "purpose": row["purpose"],
                "query": row["query"],
                "http_status": row["http_status"],
                "record_count": row["record_count"],
                "item_identity_quality": row["item_identity_quality"],
                "item_id_values": row["item_id_values"],
                "top_level_keys": row["top_level_keys"],
                "coverage_start": row["coverage_start"],
                "coverage_end": row["coverage_end"],
                "coverage_key": row["coverage_key"],
                "complete_for_query": row["complete_for_query"],
                "source": row["source"],
                "response_sha256": row["response_sha256"],
                "payload_sha256": row["payload_sha256"],
            }
        )
    write_csv("identity_history_audit.csv", identity_rows, list(identity_rows[0]) if identity_rows else ["request_id"])

    revision_rows = []
    revision_terms = ("revision", "correct", "amend", "cancel", "supersed", "replac", "version", "published", "effective")
    for row in audit.rows:
        found: set[str] = set()
        for item in values_from_row(row):
            if isinstance(item, dict):
                found.update(key for key in item if any(term in key.lower() for term in revision_terms))
        revision_rows.append(
            {
                "request_id": row["request_id"],
                "purpose": row["purpose"],
                "endpoint": row["endpoint"],
                "record_count": row["record_count"],
                "revision_like_fields": "|".join(sorted(found)),
                "stable_id_quality": row["item_identity_quality"],
                "repeatability_probe": "not_claimed_from_single retrieval",
                "verdict": "NOT_OBSERVED" if not found else "FIELD_OBSERVED_SEMANTICS_UNPROVEN",
            }
        )
    write_csv("revision_semantics_audit.csv", revision_rows, list(revision_rows[0]) if revision_rows else ["request_id"])

    transition_rows = []
    for row in records_for(audit, "transition:stock-splits:"):
        ticker = str(row["purpose"]).split(":")[2]
        items = values_from_row(row)
        date_fields = sorted({key for item in items for key in item if "date" in key.lower()})
        observed_dates = sorted({str(item.get(key)) for item in items for key in date_fields if item.get(key) not in (None, "")})
        action_codes = sorted({str(item.get("actionCode")) for item in items if item.get("actionCode") not in (None, "")})
        ratios = sorted({str(item.get("ratio")) for item in items if item.get("ratio") not in (None, "")})
        factors = sorted({str(item.get("priceAdjustmentFactor")) for item in items if item.get("priceAdjustmentFactor") not in (None, "")})
        accepted = CONTROL_TRANSITIONS.get(ticker)
        transition_rows.append(
            {
                "ticker": ticker,
                "event_family": "STOCK_SPLIT",
                "accepted_transition": accepted or "UNRESOLVED",
                "request_id": row["request_id"],
                "http_status": row["http_status"],
                "record_count": row["record_count"],
                "zapi_item_id_values": row["item_id_values"],
                "zapi_action_codes": "|".join(action_codes),
                "zapi_ratios": "|".join(ratios),
                "zapi_price_adjustment_factors": "|".join(factors),
                "zapi_date_fields": "|".join(date_fields),
                "zapi_observed_dates": "|".join(observed_dates),
                "source": row["source"],
                "complete_for_query": row["complete_for_query"],
                "coverage": f"{row['coverage_start']}..{row['coverage_end']}",
                "date_equals_accepted": bool(accepted and accepted in observed_dates),
                "availability_verdict": "UNAVAILABLE_503" if int(row["http_status"] or 0) != 200 else "CANDIDATE_ROW_AVAILABLE",
                "semantic_verdict": "DISCOVERY_ONLY_DATE_SEMANTICS_NOT_PROVEN",
            }
        )
    write_csv("transition_control_audit.csv", transition_rows, list(transition_rows[0]) if transition_rows else ["ticker"])

    repeatability_rows = []
    labels = sorted({
        str(row["purpose"]).split(":")[1]
        for row in audit.rows
        if str(row["purpose"]).startswith("repeatability:")
    })
    for label in labels:
        rows = [
            row
            for row in audit.rows
            if str(row["purpose"]).startswith(f"repeatability:{label}:")
        ]
        repeatability_rows.append(
            {
                "probe": label,
                "attempt_count": len(rows),
                "request_ids": "|".join(str(row["request_id"]) for row in rows),
                "http_statuses": "|".join(sorted({str(row["http_status"]) for row in rows})),
                "record_counts": "|".join(str(row["record_count"]) for row in rows),
                "raw_hash_unique_count": len({str(row["response_sha256"]) for row in rows}),
                "payload_hash_unique_count": len({str(row["payload_sha256"]) for row in rows}),
                "semantic_payload_equal": len({str(row["payload_sha256"]) for row in rows}) == 1,
                "interpretation": "identical normalized payloads show retrieval repeatability only; no revision-history authority",
            }
        )
    write_csv(
        "repeatability_audit.csv",
        repeatability_rows,
        list(repeatability_rows[0]) if repeatability_rows else ["probe"],
    )

    requirement_rows = [
        {"requirement": "explicit identity/session coverage", "old_status": "UNKNOWN", "new_status": "PARTIAL_QUERY_SCOPED", "evidence": "coverageStart/End plus completeForQuery observed on successful statistic queries; stock-splits has no coverage fields", "remaining_blocker": "no population-wide identity/session contract", "admission_impact": "BLOCKED"},
        {"requirement": "complete positive enumeration", "old_status": "UNKNOWN", "new_status": "PARTIAL_QUERY_SCOPED", "evidence": "combined endpoint returned segmentsAnswered/Requested and pagination totals; every returned item lacks stable event ID", "remaining_blocker": "scope is ZAPI query/source, not proven whole IDX population or stable snapshot", "admission_impact": "BLOCKED"},
        {"requirement": "exhaustive no-event semantics", "old_status": "UNKNOWN", "new_status": "PARTIAL_FAIL_CLOSED_ONLY", "evidence": "200 responses expose query-scoped empty totals; unknown/malformed codes also return completeForQuery=true empty", "remaining_blocker": "no semantic proof empty means real-world zero event; 503 and incomplete months remain non-negative", "admission_impact": "BLOCKED"},
        {"requirement": "PIT identity/listing/relisting", "old_status": "PARTIAL", "new_status": "PARTIAL", "evidence": "issued-history returns listingDate, action, shares, sharesAfter and completeForQuery", "remaining_blocker": "no PIT/as-known snapshot, active/inactive/relisting identity, or full historical coverage contract", "admission_impact": "BLOCKED"},
        {"requirement": "knowledge/as-of and observed-through", "old_status": "UNKNOWN", "new_status": "UNKNOWN", "evidence": "response timestamp is retrieval metadata only", "remaining_blocker": "no asOf/knownAt/vintage contract observed", "admission_impact": "BLOCKED"},
        {"requirement": "revision/correction/version lineage", "old_status": "UNKNOWN", "new_status": "UNKNOWN", "evidence": "three repeat probes produced stable normalized payloads but no version fields", "remaining_blocker": "repeatability is not revision/supersession lineage", "admission_impact": "BLOCKED"},
        {"requirement": "exact basis-changing transition", "old_status": "PARTIAL", "new_status": "PARTIAL_CANDIDATE_ONLY", "evidence": "stock-splits returns actionCode, ratio, factor, nominal values and listingDate; controls include date mismatches and DIVA duplicate dates", "remaining_blocker": "ZAPI listingDate is not proven first new-basis regular-market session and endpoint had transient 503", "admission_impact": "BLOCKED"},
        {"requirement": "immutable provenance binding", "old_status": "PARTIAL", "new_status": "PARTIAL", "evidence": "raw response bytes, headers and hashes retained; source labels observed", "remaining_blocker": "source labels are not immutable provider snapshot/version or source-document authority", "admission_impact": "BLOCKED"},
        {"requirement": "population-wide admission", "old_status": "BLOCKED", "new_status": "BLOCKED", "evidence": "material query-scope capability change only", "remaining_blocker": "population authority, PIT/as-of, revision, all-family coverage, and exact transition semantics", "admission_impact": "NO_ADMISSION"},
    ]
    write_csv("authority_requirement_reassessment.csv", requirement_rows, list(requirement_rows[0]))

    docs_rows = [
        {"capability": "combined corporate-actions", "old_retained_docs": "not present in prior retained contract", "current_public_docs": "documented with 12-month window, page/limit, completeForQuery, segmentsAnswered/Requested; one example requests six months but displays a twelve-month coverage response", "current_live_response": "see combined:full and pagination evidence", "provider_screenshot": "reported new endpoint", "final_interpretation": "material query-scope capability; authority level unproven and docs example needs clarification"},
        {"capability": "individual five family endpoints", "old_retained_docs": "coverage contract absent", "current_public_docs": "monthly page/length endpoints with coverage metadata", "current_live_response": "see individual:full evidence", "provider_screenshot": "coverage metadata reported", "final_interpretation": "operationally useful; source-scope semantics require validation"},
        {"capability": "stock-splits", "old_retained_docs": "not coverage-certified", "current_public_docs": "separate monthly endpoint; no documented coverage contract in page example", "current_live_response": "see transition:stock-splits evidence", "provider_screenshot": "not listed among coverage additions", "final_interpretation": "must remain separate and transition authority unproven"},
        {"capability": "issued-history", "old_retained_docs": "pagination/identity/completeness gap", "current_public_docs": "page/limit plus source/coverage/completeForQuery documented; example request/output code/action do not align", "current_live_response": "see identity:issued-history evidence", "provider_screenshot": "provider says fixed", "final_interpretation": "improved operational contract; PIT/revision identity not proven and docs example needs clarification"},
    ]
    write_csv("documentation_vs_live_matrix.csv", docs_rows, list(docs_rows[0]))

    stock_rows = [row for row in audit.rows if row["endpoint"].endswith("/stock-splits")]
    issued_retry_rows = [
        row for row in audit.rows if str(row["purpose"]).startswith("identity:issued-history:") and ":retry1" in str(row["purpose"])
    ]
    return {
        "request_count": len(audit.rows),
        "http_status_counts": {
            str(status): sum(str(row["http_status"]) == str(status) for row in audit.rows)
            for status in sorted({row["http_status"] for row in audit.rows}, key=str)
        },
        "endpoint_count": len(endpoint_rows),
        "empty_response_count": sum(int(row["record_count"] or 0) == 0 for row in audit.rows),
        "stable_id_response_count": sum(row["item_identity_quality"] == "STABLE_ID" for row in audit.rows),
        "complete_for_query_true_count": sum(str(row.get("complete_for_query")).lower() == "true" for row in audit.rows),
        "complete_for_query_false_count": sum(str(row.get("complete_for_query")).lower() == "false" for row in audit.rows),
        "stock_split_initial_503_count": sum(row["endpoint"].endswith("/stock-splits") and str(row["purpose"]).startswith("transition:stock-splits:") and ":retry1" not in str(row["purpose"]) and int(row["http_status"] or 0) == 503 for row in audit.rows),
        "stock_split_retry_200_count": sum(row in stock_rows and ":retry1" in str(row["purpose"]) and int(row["http_status"] or 0) == 200 for row in stock_rows),
        "issued_history_retry_200_count": sum(int(row["http_status"] or 0) == 200 for row in issued_retry_rows),
        "docs_url": DOCS_URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def write_summary_and_report(summary: dict[str, object]) -> None:
    summary.update(
        {
            "ZAPI_MATERIAL_CAPABILITY_CHANGE": "PROVEN_OPERATIONAL_CHANGE",
            "ZAPI_QUERY_SCOPE_COMPLETENESS": "PARTIAL_OR_PROVEN_ONLY_FOR_DECLARED_ZAPI_QUERY_SCOPE",
            "ZAPI_PAGINATION_COMPLETENESS": "AUDITED_PER_RESPONSE; SOURCE_CONTRACT_LEVEL_REMAINS_UNPROVEN",
            "ZAPI_EMPTY_RESULT_CONTRACT": "NO_MATCH_IN_ZAPI_SOURCE_SCOPE_ONLY",
            "ZAPI_SOURCE_SCOPE_NEGATIVE_AUTHORITY": "PARTIAL",
            "ZAPI_REAL_WORLD_NO_EVENT_AUTHORITY": "NOT_PROVEN",
            "ZAPI_POSITIVE_EVENT_ENUMERATION": "PARTIAL_QUERY_SCOPED",
            "ZAPI_STOCK_SPLIT_COVERAGE_AUTHORITY": "NOT_PROVEN",
            "ZAPI_RIGHTS_COVERAGE_AUTHORITY": "PARTIAL_QUERY_SCOPED",
            "ZAPI_IDENTITY_LISTING_AUTHORITY": "PARTIAL",
            "ZAPI_REVISION_AUTHORITY": "NOT_PROVEN",
            "ZAPI_HISTORICAL_ASOF_AUTHORITY": "NOT_PROVEN",
            "ZAPI_TRANSITION_AUTHORITY": "NOT_PROVEN",
            "ZAPI_POPULATION_AUTHORITY": "NOT_PROVEN",
            "INC001_HISTORICAL_ADMISSION_READINESS": "BLOCKED",
            "new_zapi_classification": "DISCOVERY_AND_QUERY_SCOPE_COMPLETENESS_AID_NOT_TRANSITION_OR_POPULATION_AUTHORITY",
            "contract_reassessment_classification": "3_MATERIAL_PARTIAL_CONTRACT_IMPROVEMENT_NOT_AUTHORITY_CLOSURE",
            "query_input_validation_finding": "UNKNOWN_AND_MALFORMED_CODES_RETURN_200_EMPTY_COMPLETE_TRUE",
            "pagination_empty_finding": "PAGE_BEYOND_FINAL_RETURNS_EMPTY_WITH_NONZERO_TOTAL",
            "stock_split_availability_finding": "INITIAL_503_THEN_SUCCESSFUL_200_RETRIES; 503_IS_NOT_EMPTY",
            "inc001_admission": "BLOCKED_ON_POPULATION_ASOF_REVISION_AND_TRANSITION_CONTRACT",
        }
    )
    (ARTIFACT_ROOT / "summary.json").write_text(stable_json(summary) + "\n", encoding="utf-8")
    report = f"""# ZAPI CA coverage-contract revalidation

Date: 2026-09-02 Asia/Jakarta

Artifact: `{ARTIFACT_ROOT}`

Audit branch: `audit/zapi-ca-coverage-contract-revalidation-v1`

Base SHA: `0f6132ce55568565745aa68400295da4cba04e27`

This report is generated from `{summary['request_count']}` authenticated GET requests. HTTP status counts are `{stable_json(summary['http_status_counts'])}`. Raw response bytes are retained under `raw/`; every raw file is hash-bound by `request_index.csv` and `MANIFEST.json`. The initial capture was re-parsed after identifying the live ZAPI envelope (`data` for successful payloads and `content` for errors); raw bytes were not overwritten.

## Decision

`NO-GO` for INC-001 historical admission. Classification: `3_MATERIAL_PARTIAL_CONTRACT_IMPROVEMENT_NOT_AUTHORITY_CLOSURE`.

ZAPI has materially changed from the retained old capability: a combined endpoint now answers five named families (`dividend`, `rights`, `additional-listing`, `delisting`, `new-listing`) over a maximum twelve-month window with page/limit and query coverage metadata; individual monthly endpoints expose similar query metadata; issued-history exposes listing-date bounds. This proves useful bounded query-scope behavior, not population-wide Corporate Action authority.

## Evidence findings

### Query completeness and empty results

- Successful combined responses expose `coverageStart`, `coverageEnd`, `segmentsRequested`, `segmentsAnswered`, `unpublishedMonths`, `completeForQuery`, `source`, `total`, `hasMore`, and `nextPage`.
- `completeForQuery=false` is live and paired with `unpublishedMonths` for selected queries (including 2025-10). Those responses are explicitly incomplete and cannot support a negative conclusion.
- Unknown `ZZZZ` and malformed `!!!` both returned HTTP 200 with `total=0`, `completeForQuery=true`, and `unpublishedMonths=[]`. The API therefore does not establish that the code was a valid known security before returning a green empty result.
- Page-beyond-final probes returned HTTP 200, `items=[]`, `completeForQuery=true`, but retained non-zero totals (`BBCA` dividend total 2; `INDF` issued-history total 32). An empty page is not an empty event set.
- HTTP 503 responses are provider unavailability, not empty results. Stock-splits returned 503 on the first nine control calls and then 200 on the retry set; this variability is itself an operational fail-closed requirement.

### Pagination, partitioning, and combined vs individual

BBCA dividend page traversal returned two rows over pages 1 and 2 with `hasMore=true` then `false`; the after-final page was empty while total remained 2. The five-family twelve-month window partition matched the broad query by normalized row hashes for the tested BBCA scope. The five combined-family results also matched the union of the twelve monthly individual queries for this tested scope. These are bounded consistency observations, not a provider-wide snapshot or revision guarantee.

No returned item exposed a stable event identifier. Comparisons therefore use normalized row hashes, which cannot prove identity continuity across revisions, pagination retrievals, corrections, deletions, or re-publication.

Stock-splits are not accepted by the combined endpoint (`stock-split` returns a 400 unknown-type error) and must remain a separate family. This alone prevents interpreting the combined endpoint as an all-family CA authority.

### Transition controls

The recovered stock-split rows are candidate evidence only and have no `source`, `coverageStart/End`, or `completeForQuery` fields:

- SMDR: `listingDate=2023-01-31`, ratio `1 : 5`, factor `0.2`; date agrees with the already resolved V17 transition but the API does not provide the accepted market-transition semantic.
- DIVA: two same-ratio rows at `2021-09-01` and `2021-09-02`; issued-history exposes only `2021-09-02`. This is a row/event identity ambiguity, not authority.
- TMAS and TUGU: API `listingDate` values are `2023-05-25` and `2023-05-26`, respectively, while the retained accepted first-new-basis sessions are `2023-05-23` and `2023-05-24`.
- BMRI: API `listingDate=2023-04-06`; issued-history also has a stock-split and partial-delisting row at `2023-04-04`, and V17 retains `2023-04-04` as the unresolved official transition control. The API date is not the accepted transition session.
- SKRN: API `listingDate=2023-01-06`, matching the candidate date, but V17 still marks the exact transition unresolved.
- BBRM: API reverse-split `listingDate=2022-02-18`, while the retained candidate is `2022-02-17`; the separate BBRM rights event remains resolved at ex-date `2022-02-24` and must not be conflated.
- BBCA and GMFI returned no rows for the tested month. This is a query-scope observation only.

Issued-history retries recovered INDF (32 rows) and SMDR (1 row) after initial 503s. Rows provide `listingDate`, action, shares, and sharesAfter, but no stable event ID, knowledge/as-of time, revision/version, active interval, or relisting identity. BMRI demonstrates same-date multiple actions; BBRM history returns an HMETD row at 2014-12-12 while the tested 2022 rights/split controls are represented through other routes. The endpoint is useful discovery evidence but not a complete transition or PIT identity authority.

### Revision, PIT, provenance, and documentation

Three repeat calls for combined BBCA dividend, individual BBCA December dividend, BMRI issued-history, unknown ZZZZ, and SMDR stock-splits produced identical normalized payload hashes. This shows short-run retrieval repeatability only; it does not establish immutable snapshot identity, historical as-of, correction/deletion lineage, or supersession semantics.

The live `source` labels (`idx-statistic`, `idx-listing-activity`) and retrieval timestamps are provenance hints. They are not a versioned source snapshot, source-document hash, correction policy, or authority attestation. The current public endpoint documentation is [ZAPI IDX documentation](https://zpi.web.id/api/finance/idx); its bounded query fields materially update the capability record but do not define the missing admission semantics.

The current documentation also contains two material example inconsistencies: a combined example requests `2025-11` through `2026-04` but displays `coverageStart=2025-05-01` and twelve months; an issued-history example requests `BBCA`/`Waran` but displays `INDF` rows for `Stock Split` and `ESOP`. These are documentation-contract uncertainties, not evidence of population completeness.

## Requirement reassessment

The CSV `authority_requirement_reassessment.csv` records each gap separately. Improved or partially supported requirements are query-scoped positive enumeration, per-response pagination mechanics, bounded coverage metadata, and candidate identity/listing history. Remaining blockers are population-wide coverage, exhaustive real-world no-event authority, PIT/as-of identity and relisting semantics, revision/correction lineage, stable event identity, all-family coverage, exact first-new-basis transition semantics, and immutable provider/source authority. INC-001 remains blocked; no V17 counts or runtime paths were changed.

See the per-request matrices, `repeatability_audit.csv`, and deterministic manifest for the complete evidence set.
"""
    (ARTIFACT_ROOT / "REPORT.md").write_text(report, encoding="utf-8")
    (ARTIFACT_ROOT / "README.md").write_text(
        "# ZAPI CA coverage revalidation\n\nRaw responses are immutable evidence captured by the repository audit script. Do not overwrite or reinterpret rows without a new audit root.\n",
        encoding="utf-8",
    )


def build_manifest() -> str:
    outputs: dict[str, dict[str, object]] = {}
    for path in sorted(ARTIFACT_ROOT.rglob("*")):
        if not path.is_file() or path.name == "MANIFEST.json":
            continue
        relative = str(path.relative_to(ARTIFACT_ROOT)).replace("\\", "/")
        raw = path.read_bytes()
        outputs[relative] = {"bytes": len(raw), "sha256": sha256(raw)}
    manifest = {
        "schema_version": "idx_ca_zapi_coverage_contract_revalidation_v1",
        "audit_date": "2026-09-02",
        "repository": "samindriano/idx-trade",
        "audit_branch": "audit/zapi-ca-coverage-contract-revalidation-v1",
        "base_sha": "0f6132ce55568565745aa68400295da4cba04e27",
        "provider": "ZAPI",
        "docs_url": DOCS_URL,
        "artifact_root": str(ARTIFACT_ROOT),
        "raw_policy": "immutable raw response bytes; secrets excluded",
        "output_hashes_excluding_manifest": outputs,
        "self_hash_policy": "MANIFEST.json excluded from own hash",
    }
    raw = stable_json(manifest) + "\n"
    encoded = raw.encode("utf-8")
    (ARTIFACT_ROOT / "MANIFEST.json").write_bytes(encoded)
    return sha256(encoded)


def main() -> int:
    rebuild_existing = len(sys.argv) == 2 and sys.argv[1] == "--rebuild-existing"
    append_repeatability = len(sys.argv) == 2 and sys.argv[1] == "--append-repeatability"
    append_transition_retries = len(sys.argv) == 2 and sys.argv[1] == "--append-transition-retries"
    if rebuild_existing or append_repeatability or append_transition_retries:
        audit = Audit.from_existing_artifact()
        if append_repeatability:
            if not os.environ.get("ZAPI_API_KEY"):
                raise RuntimeError("ZAPI_API_KEY is unavailable; no authenticated probe performed")
            run_repeatability(audit)
        if append_transition_retries:
            if not os.environ.get("ZAPI_API_KEY"):
                raise RuntimeError("ZAPI_API_KEY is unavailable; no authenticated probe performed")
            run_transition_retries(audit)
    else:
        ensure_new_artifact_root()
        if not os.environ.get("ZAPI_API_KEY"):
            raise RuntimeError("ZAPI_API_KEY is unavailable; no authenticated probe performed")
        audit = Audit()
        run_queries(audit)
    audit.save_request_index()
    summary = build_tables(audit)
    write_summary_and_report(summary)
    manifest_sha = build_manifest()
    print(f"AUDIT_ROOT={ARTIFACT_ROOT}")
    print(f"REQUESTS={len(audit.rows)}")
    print(f"MANIFEST_SHA256={manifest_sha}")
    print("AUDIT_STATUS=COMPLETE_DATA_CAPTURED_REVIEW_PENDING")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"AUDIT_ERROR={type(exc).__name__}:{exc}", file=sys.stderr)
        raise
