"""PIT-safe sparse Financial PIT feature materialization.

This module materializes the already accepted 13-feature contract.  It is an
offline, change-point as-of panel: a row is emitted when a GENERAL +
CONSOLIDATED filing version becomes knowable, and the row contains the
selected filing state for that issuer at that exact UTC timestamp.  No daily
calendar is invented and no unresolved fact is carried across a state.

The output is intentionally long by feature and reporting period.  Keeping
the reporting-period identity in every row prevents a downstream join from
silently pooling Q1/H1/9M/FY cumulative values.  ``feature_value`` is only
populated when the frozen availability contract returns AVAILABLE; all other
statuses remain explicit and fail closed.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

from .financial_feature_contract import (
    CONTRACT_VERSION,
    FEATURE_DEFINITIONS,
    MODEL_SAFE_INDUSTRIES,
    MODEL_SAFE_SCOPES,
    AvailabilityStatus,
    FeatureDefinition,
    PeriodShape,
    _Fact,
    _Version,
    _availability,
    _build_versions,
    _fact_from_version,
    _load_jsonl,
    _parse_timestamp,
    _select_version,
    _sha256_file,
    normalize_period,
)
from .financial_period_boundaries import validate_period_sidecar


PANEL_VERSION = "financial_pit_feature_panel_v1"
PANEL_COLUMNS = (
    "ticker",
    "decision_date",
    "as_of_timestamp_utc",
    "fiscal_year",
    "fiscal_period",
    "period_stratification_key",
    "statement_scope",
    "industry_class",
    "representation_format",
    "reporting_version_id",
    "reporting_attachment_sha256",
    "reporting_publication_at_utc",
    "reporting_knowledge_at_utc",
    "reporting_period_start",
    "reporting_period_end",
    "reporting_instant_date",
    "reporting_period_evidence_kind",
    "reporting_period_evidence_location",
    "feature_id",
    "feature_family",
    "feature_formula",
    "feature_value",
    "availability_status",
    "availability_reason",
    "current_filing_age_days",
    "input_version_ids_json",
    "input_attachment_sha256s_json",
    "input_publication_at_utc_json",
    "input_knowledge_at_utc_json",
    "input_period_boundaries_json",
    "input_fact_identities_json",
    "input_source_refs_json",
    "input_source_locations_json",
    "input_fact_provenance_json",
    "feature_contract_version",
)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fact_payload(fact: _Fact) -> dict[str, Any]:
    return {
        "fact_identity": fact.fact_identity,
        "version_id": fact.version_id,
        "attachment_sha256": fact.attachment_sha256,
        "value": str(fact.value) if fact.value is not None else None,
        "currency": fact.currency,
        "unit": fact.unit,
        "scale": fact.scale,
        "period_shape": fact.period_shape.value if fact.period_shape else None,
        "period_start": fact.period_start,
        "period_end": fact.period_end,
        "instant_date": fact.instant_date,
        "period_bounds_verified": fact.period_bounds_verified,
        "period_evidence_kind": fact.period_evidence_kind,
        "period_evidence_location": fact.period_evidence_location,
        "source_ref": fact.source_ref,
        "source_location": fact.source_location,
    }


def _version_facts(version: _Version, feature: FeatureDefinition, versions: Mapping[tuple[str, int, str, str], list[_Version]], as_of: datetime, availability: Any) -> list[_Fact]:
    """Resolve the exact current/prior facts used by one AVAILABLE feature."""

    facts: list[_Fact] = []
    for identity, shape in feature.required_facts:
        fact, status = _fact_from_version(version, identity, shape)
        if status is not None or fact is None:
            raise ValueError(f"availability/fact disagreement for {feature.feature_id}: {identity}")
        facts.append(fact)
    if feature.comparable_prior_period:
        prior_key = (version.ticker, version.fiscal_year - 1, version.fiscal_period, version.scope)
        prior, status = _select_version(versions, prior_key, as_of)
        if status is not None or prior is None:
            raise ValueError(f"availability/prior disagreement for {feature.feature_id}")
        identity, shape = feature.required_facts[0]
        fact, status = _fact_from_version(prior, identity, shape)
        if status is not None or fact is None:
            raise ValueError(f"availability/prior fact disagreement for {feature.feature_id}")
        facts.append(fact)
    if any(fact.knowledge_at > as_of for fact in facts):
        raise ValueError(f"future input selected for {feature.feature_id}")
    return facts


def _fact_values(feature: FeatureDefinition, facts: list[_Fact]) -> dict[str, Any]:
    current = {fact.fact_identity: fact.value for fact in facts[: len(feature.required_facts)]}
    values = dict(current)
    if feature.comparable_prior_period:
        values[f"prior:{feature.required_facts[0][0]}"] = facts[-1].value
    return values


def _calculate(feature: FeatureDefinition, facts: list[_Fact]) -> float:
    values = _fact_values(feature, facts)

    def positive(identity: str) -> float:
        value = values.get(identity)
        if value is None or value <= 0:
            raise ValueError(f"non-positive denominator: {identity}")
        result = float(value)
        if not math.isfinite(result):
            raise ValueError(f"non-finite value: {identity}")
        return result

    def raw(identity: str) -> float:
        value = values.get(identity)
        if value is None:
            raise ValueError(f"missing input: {identity}")
        result = float(value)
        if not math.isfinite(result):
            raise ValueError(f"non-finite value: {identity}")
        return result

    formulas = {
        "size_log_total_assets": lambda: math.log(positive("total_assets")),
        "size_log_revenue": lambda: math.log(positive("revenue")),
        "leverage_liabilities_to_assets": lambda: raw("total_liabilities") / positive("total_assets"),
        "capital_equity_to_assets": lambda: raw("total_equity") / positive("total_assets"),
        "liquidity_cash_to_assets": lambda: raw("cash_and_cash_equivalents") / positive("total_assets"),
        "profitability_net_income_to_assets": lambda: raw("net_income") / positive("total_assets"),
        "profitability_attributable_income_to_equity": lambda: raw("net_income_attributable") / positive("total_equity"),
        "cash_flow_ocf_to_net_income": lambda: raw("operating_cash_flow") / positive("net_income"),
        "cash_flow_ocf_to_revenue": lambda: raw("operating_cash_flow") / positive("revenue"),
        "margin_net_income_to_revenue": lambda: raw("net_income") / positive("revenue"),
        "yoy_revenue": lambda: raw("revenue") / positive("prior:revenue") - 1.0,
        "yoy_net_income": lambda: raw("net_income") / positive("prior:net_income") - 1.0,
        "yoy_total_assets": lambda: raw("total_assets") / positive("prior:total_assets") - 1.0,
    }
    if feature.feature_id not in formulas:
        raise ValueError(f"unrecognized frozen feature: {feature.feature_id}")
    value = float(formulas[feature.feature_id]())
    if not math.isfinite(value):
        raise ValueError(f"non-finite feature value: {feature.feature_id}")
    return value


def _current_period_metadata(version: _Version) -> tuple[str | None, str | None, str | None, str, str]:
    facts = [fact for rows in version.facts.values() for fact in rows]
    verified = [fact for fact in facts if fact.period_bounds_verified]
    if not verified:
        return None, None, None, "", ""
    starts = {fact.period_start for fact in verified if fact.period_start}
    ends = {fact.period_end for fact in verified if fact.period_end}
    instants = {fact.instant_date for fact in verified if fact.instant_date}
    kinds = {fact.period_evidence_kind for fact in verified if fact.period_evidence_kind}
    locations = {fact.period_evidence_location for fact in verified if fact.period_evidence_location}
    return (
        sorted(starts)[0] if starts else None,
        sorted(ends)[0] if ends else None,
        sorted(instants)[0] if instants else None,
        ";".join(sorted(kinds)),
        ";".join(sorted(locations)),
    )


def _selected_for_ticker(
    versions: Mapping[tuple[str, int, str, str], list[_Version]],
    ticker: str,
    as_of: datetime,
) -> list[_Version]:
    selected: list[_Version] = []
    for key in sorted(versions):
        if key[0] != ticker or key[3] not in MODEL_SAFE_SCOPES:
            continue
        current, status = _select_version(versions, key, as_of)
        if current is not None and status is None and current.industry_class in MODEL_SAFE_INDUSTRIES:
            selected.append(current)
    return selected


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(_json(dict(row)) + "\n")


def _provenance_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Keep the materialized-value sidecar complete but compact."""

    fields = (
        "ticker", "decision_date", "as_of_timestamp_utc", "fiscal_year", "fiscal_period",
        "period_stratification_key", "statement_scope", "industry_class", "feature_id",
        "feature_value", "reporting_version_id", "reporting_attachment_sha256",
        "reporting_publication_at_utc", "reporting_knowledge_at_utc", "reporting_period_start",
        "reporting_period_end", "reporting_instant_date", "reporting_period_evidence_kind",
        "reporting_period_evidence_location", "input_version_ids_json", "input_attachment_sha256s_json",
        "input_publication_at_utc_json", "input_knowledge_at_utc_json", "input_period_boundaries_json",
        "input_fact_identities_json", "input_source_refs_json", "input_source_locations_json",
        "feature_contract_version",
    )
    return {field: row[field] for field in fields}


