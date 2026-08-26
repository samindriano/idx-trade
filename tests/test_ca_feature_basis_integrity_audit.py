from __future__ import annotations

from scripts.run_ca_feature_basis_integrity_audit_v1 import (
    build_spillover_summary,
    parse_bool,
)


def test_spillover_summary_is_identity_only_and_deterministic() -> None:
    rows = [
        {
            "head": "H5",
            "ticker": "AAPL",
            "date": "2022-01-03",
            "direct_or_spillover": "DIRECT",
        },
        {
            "head": "H5",
            "ticker": "BBCA",
            "date": "2022-01-03",
            "direct_or_spillover": "SPILLOVER",
        },
    ]
    summary = build_spillover_summary(rows)
    assert summary == [
        {
            "head": "H5",
            "scope": "DIRECT",
            "changed_rows": 1,
            "changed_tickers": 1,
            "changed_dates": 1,
            "source": "v1.2 exact-fit support-only reconstruction",
        },
        {
            "head": "H5",
            "scope": "SPILLOVER",
            "changed_rows": 1,
            "changed_tickers": 1,
            "changed_dates": 1,
            "source": "v1.2 exact-fit support-only reconstruction",
        },
        {
            "head": "UNION",
            "scope": "DIRECT",
            "changed_rows": 1,
            "changed_tickers": 1,
            "changed_dates": 1,
            "source": "v1.2 exact-fit support-only reconstruction",
        },
        {
            "head": "UNION",
            "scope": "SPILLOVER",
            "changed_rows": 1,
            "changed_tickers": 1,
            "changed_dates": 1,
            "source": "v1.2 exact-fit support-only reconstruction",
        },
    ]
    assert all("outcome" not in key.lower() for item in summary for key in item)


def test_parse_bool_fails_closed() -> None:
    assert parse_bool("true", field="guard") is True
    assert parse_bool("FALSE", field="guard") is False
