from __future__ import annotations

from datetime import datetime, timezone

from idx_trade.financial_feature_contract import (
    AvailabilityStatus,
    FeatureDefinition,
    FEATURE_DEFINITIONS,
    PeriodShape,
    _availability,
    _build_versions,
    applicability_matrix,
    normalize_period,
)


def _fact(
    *,
    version: str = "v1",
    ticker: str = "TEST",
    year: int = 2025,
    period: str = "tw1",
    scope: str = "CONSOLIDATED",
    identity: str,
    shape: str,
    value: str,
    knowledge: str = "2025-05-01T02:00:00Z",
    currency: str = "IDR",
    unit: str = "IDR",
    scale: int = 1,
    status: str = "EXTRACTED",
) -> dict:
    return {
        "ticker": ticker,
        "fiscal_year": year,
        "fiscal_period": period,
        "statement_scope": scope,
        "publication_at_utc": knowledge,
        "knowledge_at_utc": knowledge,
        "attachment_sha256": (version + "0" * 64)[:64],
        "source_ref": f"IDX/{version}",
        "representation_format": "XLSX",
        "statement_identity": "statement_of_financial_position" if shape == "instant" else "income_statement",
        "fact_identity": identity,
        "value": value,
        "currency": currency,
        "unit": unit,
        "scale": scale,
        "fiscal_period_covered": {
            "period_kind": shape,
            "report_period": period,
            "report_year": year,
            "period_start": f"{year}-01-01" if shape == "duration" else None,
            "period_end": f"{year}-03-31",
            "instant_date": f"{year}-03-31" if shape == "instant" else None,
        },
        "source_location": f"sheet=1000000;cell={identity}",
        "evidence_kind": "fixture",
        "raw_label": identity,
        "taxonomy": "GENERAL",
        "taxonomy_version": "fixture",
        "version_id": version,
        "extraction_status": status,
    }


def _diagnostic(
    version: str,
    *,
    ticker: str = "TEST",
    year: int = 2025,
    period: str = "tw1",
    industry: str = "GENERAL",
    knowledge: str = "2025-05-01T02:00:00Z",
) -> dict:
    return {
        "version_id": version,
        "ticker": ticker,
        "fiscal_year": year,
        "fiscal_period": period,
        "industry_class": industry,
        "representation_format": "XLSX",
        "scope": "CONSOLIDATED",
        "publication_at_utc": knowledge,
        "source_attachment_sha256": (version + "0" * 64)[:64],
    }


def test_period_aliases_do_not_sum_cumulative_periods() -> None:
    assert normalize_period("tw1") == "Q1"
    assert normalize_period("tw2") == "H1"
    assert normalize_period("tw3") == "9M"
    assert normalize_period("audit") == "FY"
    assert normalize_period("Q1+H1") is None


def test_same_version_and_explicit_units_are_required_for_ratio() -> None:
    facts = [
        _fact(version="v1", identity="total_assets", shape="instant", value="100"),
        _fact(version="v1", identity="total_liabilities", shape="instant", value="50"),
    ]
    versions = _build_versions(facts, [_diagnostic("v1")])
    feature = next(item for item in FEATURE_DEFINITIONS if item.feature_id == "leverage_liabilities_to_assets")
    selected = versions[("TEST", 2025, "tw1", "CONSOLIDATED")][0]
    result = _availability(feature, selected, versions)
    assert result.status is AvailabilityStatus.AVAILABLE
    assert result.input_version_ids == ("v1",)
    assert result.attachment_sha256s


def test_revision_is_not_mixed_when_latest_version_lacks_an_input() -> None:
    facts = [
        _fact(version="old", identity="total_assets", shape="instant", value="100", knowledge="2025-04-01T02:00:00Z"),
        _fact(version="old", identity="total_liabilities", shape="instant", value="50", knowledge="2025-04-01T02:00:00Z"),
        _fact(version="new", identity="total_assets", shape="instant", value="120", knowledge="2025-05-01T02:00:00Z"),
    ]
    versions = _build_versions(
        facts,
        [
            _diagnostic("old", knowledge="2025-04-01T02:00:00Z"),
            _diagnostic("new", knowledge="2025-05-01T02:00:00Z"),
        ],
    )
    feature = next(item for item in FEATURE_DEFINITIONS if item.feature_id == "leverage_liabilities_to_assets")
    selected = next(item for item in versions[("TEST", 2025, "tw1", "CONSOLIDATED")] if item.version_id == "new")
    result = _availability(feature, selected, versions)
    assert result.status is AvailabilityStatus.MISSING_INPUT
    assert "total_liabilities" in result.reason


