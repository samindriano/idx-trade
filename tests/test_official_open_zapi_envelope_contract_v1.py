import json

import pytest

from idx_trade.official_open_evidence_v1 import (
    UPSTREAM_PATH,
    ZAPI_PROJECT,
    ZAPI_RAW_TRANSPORT,
    OfficialOpenEvidenceError,
    validate_transport_provenance,
)


def _envelope(*, project=ZAPI_PROJECT, include_timestamp=True, timestamp="2026-08-22T00:00:00Z"):
    payload = {
        "project": project,
        "data": {
            "provider": "idx",
            "path": UPSTREAM_PATH,
            "recordsTotal": 0,
            "recordsFiltered": 0,
            "data": [],
        },
    }
    if include_timestamp:
        payload["timestamp"] = timestamp
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def test_zapi_envelope_requires_expected_project_marker():
    with pytest.raises(OfficialOpenEvidenceError, match="ZAPI_RAW_PROJECT_MISMATCH"):
        validate_transport_provenance(
            _envelope(project="finance:other"), transport=ZAPI_RAW_TRANSPORT
        )


def test_zapi_envelope_requires_timestamp_marker():
    with pytest.raises(OfficialOpenEvidenceError, match="ZAPI_RAW_TIMESTAMP_MISSING"):
        validate_transport_provenance(
            _envelope(include_timestamp=False), transport=ZAPI_RAW_TRANSPORT
        )
    with pytest.raises(OfficialOpenEvidenceError, match="ZAPI_RAW_TIMESTAMP_MISSING"):
        validate_transport_provenance(
            _envelope(timestamp=""), transport=ZAPI_RAW_TRANSPORT
        )


def test_zapi_envelope_accepts_observed_gateway_markers():
    validate_transport_provenance(_envelope(), transport=ZAPI_RAW_TRANSPORT)
