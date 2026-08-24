"""Freeze an outcome-blind historical E2E completeness scope.

This command only consumes structural ledgers, certified official Open
artifacts, and already accepted CA/dividend readiness manifests.  It never
loads labels, targets, returns, scores, or protected forward outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade.historical_e2e_scope_validator_v1 import MIN_STRICT_SESSION_COUNT  # noqa: E402
from idx_trade.v4_x1_execution_v1_verify import verify_open_execution_inputs  # noqa: E402


READINESS_SUMMARY_SHA256 = "31aea94cf6cea52b7a2dcea25676f944bd13f06731b745f0179044f2aca9a040"
READINESS_MANIFEST_SHA256 = "86304dac2226f40e58f18ea302f709106b67609165b4bb488bda4c5d7b4564e7"
CALENDAR_SHA256 = "661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a"
STRUCTURAL_MANIFEST_SHA256 = "a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba"
CA_MANIFEST_SHA256 = "c635ee354c923eebdb586bc4d82a6693d230e1a347df50879dda4c1f5f56bff4"
DIVIDEND_RESULT_SHA256 = "454213df35c3ffd741cc137c24d502f1fc45cd46e229c1c553852b2418e07aac"
EXPOSURE_UNIVERSE_SHA256 = "110d3f7543c33e90a7d2cea1352f6360e0385fd5399c4b61409ee3acba56d030"
CA_EXPOSURE_GAP_SHA256 = "8172ef21fde01545a8d176ed1d2b40703663675c9577bc34791b820ab50e973b"
DIVIDEND_EXPOSURE_GAP_SHA256 = "625c3dfe6986bd9f9309a9a2fad4cb0f8398dfb1edb770655784eac4187c2322"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()
    ).hexdigest()


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def next_session_map(calendar_path: Path) -> dict[str, str]:
    calendar = pd.read_csv(calendar_path, usecols=["date"])
    dates = pd.to_datetime(calendar["date"], errors="raise").dt.normalize()
    values = [x.date().isoformat() for x in dates]
    if len(values) != 1260 or len(values) != len(set(values)):
        raise RuntimeError("CALENDAR_SHAPE_INVALID")
    return dict(zip(values, values[1:]))


def certified_open_map(
    open_root: Path, execution_sessions: set[str]
) -> tuple[dict[str, set[str]], dict[str, set[str]], list[dict[str, object]]]:
    available: dict[str, set[str]] = {}
    evidence: dict[str, set[str]] = {}
    diagnostics: list[dict[str, object]] = []
    for session in sorted(execution_sessions):
        manifest = open_root / "official_open" / session / "manifest.json"
        if not manifest.is_file():
            diagnostics.append({"session_date": session, "status": "MISSING_MANIFEST"})
            continue
        try:
            verified = verify_open_execution_inputs(execution_session_date=session, manifest_path=manifest)
        except Exception as exc:
            diagnostics.append({"session_date": session, "status": "INVALID_MANIFEST", "error": str(exc)})
            continue
        available[session] = set(verified.available_tickers)
        evidence[session] = set(verified.evidence_tickers)
        manifest_payload = load_json(manifest)
        diagnostics.append({
            "session_date": session,
            "status": "CERTIFIED",
            "transport": verified.transport,
            "row_count": int(manifest_payload.get("row_count") or 0),
            "available_open_count": len(verified.available_tickers),
            "evidence_ticker_count": len(verified.evidence_tickers),
            "nonpositive_open_count": len(verified.nonpositive_tickers),
            "manifest_sha256": sha256(manifest),
        })
    return available, evidence, diagnostics


def exposure_window_gate_map(
    readiness_root: Path,
) -> tuple[dict[int, bool], dict[int, bool], dict[str, object]]:
    """Return per-session CA/dividend gates from the pinned exposure ledgers.

    The source-level CA and dividend manifests are intentionally broader than
    a replay exposure window.  This helper narrows only by exact structural
    ``spell_id``/``session_index`` identity; it never treats an absent event
    as proof of no event.
    """

    exposure_path = readiness_root / "decision_v2_exposure_universe.csv"
    ca_path = readiness_root / "ca_exposure_gap.csv"
    dividend_path = readiness_root / "dividend_exposure_gap.csv"
    if sha256(exposure_path) != EXPOSURE_UNIVERSE_SHA256:
        raise RuntimeError("EXPOSURE_UNIVERSE_SHA_MISMATCH")
    if sha256(ca_path) != CA_EXPOSURE_GAP_SHA256:
        raise RuntimeError("CA_EXPOSURE_GAP_SHA_MISMATCH")
    if sha256(dividend_path) != DIVIDEND_EXPOSURE_GAP_SHA256:
        raise RuntimeError("DIVIDEND_EXPOSURE_GAP_SHA_MISMATCH")

    key_columns = [
        "spell_id",
        "session_index",
        "signal_date",
        "ticker",
        "entry_date",
        "exit_date_exclusive",
    ]
    exposure = pd.read_csv(exposure_path, usecols=key_columns)
    ca = pd.read_csv(ca_path, usecols=key_columns + ["ca_strict_pass"])
    dividend = pd.read_csv(
        dividend_path,
        usecols=[
            "spell_id",
            "bounded_certified_event_count",
            "dividend_gap_status",
            "market_wide_no_event_ledger",
        ],
    )
    def keyset(frame: pd.DataFrame) -> set[tuple[str, ...]]:
        return {
            tuple("" if pd.isna(value) else str(value) for value in row)
            for row in frame.loc[:, key_columns].itertuples(index=False, name=None)
        }

    if len(ca) != len(exposure) or keyset(ca) != keyset(exposure):
        raise RuntimeError("CA_EXPOSURE_WINDOW_KEYSET_MISMATCH")
    if set(dividend["spell_id"]) != set(exposure["spell_id"].unique()):
        raise RuntimeError("DIVIDEND_EXPOSURE_WINDOW_KEYSET_MISMATCH")

    ca["ca_strict_pass"] = ca["ca_strict_pass"].map(
        lambda value: str(value).strip().lower() == "true"
    )
    ca_by_session = ca.groupby("session_index", sort=True)["ca_strict_pass"].all()

    # Dividend dispositions are one row per holding spell; expand them over
    # the exact exposure rows for that spell before applying a per-session all
    # gate.  A spell may legitimately span many signal sessions.
    dividend = dividend.merge(exposure, on="spell_id", how="right", validate="one_to_many")
    dividend["dividend_row_ready"] = (
        dividend["dividend_gap_status"].eq("BOUNDED_CERTIFIED_EVENT_OVERLAP")
        & dividend["bounded_certified_event_count"].fillna(0).gt(0)
    ) | dividend["market_wide_no_event_ledger"].map(
        lambda value: str(value).strip().lower() == "true"
    )
    dividend_by_session = dividend.groupby("session_index", sort=True)[
        "dividend_row_ready"
    ].all()
    ca_map = {int(index): bool(value) for index, value in ca_by_session.items()}
    dividend_map = {
        int(index): bool(value) for index, value in dividend_by_session.items()
    }
    return ca_map, dividend_map, {
        "ca_exposure_rows": int(len(ca)),
        "ca_exposure_ready_rows": int(ca["ca_strict_pass"].sum()),
        "ca_exposure_ready_sessions": int(sum(ca_map.values())),
        "dividend_exposure_rows": int(len(dividend)),
        "dividend_exposure_ready_rows": int(dividend["dividend_row_ready"].sum()),
        "dividend_exposure_ready_sessions": int(sum(dividend_map.values())),
        "ca_exposure_gap_sha256": CA_EXPOSURE_GAP_SHA256,
        "dividend_exposure_gap_sha256": DIVIDEND_EXPOSURE_GAP_SHA256,
        "exposure_universe_sha256": EXPOSURE_UNIVERSE_SHA256,
    }


def longest_contiguous_indices(rows: list[dict[str, object]], key: str) -> list[int]:
    """Choose the longest true run, breaking ties by earliest session index."""

    runs: list[list[int]] = []
    current: list[int] = []
    for row in rows:
        index = int(row["session_index"])
        if bool(row[key]) and (not current or index == current[-1] + 1):
            current.append(index)
        else:
            if current:
                runs.append(current)
            current = [index] if bool(row[key]) else []
    if current:
        runs.append(current)
    return max(runs, key=lambda run: (len(run), -run[0]), default=[])


def freeze(
    *,
    readiness_root: Path,
    structural_root: Path,
    calendar_path: Path,
    open_root: Path,
    ca_root: Path,
    dividend_result: Path,
    output: Path,
) -> dict[str, object]:
    readiness_manifest = readiness_root / "MANIFEST.json"
    readiness_summary = readiness_root / "summary.json"
    if sha256(readiness_manifest) != READINESS_MANIFEST_SHA256:
        raise RuntimeError("READINESS_MANIFEST_SHA_MISMATCH")
    if sha256(readiness_summary) != READINESS_SUMMARY_SHA256:
        raise RuntimeError("READINESS_SUMMARY_SHA_MISMATCH")
    readiness_manifest_payload = load_json(readiness_manifest)
    readiness_output_hashes = readiness_manifest_payload.get("output_hashes")
    if not isinstance(readiness_output_hashes, dict):
        raise RuntimeError("READINESS_OUTPUT_HASHES_MISSING")
    for name, expected in {
        "decision_v2_exposure_universe.csv": EXPOSURE_UNIVERSE_SHA256,
        "ca_exposure_gap.csv": CA_EXPOSURE_GAP_SHA256,
        "dividend_exposure_gap.csv": DIVIDEND_EXPOSURE_GAP_SHA256,
    }.items():
        if readiness_output_hashes.get(name) != expected:
            raise RuntimeError(f"READINESS_OUTPUT_HASH_MISMATCH:{name}")
    structural_manifest = structural_root / "MANIFEST.json"
    if sha256(structural_manifest) != STRUCTURAL_MANIFEST_SHA256:
        raise RuntimeError("STRUCTURAL_MANIFEST_SHA_MISMATCH")
    if sha256(calendar_path) != CALENDAR_SHA256:
        raise RuntimeError("CALENDAR_SHA_MISMATCH")
    if sha256(ca_root / "MANIFEST.json") != CA_MANIFEST_SHA256:
        raise RuntimeError("CA_MANIFEST_SHA_MISMATCH")
    if sha256(dividend_result) != DIVIDEND_RESULT_SHA256:
        raise RuntimeError("DIVIDEND_RESULT_SHA_MISMATCH")
    acquisition_manifest = open_root / "ACQUISITION_MANIFEST.json"
    acquisition = load_json(acquisition_manifest)
    records = acquisition.get("records")
    if (
        acquisition.get("status") != "COMPLETE"
        or acquisition.get("session_count") != 600
        or not isinstance(records, list)
        or len(records) != 600
        or any(not isinstance(row, dict) or row.get("status") != "CERTIFIED" for row in records)
    ):
        raise RuntimeError("OPEN_ACQUISITION_NOT_COMPLETE_CERTIFIED")

    sessions = pd.read_csv(structural_root / "decision_session_ledger.csv", usecols=["index", "date"])
    intents = pd.read_csv(structural_root / "decision_intent_ledger.csv", usecols=["index", "date", "side", "ticker"])
    if len(sessions) != 600 or sessions["index"].tolist() != list(range(600)):
        raise RuntimeError("STRUCTURAL_SESSION_LEDGER_INVALID")
    next_by_date = next_session_map(calendar_path)
    execution_dates = {next_by_date[str(row.date)[:10]] for row in sessions.itertuples()}
    opens, open_evidence, open_diagnostics = certified_open_map(open_root, execution_dates)
    ca_by_session, dividend_by_session, exposure_diagnostics = exposure_window_gate_map(
        readiness_root
    )

    per_session: list[dict[str, object]] = []
    for row in sessions.itertuples(index=False):
        decision_date = str(row.date)[:10]
        execution_date = next_by_date[decision_date]
        required = set(
            intents.loc[
                (intents["index"] == row.index) & (intents["side"] == "BUY_INTENT"), "ticker"
            ].astype(str).str.upper()
        )
        sell_required = set(
            intents.loc[
                (intents["index"] == row.index) & (intents["side"] == "SELL_INTENT"), "ticker"
            ].astype(str).str.upper()
        )
        available = opens.get(execution_date, set())
        certified_evidence = open_evidence.get(execution_date, set())
        missing = sorted(required - certified_evidence)
        nonpositive = sorted((required & certified_evidence) - available)
        sell_missing = sorted(sell_required - certified_evidence)
        sell_nonpositive = sorted((sell_required & certified_evidence) - available)
        ca_exposure_ready = ca_by_session.get(int(row.index), False)
        dividend_exposure_ready = dividend_by_session.get(int(row.index), False)
        per_session.append({
            "session_index": int(row.index),
            "decision_session_date": decision_date,
            "execution_session_date": execution_date,
            "buy_required_count": len(required),
            "buy_open_available_count": len(required & available),
            "buy_open_evidence_count": len(required & certified_evidence),
            "buy_open_missing_tickers": missing,
            "buy_open_nonpositive_tickers": nonpositive,
            "buy_open_positive_missing_tickers": sorted(required - available),
            "buy_open_ready": not missing,
            "sell_required_count": len(sell_required),
            "sell_open_available_count": len(sell_required & available),
            "sell_open_evidence_count": len(sell_required & certified_evidence),
            "sell_open_missing_tickers": sell_missing,
            "sell_open_nonpositive_tickers": sell_nonpositive,
            "sell_open_positive_missing_tickers": sorted(sell_required - available),
            "sell_open_ready": not sell_missing,
            "ca_exposure_ready": ca_exposure_ready,
            "dividend_exposure_ready": dividend_exposure_ready,
            "scope_candidate_ready": (
                not missing
                and not sell_missing
                and ca_exposure_ready
                and dividend_exposure_ready
            ),
        })

    readiness = load_json(readiness_summary)
    readiness_open = readiness.get("open_execution") if isinstance(readiness.get("open_execution"), dict) else {}
    readiness_holding = readiness.get("holding_inputs") if isinstance(readiness.get("holding_inputs"), dict) else {}
    readiness_ca = readiness.get("corporate_actions") if isinstance(readiness.get("corporate_actions"), dict) else {}
    ca_manifest = load_json(ca_root / "MANIFEST.json")
    dividend = load_json(dividend_result)
    buy_ready = sum(bool(row["buy_open_ready"]) for row in per_session)
    sell_ready = sum(bool(row["sell_open_ready"]) for row in per_session)
    all_open_certified = len(opens) == len(execution_dates)
    dividend_no_event_proof = bool(dividend.get("market_wide_no_event_proof"))
    blockers = []
    if not all_open_certified:
        blockers.append("OFFICIAL_OPEN_SESSION_COVERAGE_INCOMPLETE")
    if not buy_ready == len(per_session):
        blockers.append("BUY_OPEN_EVIDENCE_INCOMPLETE")
    if not sell_ready == len(per_session):
        blockers.append("SELL_OPEN_EVIDENCE_INCOMPLETE")
    strict_sessions = longest_contiguous_indices(per_session, "scope_candidate_ready")
    if not strict_sessions:
        blockers.append("NO_CONTIGUOUS_EXPOSURE_COMPLETE_RANGE")
    elif len(strict_sessions) < MIN_STRICT_SESSION_COUNT:
        blockers.append("NO_CONTIGUOUS_EXPOSURE_COMPLETE_RANGE_MINIMUM_20")
        strict_sessions = []
    if not any(bool(row["ca_exposure_ready"]) for row in per_session):
        blockers.append("CA_EXPOSURE_WINDOW_CONTINUITY_BLOCKED")
    if not any(bool(row["dividend_exposure_ready"]) for row in per_session):
        blockers.append("DIVIDEND_EXPOSURE_WINDOW_PROOF_INCOMPLETE")
    strict_rows = [per_session[index] for index in strict_sessions]
    body: dict[str, object] = {
        "schema_version": "idx_trade_historical_e2e_scope_v1",
        "status": "STRICT_SCOPE_FROZEN" if strict_sessions else "STRICT_SCOPE_EMPTY_BLOCKED",
        "outcome_access": False,
        "model_fit": False,
        "protected_outcome_access": False,
        "source_pins": {
            "readiness_manifest_sha256": READINESS_MANIFEST_SHA256,
            "readiness_summary_sha256": READINESS_SUMMARY_SHA256,
            "exposure_universe_sha256": EXPOSURE_UNIVERSE_SHA256,
            "ca_exposure_gap_sha256": CA_EXPOSURE_GAP_SHA256,
            "dividend_exposure_gap_sha256": DIVIDEND_EXPOSURE_GAP_SHA256,
            "structural_manifest_sha256": STRUCTURAL_MANIFEST_SHA256,
            "calendar_sha256": CALENDAR_SHA256,
            "open_acquisition_manifest_sha256": sha256(open_root / "ACQUISITION_MANIFEST.json"),
            "ca_manifest_sha256": sha256(ca_root / "MANIFEST.json"),
            "dividend_result_sha256": sha256(dividend_result),
        },
        "candidate_session_count": len(per_session),
        "strict_session_indices": strict_sessions,
        "start_session": strict_rows[0]["decision_session_date"] if strict_rows else None,
        "end_session": strict_rows[-1]["decision_session_date"] if strict_rows else None,
        "session_count": len(strict_sessions),
        "blockers": blockers,
        "open": {
            "execution_session_count": len(execution_dates),
            "certified_execution_session_count": len(opens),
            "all_session_manifests_certified": all_open_certified,
            "buy_ready_session_count": buy_ready,
            "sell_ready_session_count": sell_ready,
            "per_session": per_session,
            "diagnostics": open_diagnostics,
        },
        "exposure_window": exposure_diagnostics,
        "readiness_audit": {
            "official_open": readiness_open,
            "holding_inputs": readiness_holding,
            "corporate_actions": readiness_ca,
        },
        "ca_status": ca_manifest.get("status"),
        "ca_source_status": ca_manifest.get("status"),
        "dividend_market_wide_no_event_proof": dividend_no_event_proof,
    }
    body["scope_payload_sha256"] = canonical_hash(body)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise RuntimeError(f"SCOPE_OUTPUT_EXISTS:{output}")
    output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness-root", type=Path, required=True)
    parser.add_argument("--structural-root", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--open-root", type=Path, required=True)
    parser.add_argument("--ca-root", type=Path, required=True)
    parser.add_argument("--dividend-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = freeze(
        readiness_root=args.readiness_root.resolve(),
        structural_root=args.structural_root.resolve(),
        calendar_path=args.calendar.resolve(),
        open_root=args.open_root.resolve(),
        ca_root=args.ca_root.resolve(),
        dividend_result=args.dividend_result.resolve(),
        output=args.output.resolve(),
    )
    print(json.dumps({
        "status": result["status"],
        "candidate_session_count": result["candidate_session_count"],
        "strict_session_count": len(result["strict_session_indices"]),
        "blockers": result["blockers"],
        "scope_payload_sha256": result["scope_payload_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
