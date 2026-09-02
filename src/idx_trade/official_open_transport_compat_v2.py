"""Strict Official Open transport compatibility for the current ZAPI raw shape.

The accepted V1 evidence contract historically observed a gateway envelope with
``project``/``timestamp`` and the IDX raw payload nested under ``data``.  The
same ``finance:idx/raw`` endpoint may now return that raw IDX payload directly
at the top level.  This adapter accepts exactly those two provenance shapes and
keeps the underlying authority/path/session/count/field semantics unchanged.

It does not relax normalization, execution admission, archive immutability, or
any model/paper/outcome boundary.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator, Mapping

import requests

from . import official_open_evidence_v1 as v1


TOP_LEVEL_RAW_ENVELOPE = "top_level_idx_raw"
LEGACY_PROJECT_ENVELOPE = "legacy_project_data"
_ORIGINAL_ZAPI_INNER_PAYLOAD = v1._zapi_inner_payload


def _strict_zapi_payload(payload: Mapping[str, object]) -> tuple[dict[str, object], str]:
    """Return the exact IDX raw object and its admitted gateway shape."""

    if "project" in payload:
        # Preserve the accepted legacy envelope contract byte-for-byte in
        # semantics: exact project marker, timestamp, and nested object.
        inner = _ORIGINAL_ZAPI_INNER_PAYLOAD(payload)
        envelope = LEGACY_PROJECT_ENVELOPE
    else:
        # Project-less responses are admitted only when they are already the
        # exact IDX raw passthrough object.  A different wrapper cannot become
        # authoritative merely by omitting ``project``.
        inner = dict(payload)
        envelope = TOP_LEVEL_RAW_ENVELOPE

    if inner.get("provider") != "idx":
        raise v1.OfficialOpenEvidenceError("OFFICIAL_OPEN_ZAPI_RAW_PROVIDER_MISMATCH")
    if inner.get("path") != v1.UPSTREAM_PATH:
        raise v1.OfficialOpenEvidenceError("OFFICIAL_OPEN_ZAPI_RAW_PATH_MISMATCH")
    if not isinstance(inner.get("data"), list):
        raise v1.OfficialOpenEvidenceError("OFFICIAL_OPEN_ZAPI_RAW_DATA_MISSING")
    return inner, envelope


def _zapi_inner_payload_v2(payload: Mapping[str, object]) -> dict[str, object]:
    inner, _ = _strict_zapi_payload(payload)
    return inner


def validate_zapi_raw_provenance_v2(raw_bytes: bytes) -> str:
    payload = v1._json_object(raw_bytes)
    _, envelope = _strict_zapi_payload(payload)
    return envelope


def fetch_zapi_raw_idx_stock_summary_v2(
    session_date: str,
    *,
    api_key: str,
    get: Callable[..., requests.Response] = requests.get,
    timeout_seconds: float = 30.0,
) -> tuple[bytes, dict[str, object]]:
    """Fetch current ZAPI raw bytes with strict dual-shape provenance proof."""

    if not api_key:
        raise v1.OfficialOpenEvidenceError("OFFICIAL_OPEN_ZAPI_API_KEY_MISSING")
    session = v1._session(session_date)
    upstream_query = f"date={session.replace('-', '')}&start=0&length=9999"
    params = {"path": v1.UPSTREAM_PATH, "query": upstream_query}
    try:
        response = get(
            v1.ZAPI_RAW_URL,
            params=params,
            headers={"x-api-key": api_key, "Accept": "application/json"},
            timeout=timeout_seconds,
        )
    except requests.RequestException as exc:
        raise v1.OfficialOpenEvidenceError(
            f"OFFICIAL_OPEN_ZAPI_RAW_REQUEST_ERROR:{v1._request_error_detail(exc)}"
        ) from exc
    if response.status_code != 200:
        raise v1.OfficialOpenEvidenceError(
            f"OFFICIAL_OPEN_ZAPI_RAW_HTTP_{response.status_code}"
        )
    raw = bytes(response.content)
    if not raw:
        raise v1.OfficialOpenEvidenceError("OFFICIAL_OPEN_ZAPI_RAW_EMPTY_RESPONSE")
    envelope = validate_zapi_raw_provenance_v2(raw)
    return raw, {
        "transport": v1.ZAPI_RAW_TRANSPORT,
        "url": v1.ZAPI_RAW_URL,
        "upstream_path": v1.UPSTREAM_PATH,
        "request_params": {"path": v1.UPSTREAM_PATH, "query": upstream_query},
        "http_status": int(response.status_code),
        "provider": "idx",
        "response_envelope": envelope,
    }


@contextmanager
def _patched_zapi_transport() -> Iterator[None]:
    original_fetch = v1.fetch_zapi_raw_idx_stock_summary
    original_inner = v1._zapi_inner_payload
    v1.fetch_zapi_raw_idx_stock_summary = fetch_zapi_raw_idx_stock_summary_v2
    v1._zapi_inner_payload = _zapi_inner_payload_v2
    try:
        yield
    finally:
        v1.fetch_zapi_raw_idx_stock_summary = original_fetch
        v1._zapi_inner_payload = original_inner


def capture_official_open_with_transport_fallback_v2(
    session_date: str,
    *,
    output_root,
    zapi_api_key: str | None,
    direct_get=None,
    zapi_get=None,
    timeout_seconds: float = 30.0,
):
    """Run accepted V1 fallback/certification with strict ZAPI compatibility."""

    # Certification revalidates the same immutable raw bytes after the fetch.
    # Keep both V1 dynamic lookups patched for the complete single capture, then
    # restore them even when any transport/certification guard fails.
    with _patched_zapi_transport():
        return v1.capture_official_open_with_transport_fallback(
            session_date,
            output_root=output_root,
            zapi_api_key=zapi_api_key,
            direct_get=direct_get,
            zapi_get=zapi_get,
            timeout_seconds=timeout_seconds,
        )


__all__ = [
    "LEGACY_PROJECT_ENVELOPE",
    "TOP_LEVEL_RAW_ENVELOPE",
    "capture_official_open_with_transport_fallback_v2",
    "fetch_zapi_raw_idx_stock_summary_v2",
    "validate_zapi_raw_provenance_v2",
]
