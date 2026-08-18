"""Compatibility-fixed V4-3 CA residual attribution runner.

The immutable KSEI-129 offline replay intentionally writes a compact continuity
CSV containing status/reason but not ``blocking_event_ids``.  V1 residual
attribution incorrectly required that diagnostic-only column even though the
frozen CA semantics can reconstruct schedule-event attribution deterministically
from the separately hash-pinned event audit:

* ``window_continuity`` treats every SCHEDULE_REQUIRED event on a ticker as
  unresolved for that ticker's windows until an exact official schedule exists;
* the event audit contains the stable event_id/ticker/semantic_class identity.

This wrapper changes diagnostic plumbing only.  Scenario support, 90% gates,
exact mechanical crossings, parent hashes, and all pre-target guardrails remain
those of the V1 runner.  No provider/network/target/model/performance access.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = Path(__file__).resolve().parent
for value in (REPO_ROOT / "src", SCRIPTS_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import run_v4_3_ca_training_domain_residual_attribution as v1  # noqa: E402


def prepare_inputs_compact(
    combined: pd.DataFrame, continuity: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reuse all V1 validation while supplying an empty diagnostic field.

    ``blocking_event_ids`` is not used by scenario computation.  The V2
    schedule-impact function below reconstructs it from the event audit rather
    than fabricating values in the parent replay.
    """

    w = continuity.copy()
    if "blocking_event_ids" not in w.columns:
        w["blocking_event_ids"] = ""
    return v1._prepare_inputs_original(combined, w)


def schedule_event_impact_from_audit(
    continuity: pd.DataFrame,
    event_audit: pd.DataFrame,
    folds: pd.DataFrame,
) -> pd.DataFrame:
    """Attribute schedule-blocked windows using frozen event-audit identity."""

    required_audit = {"event_id", "ticker", "semantic_class"}
    missing = required_audit - set(event_audit.columns)
    if missing:
        raise RuntimeError(f"EVENT_AUDIT_COLUMNS_MISSING:{sorted(missing)}")

    audit = event_audit.copy()
    audit["ticker"] = v1.normalize_ticker(audit["ticker"])
    audit["event_id"] = audit["event_id"].astype(str).str.strip()
    audit["semantic_class"] = audit["semantic_class"].astype(str).str.strip()
    if audit["event_id"].eq("").any():
        raise RuntimeError("EVENT_AUDIT_EMPTY_EVENT_ID")
    if audit.duplicated(["event_id", "ticker"]).any():
        # Exact duplicates are harmless only when their diagnostic semantics are
        # byte-equivalent across the columns we consume.  Collapse first and
        # fail if the same event identity maps to conflicting semantic classes.
        conflicts = (
            audit.groupby(["event_id", "ticker"])["semantic_class"]
            .nunique(dropna=False)
            .gt(1)
        )
        if bool(conflicts.any()):
            raise RuntimeError("EVENT_AUDIT_EVENT_ID_SEMANTIC_CONFLICT")
        audit = audit.drop_duplicates(["event_id", "ticker"], keep="first")

    schedule_events = audit[audit["semantic_class"].eq("SCHEDULE_REQUIRED")].copy()
    schedule_windows = continuity[
        continuity["continuity_reason"].eq(v1.REASON_SCHEDULE)
    ][["ticker", "signal_date", "horizon"]].copy()

    output_columns = [
        "event_id",
        "ticker",
        "source_type",
        "family",
        "semantic_class",
        "reason",
        "affected_windows",
        "affected_frozen_windows",
        "affected_signal_dates",
    ]
    if schedule_windows.empty:
        return pd.DataFrame(columns=output_columns)

    schedule_windows["ticker"] = v1.normalize_ticker(schedule_windows["ticker"])
    schedule_windows["signal_date"] = pd.to_datetime(
        schedule_windows["signal_date"], errors="coerce"
    ).dt.normalize()
    if schedule_windows["signal_date"].isna().any():
        raise RuntimeError("SCHEDULE_WINDOW_DATE_INVALID")

    event_tickers = set(schedule_events["ticker"])
    window_tickers = set(schedule_windows["ticker"])
    missing_event_identity = sorted(window_tickers - event_tickers)
    if missing_event_identity:
        raise RuntimeError(
            "SCHEDULE_WINDOW_WITHOUT_SCHEDULE_EVENT_AUDIT:"
            + ",".join(missing_event_identity)
        )

    frozen_dates = set(pd.to_datetime(folds["date"]).dt.normalize())
    rows: list[dict[str, object]] = []
    diagnostic_cols = [
        column
        for column in ("source_type", "family", "semantic_class", "reason")
        if column in schedule_events.columns
    ]

    # Frozen semantics are ticker-global for an unresolved schedule event:
    # every SCHEDULE_REQUIRED event on a ticker is part of the missing-schedule
    # set for every schedule-blocked window on that ticker.
    for ticker, event_group in schedule_events.groupby("ticker", sort=True):
        windows = schedule_windows[schedule_windows["ticker"].eq(ticker)]
        if windows.empty:
            continue
        affected_windows = int(len(windows))
        affected_frozen = int(windows["signal_date"].isin(frozen_dates).sum())
        affected_dates = int(windows["signal_date"].nunique())
        for event in event_group.itertuples(index=False):
            row = {
                "event_id": str(event.event_id),
                "ticker": ticker,
                "affected_windows": affected_windows,
                "affected_frozen_windows": affected_frozen,
                "affected_signal_dates": affected_dates,
            }
            for column in diagnostic_cols:
                row[column] = getattr(event, column)
            rows.append(row)

    if not rows:
        raise RuntimeError("SCHEDULE_REASON_PRESENT_BUT_NO_EVENT_IMPACT_ROWS")
    result = pd.DataFrame(rows)
    for column in output_columns:
        if column not in result.columns:
            result[column] = ""
    return result[output_columns].sort_values(
        ["affected_frozen_windows", "affected_windows", "ticker", "event_id"],
        ascending=[False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def main() -> int:
    # Preserve references to the original functions once.  Assignments are
    # module-local at process scope; the parent V1 file itself is unchanged.
    if not hasattr(v1, "_prepare_inputs_original"):
        v1._prepare_inputs_original = v1.prepare_inputs
    v1.prepare_inputs = prepare_inputs_compact
    v1.schedule_event_impact = schedule_event_impact_from_audit
    return v1.main()


if __name__ == "__main__":
    raise SystemExit(main())
