from __future__ import annotations

from dataclasses import replace

import pytest

from idx_trade.providers.ksei_ownership import (
    fetch_holding_composition_zip,
    holding_composition_url,
)


class _Response:
    def __init__(self, content: bytes) -> None:
        self.status_code = 200
        self.url = "https://web.ksei.co.id/Download/BalanceposEfek20260227.zip"
        self.content = content

    def raise_for_status(self) -> None:
        return None


class _Session:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def get(self, *args: object, **kwargs: object) -> _Response:
        self.calls.append((args, kwargs))
        return self.response


def test_holding_composition_url_uses_embedded_snapshot_date() -> None:
    assert holding_composition_url("2026-02-27").endswith(
        "BalanceposEfek20260227.zip"
    )


def test_holding_composition_capture_preserves_zip_bytes_and_hash() -> None:
    session = _Session(_Response(b"PK\x03\x04fakezip"))
    capture = fetch_holding_composition_zip("2026-02-27", session=session)
    assert capture.snapshot_date == "2026-02-27"
    assert capture.raw_bytes == b"PK\x03\x04fakezip"
    assert len(capture.raw_sha256) == 64
    assert len(session.calls) == 1


def test_holding_composition_rejects_non_zip_response() -> None:
    session = _Session(_Response(b"<html>blocked</html>"))
    with pytest.raises(ValueError, match="not a ZIP"):
        fetch_holding_composition_zip("2026-02-27", session=session)
