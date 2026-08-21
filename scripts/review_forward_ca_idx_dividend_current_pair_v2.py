from __future__ import annotations

import argparse
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

SCHEMA = "idx_trade_forward_ca_direct_idx_dividend_current_pair_probe_v2"
REVIEW_SCHEMA = "idx_trade_forward_ca_direct_idx_dividend_current_pair_review_v2"
EXPECTED_PROVIDER = "nichsedge/idx-bei"
EXPECTED_PROVIDER_COMMIT = "75d6c0f74fa360d225794c70c383348977de6798"
EXPECTED_UPSTREAM = "https://www.idx.co.id/primary"
EXPECTED_DIVIDEND_ENDPOINT = "/DigitalStatistic/GetApiDataPaginated"
EXPECTED_ANNOUNCEMENT_ENDPOINT = "/ListedCompany/GetAnnouncement"
EXPECTED_EVENT = {
    "ticker": "BBCA",
    "gross_dividend_per_share_idr": Decimal("25"),
    "cum_date": "2026-08-28",
    "ex_date": "2026-08-31",
    "recording_date": "2026-09-01",
    "payment_date": "2026-09-16",
    "announcement_date": "2026-08-19",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _decimal(value: Any) -> Decimal | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() else None


def _parse_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    for candidate in (text[:10], text):
        try:
            return date.fromisoformat(candidate).isoformat()
        except Exception:
            pass
    for fmt in ("%Y%m%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except Exception:
            pass
    return None


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


def _dates_in(value: Any) -> set[str]:
    result: set[str] = set()
    for text in _walk_strings(value):
        for pattern in (
            r"\b20\d{2}-\d{2}-\d{2}\b",
            r"\b\d{2}/\d{2}/20\d{2}\b",
            r"\b20\d{6}\b",
        ):
            for match in re.findall(pattern, text):
                parsed = _parse_date(match)
                if parsed:
                    result.add(parsed)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline review for direct IDX current dividend pair V2.")
    parser.add_argument("--probe-dir", required=True)
    args = parser.parse_args()

    root = Path(args.probe_dir).expanduser().resolve()
    manifest_path = root / "PROBE_MANIFEST.json"
    failures: list[str] = []
    warnings: list[str] = []

    if not manifest_path.is_file():
        raise SystemExit(f"manifest missing: {manifest_path}")
    manifest = _load(manifest_path)

    if manifest.get("schema_version") != SCHEMA:
        failures.append("MANIFEST_SCHEMA_MISMATCH")
    if manifest.get("status") != "COMPLETE_AWAITING_OFFLINE_REVIEW":
        failures.append("MANIFEST_STATUS_INVALID")
    if manifest.get("provider_repository") != EXPECTED_PROVIDER:
        failures.append("PROVIDER_REPOSITORY_MISMATCH")
    if manifest.get("provider_commit") != EXPECTED_PROVIDER_COMMIT:
        failures.append("PROVIDER_COMMIT_MISMATCH")
    if manifest.get("upstream_base_url") != EXPECTED_UPSTREAM:
        failures.append("UPSTREAM_MISMATCH")
    if manifest.get("target_code") != "BBCA":
        failures.append("TARGET_CODE_MISMATCH")
    if int(manifest.get("direct_idx_request_count") or 0) != 2:
        failures.append("DIRECT_IDX_REQUEST_COUNT_NOT_TWO")
    if int(manifest.get("retry_count") or 0) != 0:
        failures.append("RETRY_COUNT_NOT_ZERO")
    if manifest.get("request_policy") != "DIRECT_ONE_SHOT_NO_RETRY_HELPER":
        failures.append("REQUEST_POLICY_MISMATCH")

    artifacts = manifest.get("raw_artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 2:
        failures.append("RAW_ARTIFACT_COVERAGE_INVALID")
        artifacts = []

    by_name: dict[str, tuple[dict[str, Any], Any]] = {}
    for row in artifacts:
        if not isinstance(row, dict):
            failures.append("RAW_ARTIFACT_ROW_INVALID")
            continue
        name = str(row.get("name") or "")
        path = root / str(row.get("path") or "")
        if not path.is_file():
            failures.append(f"RAW_MISSING:{name}")
            continue
        if _sha256(path) != str(row.get("sha256") or ""):
            failures.append(f"RAW_SHA_MISMATCH:{name}")
            continue
        if int(row.get("http_status") or 0) != 200:
            failures.append(f"HTTP_STATUS_NOT_200:{name}")
        content_type = str(row.get("content_type") or "").lower()
        if content_type and "json" not in content_type:
            failures.append(f"CONTENT_TYPE_NOT_JSON:{name}")
        try:
            payload = _load(path)
        except Exception:
            failures.append(f"RAW_NOT_JSON:{name}")
            continue
        by_name[name] = (row, payload)

    dividend_match = False
    dividend_rows: list[dict[str, Any]] = []
    normalized_dividends: list[dict[str, Any]] = []
    if "dividend" not in by_name:
        failures.append("DIVIDEND_ARTIFACT_MISSING")
    else:
        row, payload = by_name["dividend"]
        if row.get("endpoint") != EXPECTED_DIVIDEND_ENDPOINT:
            failures.append("DIVIDEND_ENDPOINT_MISMATCH")
        expected_params = {
            "urlName": "LINK_DIVIDEND",
            "periodYear": 2026,
            "periodMonth": 8,
            "periodType": "monthly",
            "isPrint": "False",
            "cumulative": "false",
            "pageSize": 100,
            "pageNumber": 1,
            "orderBy": "",
            "search": "BBCA",
        }
        if row.get("params") != expected_params:
            failures.append("DIVIDEND_PARAMS_MISMATCH")
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            failures.append("DIVIDEND_DATA_NOT_LIST")
        else:
            dividend_rows = [x for x in data if isinstance(x, dict)]
            for item in dividend_rows:
                if str(item.get("code") or "").strip().upper() != "BBCA":
                    continue
                amount = _decimal(item.get("cashDividend"))
                normalized = {
                    "ticker": "BBCA",
                    "gross_dividend_per_share_idr": str(amount) if amount is not None else None,
                    "cum_date": _parse_date(item.get("cumDividend")),
                    "ex_date": _parse_date(item.get("exDividend")),
                    "recording_date": _parse_date(item.get("recordDate")),
                    "payment_date": _parse_date(item.get("paymentDate")),
                    "currency": item.get("currency"),
                    "note": item.get("note"),
                }
                normalized_dividends.append(normalized)
                if (
                    amount == EXPECTED_EVENT["gross_dividend_per_share_idr"]
                    and normalized["cum_date"] == EXPECTED_EVENT["cum_date"]
                    and normalized["ex_date"] == EXPECTED_EVENT["ex_date"]
                    and normalized["recording_date"] == EXPECTED_EVENT["recording_date"]
                    and normalized["payment_date"] == EXPECTED_EVENT["payment_date"]
                ):
                    dividend_match = True
        if not dividend_match:
            failures.append("CURRENT_BBCA_DIVIDEND_TERMS_NOT_FOUND")

    announcement_match = False
    announcement_candidates: list[dict[str, Any]] = []
    announcement_row_count = 0
    if "announcements" not in by_name:
        failures.append("ANNOUNCEMENT_ARTIFACT_MISSING")
    else:
        row, payload = by_name["announcements"]
        if row.get("endpoint") != EXPECTED_ANNOUNCEMENT_ENDPOINT:
            failures.append("ANNOUNCEMENT_ENDPOINT_MISMATCH")
        expected_params = {
            "kodeEmiten": "BBCA",
            "emitenType": "*",
            "indexFrom": 0,
            "pageSize": 100,
            "dateFrom": "20260818",
            "dateTo": "20260821",
            "lang": "id",
            "keyword": "",
        }
        if row.get("params") != expected_params:
            failures.append("ANNOUNCEMENT_PARAMS_MISMATCH")
        replies = payload.get("Replies") if isinstance(payload, dict) else None
        if not isinstance(replies, list):
            failures.append("ANNOUNCEMENT_REPLIES_NOT_LIST")
        else:
            announcement_row_count = len(replies)
            for item in replies:
                if not isinstance(item, dict):
                    continue
                strings = " ".join(_walk_strings(item)).lower()
                dates = sorted(_dates_in(item))
                is_dividend = "dividen" in strings or "dividend" in strings
                has_ticker = "bbca" in strings
                if is_dividend:
                    announcement_candidates.append(
                        {
                            "has_bbca_string": has_ticker,
                            "dates": dates,
                            "text_sample": strings[:600],
                        }
                    )
                if is_dividend and has_ticker and EXPECTED_EVENT["announcement_date"] in dates:
                    announcement_match = True
        if not announcement_match:
            failures.append("CURRENT_BBCA_DIVIDEND_ANNOUNCEMENT_NOT_FOUND")

    report = {
        "schema_version": REVIEW_SCHEMA,
        "status": "PASS_DIRECT_IDX_CURRENT_DIVIDEND_PAIR_V2_ELIGIBLE_FOR_V1_1" if not failures else "FAIL_DIRECT_IDX_CURRENT_DIVIDEND_PAIR_V2_NOT_ADMITTED",
        "provider_repository": manifest.get("provider_repository"),
        "provider_commit": manifest.get("provider_commit"),
        "upstream_base_url": manifest.get("upstream_base_url"),
        "expected_event": {
            k: (str(v) if isinstance(v, Decimal) else v) for k, v in EXPECTED_EVENT.items()
        },
        "dividend_row_count": len(dividend_rows),
        "normalized_bbca_dividends": normalized_dividends,
        "dividend_terms_match": dividend_match,
        "announcement_row_count": announcement_row_count,
        "announcement_candidates": announcement_candidates,
        "announcement_match": announcement_match,
        "failures": failures,
        "warnings": warnings,
        "v1_1_direct_idx_dividend_authority_recommendation": not failures,
        "zapi_required": False,
    }
    output = root / "PROBE_REVIEW.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
