"""Offline forensic replay for V4 Voluntary Conversion semantics.

This module does not introduce a new corporate-action semantic rule.  It only
checks whether the already-frozen voluntary security-to-currency remediation
was applied and reported consistently.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable, Mapping

import pandas as pd

from idx_trade.v4_ca_event_windows import (
    EventSemantic,
    classify_event as classify_parent,
    event_identity,
)
from idx_trade.v4_ca_voluntary_conversion_semantics import (
    classify_event as classify_remediated,
    is_exact_security_to_currency_voluntary_conversion,
)


VERDICT_CONFIRMED_REPORTING_UNDERCOUNT = (
    "FORENSIC_REPLAY_CONFIRMS_VOLUNTARY_CASH_RECLASSIFICATION_REPORTING_UNDERCOUNT"
)
VERDICT_ZERO_RECLASS_IDENTITY = "FORENSIC_REPLAY_ZERO_RECLASS_IDENTITY_PASS"
VERDICT_INCONSISTENT = "FORENSIC_REPLAY_INCONSISTENT_BLOCKED"


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _date_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return pd.Timestamp(value).date().isoformat()


def _semantic_row(event: EventSemantic) -> dict[str, Any]:
    row = asdict(event)
    row["transition_date"] = _date_text(event.transition_date)
    row["source_dates"] = "|".join(_date_text(value) for value in event.source_dates)
    return row


def build_history_identity_map(
    history_rows: Iterable[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in history_rows:
        identity = event_identity(row)
        if identity in result:
            raise RuntimeError(f"DUPLICATE_HISTORY_EVENT_ID:{identity}")
        result[identity] = row
    return result


def replay_parent_relevant_events(
    *,
    history_rows: Iterable[Mapping[str, Any]],
    official_sessions: Iterable[Any],
    parent_audit: pd.DataFrame,
    remediation_audit: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Replay both classifiers on the exact immutable parent-relevant rows."""

    required = {"event_id", "ticker", "source_type", "semantic_class", "family"}
    for label, frame in (("parent", parent_audit), ("remediation", remediation_audit)):
        missing = required - set(frame.columns)
        if missing:
            raise RuntimeError(f"{label.upper()}_AUDIT_COLUMNS_MISSING:{sorted(missing)}")
        if frame["event_id"].duplicated().any():
            raise RuntimeError(f"{label.upper()}_AUDIT_DUPLICATE_EVENT_ID")

    parent_ids = set(parent_audit["event_id"].astype(str))
    remediation_ids = set(remediation_audit["event_id"].astype(str))
    removed_ids = parent_ids - remediation_ids
    added_ids = remediation_ids - parent_ids

    history_map = build_history_identity_map(history_rows)
    missing_history = sorted(parent_ids - set(history_map))
    if missing_history:
        raise RuntimeError(f"PARENT_EVENT_ID_NOT_IN_IMMUTABLE_HISTORY:{missing_history[:5]}")

    sessions = list(official_sessions)
    side_rows: list[dict[str, Any]] = []
    voluntary_rows: list[dict[str, Any]] = []
    reclassified_nonblocking_ids: set[str] = set()

    parent_by_id = parent_audit.set_index("event_id", drop=False)
    remediation_by_id = remediation_audit.set_index("event_id", drop=False)

    for identity in sorted(parent_ids):
        source = history_map[identity]
        parent = classify_parent(source, official_sessions=sessions, schedule_evidence=())
        remediated = classify_remediated(
            source, official_sessions=sessions, schedule_evidence=()
        )
        if parent.event_id != identity or remediated.event_id != identity:
            raise RuntimeError(f"CLASSIFIER_EVENT_ID_DRIFT:{identity}")

        parent_artifact = parent_by_id.loc[identity]
        if (
            _text(parent_artifact["semantic_class"]) != parent.semantic_class
            or _text(parent_artifact["family"]) != parent.family
        ):
            raise RuntimeError(f"PARENT_CLASSIFIER_ARTIFACT_MISMATCH:{identity}")

        retained = identity in remediation_ids
        if retained:
            remediation_artifact = remediation_by_id.loc[identity]
            if (
                _text(remediation_artifact["semantic_class"])
                != remediated.semantic_class
                or _text(remediation_artifact["family"]) != remediated.family
            ):
                raise RuntimeError(
                    f"REMEDIATION_CLASSIFIER_ARTIFACT_MISMATCH:{identity}"
                )

        strict_cash = is_exact_security_to_currency_voluntary_conversion(source)
        if parent.semantic_class != "NON_BLOCKING" and remediated.semantic_class == "NON_BLOCKING":
            reclassified_nonblocking_ids.add(identity)

        common = {
            "event_id": identity,
            "ticker": _text(source.get("ticker")).upper(),
            "row_index": source.get("row_index"),
            "source_type": _text(source.get("event_family_source")),
            "status": _text(source.get("status")),
            "ratio_raw": _text(source.get("ratio_raw")),
            "ratio_parse_status": _text(source.get("ratio_parse_status")),
            "ratio_left_security": _text(source.get("ratio_left_security")),
            "ratio_right_security": _text(source.get("ratio_right_security")),
            "strict_security_to_currency_predicate": bool(strict_cash),
            "present_in_parent_audit": True,
            "present_in_remediation_audit": retained,
            "removed_from_relevant_audit": identity in removed_ids,
            "parent_family": parent.family,
            "parent_semantic_class": parent.semantic_class,
            "parent_transition_date": _date_text(parent.transition_date),
            "remediation_family": remediated.family,
            "remediation_semantic_class": remediated.semantic_class,
            "remediation_transition_date": _date_text(remediated.transition_date),
            "remediation_reason": remediated.reason,
        }
        side_rows.append(common)
        if common["source_type"].casefold() == "voluntary conversion":
            voluntary_rows.append(common)

    side = pd.DataFrame(side_rows).sort_values(
        ["ticker", "row_index", "event_id"], kind="mergesort"
    ).reset_index(drop=True)
    voluntary = pd.DataFrame(voluntary_rows).sort_values(
        ["ticker", "row_index", "event_id"], kind="mergesort"
    ).reset_index(drop=True)

    diff_rows: list[dict[str, Any]] = []
    for identity in sorted(removed_ids | added_ids):
        relation = "REMOVED_FROM_REMEDIATION_AUDIT" if identity in removed_ids else "ADDED_IN_REMEDIATION_AUDIT"
        source = history_map.get(identity, {})
        matching = side[side["event_id"].eq(identity)]
        diff_rows.append(
            {
                "event_id": identity,
                "relation": relation,
                "ticker": _text(source.get("ticker")).upper(),
                "source_type": _text(source.get("event_family_source")),
                "ratio_raw": _text(source.get("ratio_raw")),
                "ratio_parse_status": _text(source.get("ratio_parse_status")),
                "ratio_left_security": _text(source.get("ratio_left_security")),
                "ratio_right_security": _text(source.get("ratio_right_security")),
                "strict_security_to_currency_predicate": (
                    bool(matching.iloc[0]["strict_security_to_currency_predicate"])
                    if len(matching)
                    else False
                ),
                "parent_semantic_class": (
                    _text(matching.iloc[0]["parent_semantic_class"])
                    if len(matching)
                    else ""
                ),
                "remediation_semantic_class": (
                    _text(matching.iloc[0]["remediation_semantic_class"])
                    if len(matching)
                    else ""
                ),
            }
        )
    diff = pd.DataFrame(diff_rows)
    if diff.empty:
        diff = pd.DataFrame(
            columns=[
                "event_id",
                "relation",
                "ticker",
                "source_type",
                "ratio_raw",
                "ratio_parse_status",
                "ratio_left_security",
                "ratio_right_security",
                "strict_security_to_currency_predicate",
                "parent_semantic_class",
                "remediation_semantic_class",
            ]
        )

    removed_equals_reclassified = removed_ids == reclassified_nonblocking_ids
    all_removed_strict_cash = bool(removed_ids) and all(
        bool(side.loc[side["event_id"].eq(identity), "strict_security_to_currency_predicate"].iloc[0])
        and _text(side.loc[side["event_id"].eq(identity), "source_type"].iloc[0]).casefold()
        == "voluntary conversion"
        for identity in removed_ids
    )

    summary = {
        "parent_relevant_event_count": len(parent_ids),
        "remediation_relevant_event_count": len(remediation_ids),
        "removed_event_count": len(removed_ids),
        "added_event_count": len(added_ids),
        "parent_relevant_voluntary_conversion_count": int(len(voluntary)),
        "strict_cash_predicate_count": int(
            voluntary["strict_security_to_currency_predicate"].sum()
        ) if len(voluntary) else 0,
        "reclassified_to_nonblocking_count": len(reclassified_nonblocking_ids),
        "remaining_voluntary_schedule_required_count": int(
            (
                voluntary["remediation_semantic_class"].eq("SCHEDULE_REQUIRED")
            ).sum()
        ) if len(voluntary) else 0,
        "removed_ids_equal_reclassified_nonblocking_ids": removed_equals_reclassified,
        "all_removed_ids_are_strict_voluntary_cash": all_removed_strict_cash,
        "added_ids_empty": not added_ids,
    }

    if not reclassified_nonblocking_ids:
        identity_pass = parent_ids == remediation_ids
        summary["zero_reclassification_event_identity_invariant"] = identity_pass
        verdict = VERDICT_ZERO_RECLASS_IDENTITY if identity_pass else VERDICT_INCONSISTENT
    else:
        summary["zero_reclassification_event_identity_invariant"] = None
        verdict = (
            VERDICT_CONFIRMED_REPORTING_UNDERCOUNT
            if removed_equals_reclassified and all_removed_strict_cash and not added_ids
            else VERDICT_INCONSISTENT
        )
    summary["verdict"] = verdict
    return side, voluntary, diff, summary


