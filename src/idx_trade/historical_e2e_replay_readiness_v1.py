"""Outcome-blind historical E2E paper replay data-readiness audit.

This module deliberately audits inputs only.  It never loads target ledgers,
labels, returns, fills, NAV, or provider data.  The external artifacts are
treated as evidence bundles and are hash-verified before their safe columns
are read.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


OFFICIAL_OPEN_STATUS = "IDX_PUBLIC_STOCK_SUMMARY_OPEN_OPTIONAL"
RESOLVED_CA_STATUS = "RESOLVED_NO_MECHANICAL_DISCONTINUITY"
EXPECTED_DECISION_SESSIONS = 600
EXPECTED_SCORE_SHA256 = "48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b"
EXPECTED_PANEL_SHA256 = "25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e"
EXPECTED_CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
FORBIDDEN_INPUT_TOKENS = (
    "outcome",
    "label",
    "r5",
    "r10",
    "return",
    "pnl",
    "profit",
    "nav",
    "fill",
    "notional",
    "shares",
    "lots",
)


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"INPUT_MISSING:{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def ensure_safe_columns(columns: Iterable[str], *, context: str) -> None:
    bad = []
    for column in columns:
        lowered = str(column).lower()
        if any(
            lowered == token or lowered.startswith(f"{token}_") or lowered.endswith(f"_{token}")
            for token in FORBIDDEN_INPUT_TOKENS
        ):
            bad.append(str(column))
    if bad:
        raise RuntimeError(f"PROTECTED_OR_OUTCOME_COLUMN_REJECTED:{context}:{sorted(bad)}")


def _normalise_keys(frame: pd.DataFrame, *, context: str) -> pd.DataFrame:
    ensure_safe_columns(frame.columns, context=context)
    out = frame.copy()
    if "ticker" in out:
        out["ticker"] = out["ticker"].astype(str).str.upper().str.replace(".JK", "", regex=False).str.strip()
    if "date" in out:
        out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.normalize()
    return out


def _hash_manifest_artifacts(root: Path, manifest: dict) -> dict[str, str]:
    artifacts = manifest.get("artifacts") or {}
    if not isinstance(artifacts, dict):
        raise RuntimeError("STRUCTURAL_ARTIFACT_MAP_MISSING")
    observed = {}
    for name, expected in artifacts.items():
        actual = sha256_file(root / str(name))
        if actual != expected:
            raise RuntimeError(f"STRUCTURAL_ARTIFACT_SHA_MISMATCH:{name}:{actual}!={expected}")
        observed[str(name)] = actual
    return observed


def load_structural_evidence(root: Path) -> tuple[dict, dict[str, pd.DataFrame], dict[str, str]]:
    manifest_path = root / "MANIFEST.json"
    manifest_sha = sha256_file(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "decision_v2_minimal_structural_replay_manifest_v1":
        raise RuntimeError("STRUCTURAL_MANIFEST_SCHEMA_CHANGED")
    if manifest.get("status") != "DECISION_V2_MINIMAL_STRUCTURAL_REJECT":
        raise RuntimeError(f"STRUCTURAL_STATUS_CHANGED:{manifest.get('status')}")
    guards = manifest.get("guards") or {}
    forbidden_true = [key for key, value in guards.items() if bool(value)]
    if forbidden_true:
        raise RuntimeError(f"STRUCTURAL_GUARD_NOT_OUTCOME_BLIND:{sorted(forbidden_true)}")
    observed_hashes = _hash_manifest_artifacts(root, manifest)
    names = (
        "decision_intent_ledger.csv",
        "decision_membership_ledger.csv",
        "decision_session_ledger.csv",
        "holding_spells.csv",
    )
    frames = {name: _normalise_keys(pd.read_csv(root / name), context=name) for name in names}
    sessions = frames["decision_session_ledger.csv"]
    if len(sessions) != EXPECTED_DECISION_SESSIONS or sessions["index"].tolist() != list(range(EXPECTED_DECISION_SESSIONS)):
        raise RuntimeError("STRUCTURAL_SESSION_INDEX_NOT_0_TO_599")
    if sessions["date"].isna().any() or sessions["date"].duplicated().any():
        raise RuntimeError("STRUCTURAL_SESSION_DATE_INVALID")
    frames["decision_intent_ledger.csv"]["date"] = pd.to_datetime(
        frames["decision_intent_ledger.csv"]["date"], errors="raise"
    ).dt.normalize()
    frames["holding_spells.csv"]["entry_date"] = pd.to_datetime(
        frames["holding_spells.csv"]["entry_date"], errors="raise"
    ).dt.normalize()
    if "exit_date" in frames["holding_spells.csv"]:
        frames["holding_spells.csv"]["exit_date"] = pd.to_datetime(
            frames["holding_spells.csv"]["exit_date"], errors="coerce"
        ).dt.normalize()
    return {
        "manifest": manifest,
        "manifest_sha256": manifest_sha,
        "source_artifact_hashes": observed_hashes,
    }, frames, observed_hashes


def build_exposure_universe(structural: dict[str, pd.DataFrame]) -> pd.DataFrame:
    sessions = structural["decision_session_ledger.csv"].sort_values("index")
    session_count = int(len(sessions))
    date_by_index = dict(zip(sessions["index"].astype(int), sessions["date"], strict=True))
    fold_by_index = dict(zip(sessions["index"].astype(int), sessions["fold"].astype(int), strict=True))
    rows: list[dict] = []
    for spell_id, spell in structural["holding_spells.csv"].reset_index(drop=True).iterrows():
        entry_index = int(spell["entry_index"])
        exit_index = int(spell["exit_index"]) if pd.notna(spell["exit_index"]) else session_count
        if not 0 <= entry_index < exit_index <= session_count:
            raise RuntimeError(f"HOLDING_SPELL_INTERVAL_INVALID:{spell_id}")
        for index in range(entry_index, exit_index):
            rows.append(
                {
                    "spell_id": int(spell_id),
                    "session_index": index,
                    "signal_date": date_by_index[index],
                    "fold": fold_by_index[index],
                    "ticker": str(spell["ticker"]),
                    "entry_index": entry_index,
                    "entry_date": date_by_index[entry_index],
                    "exit_index": None if pd.isna(spell["exit_index"]) else exit_index,
                        "exit_date_exclusive": None if exit_index == session_count else date_by_index[exit_index],
                    "entry_reason": str(spell["entry_reason"]),
                    "right_censored": bool(spell["right_censored"]),
                }
            )
    exposure = pd.DataFrame(rows)
    if exposure.empty or exposure.duplicated(["session_index", "ticker"]).any():
        raise RuntimeError("EXPOSURE_UNIVERSE_DUPLICATE_OR_EMPTY")
    return exposure.sort_values(["session_index", "ticker"], kind="mergesort").reset_index(drop=True)


def load_calendar(path: Path) -> pd.DataFrame:
    actual_sha = sha256_file(path)
    if actual_sha != EXPECTED_CALENDAR_SHA256:
        raise RuntimeError(f"CALENDAR_SHA_MISMATCH:{actual_sha}!={EXPECTED_CALENDAR_SHA256}")
    calendar = pd.read_csv(path, usecols=["date"])
    calendar["date"] = pd.to_datetime(calendar["date"], errors="raise").dt.normalize()
    if len(calendar) != 1260 or calendar["date"].duplicated().any():
        raise RuntimeError("CALENDAR_NOT_1260_UNIQUE")
    calendar["next_date"] = calendar["date"].shift(-1)
    return calendar


def load_clean_panel(path: Path) -> pd.DataFrame:
    actual_sha = sha256_file(path)
    if actual_sha != EXPECTED_PANEL_SHA256:
        raise RuntimeError(f"CLEAN_PANEL_SHA_MISMATCH:{actual_sha}!={EXPECTED_PANEL_SHA256}")
    columns = [
        "ticker",
        "date",
        "high",
        "low",
        "close",
        "volume",
        "regular_market_value",
        "price_provenance",
        "open",
        "open_available",
        "open_evidence_status",
        "corporate_action_integrity_verified",
    ]
    panel = _normalise_keys(pd.read_parquet(path, columns=columns), context="clean_panel")
    if panel.duplicated(["ticker", "date"]).any():
        raise RuntimeError("CLEAN_PANEL_DUPLICATE_TICKER_DATE")
    return panel


def join_panel(frame: pd.DataFrame, panel: pd.DataFrame, *, frame_date: str, suffix: str = "") -> pd.DataFrame:
    return frame.merge(
        panel,
        left_on=["ticker", frame_date],
        right_on=["ticker", "date"],
        how="left",
        suffixes=("", suffix),
        validate="many_to_one",
    ).drop(columns=["date"])


def _numeric_ok(row: pd.Series, column: str) -> bool:
    value = row.get(column)
    return value is not None and pd.notna(value) and np.isfinite(float(value))


def build_order_coverage(intents: pd.DataFrame, panel: pd.DataFrame, calendar: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    next_map = dict(zip(calendar["date"], calendar["next_date"]))
    orders = intents.copy()
    orders["signal_date"] = pd.to_datetime(orders["date"], errors="raise").dt.normalize()
    orders["execution_date"] = orders.apply(
        lambda row: next_map.get(row["signal_date"]) if row["side"] == "BUY_INTENT" else row["signal_date"], axis=1
    )
    orders["required_open"] = orders["side"].eq("BUY_INTENT")
    orders = join_panel(orders, panel, frame_date="execution_date", suffix="_execution")
    orders["official_open_eligible"] = (
        orders["open_evidence_status"].eq(OFFICIAL_OPEN_STATUS)
        & orders["open"].map(lambda x: pd.notna(x) and np.isfinite(float(x)) and float(x) > 0)
    )
    orders["hlcvrmv_complete"] = orders.apply(
        lambda row: all(_numeric_ok(row, column) for column in ("high", "low", "close", "volume", "regular_market_value")), axis=1
    )
    orders["input_status"] = np.select(
        [orders["required_open"] & ~orders["official_open_eligible"], ~orders["hlcvrmv_complete"]],
        ["OPEN_UNAVAILABLE_OR_NON_OFFICIAL", "HLCV_RMV_INCOMPLETE"],
        default="READY_FOR_INPUT_AUDIT",
    )
    orders["source_open_status"] = orders["open_evidence_status"]
    orders["source_price_provenance"] = orders["price_provenance"]
    selected = [
        "index", "signal_date", "execution_date", "side", "ticker", "rank_consensus", "reason",
        "replacement_peer", "required_open", "official_open_eligible", "hlcvrmv_complete",
        "input_status", "open", "open_evidence_status", "price_provenance", "high", "low", "close",
        "volume", "regular_market_value",
    ]
    orders = orders.loc[:, [c for c in selected if c in orders]].sort_values(
        ["signal_date", "side", "ticker"], kind="mergesort"
    ).reset_index(drop=True)
    return orders, orders.loc[orders["required_open"]].copy()


def build_holding_coverage(exposure: pd.DataFrame, panel: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    next_map = dict(zip(calendar["date"], calendar["next_date"]))
    current = join_panel(exposure, panel, frame_date="signal_date", suffix="_current")
    current["next_date"] = current["signal_date"].map(next_map)
    next_panel = panel.rename(columns={column: f"next_{column}" for column in panel.columns if column not in {"ticker", "date"}})
    current = current.merge(
        next_panel,
        left_on=["ticker", "next_date"],
        right_on=["ticker", "date"],
        how="left",
        validate="many_to_one",
    ).drop(columns=["date"])
    current["current_hlcvrmv_complete"] = current.apply(
        lambda row: all(_numeric_ok(row, column) for column in ("high", "low", "close", "volume", "regular_market_value")), axis=1
    )
    current["next_official_open_eligible"] = (
        current["next_open_evidence_status"].eq(OFFICIAL_OPEN_STATUS)
        & current["next_open"].map(lambda x: pd.notna(x) and np.isfinite(float(x)) and float(x) > 0)
    )
    current["holding_input_status"] = np.select(
        [~current["current_hlcvrmv_complete"], ~current["next_official_open_eligible"]],
        ["CURRENT_HLCV_RMV_INCOMPLETE", "NEXT_OPEN_UNAVAILABLE_OR_NON_OFFICIAL"],
        default="READY_FOR_INPUT_AUDIT",
    )
    return current.sort_values(["session_index", "ticker"], kind="mergesort").reset_index(drop=True)


def build_rmv_coverage(holding: pd.DataFrame) -> pd.DataFrame:
    grouped = holding.groupby(["session_index", "signal_date"], sort=True)
    out = grouped.agg(
        expected_holding_rows=("ticker", "size"),
        rmv_rows=("regular_market_value", lambda s: int(s.notna().sum())),
        close_rows=("close", lambda s: int(s.notna().sum())),
        current_hlcvrmv_ready=("current_hlcvrmv_complete", "sum"),
        next_official_open_ready=("next_official_open_eligible", "sum"),
    ).reset_index()
    out["rmv_coverage_pct"] = out["rmv_rows"] / out["expected_holding_rows"]
    out["close_coverage_pct"] = out["close_rows"] / out["expected_holding_rows"]
    return out


def load_ca_window(path: Path) -> tuple[pd.DataFrame, dict]:
    manifest_path = path / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED":
        raise RuntimeError("CA_WINDOW_STATUS_CHANGED")
    ledger_path = path / "v4_frozen_continuity_ledger_event_window.csv"
    expected = (manifest.get("output_hashes") or {}).get("continuity_ledger")
    actual = sha256_file(ledger_path)
    if expected and actual != expected:
        raise RuntimeError(f"CA_WINDOW_LEDGER_SHA_MISMATCH:{actual}!={expected}")
    ledger = pd.read_csv(ledger_path, low_memory=False)
    ledger["ticker"] = ledger["ticker"].astype(str).str.upper().str.strip()
    ledger["signal_date"] = pd.to_datetime(ledger["signal_date"], errors="raise").dt.normalize()
    return ledger, {"manifest_sha256": sha256_file(manifest_path), "ledger_sha256": actual, "manifest": manifest}


def build_ca_gap(exposure: pd.DataFrame, ca_ledger: pd.DataFrame) -> pd.DataFrame:
    keyed = ca_ledger.loc[:, ["ticker", "signal_date", "horizon", "continuity_status", "continuity_reason", "blocking_event_ids", "blocking_transition_dates"]].copy()
    pivot = keyed.pivot_table(index=["ticker", "signal_date"], columns="horizon", values=["continuity_status", "continuity_reason", "blocking_event_ids", "blocking_transition_dates"], aggfunc="first")
    pivot.columns = [f"h{int(horizon)}_{name}" for name, horizon in pivot.columns]
    pivot = pivot.reset_index()
    out = exposure.merge(pivot, on=["ticker", "signal_date"], how="left", validate="one_to_one")
    for horizon in (5, 10):
        status_column = f"h{horizon}_continuity_status"
        if status_column not in out:
            out[status_column] = pd.NA
        out[status_column] = out[status_column].fillna("CA_EVIDENCE_UNAVAILABLE")
    out["ca_strict_pass"] = out["h5_continuity_status"].eq(RESOLVED_CA_STATUS) & out["h10_continuity_status"].eq(RESOLVED_CA_STATUS)
    out["ca_gap_status"] = np.where(out["ca_strict_pass"], "RESOLVED_NO_MECHANICAL_DISCONTINUITY", "UNRESOLVED_CA_CONTINUITY")
    return out.sort_values(["session_index", "ticker"], kind="mergesort").reset_index(drop=True)


def load_bounded_dividends(root: Path) -> tuple[pd.DataFrame, dict]:
    result_path = root / "OFFLINE_REPLAY_V1_2_RESULT.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("network_access") != "NONE_FILE_ONLY":
        raise RuntimeError("DIVIDEND_REPLAY_NOT_OFFLINE")
    disposition = {row.get("announcement_identity"): row for row in result.get("dispositions", [])}
    rows = []
    for review_path in root.parent.joinpath("idx-e2e-forward-dividend-acquisition-batch-smoke-20260823-v6").rglob("ATTACHMENT_REVIEW_V1_2.json"):
        try:
            review = json.loads(review_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        event = review.get("expected_event") or {}
        if not event or not str(review.get("status", "")).startswith("PASS_"):
            continue
        announcement = review.get("announcement") or {}
        identity = f"{event.get('ticker')}|NUMBER|{announcement.get('number')}"
        disposition_row = disposition.get(identity, {})
        rows.append(
            {
                "ticker": str(event.get("ticker", "")).upper(),
                "announcement_identity": identity,
                "announcement_at": announcement.get("date"),
                "ex_regular_negotiated": event.get("ex_regular_negotiated"),
                "payment_date": event.get("payment_date"),
                "status": disposition_row.get("status", "OBSERVED_BOUNDED"),
                "event_id": result.get("event_ids", {}).get(identity),
            }
        )
    events = pd.DataFrame(rows)
    if events.empty:
        events = pd.DataFrame(columns=["ticker", "announcement_identity", "announcement_at", "ex_regular_negotiated", "payment_date", "status", "event_id"])
    else:
        events["ex_regular_negotiated"] = pd.to_datetime(events["ex_regular_negotiated"], errors="coerce").dt.normalize()
        events["announcement_at"] = pd.to_datetime(events["announcement_at"], errors="coerce")
    return events, {"result_sha256": sha256_file(result_path), "result": result}


def build_dividend_gap(exposure: pd.DataFrame, spells: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, spell in spells.iterrows():
        start = pd.Timestamp(spell["entry_date"])
        end = pd.Timestamp(spell["exit_date_exclusive"]) if pd.notna(spell["exit_date_exclusive"]) else pd.Timestamp("2262-04-11")
        matches = events.loc[(events["ticker"] == spell["ticker"]) & events["ex_regular_negotiated"].ge(start) & events["ex_regular_negotiated"].lt(end)]
        rows.append(
            {
                "spell_id": int(spell["spell_id"]),
                "ticker": spell["ticker"],
                "entry_date": start,
                "exit_date_exclusive": None if end.year == 2262 else end,
                "bounded_certified_event_count": int(len(matches)),
                "bounded_event_ids": "|".join(sorted(str(x) for x in matches["event_id"].dropna())),
                "dividend_gap_status": "BOUNDED_CERTIFIED_EVENT_OVERLAP" if len(matches) else "NO_MARKET_WIDE_NO_EVENT_PROOF",
                "market_wide_no_event_ledger": False,
            }
        )
    return pd.DataFrame(rows).sort_values(["ticker", "spell_id"], kind="mergesort").reset_index(drop=True)


def build_segments(
    sessions: pd.DataFrame,
    orders: pd.DataFrame,
    holding: pd.DataFrame,
    ca_gap: pd.DataFrame,
    dividend_gap: pd.DataFrame,
) -> pd.DataFrame:
    order_day = orders.groupby("signal_date", sort=True).agg(
        buy_order_count=("required_open", lambda s: int(s.sum())),
        buy_open_ready=("official_open_eligible", lambda s: int(s[s.index.isin(orders.index[orders["required_open"]])].sum())),
    ).reset_index()
    order_day["buy_open_gate"] = order_day["buy_order_count"].eq(order_day["buy_open_ready"])
    hold_day = holding.groupby("signal_date", sort=True).agg(
        holding_rows=("ticker", "size"),
        holding_input_ready=("holding_input_status", lambda s: int(s.eq("READY_FOR_INPUT_AUDIT").sum())),
    ).reset_index()
    hold_day["holding_input_gate"] = hold_day["holding_rows"].eq(hold_day["holding_input_ready"])
    ca_day = ca_gap.groupby("signal_date", sort=True).agg(
        ca_rows=("ticker", "size"), ca_ready=("ca_strict_pass", "sum")
    ).reset_index()
    ca_day["ca_gate"] = ca_day["ca_rows"].eq(ca_day["ca_ready"])
    # A full dividend no-event corpus is intentionally absent; this is never
    # converted to PASS merely because no bounded event was observed.
    div_day = dividend_gap.assign(_all=False).groupby(lambda _: True).agg(dividend_gate=("_all", "all")).reset_index(drop=True)
    dividend_gate = bool(div_day.loc[0, "dividend_gate"]) if not div_day.empty else False
    out = sessions.loc[:, ["index", "date"]].rename(columns={"index": "session_index", "date": "signal_date"})
    for frame in (order_day, hold_day, ca_day):
        out = out.merge(frame, on="signal_date", how="left")
    for column in ("buy_order_count", "buy_open_ready", "holding_rows", "holding_input_ready", "ca_rows", "ca_ready"):
        out[column] = out[column].fillna(0).astype(int)
    for column in ("buy_open_gate", "holding_input_gate", "ca_gate"):
        out[column] = out[column].astype("boolean").fillna(False).astype(bool)
    out["dividend_gate"] = dividend_gate
    out["price_execution_strict_pass"] = out["buy_open_gate"] & out["holding_input_gate"]
    out["full_economic_strict_pass"] = out["price_execution_strict_pass"] & out["ca_gate"] & out["dividend_gate"]
    out["strict_status"] = np.select(
        [out["full_economic_strict_pass"], out["price_execution_strict_pass"]],
        ["FULL_ECONOMIC_REPLAY_READY", "PRICE_EXECUTION_ONLY_CA_OR_DIVIDEND_GAP"],
        default="INPUT_GAP",
    )
    out["dividend_gate_reason"] = "NO_MARKET_WIDE_PIT_DIVIDEND_LEDGER"
    return out


def longest_segments(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    rows = []
    start = None
    previous = None
    for _, row in frame.sort_values("signal_date").iterrows():
        current = pd.Timestamp(row["signal_date"])
        if bool(row[column]) and start is None:
            start = current
        if (not bool(row[column]) or current == frame["signal_date"].max()) and start is not None:
            end = current if bool(row[column]) else previous
            rows.append({"gate": column, "start_date": start, "end_date": end, "sessions": int((frame["signal_date"].between(start, end)).sum())})
            start = None
        previous = current
    return pd.DataFrame(rows, columns=["gate", "start_date", "end_date", "sessions"])


def inventory_row(name: str, path: Path, *, status: str, reason: str, rows: int | None = None, dates: str | None = None, scope: str = "") -> dict:
    exists = path.is_file()
    return {
        "dataset": name,
        "path": str(path),
        "exists": exists,
        "bytes": path.stat().st_size if exists else None,
        "sha256": sha256_file(path) if exists else None,
        "rows": rows,
        "date_range": dates,
        "scope": scope,
        "status": status,
        "reason": reason,
    }


def run_audit(
    *,
    structural_root: Path,
    panel_path: Path,
    calendar_path: Path,
    ca_window_root: Path,
    dividend_root: Path,
    output_dir: Path,
) -> dict:
    if output_dir.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE:{output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    structural_meta, structural, artifact_hashes = load_structural_evidence(structural_root)
    score_path = Path(r"D:/Documents/Project/idx-v4-x1-clean-historical-oos-replay-20260820-v2/clean_challenger_validation_scores.parquet")
    score_sha = sha256_file(score_path)
    if score_sha != EXPECTED_SCORE_SHA256:
        raise RuntimeError(f"SCORE_SHA_MISMATCH:{score_sha}!={EXPECTED_SCORE_SHA256}")
    exposure = build_exposure_universe(structural)
    sessions = structural["decision_session_ledger.csv"].sort_values("index").copy()
    calendar = load_calendar(calendar_path)
    panel = load_clean_panel(panel_path)
    orders, open_orders = build_order_coverage(structural["decision_intent_ledger.csv"], panel, calendar)
    holding = build_holding_coverage(exposure, panel, calendar)
    rmv = build_rmv_coverage(holding)
    ca_ledger, ca_meta = load_ca_window(ca_window_root)
    ca_gap = build_ca_gap(exposure, ca_ledger)
    dividend_events, dividend_meta = load_bounded_dividends(dividend_root)
    dividend_gap = build_dividend_gap(exposure, exposure.merge(
        structural["holding_spells.csv"].reset_index().rename(columns={"index": "spell_id"}), on="spell_id", how="left", suffixes=("", "_spell"), validate="many_to_one"
    ).drop_duplicates("spell_id"), dividend_events)
    segments = build_segments(sessions, orders, holding, ca_gap, dividend_gap)
    segment_rows = longest_segments(segments, "full_economic_strict_pass")
    if segment_rows.empty:
        segment_rows = pd.DataFrame([{"gate": "full_economic_strict_pass", "start_date": None, "end_date": None, "sessions": 0}])

    exposure.to_csv(output_dir / "decision_v2_exposure_universe.csv", index=False, lineterminator="\n")
    sessions.to_csv(output_dir / "decision_v2_session_trajectory.csv", index=False, lineterminator="\n")
    orders.to_csv(output_dir / "order_input_coverage.csv", index=False, lineterminator="\n")
    holding.to_csv(output_dir / "holding_input_coverage.csv", index=False, lineterminator="\n")
    rmv.to_csv(output_dir / "regular_market_value_coverage.csv", index=False, lineterminator="\n")
    open_orders.to_csv(output_dir / "open_execution_coverage.csv", index=False, lineterminator="\n")
    ca_gap.to_csv(output_dir / "ca_exposure_gap.csv", index=False, lineterminator="\n")
    dividend_gap.to_csv(output_dir / "dividend_exposure_gap.csv", index=False, lineterminator="\n")
    segments.to_csv(output_dir / "strict_replayable_segments.csv", index=False, lineterminator="\n")
    segment_rows.to_csv(output_dir / "strict_replayable_contiguous_segments.csv", index=False, lineterminator="\n")

    buy_open_ready = int(open_orders["official_open_eligible"].sum())
    buy_open_total = int(len(open_orders))
    holding_ready = int(holding["holding_input_status"].eq("READY_FOR_INPUT_AUDIT").sum())
    ca_ready = int(ca_gap["ca_strict_pass"].sum())
    readiness_rows = [
        {"dataset": "DECISION_V2_STRUCTURAL_LEDGER", "dimension": "600_sessions", "status": "PARTIAL", "expected": 600, "observed": 600, "coverage_pct": 1.0, "reason": "Structural ledger is hash-verified but no sizing/execution quantities or generator commit are present."},
        {"dataset": "CLEAN_CLOSE_HLCV_RMV", "dimension": "panel_rows", "status": "READY", "expected": int(len(panel)), "observed": int(len(panel)), "coverage_pct": 1.0, "reason": "Accepted final clean panel has complete HLCV/RMV fields for the audited rows."},
        {"dataset": "OFFICIAL_OPEN", "dimension": "buy_order_rows", "status": "PARTIAL", "expected": buy_open_total, "observed": buy_open_ready, "coverage_pct": buy_open_ready / buy_open_total if buy_open_total else 0.0, "reason": "Only explicit IDX stock-summary Open status is admitted; Yahoo and unavailable rows fail closed."},
        {"dataset": "HOLDING_INPUTS", "dimension": "exposure_rows", "status": "PARTIAL", "expected": int(len(holding)), "observed": holding_ready, "coverage_pct": holding_ready / len(holding) if len(holding) else 0.0, "reason": "Current HLCV/RMV plus next-session official Open are required for this input audit."},
        {"dataset": "CORPORATE_ACTION_PIT", "dimension": "exposure_rows", "status": "BLOCKED", "expected": int(len(ca_gap)), "observed": ca_ready, "coverage_pct": ca_ready / len(ca_gap) if len(ca_gap) else 0.0, "reason": "The accepted event-window ledger explicitly fails closed on missing market-wide no-event evidence and unresolved effective dates."},
        {"dataset": "DIVIDEND_PIT", "dimension": "holding_spells", "status": "BLOCKED", "expected": int(len(dividend_gap)), "observed": int((dividend_gap["dividend_gap_status"] == "BOUNDED_CERTIFIED_EVENT_OVERLAP").sum()), "coverage_pct": float((dividend_gap["dividend_gap_status"] == "BOUNDED_CERTIFIED_EVENT_OVERLAP").mean()) if len(dividend_gap) else 0.0, "reason": "Only a bounded BBCA/BBRI/TLKM event batch exists; no market-wide no-event ledger or position entitlement history exists."},
        {"dataset": "SIZING_V1_EXECUTION_V1", "dimension": "full_historical_exposure", "status": "BLOCKED", "expected": 600, "observed": 0, "coverage_pct": 0.0, "reason": "No pinned 600-session NAV/cash/sizing/fill/state artifact bundle exists."},
    ]
    pd.DataFrame(readiness_rows).to_csv(output_dir / "historical_e2e_data_readiness.csv", index=False, lineterminator="\n")

    dataset_rows = [
        inventory_row("decision_v2_structural_manifest", structural_root / "MANIFEST.json", status="PARTIAL", reason="Hash-verified structural-only evidence; manifest says rejected and no execution quantities.", rows=None, dates="2023-12-28..2026-07-17", scope="600 sessions"),
        inventory_row("decision_v2_score_source", score_path, status="PARTIAL", reason="Frozen score input only; bytes hash-verified; score values not loaded by this audit.", rows=172697, dates="2023-12-28..2026-07-17", scope="model score rows"),
        inventory_row("clean_panel", panel_path, status="READY", reason="Accepted final clean HLCV/RMV panel.", rows=len(panel), dates=f"{panel['date'].min().date()}..{panel['date'].max().date()}", scope="981940 rows/1260 dates"),
        inventory_row("official_calendar", calendar_path, status="READY", reason="Pinned 1260-session calendar.", rows=len(calendar), dates=f"{calendar['date'].min().date()}..{calendar['date'].max().date()}", scope="official sessions"),
        inventory_row("ca_event_window", ca_window_root / "v4_frozen_continuity_ledger_event_window.csv", status="BLOCKED", reason="Accepted continuity ledger is explicitly blocked.", rows=len(ca_ledger), dates="600 signal dates", scope="event-window continuity"),
        inventory_row("bounded_dividend_replay", dividend_root / "OFFLINE_REPLAY_V1_2_RESULT.json", status="BLOCKED", reason="Bounded 11-candidate file-only replay, not market-wide historical PIT.", rows=int(dividend_meta["result"].get("candidate_count", 0)), dates="bounded 2025..2026 events", scope="BBCA/BBRI/TLKM"),
        inventory_row("historical_open_overlay", Path(r"D:/Documents/Project/idx-open-ca-scale-reconstruction-20260817-v1/open_recovery_overlay.parquet"), status="PARTIAL", reason="Accepted 2184-row overlay is bounded and does not close residual Open coverage.", rows=2184, dates="bounded", scope="official factor transformed Open"),
        inventory_row("sizing_execution_600_session_bundle", Path(r"D:/Documents/Project/idx-e2e-paper-production-replay-20260823-v1"), status="BLOCKED", reason="No 600-session execution bundle; available production replay is synthetic/short and not used.", rows=None, dates=None, scope="not found as single file"),
    ]
    pd.DataFrame(dataset_rows).to_csv(output_dir / "dataset_inventory.csv", index=False, lineterminator="\n")

    full_pass = bool(segments["full_economic_strict_pass"].all())
    price_pass = bool(segments["price_execution_strict_pass"].all())
    open_per_date = open_orders.groupby("signal_date", sort=True)["official_open_eligible"].agg(["count", "sum", "mean"])
    holding_per_date = holding.groupby("signal_date", sort=True)["holding_input_status"].apply(
        lambda values: float(values.eq("READY_FOR_INPUT_AUDIT").mean())
    )
    summary = {
        "schema_version": "historical_e2e_replay_data_readiness_summary_v1",
        "verdict": "HISTORICAL_E2E_REPLAY_PARTIAL_STRICT_SCOPE_AVAILABLE" if price_pass and not full_pass else "HISTORICAL_E2E_REPLAY_BLOCKED_BY_DATA",
        "historical_sessions_total": int(len(sessions)),
        "historical_session_range": [str(sessions["date"].min().date()), str(sessions["date"].max().date())],
        "decision_v2_structural": {
            "sessions": int(len(sessions)), "source_manifest_sha256": structural_meta["manifest_sha256"], "score_sha256": score_sha, "artifact_hashes": artifact_hashes,
            "intent_rows": int(len(structural["decision_intent_ledger.csv"])), "buy_intents": int(structural["decision_intent_ledger.csv"]["side"].eq("BUY_INTENT").sum()), "sell_intents": int(structural["decision_intent_ledger.csv"]["side"].eq("SELL_INTENT").sum()), "exposure_rows": int(len(exposure)), "unique_tickers": int(exposure["ticker"].nunique()),
            "structural_verdict": "DECISION_V2_MINIMAL_STRUCTURAL_REJECT",
            "execution_quantities_present": False, "sizing_execution_ledger_present": False,
        },
        "clean_panel": {"rows": int(len(panel)), "dates": int(panel["date"].nunique()), "tickers": int(panel["ticker"].nunique()), "open_evidence_status_counts": {str(key): int(value) for key, value in panel["open_evidence_status"].value_counts(dropna=False).items()}, "corporate_action_integrity_verified_rows": int(panel["corporate_action_integrity_verified"].eq(True).sum())},
        "open_execution": {"buy_order_rows": buy_open_total, "official_open_ready_rows": buy_open_ready, "official_open_coverage_pct": buy_open_ready / buy_open_total if buy_open_total else 0.0, "non_official_or_unavailable_rows": buy_open_total - buy_open_ready, "source_status_admitted": OFFICIAL_OPEN_STATUS},
        "open_execution_per_signal_date": {"dates_with_buy_orders": int(len(open_per_date)), "dates_all_buy_open_ready": int((open_per_date["sum"] == open_per_date["count"]).sum()), "min_coverage_pct": float(open_per_date["mean"].min()) if not open_per_date.empty else None, "median_coverage_pct": float(open_per_date["mean"].median()) if not open_per_date.empty else None, "max_coverage_pct": float(open_per_date["mean"].max()) if not open_per_date.empty else None},
        "holding_inputs": {"rows": int(len(holding)), "ready_rows": holding_ready, "coverage_pct": holding_ready / len(holding) if len(holding) else 0.0, "current_close_complete": int(holding["close"].notna().sum()), "regular_market_value_complete": int(holding["regular_market_value"].notna().sum())},
        "holding_inputs_per_signal_date": {"dates": int(len(holding_per_date)), "dates_all_ready": int((holding_per_date == 1.0).sum()), "min_coverage_pct": float(holding_per_date.min()) if not holding_per_date.empty else None, "median_coverage_pct": float(holding_per_date.median()) if not holding_per_date.empty else None, "max_coverage_pct": float(holding_per_date.max()) if not holding_per_date.empty else None},
        "corporate_actions": {"source_manifest_sha256": ca_meta["manifest_sha256"], "ledger_sha256": ca_meta["ledger_sha256"], "exposure_rows": int(len(ca_gap)), "strict_resolved_rows": ca_ready, "unresolved_rows": int(len(ca_gap) - ca_ready), "full_exposure_gate": False, "policy": "absence_does_not_prove_no_event"},
        "dividends": {"source_result_sha256": dividend_meta["result_sha256"], "candidate_count": int(dividend_meta["result"].get("candidate_count", 0)), "bounded_event_rows": int(len(dividend_events)), "holding_spells": int(len(dividend_gap)), "bounded_event_overlap_spells": int((dividend_gap["dividend_gap_status"] == "BOUNDED_CERTIFIED_EVENT_OVERLAP").sum()), "market_wide_no_event_ledger": False, "full_exposure_gate": False},
        "strict_scope": {"price_execution_all_sessions": price_pass, "full_economic_all_sessions": full_pass, "longest_full_economic_contiguous_sessions": int(segment_rows["sessions"].max() if not segment_rows.empty else 0), "strict_segments_path": "strict_replayable_contiguous_segments.csv"},
        "guards": {"outcome_blind": True, "labels_loaded": False, "target_values_accessed": False, "returns_loaded": False, "r5_loaded": False, "r10_loaded": False, "pnl_computed": False, "protected_outcomes_accessed": False, "provider_calls": False, "network_calls": False, "model_fit": False, "model_scoring": False},
        "blockers": ["DECISION_V2_STRUCTURAL_ARTIFACT_REJECTED_AND_NO_GENERATOR_PIN", "NO_600_SESSION_SIZING_EXECUTION_LEDGER", "OPEN_COVERAGE_PARTIAL", "CORPORATE_ACTION_PIT_CONTINUITY_BLOCKED", "DIVIDEND_MARKET_WIDE_PIT_LEDGER_MISSING"],
    }
    write_json(output_dir / "summary.json", summary)
    output_hashes = {path.name: sha256_file(path) for path in output_dir.iterdir() if path.is_file() and path.name != "MANIFEST.json"}
    manifest = {
        "schema_version": "historical_e2e_replay_data_readiness_manifest_v1",
        "status": summary["verdict"],
        "source_commit": "d49b1540d4e6b29deddc0f47ca0cf7cacc9e3b75",
        "source_roots": {"structural": str(structural_root), "panel": str(panel_path), "calendar": str(calendar_path), "ca_window": str(ca_window_root), "dividend": str(dividend_root)},
        "source_hashes": {"structural_manifest": structural_meta["manifest_sha256"], "ca_window_manifest": ca_meta["manifest_sha256"], "ca_window_ledger": ca_meta["ledger_sha256"], "dividend_result": dividend_meta["result_sha256"]},
        "output_hashes": output_hashes,
        "guards": summary["guards"],
    }
    write_json(output_dir / "MANIFEST.json", manifest)
    summary["manifest_sha256"] = sha256_file(output_dir / "MANIFEST.json")
    return summary
