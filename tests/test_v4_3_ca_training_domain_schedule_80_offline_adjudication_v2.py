from __future__ import annotations

from pathlib import Path


def test_v2_rebinds_only_hardened_parser() -> None:
    source = Path(
        "scripts/run_v4_3_ca_training_domain_schedule_80_offline_adjudication_v2.py"
    ).read_text(encoding="utf-8")
    assert "parse_residual_document_hardened" in source
    assert "v1.parse_residual_document = parse_residual_document_hardened" in source
    assert "return v1.main()" in source


def test_v2_has_no_provider_or_outcome_path() -> None:
    source = Path(
        "scripts/run_v4_3_ca_training_domain_schedule_80_offline_adjudication_v2.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "curl_cffi",
        "requests.get",
        "urllib.request",
        "capture_request(",
        "materialize_v4_target_ledger",
        "HistGradientBoostingRegressor",
        "fit_v4_head",
        "score_v4_head",
    )
    for token in forbidden:
        assert token not in source


def test_hardened_parser_requires_layout_bound_admissive_dates() -> None:
    source = Path("src/idx_trade/v4_ca_residual_document_semantics_hardened.py").read_text(
        encoding="utf-8"
    )
    assert "layout_bound_dates" in source
    assert 'record_date=_one(bound["RECORD_DATE"])' in source
    assert 'distribution_date=_one(bound["DISTRIBUTION_DATE"])' in source
    assert 'transition_date=transition_date' in source
    assert 'payment_dates=bound["PAYMENT_DATE"]' in source