def test_yoy_requires_same_period_prior_filing_known_at_current_time() -> None:
    facts = [
        _fact(version="current", year=2025, period="tw1", identity="revenue", shape="duration", value="120", knowledge="2025-05-01T02:00:00Z"),
        _fact(version="prior", year=2024, period="tw1", identity="revenue", shape="duration", value="100", knowledge="2025-06-01T02:00:00Z"),
    ]
    diagnostics = [
        _diagnostic("current", year=2025, knowledge="2025-05-01T02:00:00Z"),
        _diagnostic("prior", year=2024, knowledge="2025-06-01T02:00:00Z"),
    ]
    versions = _build_versions(facts, diagnostics)
    feature = next(item for item in FEATURE_DEFINITIONS if item.feature_id == "yoy_revenue")
    current = next(item for item in versions[("TEST", 2025, "tw1", "CONSOLIDATED")] if item.version_id == "current")
    result = _availability(feature, current, versions)
    assert result.status is AvailabilityStatus.MISSING_INPUT


def test_zero_and_negative_denominators_fail_closed() -> None:
    for denominator, expected in (("0", AvailabilityStatus.DENOMINATOR_NONPOSITIVE), ("-5", AvailabilityStatus.DENOMINATOR_NONPOSITIVE)):
        facts = [
            _fact(identity="total_assets", shape="instant", value=denominator),
            _fact(identity="total_liabilities", shape="instant", value="50"),
        ]
        versions = _build_versions(facts, [_diagnostic("v1")])
        feature = next(item for item in FEATURE_DEFINITIONS if item.feature_id == "leverage_liabilities_to_assets")
        selected = versions[("TEST", 2025, "tw1", "CONSOLIDATED")][0]
        assert _availability(feature, selected, versions).status is expected


def test_unknown_and_financial_applicability_fail_closed_or_not_applicable() -> None:
    facts = [
        _fact(identity="operating_cash_flow", shape="duration", value="10"),
        _fact(identity="net_income", shape="duration", value="5"),
    ]
    feature = next(item for item in FEATURE_DEFINITIONS if item.feature_id == "cash_flow_ocf_to_net_income")
    unknown_versions = _build_versions(facts, [_diagnostic("v1", industry="UNKNOWN_UNLESS_EXPLICIT_IN_TAXONOMY")])
    selected = unknown_versions[("TEST", 2025, "tw1", "CONSOLIDATED")][0]
    assert _availability(feature, selected, unknown_versions).status is AvailabilityStatus.UNRESOLVED_APPLICABILITY

    financial_versions = _build_versions(facts, [_diagnostic("v1", industry="FINANCIAL_SHARIA")])
    selected = financial_versions[("TEST", 2025, "tw1", "CONSOLIDATED")][0]
    assert _availability(feature, selected, financial_versions).status is AvailabilityStatus.NOT_APPLICABLE


def test_missing_period_boundaries_fail_closed_even_when_shape_is_present() -> None:
    row = _fact(identity="total_assets", shape="instant", value="100")
    row["fiscal_period_covered"] = {"period_kind": "instant", "report_period": "tw1", "report_year": 2025}
    facts = [row]
    versions = _build_versions(facts, [_diagnostic("v1")])
    feature = next(item for item in FEATURE_DEFINITIONS if item.feature_id == "size_log_total_assets")
    selected = versions[("TEST", 2025, "tw1", "CONSOLIDATED")][0]
    assert _availability(feature, selected, versions).status is AvailabilityStatus.UNRESOLVED_PERIOD


def test_applicability_matrix_has_fail_closed_unknown_column() -> None:
    matrix = applicability_matrix()
    assert len(matrix) == len(FEATURE_DEFINITIONS)
    assert all(row["unknown"] == "FAIL_CLOSED" for row in matrix)
