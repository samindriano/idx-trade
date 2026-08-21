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


def test_company_profile_semantic_rows_extract_complete_dividend():
    reviewer = _load_script(
        "review_zapi_idx_company_profile_dividends_v1",
        "review_zapi_idx_company_profile_dividends_v1.py",
    )
    core = {
        "code": "BBCA",
        "provider": "idx",
        "dataset": "company-profile",
        "dividends": [
            {
                "type": "dti",
                "cashPerShare": 20,
                "cumDate": "2026-06-15",
                "exDate": "2026-06-17",
                "recordDate": "2026-06-18",
                "paymentDate": "2026-06-26",
                "bookYear": "2026",
            }
        ],
    }

    rows = reviewer._semantic_rows(core, "BBCA")
    assert len(rows) == 1
    assert rows[0]["gross_dividend_per_share_idr"] == 20.0
    assert rows[0]["cum_date"] == "2026-06-15"
    assert rows[0]["ex_date"] == "2026-06-17"
    assert rows[0]["recording_date"] == "2026-06-18"
    assert rows[0]["payment_date"] == "2026-06-26"


def test_company_profile_expected_parity_requires_exact_official_event():
    reviewer = _load_script(
        "review_zapi_idx_company_profile_dividends_v1_parity",
        "review_zapi_idx_company_profile_dividends_v1.py",
    )
    good = dict(reviewer.EXPECTED_PARITY)
    assert reviewer._matches_expected(good)

    wrong = dict(good)
    wrong["gross_dividend_per_share_idr"] = 19.0
    assert not reviewer._matches_expected(wrong)
