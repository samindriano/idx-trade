from __future__ import annotations

from scripts.capture_historical_dividend_corpus_batch_v1 import (
    RETRYABLE_STATUS,
    classify_failure,
)


def test_only_bounded_transport_statuses_are_retryable() -> None:
    assert RETRYABLE_STATUS == {403, 429, 500, 502, 503, 504}
    assert classify_failure(403, "HTTP_403") == "HTTP_403"
    assert classify_failure(404, "HTTP_404") == "HTTP_404"
    assert classify_failure(None, "timeout") == "TRANSPORT_ERROR"