def _load_boundaries(
    path: Path,
    manifest_path: Path,
    diagnostics_path: Path,
    facts_path: Path,
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Any]]:
    validation = validate_period_sidecar(path, manifest_path, diagnostics_path, facts_path)
    rows = _load_jsonl(path)
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        version_id = str(row.get("version_id") or "")
        if not version_id or version_id in result:
            raise ValueError(f"duplicate/missing period boundary version: {version_id}")
        result[version_id] = row
    return result, validation


def _diagnostic_metadata(rows: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        version_id = str(row.get("version_id") or "")
        if not version_id:
            raise ValueError("diagnostic row missing version_id")
        if version_id in result and dict(result[version_id]) != dict(row):
            raise ValueError(f"conflicting diagnostic metadata: {version_id}")
        result[version_id] = row
    return result


def _build_rows(
    versions: Mapping[tuple[str, int, str, str], list[_Version]],
    diagnostic_by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    allowed_versions = [
        version
        for rows in versions.values()
        for version in rows
        if version.scope in MODEL_SAFE_SCOPES and version.industry_class in MODEL_SAFE_INDUSTRIES
    ]
    events: dict[datetime, set[str]] = defaultdict(set)
    for version in allowed_versions:
        events[version.knowledge_at].add(version.ticker)

    rows: list[dict[str, Any]] = []
    for as_of in sorted(events):
        timestamp = _iso(as_of)
        decision_date = as_of.date().isoformat()
        for ticker in sorted(events[as_of]):
            for current in _selected_for_ticker(versions, ticker, as_of):
                diagnostic = diagnostic_by_id[current.version_id]
                start, end, instant, evidence_kind, evidence_location = _current_period_metadata(current)
                current_age = (as_of - current.knowledge_at).total_seconds() / 86400.0
                for feature in FEATURE_DEFINITIONS:
                    availability = _availability(feature, current, versions, as_of=as_of)
                    input_facts: list[_Fact] = []
                    feature_value: float | None = None
                    if availability.status is AvailabilityStatus.AVAILABLE:
                        input_facts = _version_facts(current, feature, versions, as_of, availability)
                        feature_value = _calculate(feature, input_facts)
                    input_versions = [fact.version_id for fact in input_facts]
                    input_attachments = [fact.attachment_sha256 for fact in input_facts]
                    input_publication = [
                        str(diagnostic_by_id[fact.version_id].get("publication_at_utc") or "")
                        for fact in input_facts
                    ]
                    input_knowledge = [_iso(fact.knowledge_at) for fact in input_facts]
                    input_boundaries = [
                        {
                            "fact_identity": fact.fact_identity,
                            "period_shape": fact.period_shape.value if fact.period_shape else None,
                            "period_start": fact.period_start,
                            "period_end": fact.period_end,
                            "instant_date": fact.instant_date,
                            "period_bounds_verified": fact.period_bounds_verified,
                            "period_evidence_kind": fact.period_evidence_kind,
                            "period_evidence_location": fact.period_evidence_location,
                        }
                        for fact in input_facts
                    ]
                    input_payloads = [_fact_payload(fact) for fact in input_facts]
                    rows.append(
                        {
                            "ticker": ticker,
                            "decision_date": decision_date,
                            "as_of_timestamp_utc": timestamp,
                            "fiscal_year": current.fiscal_year,
                            "fiscal_period": current.fiscal_period,
                            "period_stratification_key": availability.period_stratification_key,
                            "statement_scope": current.scope,
                            "industry_class": current.industry_class,
                            "representation_format": current.representation_format,
                            "reporting_version_id": current.version_id,
                            "reporting_attachment_sha256": current.attachment_sha256,
                            "reporting_publication_at_utc": str(diagnostic.get("publication_at_utc") or ""),
                            "reporting_knowledge_at_utc": _iso(current.knowledge_at),
                            "reporting_period_start": start,
                            "reporting_period_end": end,
                            "reporting_instant_date": instant,
                            "reporting_period_evidence_kind": evidence_kind,
                            "reporting_period_evidence_location": evidence_location,
                            "feature_id": feature.feature_id,
                            "feature_family": feature.family.value,
                            "feature_formula": feature.formula,
                            "feature_value": feature_value,
                            "availability_status": availability.status.value,
                            "availability_reason": availability.reason,
                            "current_filing_age_days": round(current_age, 9),
                            "input_version_ids_json": _json(input_versions),
                            "input_attachment_sha256s_json": _json(input_attachments),
                            "input_publication_at_utc_json": _json(input_publication),
                            "input_knowledge_at_utc_json": _json(input_knowledge),
                            "input_period_boundaries_json": _json(input_boundaries),
                            "input_fact_identities_json": _json([fact.fact_identity for fact in input_facts]),
                            "input_source_refs_json": _json([fact.source_ref for fact in input_facts]),
                            "input_source_locations_json": _json([fact.source_location for fact in input_facts]),
                            "input_fact_provenance_json": _json(input_payloads),
                            "feature_contract_version": CONTRACT_VERSION,
                        }
                    )

    rows.sort(key=lambda row: (
        row["ticker"], row["as_of_timestamp_utc"], row["fiscal_year"],
        row["fiscal_period"], row["reporting_version_id"], row["feature_id"],
    ))

    transitions: list[dict[str, Any]] = []
    for key, candidates in sorted(versions.items()):
        eligible = [item for item in candidates if item.scope in MODEL_SAFE_SCOPES and item.industry_class in MODEL_SAFE_INDUSTRIES]
        eligible.sort(key=lambda item: (item.knowledge_at, item.version_id))
        for prior, newer in zip(eligible, eligible[1:]):
            if prior.attachment_sha256 != newer.attachment_sha256 or prior.version_id != newer.version_id:
                transitions.append({
                    "ticker": key[0],
                    "fiscal_year": key[1],
                    "fiscal_period": key[2],
                    "statement_scope": key[3],
                    "prior_version_id": prior.version_id,
                    "new_version_id": newer.version_id,
                    "prior_attachment_sha256": prior.attachment_sha256,
                    "new_attachment_sha256": newer.attachment_sha256,
                    "prior_knowledge_at_utc": _iso(prior.knowledge_at),
                    "new_knowledge_at_utc": _iso(newer.knowledge_at),
                })
    return rows, transitions, [{"as_of_timestamp_utc": _iso(item)} for item in sorted(events)]


def _coverage_summary(panel: pd.DataFrame) -> dict[str, Any]:
    if panel.empty:
        return {"rows": 0, "unique_ticker_decision_dates": 0, "unique_ticker_as_of_timestamps": 0}
    status_by_feature = {
        feature: dict(sorted(group["availability_status"].value_counts().to_dict().items()))
        for feature, group in panel.groupby("feature_id", sort=True)
    }
    available = panel[panel["availability_status"] == AvailabilityStatus.AVAILABLE.value]
    prov_fields = [
        "reporting_version_id", "reporting_attachment_sha256", "reporting_knowledge_at_utc",
        "input_version_ids_json", "input_attachment_sha256s_json", "input_knowledge_at_utc_json",
        "input_period_boundaries_json", "input_fact_identities_json", "input_source_refs_json",
        "input_source_locations_json", "input_fact_provenance_json", "feature_contract_version",
    ]
    full_prov = panel[prov_fields].notna().all(axis=1) & panel[prov_fields].astype(str).ne("").all(axis=1)
    available_prov = available[prov_fields].notna().all(axis=1) & available[prov_fields].astype(str).ne("").all(axis=1)
    future_input_count = 0
    input_age: list[float] = []
    for row in available.itertuples(index=False):
        as_of = _parse_timestamp(row.as_of_timestamp_utc)
        knowledge = json.loads(row.input_knowledge_at_utc_json)
        parsed = [_parse_timestamp(value) for value in knowledge if value]
        if any(value > as_of for value in parsed):
            future_input_count += 1
        input_age.extend((as_of - value).total_seconds() / 86400.0 for value in parsed)
    age = panel["current_filing_age_days"].astype(float)
    supported_periods = {"Q1", "H1", "9M", "FY"}
    duration_sensitive = {
        "size_log_revenue", "profitability_net_income_to_assets",
        "profitability_attributable_income_to_equity", "cash_flow_ocf_to_net_income",
        "cash_flow_ocf_to_revenue", "margin_net_income_to_revenue",
        "yoy_revenue", "yoy_net_income",
    }
    duration_rows = available[available["feature_id"].isin(duration_sensitive)]
    period_consistency = bool(
        available["period_stratification_key"].isin(supported_periods).all()
        and duration_rows["period_stratification_key"].isin(supported_periods).all()
    )
    by_period = (
        panel.groupby(["period_stratification_key", "feature_id", "availability_status"], dropna=False, sort=True)
        .size().reset_index(name="rows").to_dict(orient="records")
    )
    by_date = (
        panel.groupby("decision_date", sort=True)
        .agg(rows=("feature_id", "size"), issuers=("ticker", "nunique"), available=("feature_value", lambda values: values.notna().sum()))
        .reset_index().to_dict(orient="records")
    )
    by_year = (
        panel.assign(decision_year=panel["decision_date"].str[:4])
        .groupby("decision_year", sort=True)
        .agg(rows=("feature_id", "size"), issuers=("ticker", "nunique"), available=("feature_value", lambda values: values.notna().sum()))
        .reset_index().to_dict(orient="records")
    )
    return {
        "rows": int(len(panel)),
        "unique_ticker_decision_dates": int(panel[["ticker", "decision_date"]].drop_duplicates().shape[0]),
        "unique_ticker_as_of_timestamps": int(panel[["ticker", "as_of_timestamp_utc"]].drop_duplicates().shape[0]),
        "unique_issuers": int(panel["ticker"].nunique()),
        "unique_decision_dates": int(panel["decision_date"].nunique()),
        "status_by_feature": status_by_feature,
        "coverage_by_period_feature_status": by_period,
        "coverage_by_decision_date": by_date,
        "coverage_by_decision_year": by_year,
        "available_rows": int(len(available)),
        "available_provenance_complete_rows": int(available_prov.sum()),
        "all_rows_reporting_provenance_complete": int(full_prov.sum()),
        "provenance_completeness": {
            "all_rows_fraction": round(float(full_prov.mean()), 9),
            "available_rows_fraction": round(float(available_prov.mean()), 9) if len(available) else 1.0,
        },
        "knowledge_time_violations": future_input_count,
        "period_strata_consistency_pass": bool(period_consistency),
        "period_strata_policy": "each row retains one exact Q1/H1/9M/FY stratum; multiple reporting periods may coexist in a sparse issuer snapshot, but no feature calculation pools them",
        "current_filing_age_days": {
            "min": round(float(age.min()), 9),
            "median": round(float(age.median()), 9),
            "max": round(float(age.max()), 9),
        },
        "input_filing_age_days": {
            "min": round(min(input_age), 9) if input_age else None,
            "median": round(float(pd.Series(input_age).median()), 9) if input_age else None,
            "max": round(max(input_age), 9) if input_age else None,
        },
    }


def _manifest(output_root: Path, source_artifacts: Mapping[str, Any], files: Iterable[str], metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "manifest_version": PANEL_VERSION,
        "contract_version": CONTRACT_VERSION,
        "files": {
            name: {"bytes": (output_root / name).stat().st_size, "sha256": _sha256_file(output_root / name)}
            for name in sorted(files)
        },
        "source_artifacts": dict(source_artifacts),
        "metadata": dict(metadata),
        "network_calls": 0,
        "protected_outcomes_accessed": False,
        "model_work": False,
    }


def materialize_financial_feature_panel(
    fact_records_path: Path,
    filing_diagnostics_path: Path,
    period_boundaries_path: Path,
    period_boundaries_manifest_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Materialize one deterministic offline feature-panel artifact set."""

    if output_root.exists() and any(output_root.iterdir()):
        raise ValueError(f"output root must be new and empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    facts = _load_jsonl(fact_records_path)
    diagnostics = _load_jsonl(filing_diagnostics_path)
    boundaries, boundary_validation = _load_boundaries(
        period_boundaries_path, period_boundaries_manifest_path, filing_diagnostics_path, fact_records_path
    )
    versions = _build_versions(facts, diagnostics, boundaries)
    diagnostic_by_id = _diagnostic_metadata(diagnostics)
    rows, transitions, decision_timestamps = _build_rows(versions, diagnostic_by_id)
    unresolved_boundary_rows = sum(
        1
        for version_rows in versions.values()
        for version in version_rows
        for fact_rows in version.facts.values()
        for fact in fact_rows
        if not fact.period_bounds_verified
    )
    panel = pd.DataFrame(rows, columns=PANEL_COLUMNS)
    panel_path = output_root / "feature_panel.parquet"
    panel.to_parquet(panel_path, index=False)
    provenance_path = output_root / "feature_provenance.jsonl"
    # Only materialized feature values need the expanded fact-level sidecar.
    # The panel itself retains reporting provenance and explicit status/reason
    # for every unavailable row, without duplicating hundreds of megabytes of
    # empty-input JSON.
    _write_jsonl(
        provenance_path,
        (_provenance_row(row) for row in rows if row["availability_status"] == AvailabilityStatus.AVAILABLE.value),
    )
    transitions_path = output_root / "revision_transitions.jsonl"
    _write_jsonl(transitions_path, transitions)
    decision_path = output_root / "decision_timestamps.jsonl"
    _write_jsonl(decision_path, decision_timestamps)
    # The DataFrame is now the canonical in-memory representation.  Release
    # the large construction list before the audit/manifest pass.
    del rows
    audit = {
        "status": "FINANCIAL_PIT_FEATURE_PANEL_MATERIALIZED",
        "panel_version": PANEL_VERSION,
        "contract_version": CONTRACT_VERSION,
        "model_safe_scope": {"industries": list(MODEL_SAFE_INDUSTRIES), "statement_scopes": list(MODEL_SAFE_SCOPES)},
        "source_filing_versions": len({version.version_id for rows in versions.values() for version in rows}),
        "source_logical_keys": len(versions),
        "selected_source_versions": int(panel["reporting_version_id"].nunique()) if not panel.empty else 0,
        "features": [feature.feature_id for feature in FEATURE_DEFINITIONS],
        "unresolved_period_boundary_rows_excluded": unresolved_boundary_rows,
        "coverage": _coverage_summary(panel),
        "revision_audit": {
            "transition_count": len(transitions),
            "logical_keys_with_transition": len({(row["ticker"], row["fiscal_year"], row["fiscal_period"], row["statement_scope"]) for row in transitions}),
        },
        "boundary_validation": boundary_validation,
        "as_of_contract": {
            "decision_timeline": "exact UTC filing knowledge timestamps; sparse change-point snapshots, no invented daily timestamps",
            "future_versions_excluded": True,
            "later_revisions_replace_from_own_knowledge_timestamp": True,
            "knowledge_time_violations": int(_coverage_summary(panel).get("knowledge_time_violations", 0)),
        },
        "period_policy": "Q1/H1/9M/FY remain stratified cumulative source periods; no pooling, annualization, TTM, interpolation, zero-fill, or carry-forward",
        "provenance_policy": "every row carries reporting and input version, hash, time, period-boundary, fact-identity, and source-location provenance",
        "network_calls": 0,
        "protected_outcomes_accessed": False,
        "model_work": False,
    }
    audit_path = output_root / "audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    source_artifacts = {
        "fact_records": {"path": str(fact_records_path), "sha256": _sha256_file(fact_records_path)},
        "filing_diagnostics": {"path": str(filing_diagnostics_path), "sha256": _sha256_file(filing_diagnostics_path)},
        "period_boundaries": {"path": str(period_boundaries_path), "sha256": _sha256_file(period_boundaries_path)},
        "period_boundaries_manifest": {"path": str(period_boundaries_manifest_path), "sha256": _sha256_file(period_boundaries_manifest_path)},
    }
    metadata = {
        "rows": len(panel),
        "tickers": int(panel["ticker"].nunique()) if not panel.empty else 0,
        "decision_dates": int(panel["decision_date"].nunique()) if not panel.empty else 0,
        "revision_transitions": len(transitions),
    }
    manifest_files = ["audit.json", "decision_timestamps.jsonl", "feature_panel.parquet", "feature_provenance.jsonl", "revision_transitions.jsonl"]
    manifest = _manifest(output_root, source_artifacts, manifest_files, metadata)
    manifest_path = output_root / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": audit["status"],
        "rows": len(panel),
        "tickers": metadata["tickers"],
        "decision_dates": metadata["decision_dates"],
        "audit": audit,
        "artifact_hashes": {name: _sha256_file(output_root / name) for name in manifest_files + ["MANIFEST.json"]},
        "manifest_sha256": _sha256_file(manifest_path),
        "manifest_path": str(manifest_path),
    }


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fact-records", type=Path, required=True)
    parser.add_argument("--filing-diagnostics", type=Path, required=True)
    parser.add_argument("--period-boundaries", type=Path, required=True)
    parser.add_argument("--period-boundaries-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = materialize_financial_feature_panel(
        args.fact_records, args.filing_diagnostics, args.period_boundaries,
        args.period_boundaries_manifest, args.output_root,
    )
    print(json.dumps({key: value for key, value in result.items() if key != "audit"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())


__all__ = ["PANEL_VERSION", "PANEL_COLUMNS", "materialize_financial_feature_panel"]
