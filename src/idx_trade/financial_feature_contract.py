"""PIT-safe Financial PIT feature contract and availability dry-run.

This module defines *eligibility*, not a materialized feature table.  It is a
small contract layer over the accepted immutable fact census.  It deliberately
does not calculate or persist feature values, derive financial ratios for
research, fit models, or read any outcome data.

The contract is fail-closed on missing facts, unresolved extraction status,
ambiguous same-time versions, period/unit mismatches, unsupported statement
scope, and invalid denominators.  Every eligible input remains traceable to
the exact filing version and attachment hash that supplied it.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Mapping

from .financial_period_boundaries import validate_period_sidecar


CONTRACT_VERSION = "financial_feature_contract_v1"
SUPPORTED_PERIODS = frozenset({"Q1", "H1", "9M", "FY"})
MODEL_SAFE_INDUSTRIES = ("GENERAL",)
MODEL_SAFE_SCOPES = ("CONSOLIDATED",)
PERIOD_ALIASES = {
    "q1": "Q1",
    "tw1": "Q1",
    "h1": "H1",
    "tw2": "H1",
    "9m": "9M",
    "tw3": "9M",
    "fy": "FY",
    "audit": "FY",
}
RECOGNIZED_INDUSTRIES = frozenset({"GENERAL", "FINANCIAL", "FINANCIAL_SHARIA"})


class FeatureFamily(StrEnum):
    SIZE = "SIZE"
    LEVERAGE = "LEVERAGE"
    LIQUIDITY = "LIQUIDITY"
    PROFITABILITY = "PROFITABILITY"
    CASH_FLOW_QUALITY = "CASH_FLOW_QUALITY"
    MARGINS = "MARGINS"
    YOY_GROWTH = "YOY_GROWTH"


class AvailabilityStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNRESOLVED_APPLICABILITY = "UNRESOLVED_APPLICABILITY"
    MISSING_INPUT = "MISSING_INPUT"
    UNRESOLVED_INPUT = "UNRESOLVED_INPUT"
    UNRESOLVED_PERIOD = "UNRESOLVED_PERIOD"
    NONCOMPARABLE_PERIOD = "NONCOMPARABLE_PERIOD"
    AMBIGUOUS_VERSION = "AMBIGUOUS_VERSION"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    NONFINITE_INPUT = "NONFINITE_INPUT"
    DENOMINATOR_ZERO = "DENOMINATOR_ZERO"
    DENOMINATOR_NONPOSITIVE = "DENOMINATOR_NONPOSITIVE"


class PeriodShape(StrEnum):
    INSTANT = "INSTANT"
    DURATION = "DURATION"


class DenominatorRule(StrEnum):
    NONE = "NONE"
    POSITIVE = "POSITIVE"
    NONZERO = "NONZERO"


@dataclass(frozen=True)
class FeatureDefinition:
    feature_id: str
    family: FeatureFamily
    formula: str
    required_facts: tuple[tuple[str, PeriodShape], ...]
    applicable_industries: tuple[str, ...]
    denominator_facts: tuple[str, ...] = ()
    denominator_rule: DenominatorRule = DenominatorRule.NONE
    comparable_prior_period: bool = False
    description: str = ""
    duration_period_policy: str = "NONE"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["family"] = self.family.value
        result["required_facts"] = [
            {"fact_identity": fact, "period_shape": shape.value}
            for fact, shape in self.required_facts
        ]
        result["denominator_rule"] = self.denominator_rule.value
        return result


ALL_INDUSTRIES = tuple(sorted(RECOGNIZED_INDUSTRIES))
GENERAL_ONLY = ("GENERAL",)


FEATURE_DEFINITIONS: tuple[FeatureDefinition, ...] = (
    FeatureDefinition(
        "size_log_total_assets",
        FeatureFamily.SIZE,
        "log(total_assets)",
        (("total_assets", PeriodShape.INSTANT),),
        ALL_INDUSTRIES,
        denominator_facts=("total_assets",),
        denominator_rule=DenominatorRule.POSITIVE,
        description="Period-end asset scale; raw asset fact remains the provenance anchor.",
    ),
    FeatureDefinition(
        "size_log_revenue",
        FeatureFamily.SIZE,
        "log(revenue)",
        (("revenue", PeriodShape.DURATION),),
        GENERAL_ONLY,
        denominator_facts=("revenue",),
        denominator_rule=DenominatorRule.POSITIVE,
        description="General-issuer operating scale only; financial-issuer revenue semantics are not assumed.",
        duration_period_policy="PERIOD_STRATIFIED_CUMULATIVE_NO_ANNUALIZATION",
    ),
    FeatureDefinition(
        "leverage_liabilities_to_assets",
        FeatureFamily.LEVERAGE,
        "total_liabilities / total_assets",
        (("total_liabilities", PeriodShape.INSTANT), ("total_assets", PeriodShape.INSTANT)),
        ALL_INDUSTRIES,
        denominator_facts=("total_assets",),
        denominator_rule=DenominatorRule.POSITIVE,
        description="Descriptive balance-sheet leverage; no claim that it is a bank capital-ratio substitute.",
    ),
    FeatureDefinition(
        "capital_equity_to_assets",
        FeatureFamily.LEVERAGE,
        "total_equity / total_assets",
        (("total_equity", PeriodShape.INSTANT), ("total_assets", PeriodShape.INSTANT)),
        ALL_INDUSTRIES,
        denominator_facts=("total_assets",),
        denominator_rule=DenominatorRule.POSITIVE,
        description="Equity share of period-end assets; negative equity remains observed but does not alter denominator rules.",
    ),
    FeatureDefinition(
        "liquidity_cash_to_assets",
        FeatureFamily.LIQUIDITY,
        "cash_and_cash_equivalents / total_assets",
        (("cash_and_cash_equivalents", PeriodShape.INSTANT), ("total_assets", PeriodShape.INSTANT)),
        ALL_INDUSTRIES,
        denominator_facts=("total_assets",),
        denominator_rule=DenominatorRule.POSITIVE,
        description="Uses only the explicit cash-and-equivalents fact; no substitution from cash or zero-fill.",
    ),
    FeatureDefinition(
        "profitability_net_income_to_assets",
        FeatureFamily.PROFITABILITY,
        "net_income / total_assets",
        (("net_income", PeriodShape.DURATION), ("total_assets", PeriodShape.INSTANT)),
        ALL_INDUSTRIES,
        denominator_facts=("total_assets",),
        denominator_rule=DenominatorRule.POSITIVE,
        description="A clearly named period-end-assets denominator, not silently relabeled as average-assets ROA.",
        duration_period_policy="PERIOD_STRATIFIED_CUMULATIVE_NO_ANNUALIZATION",
    ),
    FeatureDefinition(
        "profitability_attributable_income_to_equity",
        FeatureFamily.PROFITABILITY,
        "net_income_attributable / total_equity",
        (("net_income_attributable", PeriodShape.DURATION), ("total_equity", PeriodShape.INSTANT)),
        ALL_INDUSTRIES,
        denominator_facts=("total_equity",),
        denominator_rule=DenominatorRule.POSITIVE,
        description="Fails closed on zero or non-positive equity rather than producing an unstable ratio.",
        duration_period_policy="PERIOD_STRATIFIED_CUMULATIVE_NO_ANNUALIZATION",
    ),
    FeatureDefinition(
        "cash_flow_ocf_to_net_income",
        FeatureFamily.CASH_FLOW_QUALITY,
        "operating_cash_flow / net_income",
        (("operating_cash_flow", PeriodShape.DURATION), ("net_income", PeriodShape.DURATION)),
        GENERAL_ONLY,
        denominator_facts=("net_income",),
        denominator_rule=DenominatorRule.POSITIVE,
        description="General-issuer quality diagnostic; financial-issuer cash-flow presentation is not treated as comparable.",
    ),
    FeatureDefinition(
        "cash_flow_ocf_to_revenue",
        FeatureFamily.CASH_FLOW_QUALITY,
        "operating_cash_flow / revenue",
        (("operating_cash_flow", PeriodShape.DURATION), ("revenue", PeriodShape.DURATION)),
        GENERAL_ONLY,
        denominator_facts=("revenue",),
        denominator_rule=DenominatorRule.POSITIVE,
        description="Requires same-period cumulative OCF and revenue with matching units/currency.",
    ),
    FeatureDefinition(
        "margin_net_income_to_revenue",
        FeatureFamily.MARGINS,
        "net_income / revenue",
        (("net_income", PeriodShape.DURATION), ("revenue", PeriodShape.DURATION)),
        GENERAL_ONLY,
        denominator_facts=("revenue",),
        denominator_rule=DenominatorRule.POSITIVE,
        description="General-issuer margin only; no banking-revenue alias is introduced.",
    ),
    FeatureDefinition(
        "yoy_revenue",
        FeatureFamily.YOY_GROWTH,
        "revenue_current / revenue_prior_comparable - 1",
        (("revenue", PeriodShape.DURATION),),
        GENERAL_ONLY,
        denominator_facts=("revenue",),
        denominator_rule=DenominatorRule.POSITIVE,
        comparable_prior_period=True,
        description="Same normalized Q1/H1/9M/FY cumulative period in the prior fiscal year.",
    ),
    FeatureDefinition(
        "yoy_net_income",
        FeatureFamily.YOY_GROWTH,
        "net_income_current / net_income_prior_comparable - 1",
        (("net_income", PeriodShape.DURATION),),
        ALL_INDUSTRIES,
        denominator_facts=("net_income",),
        denominator_rule=DenominatorRule.POSITIVE,
        comparable_prior_period=True,
        description="Prior negative/zero income is not converted into a misleading percentage growth value.",
    ),
    FeatureDefinition(
        "yoy_total_assets",
        FeatureFamily.YOY_GROWTH,
        "total_assets_current / total_assets_prior_comparable - 1",
        (("total_assets", PeriodShape.INSTANT),),
        ALL_INDUSTRIES,
        denominator_facts=("total_assets",),
        denominator_rule=DenominatorRule.POSITIVE,
        comparable_prior_period=True,
        description="Same normalized reporting period and instant semantics in the prior fiscal year.",
    ),
)


@dataclass(frozen=True)
class _Fact:
    ticker: str
    fiscal_year: int
    fiscal_period: str
    scope: str
    version_id: str
    attachment_sha256: str
    knowledge_at: datetime
    fact_identity: str
    period_shape: PeriodShape | None
    period_start: str | None
    period_end: str | None
    instant_date: str | None
    period_bounds_verified: bool
    value: Decimal | None
    status: str
    currency: str | None
    unit: str | None
    scale: int | None
    source_ref: str
    source_location: str
    period_evidence_kind: str = ""
    period_evidence_location: str = ""


@dataclass
class _Version:
    ticker: str
    fiscal_year: int
    fiscal_period: str
    scope: str
    version_id: str
    attachment_sha256: str
    knowledge_at: datetime
    representation_format: str
    industry_class: str
    facts: dict[str, list[_Fact]]


@dataclass(frozen=True)
class FeatureAvailability:
    feature_id: str
    ticker: str
    fiscal_year: int
    fiscal_period: str
    statement_scope: str
    industry_class: str
    status: AvailabilityStatus
    reason: str
    period_stratification_key: str | None = None
    input_version_ids: tuple[str, ...] = ()
    attachment_sha256s: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"status": self.status.value}


def normalize_period(period: str) -> str | None:
    """Normalize accepted census aliases without combining cumulative periods."""

    return PERIOD_ALIASES.get(str(period).strip().casefold())


def normalize_industry_class(industry_class: str | None) -> str:
    text = str(industry_class or "").strip().upper()
    if text == "GENERAL":
        return "GENERAL"
    if text == "FINANCIAL":
        return "FINANCIAL"
    if "FINANCIAL" in text and "SHARIA" in text:
        return "FINANCIAL_SHARIA"
    return "UNKNOWN"


def feature_definitions() -> tuple[FeatureDefinition, ...]:
    return FEATURE_DEFINITIONS


def applicability_matrix() -> list[dict[str, Any]]:
    return [
        {
            "feature_id": feature.feature_id,
            "family": feature.family.value,
            "GENERAL": "ELIGIBLE" if "GENERAL" in feature.applicable_industries else "NOT_APPLICABLE",
            "FINANCIAL": "ELIGIBLE" if "FINANCIAL" in feature.applicable_industries else "NOT_APPLICABLE",
            "FINANCIAL_SHARIA": "ELIGIBLE" if "FINANCIAL_SHARIA" in feature.applicable_industries else "NOT_APPLICABLE",
            "unknown": "FAIL_CLOSED",
        }
        for feature in FEATURE_DEFINITIONS
    ]


def _parse_timestamp(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("missing knowledge timestamp")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("naive financial fact timestamp is not PIT-safe")
    return parsed.astimezone(timezone.utc)


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = Decimal(str(value))
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def _period_shape(row: Mapping[str, Any]) -> PeriodShape | None:
    covered = row.get("fiscal_period_covered") or {}
    raw = str(covered.get("period_kind") or "").strip().casefold()
    if raw == "instant":
        return PeriodShape.INSTANT
    if raw == "duration":
        return PeriodShape.DURATION
    return None


def _period_metadata(
    row: Mapping[str, Any],
    boundary: Mapping[str, Any] | None = None,
) -> tuple[str | None, str | None, str | None, bool, str, str]:
    covered = row.get("fiscal_period_covered") or {}
    shape = _period_shape(row)
    start = str(covered.get("period_start") or "").strip() or None
    end = str(covered.get("period_end") or "").strip() or None
    instant = str(covered.get("instant_date") or "").strip() or None
    evidence_kind = ""
    evidence_location = ""
    if boundary:
        if shape is PeriodShape.INSTANT:
            instant = (
                str(boundary.get("instant_date") or "").strip() or None
                if boundary.get("instant_status") == "RECOVERED"
                else None
            )
            start = None
            end = None
            evidence_kind = str(boundary.get("evidence_kind") or "")
            evidence_location = ";".join(
                str(item.get("source_location") or "") for item in boundary.get("instant_evidence", ()) if item.get("source_location")
            )
        elif shape is PeriodShape.DURATION:
            if boundary.get("duration_status") == "RECOVERED":
                start = str(boundary.get("period_start") or "").strip() or None
                end = str(boundary.get("period_end") or "").strip() or None
            else:
                start = None
                end = None
            instant = None
            evidence_kind = str(boundary.get("evidence_kind") or "")
            evidence_location = ";".join(
                str(item.get("source_location") or "") for item in boundary.get("duration_evidence", ()) if item.get("source_location")
            )
    if shape is PeriodShape.INSTANT:
        verified = bool(instant or end) and not bool(start)
    elif shape is PeriodShape.DURATION:
        verified = bool(start and end and not instant)
    else:
        verified = False
    return start, end, instant, verified, evidence_kind, evidence_location


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected object")
            rows.append(value)
    return rows


def _build_versions(
    fact_rows: Iterable[Mapping[str, Any]],
    diagnostic_rows: Iterable[Mapping[str, Any]],
    period_boundaries: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[tuple[str, int, str, str], list[_Version]]:
    diagnostics: dict[str, Mapping[str, Any]] = {}
    for row in diagnostic_rows:
        version_id = str(row.get("version_id") or "")
        if not version_id:
            raise ValueError("diagnostic row missing version_id")
        prior = diagnostics.get(version_id)
        if prior is not None and dict(prior) != dict(row):
            raise ValueError(f"conflicting diagnostics for version {version_id}")
        diagnostics[version_id] = row

    grouped: dict[tuple[str, int, str, str, str], _Version] = {}
    for version_id, diagnostic in diagnostics.items():
        ticker = str(diagnostic.get("ticker") or "").strip().upper()
        period = str(diagnostic.get("fiscal_period") or "").strip()
        scope = str(diagnostic.get("scope") or diagnostic.get("statement_scope") or "").strip().upper()
        attachment_sha = str(diagnostic.get("source_attachment_sha256") or diagnostic.get("attachment_sha256") or "").strip().lower()
        knowledge_raw = diagnostic.get("knowledge_at_utc") or diagnostic.get("publication_at_utc")
        if not ticker or not period or not scope or len(attachment_sha) != 64 or knowledge_raw is None:
            raise ValueError(f"diagnostic row has incomplete filing identity: {version_id}")
        key = (ticker, int(diagnostic["fiscal_year"]), period, scope, version_id)
        grouped[key] = _Version(
            ticker=ticker,
            fiscal_year=int(diagnostic["fiscal_year"]),
            fiscal_period=period,
            scope=scope,
            version_id=version_id,
            attachment_sha256=attachment_sha,
            knowledge_at=_parse_timestamp(knowledge_raw),
            representation_format=str(diagnostic.get("representation_format") or "").strip().upper(),
            industry_class=normalize_industry_class(diagnostic.get("industry_class") or diagnostic.get("template_or_industry_family")),
            facts={},
        )

    for row in fact_rows:
        required = ("ticker", "fiscal_year", "fiscal_period", "statement_scope", "version_id", "attachment_sha256", "knowledge_at_utc", "fact_identity")
        missing = [key for key in required if str(row.get(key) or "").strip() == ""]
        if missing:
            raise ValueError(f"fact row missing required identity fields: {missing}")
        version_id = str(row["version_id"])
        diagnostic = diagnostics.get(version_id)
        if diagnostic is None:
            raise ValueError(f"fact row has no filing diagnostic: {version_id}")
        ticker = str(row["ticker"]).strip().upper()
        year = int(row["fiscal_year"])
        period = str(row["fiscal_period"]).strip()
        scope = str(row["statement_scope"]).strip().upper()
        attachment_sha = str(row["attachment_sha256"]).strip().lower()
        if len(attachment_sha) != 64:
            raise ValueError(f"invalid attachment SHA for version {version_id}")
        knowledge_at = _parse_timestamp(row["knowledge_at_utc"])
        key = (ticker, year, period, scope, version_id)
        current = grouped.get(key)
        if current is None:
            raise ValueError(f"fact row has no matching filing diagnostic: {version_id}")
        fmt = str(row.get("representation_format") or diagnostic.get("representation_format") or "").strip().upper()
        industry = normalize_industry_class(diagnostic.get("industry_class") or diagnostic.get("template_or_industry_family"))
        if (current.attachment_sha256, current.knowledge_at, current.representation_format) != (attachment_sha, knowledge_at, fmt):
            raise ValueError(f"conflicting metadata within version {version_id}")
        boundary = period_boundaries.get(version_id) if period_boundaries else None
        if boundary is not None:
            boundary_sha = str(boundary.get("attachment_sha256") or "").lower()
            if boundary_sha != attachment_sha:
                raise ValueError(f"period boundary sidecar hash mismatch for version {version_id}")
        start, end, instant, bounds_verified, evidence_kind, evidence_location = _period_metadata(row, boundary)
        current.facts.setdefault(str(row["fact_identity"]), []).append(
            _Fact(
                ticker=ticker,
                fiscal_year=year,
                fiscal_period=period,
                scope=scope,
                version_id=version_id,
                attachment_sha256=attachment_sha,
                knowledge_at=knowledge_at,
                fact_identity=str(row["fact_identity"]),
                period_shape=_period_shape(row),
                period_start=start,
                period_end=end,
                instant_date=instant,
                period_bounds_verified=bounds_verified,
                value=_parse_decimal(row.get("value")),
                status=str(row.get("extraction_status") or ""),
                currency=str(row.get("currency") or "").upper() or None,
                unit=str(row.get("unit") or "") or None,
                scale=int(row["scale"]) if row.get("scale") is not None else None,
                source_ref=str(row.get("source_ref") or ""),
                source_location=str(row.get("source_location") or ""),
                period_evidence_kind=evidence_kind,
                period_evidence_location=evidence_location,
            )
        )

    logical: dict[tuple[str, int, str, str], list[_Version]] = defaultdict(list)
    for version in grouped.values():
        logical[(version.ticker, version.fiscal_year, version.fiscal_period, version.scope)].append(version)
    for versions in logical.values():
        versions.sort(key=lambda item: (item.knowledge_at, item.version_id))
    return dict(logical)


def _select_version(
    versions: Mapping[tuple[str, int, str, str], list[_Version]],
    key: tuple[str, int, str, str],
    as_of: datetime,
) -> tuple[_Version | None, AvailabilityStatus | None]:
    candidates = [item for item in versions.get(key, ()) if item.knowledge_at <= as_of]
    if not candidates:
        return None, AvailabilityStatus.MISSING_INPUT
    latest_time = max(item.knowledge_at for item in candidates)
    latest = [item for item in candidates if item.knowledge_at == latest_time]
    hashes = {item.attachment_sha256 for item in latest}
    if len(hashes) > 1:
        return None, AvailabilityStatus.AMBIGUOUS_VERSION
    return sorted(latest, key=lambda item: item.version_id)[-1], None


def _fact_from_version(version: _Version, fact_identity: str, shape: PeriodShape) -> tuple[_Fact | None, AvailabilityStatus | None]:
    rows = version.facts.get(fact_identity, [])
    extracted = [row for row in rows if row.status == "EXTRACTED" and row.period_shape == shape]
    if not extracted:
        if rows:
            return None, AvailabilityStatus.UNRESOLVED_INPUT
        return None, AvailabilityStatus.MISSING_INPUT
    if any(row.value is None for row in extracted):
        return None, AvailabilityStatus.NONFINITE_INPUT
    fingerprints = {
        (
            row.value,
            row.currency,
            row.unit,
            row.scale,
            row.source_location,
            row.period_shape,
            row.period_start,
            row.period_end,
            row.instant_date,
            row.period_evidence_kind,
            row.period_evidence_location,
        )
        for row in extracted
    }
    if len(fingerprints) > 1:
        return None, AvailabilityStatus.UNRESOLVED_INPUT
    return sorted(extracted, key=lambda row: row.source_location)[0], None


def _same_units(facts: Iterable[_Fact]) -> bool:
    identities = {(row.currency, row.unit, row.scale) for row in facts}
    return len(identities) <= 1


def _denominator_status(values: Mapping[str, _Fact], feature: FeatureDefinition) -> AvailabilityStatus | None:
    for identity in feature.denominator_facts:
        fact = values.get(identity)
        if fact is None or fact.value is None:
            return AvailabilityStatus.NONFINITE_INPUT
        if feature.denominator_rule is DenominatorRule.NONZERO and fact.value == 0:
            return AvailabilityStatus.DENOMINATOR_ZERO
        if feature.denominator_rule is DenominatorRule.POSITIVE and fact.value <= 0:
            return AvailabilityStatus.DENOMINATOR_NONPOSITIVE
    return None


def _availability(
    feature: FeatureDefinition,
    current: _Version,
    versions: Mapping[tuple[str, int, str, str], list[_Version]],
    *,
    as_of: datetime | None = None,
) -> FeatureAvailability:
    base = dict(
        feature_id=feature.feature_id,
        ticker=current.ticker,
        fiscal_year=current.fiscal_year,
        fiscal_period=current.fiscal_period,
        statement_scope=current.scope,
        industry_class=current.industry_class,
    )
    normalized_period = normalize_period(current.fiscal_period)
    base["period_stratification_key"] = normalized_period
    if normalized_period not in SUPPORTED_PERIODS:
        return FeatureAvailability(**base, status=AvailabilityStatus.UNRESOLVED_PERIOD, reason="period is not Q1/H1/9M/FY")
    if current.industry_class == "UNKNOWN":
        return FeatureAvailability(**base, status=AvailabilityStatus.UNRESOLVED_APPLICABILITY, reason="industry/taxonomy applicability is not explicit")
    if current.industry_class not in MODEL_SAFE_INDUSTRIES or current.scope not in MODEL_SAFE_SCOPES:
        return FeatureAvailability(**base, status=AvailabilityStatus.NOT_APPLICABLE, reason="outside conservative GENERAL + CONSOLIDATED model-safe scope")
    if current.industry_class not in feature.applicable_industries:
        return FeatureAvailability(**base, status=AvailabilityStatus.NOT_APPLICABLE, reason="feature is outside its frozen industry applicability matrix")

    selected_versions = [current]
    values: dict[str, _Fact] = {}
    for identity, shape in feature.required_facts:
        fact, status = _fact_from_version(current, identity, shape)
        if status is not None:
            return FeatureAvailability(**base, status=status, reason=f"current filing input {identity}: {status.value}")
        assert fact is not None
        if fact.value is None:
            return FeatureAvailability(**base, status=AvailabilityStatus.NONFINITE_INPUT, reason=f"current filing input {identity} is not finite")
        if not fact.period_bounds_verified:
            return FeatureAvailability(**base, status=AvailabilityStatus.UNRESOLVED_PERIOD, reason=f"current filing input {identity} lacks explicit instant/duration boundaries")
        values[identity] = fact

    duration_facts = [fact for fact in values.values() if fact.period_shape is PeriodShape.DURATION]
    instant_facts = [fact for fact in values.values() if fact.period_shape is PeriodShape.INSTANT]
    if duration_facts and len({(fact.period_start, fact.period_end) for fact in duration_facts}) != 1:
        return FeatureAvailability(**base, status=AvailabilityStatus.NONCOMPARABLE_PERIOD, reason="duration inputs do not share exact period boundaries")
    if instant_facts and len({fact.instant_date for fact in instant_facts}) != 1:
        return FeatureAvailability(**base, status=AvailabilityStatus.NONCOMPARABLE_PERIOD, reason="instant inputs do not share exact instant date")
    if feature.feature_id in {"profitability_net_income_to_assets", "profitability_attributable_income_to_equity"}:
        duration_end = duration_facts[0].period_end if duration_facts else None
        instant_date = instant_facts[0].instant_date if instant_facts else None
        if not duration_end or not instant_date or duration_end != instant_date:
            return FeatureAvailability(**base, status=AvailabilityStatus.NONCOMPARABLE_PERIOD, reason="duration period_end must equal instant denominator date")

    if feature.comparable_prior_period:
        prior_key = (current.ticker, current.fiscal_year - 1, current.fiscal_period, current.scope)
        prior, version_status = _select_version(versions, prior_key, as_of or current.knowledge_at)
        if version_status is not None or prior is None:
            return FeatureAvailability(**base, status=version_status or AvailabilityStatus.MISSING_INPUT, reason="comparable prior fiscal-period filing is not knowable")
        if prior.industry_class != current.industry_class:
            return FeatureAvailability(**base, status=AvailabilityStatus.NONCOMPARABLE_PERIOD, reason="prior period applicability class differs")
        identity, shape = feature.required_facts[0]
        prior_fact, status = _fact_from_version(prior, identity, shape)
        if status is not None:
            return FeatureAvailability(**base, status=status, reason=f"prior comparable input {identity}: {status.value}")
        assert prior_fact is not None
        if prior_fact.value is None:
            return FeatureAvailability(**base, status=AvailabilityStatus.NONFINITE_INPUT, reason="prior comparable input is not finite")
        if not prior_fact.period_bounds_verified:
            return FeatureAvailability(**base, status=AvailabilityStatus.UNRESOLVED_PERIOD, reason="prior comparable input lacks explicit period boundaries")
        if not _same_units((values[identity], prior_fact)):
            return FeatureAvailability(**base, status=AvailabilityStatus.UNIT_MISMATCH, reason="current/prior comparable units differ")
        values[f"prior:{identity}"] = prior_fact
        selected_versions.append(prior)

    if not _same_units(values.values()):
        return FeatureAvailability(**base, status=AvailabilityStatus.UNIT_MISMATCH, reason="required facts have different currency/unit/scale")
    denominator_values = {key.split(":", 1)[-1]: value for key, value in values.items()}
    denominator_status = _denominator_status(denominator_values, feature)
    if denominator_status is not None:
        return FeatureAvailability(**base, status=denominator_status, reason=f"denominator rule {feature.denominator_rule.value} failed")

    return FeatureAvailability(
        **base,
        status=AvailabilityStatus.AVAILABLE,
        reason="all frozen inputs available from explicit same-version PIT facts",
        input_version_ids=tuple(item.version_id for item in selected_versions),
        attachment_sha256s=tuple(item.attachment_sha256 for item in selected_versions),
        source_refs=tuple(sorted({fact.source_ref for fact in values.values() if fact.source_ref})),
    )


def run_feature_availability_dry_run(
    fact_records_path: Path,
    filing_diagnostics_path: Path,
    *,
    output_root: Path | None = None,
    period_boundaries_path: Path | None = None,
    period_boundaries_manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Audit feature input availability without materializing feature values."""

    fact_rows = _load_jsonl(fact_records_path)
    diagnostic_rows = _load_jsonl(filing_diagnostics_path)
    period_boundaries: dict[str, Mapping[str, Any]] | None = None
    if period_boundaries_path is not None:
        if period_boundaries_manifest_path is None:
            raise ValueError("period boundary sidecar requires a manifest")
        sidecar_validation = validate_period_sidecar(
            period_boundaries_path,
            period_boundaries_manifest_path,
            filing_diagnostics_path,
            fact_records_path,
        )
        period_boundaries = {}
        for row in _load_jsonl(period_boundaries_path):
            version_id = str(row.get("version_id") or "")
            if not version_id or version_id in period_boundaries:
                raise ValueError(f"duplicate or missing period boundary version: {version_id}")
            period_boundaries[version_id] = row
    versions = _build_versions(fact_rows, diagnostic_rows, period_boundaries)
    all_versions = [version for rows in versions.values() for version in rows]
    results: list[FeatureAvailability] = []
    for version in sorted(all_versions, key=lambda item: (item.ticker, item.fiscal_year, item.fiscal_period, item.scope, item.version_id)):
        for feature in FEATURE_DEFINITIONS:
            results.append(_availability(feature, version, versions))

    by_feature: dict[str, dict[str, Any]] = {}
    for feature in FEATURE_DEFINITIONS:
        subset = [row for row in results if row.feature_id == feature.feature_id]
        counts = Counter(row.status.value for row in subset)
        by_feature[feature.feature_id] = {
            "family": feature.family.value,
            "total_filing_versions": len(subset),
            "status_counts": dict(sorted(counts.items())),
            "available": counts.get(AvailabilityStatus.AVAILABLE.value, 0),
            "availability_fraction": round(counts.get(AvailabilityStatus.AVAILABLE.value, 0) / len(subset), 6) if subset else 0.0,
        }

    by_industry: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: Counter()))
    for row in results:
        by_industry[row.industry_class][row.feature_id][row.status.value] += 1
    summary = {
        "status": "FINANCIAL_PIT_FEATURE_AVAILABILITY_DRY_RUN",
        "contract_version": CONTRACT_VERSION,
        "filing_versions": len(all_versions),
        "logical_filing_keys": len(versions),
        "features": [feature.to_dict() for feature in FEATURE_DEFINITIONS],
        "applicability_matrix": applicability_matrix(),
        "by_feature": by_feature,
        "by_industry": {
            industry: {feature: dict(sorted(statuses.items())) for feature, statuses in sorted(features.items())}
            for industry, features in sorted(by_industry.items())
        },
        "period_boundary_audit": {
            "fact_rows": len(fact_rows),
            "shape_counts": dict(sorted(Counter(
                fact.period_shape.value if fact.period_shape else "UNKNOWN"
                for version in all_versions
                for facts in version.facts.values()
                for fact in facts
            ).items())),
            "explicit_boundary_rows": sum(
                1 for version in all_versions for facts in version.facts.values() for fact in facts if fact.period_bounds_verified
            ),
            "missing_or_invalid_boundary_rows": sum(
                1 for version in all_versions for facts in version.facts.values() for fact in facts if not fact.period_bounds_verified
            ),
            "materialization_gate": "BLOCKED_UNRESOLVED_PERIOD_METADATA"
            if any(not fact.period_bounds_verified for version in all_versions for facts in version.facts.values() for fact in facts)
            else "PASS",
        },
        "source_artifacts": {
            "fact_records": {"path": str(fact_records_path), "sha256": _sha256_file(fact_records_path)},
            "filing_diagnostics": {"path": str(filing_diagnostics_path), "sha256": _sha256_file(filing_diagnostics_path)},
            "period_boundaries": {"path": str(period_boundaries_path), "sha256": _sha256_file(period_boundaries_path)}
            if period_boundaries_path is not None
            else None,
            "period_boundaries_manifest": {"path": str(period_boundaries_manifest_path), "sha256": _sha256_file(period_boundaries_manifest_path)}
            if period_boundaries_manifest_path is not None
            else None,
        },
        "period_boundary_sidecar_validation": sidecar_validation if period_boundaries_path is not None else None,
        "model_safe_scope_contract": {
            "industries": list(MODEL_SAFE_INDUSTRIES),
            "statement_scopes": list(MODEL_SAFE_SCOPES),
            "broader_scope_rows_are_audit_only": True,
        },
        "values_materialized": False,
        "alpha_metrics_computed": False,
        "model_work": False,
        "network_calls": 0,
        "protected_outcomes_accessed": False,
        "period_policy": "Q1/H1/9M/FY are cumulative source periods; never sum periods; YoY uses same normalized period and knowable prior filing",
        "revision_policy": "select latest complete filing version with knowledge_at <= decision time; never mix versions; same-time hash conflict fails closed",
        "missing_policy": "missing and unresolved facts remain missing; no zero-fill or synthetic imputation",
        "duration_period_policy": "cumulative duration facts are period-stratified by Q1/H1/9M/FY; no annualization or cross-period pooling",
    }
    if output_root is not None:
        if output_root.exists() and any(output_root.iterdir()):
            raise ValueError(f"output root must be new and empty: {output_root}")
        output_root.mkdir(parents=True, exist_ok=True)
        summary_path = output_root / "availability.json"
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest = {
            "manifest_version": f"{CONTRACT_VERSION}_dry_run",
            "files": {"availability.json": {"bytes": summary_path.stat().st_size, "sha256": _sha256_file(summary_path)}},
            "source_artifacts": summary["source_artifacts"],
        }
        manifest_path = output_root / "MANIFEST.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        summary["artifact_hashes"] = {
            "availability.json": _sha256_file(summary_path),
            "MANIFEST.json": _sha256_file(manifest_path),
        }
    return summary


__all__ = [
    "AvailabilityStatus",
    "CONTRACT_VERSION",
    "DenominatorRule",
    "FeatureDefinition",
    "FeatureFamily",
    "FEATURE_DEFINITIONS",
    "PeriodShape",
    "applicability_matrix",
    "feature_definitions",
    "normalize_industry_class",
    "normalize_period",
    "run_feature_availability_dry_run",
]
