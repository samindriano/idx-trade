"""Outcome-blind helpers for V4-3 CA schedule evidence reuse.

Only exact event identity is reusable.  Existing evidence may resolve a current
SCHEDULE_REQUIRED event as either an exact market transition or an exact
non-blocking cash/tender event.  Conflicting claims fail closed.
"""

from __future__ import annotations

import hashlib
from typing import Iterable

import pandas as pd


RESOLVED_TRANSITION = "REUSED_EXACT_TRANSITION"
RESOLVED_NON_BLOCKING = "REUSED_EXACT_NON_BLOCKING"
UNRESOLVED = "NO_EXISTING_EXACT_EVIDENCE"
CONFLICT = "CONFLICTING_EXISTING_EVIDENCE"


def _ticker(value: object) -> str:
    return str(value or "").strip().upper().replace(".JK", "")


def _text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return " ".join(str(value).split())


def event_inventory_identity(events: pd.DataFrame) -> str:
    required = {"event_id", "ticker"}
    missing = required - set(events.columns)
    if missing:
        raise RuntimeError(f"SCHEDULE_EVENT_COLUMNS_MISSING:{sorted(missing)}")
    rows = events.copy()
    rows["event_id"] = rows["event_id"].map(_text)
    rows["ticker"] = rows["ticker"].map(_ticker)
    if rows["event_id"].eq("").any() or rows["ticker"].eq("").any():
        raise RuntimeError("SCHEDULE_EVENT_IDENTITY_EMPTY")
    if rows["event_id"].duplicated().any():
        raise RuntimeError("SCHEDULE_EVENT_ID_DUPLICATED")
    payload = "\n".join(
        f"{event_id}|{ticker}"
        for event_id, ticker in rows[["event_id", "ticker"]]
        .sort_values(["event_id", "ticker"], kind="mergesort")
        .itertuples(index=False, name=None)
    )
    return hashlib.sha256((payload + "\n").encode("utf-8")).hexdigest()


def normalize_current_events(frame: pd.DataFrame, expected_count: int = 80) -> pd.DataFrame:
    required = {"event_id", "ticker", "semantic_class"}
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"SCHEDULE_EVENT_COLUMNS_MISSING:{sorted(missing)}")
    result = frame.copy()
    result["event_id"] = result["event_id"].map(_text)
    result["ticker"] = result["ticker"].map(_ticker)
    result["semantic_class"] = result["semantic_class"].map(_text)
    if len(result) != expected_count or result["event_id"].nunique() != expected_count:
        raise RuntimeError(
            f"SCHEDULE_EVENT_COUNT_CHANGED:{len(result)}:{result['event_id'].nunique()}!={expected_count}"
        )
    if set(result["semantic_class"]) != {"SCHEDULE_REQUIRED"}:
        raise RuntimeError("SCHEDULE_EVENT_SEMANTIC_CLASS_CHANGED")
    if result["event_id"].eq("").any() or result["ticker"].eq("").any():
        raise RuntimeError("SCHEDULE_EVENT_IDENTITY_EMPTY")
    return result.sort_values(["ticker", "event_id"], kind="mergesort").reset_index(drop=True)


def schedule_claims(frame: pd.DataFrame, source_name: str) -> pd.DataFrame:
    required = {
        "event_id",
        "ticker",
        "linkage_status",
        "transition_date",
        "transition_semantic",
        "ksei_reference",
        "source_sha256",
    }
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"SCHEDULE_EVIDENCE_COLUMNS_MISSING:{sorted(missing)}")
    rows = frame[frame["linkage_status"].astype(str).eq("EXACT")].copy()
    if rows.empty:
        return pd.DataFrame(
            columns=[
                "event_id", "ticker", "claim_kind", "transition_date",
                "transition_semantic", "ksei_reference", "source_sha256",
                "source_name",
            ]
        )
    rows["event_id"] = rows["event_id"].map(_text)
    rows["ticker"] = rows["ticker"].map(_ticker)
    rows["transition_date"] = rows["transition_date"].map(_text)
    rows["transition_semantic"] = rows["transition_semantic"].map(_text)
    rows["ksei_reference"] = rows["ksei_reference"].map(_text)
    rows["source_sha256"] = rows["source_sha256"].map(_text)
    required_nonempty = [
        "event_id", "ticker", "transition_date", "transition_semantic",
        "ksei_reference", "source_sha256",
    ]
    if rows[required_nonempty].eq("").any().any():
        raise RuntimeError("SCHEDULE_EXACT_EVIDENCE_INCOMPLETE")
    rows["claim_kind"] = "EXACT_TRANSITION"
    rows["source_name"] = source_name
    return rows[
        [
            "event_id", "ticker", "claim_kind", "transition_date",
            "transition_semantic", "ksei_reference", "source_sha256",
            "source_name",
        ]
    ].drop_duplicates().reset_index(drop=True)