def compare_per_date_outputs(
    parent: pd.DataFrame,
    remediation: pd.DataFrame,
    *,
    reclassified_count: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Compare the promoted 600-date support outputs without outcome access."""

    if "date" not in parent.columns or "date" not in remediation.columns:
        raise RuntimeError("PER_DATE_DATE_COLUMN_MISSING")
    if parent["date"].duplicated().any() or remediation["date"].duplicated().any():
        raise RuntimeError("PER_DATE_DUPLICATE_DATE")
    left = parent.copy()
    right = remediation.copy()
    left["date"] = pd.to_datetime(left["date"], errors="raise").dt.normalize()
    right["date"] = pd.to_datetime(right["date"], errors="raise").dt.normalize()
    if set(left["date"]) != set(right["date"]):
        raise RuntimeError("PER_DATE_IDENTITY_CHANGED")
    merged = left.merge(right, on="date", suffixes=("_parent", "_remediation"), validate="one_to_one")

    comparable = [
        column
        for column in (
            "h5_decision_rows",
            "h5_resolved_rows",
            "h5_rate",
            "h5_gate",
            "h10_decision_rows",
            "h10_resolved_rows",
            "h10_rate",
            "h10_gate",
            "consensus_resolved_rows",
            "consensus_rate",
            "consensus_gate",
        )
        if column in left.columns and column in right.columns
    ]
    equality = pd.Series(True, index=merged.index)
    for column in comparable:
        a = merged[f"{column}_parent"]
        b = merged[f"{column}_remediation"]
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            equality &= a.fillna(float("inf")).eq(b.fillna(float("inf")))
        else:
            equality &= a.astype(str).eq(b.astype(str))
    merged["all_comparable_fields_equal"] = equality

    summary = {
        "date_count": int(len(merged)),
        "identical_date_rows": int(equality.sum()),
        "changed_date_rows": int((~equality).sum()),
        "zero_reclassification_continuity_identity_invariant": (
            bool(equality.all()) if reclassified_count == 0 else None
        ),
    }
    if reclassified_count == 0 and not bool(equality.all()):
        summary["verdict"] = VERDICT_INCONSISTENT
    return merged, summary
