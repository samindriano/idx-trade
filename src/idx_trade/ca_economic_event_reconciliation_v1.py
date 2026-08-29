"""Fail-closed economic-event reconciliation for INC-001 corporate actions.

This layer deliberately separates source-native corporate-action labels from
an economic-event taxonomy.  In particular, KSEI registered-security labels
``Mandatory Conversion`` and ``Voluntary Conversion`` are operational source
labels and are never promoted to economic conversion families without
source-bound adjudication.

The module is pure/local-only.  It performs no provider calls, does not touch
outcomes, and does not mutate canonical historical data.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import date
from typing import Any, Mapping, Sequence


SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")

KSEI_OPERATIONAL_LABELS = {
    "MANDATORY CONVERSION",
    "VOLUNTARY CONVERSION",
}
KSEI_OPERATIONAL_FAMILIES = {
    "MANDATORY_CONVERSION",
    "VOLUNTARY_CONVERSION",
}

BASIS_CHANGING_FAMILIES = {
    "BONUS_SHARES",
    "CAPITAL_RESTRUCTURING",
    "MANDATORY_CONVERSION",
    "MERGER",
    "REVERSE_SPLIT",
    "RIGHTS_HMETD",
    "STOCK_DIVIDEND",
    "STOCK_SPLIT",
    "TRUE_SECURITY_CONVERSION",
    "VOLUNTARY_CONVERSION",
}
NON_BASIS_FAMILIES = {
    "TENDER_OFFER_OR_CASH_PROCESS",
}
UNKNOWN_ECONOMIC_FAMILIES = {
    "",
    "UNKNOWN_TAXONOMY",
    "UNRESOLVED_OPERATIONAL_LABEL",
}

ACCEPTED_TRANSITION_SEMANTICS = {
    "REGULAR_MARKET_EX_DATE",
    "REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE",
}


class EconomicReconciliationError(ValueError):
    """Raised when evidence would otherwise be silently over-promoted."""


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _upper(value: Any) -> str:
    return _text(value).upper()


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value.strip()))


def _valid_iso_date(value: Any) -> bool:
    text = _text(value)
    if not text:
        return False
    try:
        date.fromisoformat(text[:10])
    except ValueError:
        return False
    return True


def _source_id(row: Mapping[str, Any]) -> str:
    return _text(
        row.get("source_event_id")
        or row.get("event_id")
        or row.get("raw_row_identity")
    )


def _source_kind(row: Mapping[str, Any]) -> str:
    return _upper(row.get("source_kind"))


def _source_native_label(row: Mapping[str, Any]) -> str:
    return _upper(
        row.get("source_native_label")
        or row.get("event_family_source")
        or row.get("source_action")
    )


def _declared_family(row: Mapping[str, Any]) -> str:
    return _upper(row.get("event_family") or row.get("economic_family"))


def _is_ksei_registered(row: Mapping[str, Any]) -> bool:
    return _source_kind(row).startswith("KSEI_REGISTERED_SECURITY")


def provisional_economic_family(row: Mapping[str, Any]) -> str:
    """Return a fail-closed provisional economic family.

    Existing V1.1 raw-source ledgers may carry ``MANDATORY_CONVERSION`` or
    ``VOLUNTARY_CONVERSION`` because those are KSEI source-native labels.  This
    successor layer intentionally refuses to interpret those operational labels
    as economic conversion families without separate source-bound evidence.
    """

    label = _source_native_label(row)
    family = _declared_family(row)
    if _is_ksei_registered(row) and (
        label in KSEI_OPERATIONAL_LABELS or family in KSEI_OPERATIONAL_FAMILIES
    ):
        return "UNRESOLVED_OPERATIONAL_LABEL"
    return family or "UNKNOWN_TAXONOMY"


def _provenance(row: Mapping[str, Any]) -> tuple[str, str]:
    source_ref = _text(
        row.get("authority_source_ref")
        or row.get("source_ref")
        or row.get("evidence_source_ref")
    )
    evidence_sha = _text(
        row.get("authority_evidence_sha256")
        or row.get("evidence_sha256")
        or row.get("source_sha256")
    ).lower()
    return source_ref, evidence_sha


def _normalize_adjudications(
    rows: Sequence[Mapping[str, Any]],
    source_ids: set[str],
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for raw in rows:
        status = _upper(raw.get("adjudication_status") or raw.get("status"))
        if status != "PROVEN":
            continue
        source_event_id = _source_id(raw)
        if not source_event_id or source_event_id not in source_ids:
            raise EconomicReconciliationError(
                "proven adjudication must reference an existing source_event_id"
            )
        family = _upper(raw.get("economic_family"))
        basis_effect = _upper(raw.get("basis_effect"))
        source_ref, evidence_sha = _provenance(raw)
        if not family or family in UNKNOWN_ECONOMIC_FAMILIES:
            raise EconomicReconciliationError(
                f"proven adjudication for {source_event_id} lacks an economic family"
            )
        if basis_effect not in {"BASIS_CHANGING", "NON_BASIS", "UNKNOWN"}:
            raise EconomicReconciliationError(
                f"invalid basis_effect for proven adjudication {source_event_id}"
            )
        if not source_ref or not valid_sha256(evidence_sha):
            raise EconomicReconciliationError(
                f"proven adjudication for {source_event_id} lacks source-bound provenance"
            )
        if family in NON_BASIS_FAMILIES and basis_effect != "NON_BASIS":
            raise EconomicReconciliationError(
                f"non-basis family {family} cannot be adjudicated as {basis_effect}"
            )
        if family in BASIS_CHANGING_FAMILIES and basis_effect == "NON_BASIS":
            raise EconomicReconciliationError(
                f"basis-changing family {family} cannot be adjudicated NON_BASIS"
            )
        normalized = {
            "source_event_id": source_event_id,
            "economic_family": family,
            "basis_effect": basis_effect,
            "authority_source_ref": source_ref,
            "authority_evidence_sha256": evidence_sha,
        }
        old = result.get(source_event_id)
        if old and old != normalized:
            raise EconomicReconciliationError(
                f"conflicting proven adjudications for {source_event_id}"
            )
        result[source_event_id] = normalized
    return result


class _UnionFind:
    def __init__(self, values: Sequence[str]):
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        keep, merge = sorted((left_root, right_root))
        self.parent[merge] = keep


def _normalize_linkages(
    rows: Sequence[Mapping[str, Any]],
    source_ids: set[str],
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw in rows:
        relation = _upper(raw.get("relation") or raw.get("linkage_status"))
        if relation != "PROVEN_SAME_ECONOMIC_EVENT":
            continue
        left = _text(raw.get("left_source_event_id") or raw.get("source_event_id_left"))
        right = _text(raw.get("right_source_event_id") or raw.get("source_event_id_right"))
        if not left or not right or left == right:
            raise EconomicReconciliationError("proven same-event linkage needs two distinct source ids")
        if left not in source_ids or right not in source_ids:
            raise EconomicReconciliationError("proven linkage references an unknown source event")
        source_ref, evidence_sha = _provenance(raw)
        if not source_ref or not valid_sha256(evidence_sha):
            raise EconomicReconciliationError("proven linkage lacks source-bound provenance")
        pair = tuple(sorted((left, right)))
        if pair in seen:
            continue
        seen.add(pair)
        result.append(
            {
                "left_source_event_id": pair[0],
                "right_source_event_id": pair[1],
                "relation": relation,
                "authority_source_ref": source_ref,
                "authority_evidence_sha256": evidence_sha,
            }
        )
    return result


def _normalize_transitions(
    rows: Sequence[Mapping[str, Any]],
    source_ids: set[str],
) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for raw in rows:
        status = _upper(raw.get("transition_status") or raw.get("status"))
        if status != "RESOLVED":
            continue
        source_event_id = _source_id(raw)
        if not source_event_id or source_event_id not in source_ids:
            raise EconomicReconciliationError(
                "resolved transition must reference an existing source_event_id"
            )
        semantic = _upper(raw.get("transition_semantic"))
        transition_date = _text(raw.get("transition_date"))[:10]
        source_ref, evidence_sha = _provenance(raw)
        if semantic not in ACCEPTED_TRANSITION_SEMANTICS:
            raise EconomicReconciliationError(
                f"resolved transition for {source_event_id} uses unaccepted semantic {semantic!r}"
            )
        if not _valid_iso_date(transition_date):
            raise EconomicReconciliationError(
                f"resolved transition for {source_event_id} lacks a valid transition date"
            )
        if not source_ref or not valid_sha256(evidence_sha):
            raise EconomicReconciliationError(
                f"resolved transition for {source_event_id} lacks source-bound provenance"
            )
        result[source_event_id].append(
            {
                "source_event_id": source_event_id,
                "transition_semantic": semantic,
                "transition_date": transition_date,
                "authority_source_ref": source_ref,
                "authority_evidence_sha256": evidence_sha,
            }
        )
    return result


def _basis_effect_for_family(family: str) -> str:
    if family in NON_BASIS_FAMILIES:
        return "NON_BASIS"
    if family in BASIS_CHANGING_FAMILIES:
        return "BASIS_CHANGING"
    return "UNKNOWN"


def _component_identity(members: Sequence[str], source_rows: Mapping[str, Mapping[str, Any]]) -> str:
    explicit: set[str] = set()
    for member in members:
        row = source_rows[member]
        value = _text(row.get("economic_event_id") or row.get("underlying_event_id"))
        if value:
            explicit.add(value)
    if len(explicit) > 1:
        raise EconomicReconciliationError(
            f"linked component carries conflicting explicit economic event ids: {sorted(explicit)}"
        )
    if explicit:
        return next(iter(explicit))
    payload = "\n".join(sorted(members)).encode("utf-8")
    return "DERIVED-" + hashlib.sha256(payload).hexdigest()


def reconcile_economic_events(
    source_rows: Sequence[Mapping[str, Any]],
    *,
    adjudications: Sequence[Mapping[str, Any]] = (),
    linkages: Sequence[Mapping[str, Any]] = (),
    transition_attestations: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Reconcile source representations into economic events, fail closed.

    ``source_rows`` remain immutable evidence.  Rows are collapsed only through
    ``PROVEN_SAME_ECONOMIC_EVENT`` linkages with valid source reference + SHA.
    KSEI operational conversion labels do not decide economic taxonomy.
    """

    by_id: dict[str, Mapping[str, Any]] = {}
    for raw in source_rows:
        source_event_id = _source_id(raw)
        if not source_event_id:
            raise EconomicReconciliationError("every source row requires source_event_id")
        if source_event_id in by_id:
            raise EconomicReconciliationError(f"duplicate source_event_id {source_event_id}")
        if not _source_kind(raw):
            raise EconomicReconciliationError(f"source row {source_event_id} lacks source_kind")
        by_id[source_event_id] = raw

    source_ids = set(by_id)
    adjudication_by_id = _normalize_adjudications(adjudications, source_ids)
    normalized_linkages = _normalize_linkages(linkages, source_ids)
    transition_by_id = _normalize_transitions(transition_attestations, source_ids)

    union = _UnionFind(sorted(source_ids))
    for row in normalized_linkages:
        union.union(row["left_source_event_id"], row["right_source_event_id"])

    components: dict[str, list[str]] = defaultdict(list)
    for source_event_id in sorted(source_ids):
        components[union.find(source_event_id)].append(source_event_id)

    economic_events: list[dict[str, Any]] = []
    cross_source_collapses = 0
    same_source_collapses = 0

    for _, members in sorted(components.items(), key=lambda item: sorted(item[1])):
        members = sorted(members)
        kinds: dict[str, int] = defaultdict(int)
        for member in members:
            kinds[_source_kind(by_id[member])] += 1
        same_source_collapses += sum(max(count - 1, 0) for count in kinds.values())
        cross_source_collapses += max(len(kinds) - 1, 0)

        proven_families = {
            adjudication_by_id[member]["economic_family"]
            for member in members
            if member in adjudication_by_id
        }
        proven_effects = {
            adjudication_by_id[member]["basis_effect"]
            for member in members
            if member in adjudication_by_id
        }

        classification_conflict = False
        if len(proven_families) > 1:
            family = "CONFLICTING_ECONOMIC_CLASSIFICATION"
            classification_conflict = True
        elif proven_families:
            family = next(iter(proven_families))
        else:
            provisional = {provisional_economic_family(by_id[member]) for member in members}
            specific = provisional - UNKNOWN_ECONOMIC_FAMILIES
            if len(specific) > 1:
                family = "CONFLICTING_ECONOMIC_CLASSIFICATION"
                classification_conflict = True
            elif len(specific) == 1:
                family = next(iter(specific))
            elif "UNRESOLVED_OPERATIONAL_LABEL" in provisional:
                family = "UNRESOLVED_OPERATIONAL_LABEL"
            else:
                family = "UNKNOWN_TAXONOMY"

        if classification_conflict or len(proven_effects) > 1:
            basis_effect = "UNKNOWN"
            classification_conflict = True
        elif proven_effects:
            basis_effect = next(iter(proven_effects))
        else:
            basis_effect = _basis_effect_for_family(family)

        transition_rows = [
            row
            for member in members
            for row in transition_by_id.get(member, [])
        ]
        if basis_effect == "NON_BASIS":
            transition_status = "NOT_APPLICABLE_NON_BASIS"
            transition_date = ""
            transition_semantics: list[str] = []
        elif classification_conflict:
            transition_status = "UNRESOLVED_CLASSIFICATION_CONFLICT"
            transition_date = ""
            transition_semantics = []
        elif transition_rows:
            dates = {row["transition_date"] for row in transition_rows}
            if len(dates) == 1:
                transition_status = "RESOLVED"
                transition_date = next(iter(dates))
                transition_semantics = sorted({row["transition_semantic"] for row in transition_rows})
            else:
                transition_status = "UNRESOLVED_TRANSITION_CONFLICT"
                transition_date = ""
                transition_semantics = sorted({row["transition_semantic"] for row in transition_rows})
        else:
            transition_status = "UNRESOLVED"
            transition_date = ""
            transition_semantics = []

        economic_events.append(
            {
                "economic_event_id": _component_identity(members, by_id),
                "source_event_ids": members,
                "source_kinds": sorted(kinds),
                "economic_family": family,
                "basis_effect": basis_effect,
                "classification_conflict": classification_conflict,
                "transition_status": transition_status,
                "transition_date": transition_date,
                "transition_semantics": transition_semantics,
            }
        )

    resolved = sum(row["transition_status"] == "RESOLVED" for row in economic_events)
    non_basis = sum(row["transition_status"] == "NOT_APPLICABLE_NON_BASIS" for row in economic_events)
    unresolved = len(economic_events) - resolved - non_basis

    expected_economic = len(source_rows) - cross_source_collapses - same_source_collapses
    if expected_economic != len(economic_events):
        raise EconomicReconciliationError(
            "collapse arithmetic mismatch: source rows - collapses != economic events"
        )
    if resolved + unresolved + non_basis != len(economic_events):
        raise EconomicReconciliationError(
            "transition-state arithmetic mismatch"
        )

    return {
        "source_evidence_rows": len(source_rows),
        "economic_event_count": len(economic_events),
        "cross_source_collapses": cross_source_collapses,
        "same_source_collapses": same_source_collapses,
        "resolved_transitions": resolved,
        "unresolved_transitions": unresolved,
        "non_basis_excluded": non_basis,
        "economic_events": economic_events,
        "proven_linkages": normalized_linkages,
    }