def residual_document_claims(frame: pd.DataFrame, source_name: str) -> pd.DataFrame:
    required = {
        "event_id",
        "ticker",
        "linkage_status",
        "transition_date",
        "transition_semantic",
        "ksei_reference",
        "source_sha256",
    }
    missing = required - set(frame.columns)
    if missing:
        raise RuntimeError(f"RESIDUAL_EVIDENCE_COLUMNS_MISSING:{sorted(missing)}")
    rows = frame[
        frame["linkage_status"].astype(str).isin(["EXACT", "EXACT_NON_BLOCKING"])
    ].copy()
    if rows.empty:
        return pd.DataFrame(
            columns=[
                "event_id", "ticker", "claim_kind", "transition_date",
                "transition_semantic", "ksei_reference", "source_sha256",
                "source_name",
            ]
        )
    rows["event_id"] = rows["event_id"].map(_text)
    rows["ticker"] = rows["ticker"].map(_ticker)
    rows["transition_date"] = rows["transition_date"].map(_text)
    rows["transition_semantic"] = rows["transition_semantic"].map(_text)
    rows["ksei_reference"] = rows["ksei_reference"].map(_text)
    rows["source_sha256"] = rows["source_sha256"].map(_text)
    if rows[["event_id", "ticker", "ksei_reference", "source_sha256"]].eq("").any().any():
        raise RuntimeError("RESIDUAL_EXACT_EVIDENCE_INCOMPLETE")
    exact_mask = rows["linkage_status"].eq("EXACT")
    if rows.loc[exact_mask, ["transition_date", "transition_semantic"]].eq("").any().any():
        raise RuntimeError("RESIDUAL_EXACT_TRANSITION_INCOMPLETE")
    rows["claim_kind"] = rows["linkage_status"].map(
        {"EXACT": "EXACT_TRANSITION", "EXACT_NON_BLOCKING": "EXACT_NON_BLOCKING"}
    )
    rows["source_name"] = source_name
    return rows[
        [
            "event_id", "ticker", "claim_kind", "transition_date",
            "transition_semantic", "ksei_reference", "source_sha256",
            "source_name",
        ]
    ].drop_duplicates().reset_index(drop=True)


def resolve_existing_claims(
    current_events: pd.DataFrame,
    claim_frames: Iterable[pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    claims = pd.concat(list(claim_frames), ignore_index=True, sort=False)
    current_keys = set(zip(current_events["event_id"], current_events["ticker"]))
    if not claims.empty:
        claims = claims[
            [
                (event_id, ticker) in current_keys
                for event_id, ticker in claims[["event_id", "ticker"]].itertuples(index=False, name=None)
            ]
        ].copy()
    out: list[dict[str, object]] = []
    admitted_claims: list[pd.DataFrame] = []
    for event in current_events.itertuples(index=False):
        event_id = str(event.event_id)
        ticker = str(event.ticker)
        event_claims = claims[
            claims["event_id"].eq(event_id) & claims["ticker"].eq(ticker)
        ].copy()
        base = {
            "event_id": event_id,
            "ticker": ticker,
            "source_type": getattr(event, "source_type", ""),
            "family": getattr(event, "family", ""),
        }
        if event_claims.empty:
            out.append({**base, "reuse_status": UNRESOLVED, "reuse_reason": "NO_EXACT_EVENT_ID_TICKER_MATCH", "transition_date": "", "transition_semantic": "", "evidence_sources": "", "evidence_sha256": ""})
            continue
        kinds = set(event_claims["claim_kind"].astype(str))
        if kinds == {"EXACT_NON_BLOCKING"}:
            out.append({
                **base,
                "reuse_status": RESOLVED_NON_BLOCKING,
                "reuse_reason": "EXACT_EVENT_ID_TICKER_NON_BLOCKING_EVIDENCE",
                "transition_date": "",
                "transition_semantic": "NON_BLOCKING",
                "evidence_sources": "|".join(sorted(set(event_claims["source_name"].astype(str)))),
                "evidence_sha256": "|".join(sorted(set(event_claims["source_sha256"].astype(str)))),
            })
            admitted_claims.append(event_claims)
            continue
        if kinds == {"EXACT_TRANSITION"}:
            dates = set(event_claims["transition_date"].astype(str))
            semantics = set(event_claims["transition_semantic"].astype(str))
            if len(dates) == 1 and len(semantics) == 1:
                out.append({
                    **base,
                    "reuse_status": RESOLVED_TRANSITION,
                    "reuse_reason": "EXACT_EVENT_ID_TICKER_TRANSITION_EVIDENCE",
                    "transition_date": next(iter(dates)),
                    "transition_semantic": next(iter(semantics)),
                    "evidence_sources": "|".join(sorted(set(event_claims["source_name"].astype(str)))),
                    "evidence_sha256": "|".join(sorted(set(event_claims["source_sha256"].astype(str)))),
                })
                admitted_claims.append(event_claims)
                continue
        out.append({
            **base,
            "reuse_status": CONFLICT,
            "reuse_reason": "MULTIPLE_OR_CONFLICTING_EXISTING_CLAIMS",
            "transition_date": "",
            "transition_semantic": "",
            "evidence_sources": "|".join(sorted(set(event_claims["source_name"].astype(str)))),
            "evidence_sha256": "|".join(sorted(set(event_claims["source_sha256"].astype(str)))),
        })
    census = pd.DataFrame(out).sort_values(["ticker", "event_id"], kind="mergesort").reset_index(drop=True)
    admitted = (
        pd.concat(admitted_claims, ignore_index=True, sort=False).drop_duplicates()
        if admitted_claims
        else claims.iloc[0:0].copy()
    )
    return census, admitted
