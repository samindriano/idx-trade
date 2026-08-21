from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_uses_catalog_search_as_server_ticker_filter():
    probe = _load_script("probe_zapi_idx_dividends_v1", "probe_zapi_idx_dividends_v1.py")

    params, scope = probe._select_params(
        [
            {"name": "search"},
            {"name": "page"},
            {"name": "length"},
        ],
        "BBCA",
    )

    assert scope == "SERVER_TICKER_FILTER"
    assert params == {"search": "BBCA", "page": 1, "length": 20}


def test_probe_forwards_explicit_known_positive_year_month():
    probe = _load_script("probe_zapi_idx_dividends_period_v1", "probe_zapi_idx_dividends_v1.py")

    params, scope = probe._select_params(
        [
            {"name": "year"},
            {"name": "month"},
            {"name": "search"},
            {"name": "page"},
            {"name": "length"},
        ],
        "BBCA",
        year=2026,
        month=3,
    )

    assert scope == "SERVER_TICKER_FILTER"
    assert params == {
        "search": "BBCA",
        "page": 1,
        "length": 20,
        "year": 2026,
        "month": 3,
    }


def test_probe_rejects_half_specified_period():
    probe = _load_script("probe_zapi_idx_dividends_bad_period_v1", "probe_zapi_idx_dividends_v1.py")

    try:
        probe._select_params(
            [
                {"name": "year"},
                {"name": "month"},
                {"name": "search"},
                {"name": "page"},
                {"name": "length"},
            ],
            "BBCA",
            year=2026,
        )
    except RuntimeError as exc:
        assert str(exc) == "ZAPI_DIVIDENDS_EXPLICIT_PERIOD_REQUIRES_YEAR_AND_MONTH"
    else:
        raise AssertionError("half-specified explicit period must fail closed")


def test_reviewer_unwraps_data_envelope_and_exposes_nested_metadata():
    reviewer = _load_script("review_zapi_idx_dividends_probe_v1", "review_zapi_idx_dividends_probe_v1.py")
    payload = {
        "project": "finance:idx:dividends",
        "data": {
            "provider": "idx",
            "dataset": "dividends",
            "page": 1,
            "nextPage": None,
            "count": 0,
            "total": 0,
            "hasMore": False,
            "items": [],
        },
    }

    core = reviewer._unwrap(payload)
    assert core["provider"] == "idx"
    assert core["dataset"] == "dividends"
    assert core["total"] == 0
    assert core["nextPage"] is None
    assert core["hasMore"] is False
    assert core["items"] == []
