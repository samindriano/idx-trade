"""Replay the E2E paper path with synthetic, hash-pinned production artifacts.

The replay intentionally uses the public score/EOD/Open/CA verifiers and the
real POST_EOD/PREOPEN orchestrator. It never calls a provider or opens an
outcome artifact.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from idx_trade import forward_ca_attestation_v1 as ca
from idx_trade import forward_dividend_v1 as dividend
from idx_trade import forward_dividend_orchestration_v1 as orchestration
from idx_trade import forward_dividend_provenance_v1_2 as provenance
from idx_trade import forward_dividend_runtime_v1_1 as runtime
import idx_trade.e2e_paper_orchestration_v1 as e2e_orchestration_module
import idx_trade.forward_dividend_execution_v1_1 as dividend_execution_module
import idx_trade.v4_x1_execution_v1_verify as execution_verify_module
from idx_trade.e2e_paper_orchestration_v1 import (
    _canonical_hash,
    E2EPaperPaths,
    bootstrap_t0,
    derive_required_execution_tickers,
    execute_preopen,
    load_score_manifest,
    prepare_post_eod,
    _state_for_dividend_sizing,
)
from idx_trade.e2e_replay_boundary_v1 import replay_boundary_static_audit_v1
from idx_trade.forward_dividend_execution_v1_1 import (
    reconcile_corporate_action_attestation_v1_2_journal,
    verify_cash_dividend_evidence_for_execution,
)
from idx_trade.official_open_evidence_v1 import (
    AUTHORITY,
    FALLBACK_POLICY,
    FIELD_SEMANTICS,
    TRANSPORT_POLICY,
    UPSTREAM_PATH,
    certify_official_open_raw_response,
)
from idx_trade.v4_x1_decision_v1_contract import (
    EXPECTED_ALPHA_MODEL_FINGERPRINT,
    EXPECTED_ALPHA_MODEL_ID,
    EXPECTED_FREEZE_BOUNDARY,
    EXPECTED_GENERATION,
    EXPECTED_SCIENTIFIC_BLOBS,
    REQUIRED_SCORE_COLUMNS,
)


TICKERS = tuple(f"T{index:02d}" for index in range(11))
PROGRESS_SCHEMA = "idx_trade_e2e_paper_production_replay_progress_v1"
SESSIONS = (
    ("2026-08-24", "2026-08-25"),
    ("2026-08-25", "2026-08-26"),
    ("2026-08-26", "2026-08-27"),
    ("2026-08-27", "2026-08-28"),
    ("2026-08-28", "2026-08-31"),
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_pdf(
    path: Path,
    *,
    cum: str,
    ex: str,
    record: str,
    payment: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref}),
    })
    def display(value: str) -> str:
        parsed = date.fromisoformat(value)
        return f"{parsed.day} {parsed.strftime('%B')} {parsed.year}"

    text = (
        "BT /F1 12 Tf 72 720 Td (T00 cash dividend Rp 25 per share. "
        f"Cum dividend {display(cum)}. Ex dividend {display(ex)}. "
        f"Record date {display(record)}. Payment date {display(payment)}.) Tj ET"
    ).encode("ascii")
    stream = DecodedStreamObject()
    stream.set_data(text)
    page[NameObject("/Contents")] = writer._add_object(stream)
    with path.open("wb") as handle:
        writer.write(handle)


def _score_fixture(root: Path, session: str, index: int) -> Path:
    order = TICKERS if index == 0 else tuple(TICKERS[1:]) + (TICKERS[0],)
    ranks = {ticker: rank for rank, ticker in enumerate(order, start=1)}
    alpha = {ticker: float((len(TICKERS) - ranks[ticker]) / len(TICKERS)) for ticker in TICKERS}
    frame = pd.DataFrame({
        "ticker": list(TICKERS),
        "date": [session] * len(TICKERS),
        "alpha_h5": [alpha[ticker] for ticker in TICKERS],
        "alpha_h10": [alpha[ticker] for ticker in TICKERS],
        "alpha_consensus": [alpha[ticker] for ticker in TICKERS],
        "rank_consensus": [ranks[ticker] for ticker in TICKERS],
    })
    artifact = root / "scores" / session / "score.parquet"
    manifest = root / "scores" / session / "manifest.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(artifact, index=False)
    _write_json(manifest, {
        "schema_version": "v4_x1_prospective_score_manifest_v2",
        "status": "DONE",
        "model_id": EXPECTED_ALPHA_MODEL_ID,
        "generation": EXPECTED_GENERATION,
        "model_fingerprint": EXPECTED_ALPHA_MODEL_FINGERPRINT,
        "guards": {
            "provider_calls": False,
            "protected_outcome_accessed": False,
            "realized_forward_outcome_loaded": False,
            "historical_prediction_generated": False,
            "model_refit": False,
            "model_retuned": False,
            "science_changed": False,
        },
        "model_bundle": {"manifest_sha256": EXPECTED_ALPHA_MODEL_FINGERPRINT},
        "freshness": {"model_freeze_observed_by": EXPECTED_FREEZE_BOUNDARY},
        "science": {
            "consensus_formula": "0.5*H5_WITHIN_DATE_PERCENTILE_RANK+0.5*H10_WITHIN_DATE_PERCENTILE_RANK",
            "frozen_scientific_git_blobs": EXPECTED_SCIENTIFIC_BLOBS,
        },
        "session_date": session,
        "rows": len(frame),
        "output": {
            "artifact_path": artifact.name,
            "artifact_sha256": _sha(artifact),
            "columns": list(REQUIRED_SCORE_COLUMNS),
        },
    })
    return manifest


def _eod_fixture(root: Path, session: str, next_session: str) -> tuple[Path, Path, Path]:
    closes = {ticker: 1000.0 + index for index, ticker in enumerate(TICKERS)}
    ohlcv = root / "eod" / session / "session_ohlcv.parquet"
    model = root / "eod" / session / "model_input.parquet"
    calendar = root / "eod" / session / "calendar.csv"
    ohlcv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "ticker": list(TICKERS), "session_date": [session] * len(TICKERS),
        "close": [closes[ticker] for ticker in TICKERS],
    }).to_parquet(ohlcv, index=False)
    pd.DataFrame({
        "ticker": list(TICKERS), "date": [session] * len(TICKERS),
        "close": [closes[ticker] for ticker in TICKERS],
        "regular_market_value": [1_000_000_000.0] * len(TICKERS),
    }).to_parquet(model, index=False)
    pd.DataFrame({"date": [session, next_session]}).to_csv(calendar, index=False)
    return ohlcv, model, calendar


def _open_fixture(root: Path, session: str) -> Path:
    rows = [
        {
            "StockCode": ticker,
            "Date": session,
            "OpenPrice": 1000 + index,
            "FirstTrade": 999 + index,
        }
        for index, ticker in enumerate(TICKERS)
    ]
    raw = {
        "data": rows,
        "recordsTotal": len(rows),
        "recordsFiltered": len(rows),
    }
    folder = root / "open" / session
    folder.mkdir(parents=True, exist_ok=True)
    raw_path = folder / "raw.json"
    raw_path.write_text(json.dumps(raw, sort_keys=True) + "\n", encoding="utf-8")
    return certify_official_open_raw_response(
        raw_path.read_bytes(),
        session_date=session,
        output_dir=folder / "certified",
        transport="DIRECT_IDX_HTTPS",
        transport_metadata={"synthetic_fixture": True, "upstream_path": UPSTREAM_PATH},
    )


def _candidate(ticker: str, *, cum: str, ex: str, record: str, payment: str, announcement: str) -> dict[str, object]:
    return {
        "ticker": ticker,
        "announcement_id": f"{announcement.replace('-', '')}-001/{ticker}/2026_id-id",
        "announcement_number": f"001/{ticker}/2026",
        "announcement_timestamp": announcement,
        "title": "Jadwal Dividen Tunai Interim",
        "form_id": "11000",
        "classification": "CASH_DIVIDEND_CANDIDATE",
        "cum_regular_negotiated": cum,
        "ex_regular_negotiated": ex,
        "record_date": record,
        "payment_date": payment,
        "gross_dividend_per_share_idr": "25",
    }


def _write_v12_review(
    root: Path,
    *,
    announcement: str,
    batch_label: str = "2026-08-27_PREOPEN",
    event_schedule: tuple[str, str, str, str] = (
        "2026-08-25", "2026-08-26", "2026-08-27", "2026-08-31",
    ),
) -> tuple[Path, object]:
    batch_root = root / "batches" / batch_label
    evidence_dir = batch_root / "evidence" / "T00_late_correction"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "Id2": f"{announcement.replace('-', '')}-001/T00/2026_id-id",
        "NoPengumuman": "001/T00/2026",
        "Kode_Emiten": "T00",
        "TglPengumuman": announcement,
        "JudulPengumuman": "Jadwal Dividen Tunai Interim",
        "Form_Id": "11000",
    }
    record_sha = provenance.canonical_sha256(record)
    discovery_dir = batch_root / "discovery"
    discovery_dir.mkdir(parents=True, exist_ok=True)
    page = discovery_dir / "T00_page_001.json"
    page_payload = {"Replies": [{"pengumuman": record, "attachments": []}]}
    _write_json(page, page_payload)
    discovery = discovery_dir / "DISCOVERY_MANIFEST.json"
    cum, ex, record_date, payment = event_schedule
    candidate = _candidate(
        "T00", cum=cum, ex=ex, record=record_date,
        payment=payment, announcement=announcement,
    )
    _write_json(discovery, {
        "schema_version": "idx_trade_forward_dividend_announcement_capture_v1",
        "status": "COMPLETE",
        "raw_artifacts": [{"ticker": "T00", "path": page.name, "sha256": _sha(page)}],
        "candidates": [candidate],
    })
    pdf = evidence_dir / "official.pdf"
    _write_pdf(pdf, cum=cum, ex=ex, record=record_date, payment=payment)
    attachment_manifest = evidence_dir / "ATTACHMENT_CAPTURE_MANIFEST.json"
    _write_json(attachment_manifest, {
        "schema_version": "idx_trade_forward_dividend_attachment_capture_v1_1",
        "status": "COMPLETE_AWAITING_SEMANTIC_REVIEW",
        "candidate": candidate,
        "attachments": [{"pdf_filename": pdf.name, "sha256": _sha(pdf)}],
    })
    announcement_projection = {
        "id": candidate["announcement_id"], "number": candidate["announcement_number"],
        "date": announcement, "code": "T00", "title": candidate["title"], "form_id": "11000",
    }
    review = {
        "schema_version": provenance.REVIEW_SCHEMA_V1_2,
        "status": provenance.REVIEW_STATUS_V1_2,
        "authority_recommendation": provenance.AUTHORITY_V1_2,
        "transport_provenance": {
            "source_raw_page_sha256": [_sha(page)],
            "source_discovery_manifest_resolved_path": str(discovery.resolve()),
            "source_discovery_manifest_sha256": _sha(discovery),
            "source_attachment_manifest_sha256": _sha(attachment_manifest),
        },
        "announcement_provenance": {
            "exact_announcement_record": record,
            "announcement_record_sha256": record_sha,
        },
        "announcement": announcement_projection,
        "documents": [{"pdf_filename": pdf.name, "sha256": _sha(pdf)}],
        "expected_event": {
            "ticker": "T00", "gross_dividend_per_share_idr": "25",
            "cum_regular_negotiated": cum, "ex_regular_negotiated": ex,
            "record_date": record_date, "payment_date": payment,
        },
        "semantic_matches": {
            "ticker": True, "dividend_subject": True, "dividend_per_share": True,
            "cum_regular_negotiated": True, "ex_regular_negotiated": True,
            "record_date": True, "payment_date": True,
        },
        "documents_count": 1, "failures": [], "warnings": [],
    }
    review_path = evidence_dir / "ATTACHMENT_REVIEW_V1_2.json"
    _write_json(review_path, review)
    verified = verify_cash_dividend_evidence_for_execution(
        review_path=review_path, attachment_dir=evidence_dir,
    )
    return review_path, verified


def _ca_fixture(
    root: Path,
    session: str,
    next_session: str,
    required: tuple[str, ...],
    *,
    include_event: bool,
    capture_phase: str = "POST_EOD",
    capture_timestamp_utc: str | None = None,
    announcement: str = "2026-08-27T10:00:00",
    event_schedule: tuple[str, str, str, str] = (
        "2026-08-25", "2026-08-26", "2026-08-27", "2026-08-31",
    ),
) -> tuple[Path, Path, object | None]:
    phase_name = capture_phase.strip().upper()
    if phase_name not in {"POST_EOD", "PREOPEN"}:
        raise ValueError(f"unsupported capture phase: {capture_phase}")
    ca_root = root / "ca" / session / phase_name
    ca_root.mkdir(parents=True, exist_ok=True)
    announcement_items = []
    if include_event:
        announcement_items = [{"Code": "T00", "Date": session, "Title": "Jadwal Dividen Tunai Interim T00"}]
    raw_rows = {
        "issued_history": ({"data": []}, "/ListingActivity/GetIssuedHistory"),
        "announcements": ({"Items": announcement_items}, "/NewsAnnouncement/GetAllAnnouncement"),
        "calendar": ({"Results": [{"Date": next_session, "Code": "T00", "Title": "Dividend"}]}, "/Home/GetCalendar"),
    }
    artifacts = []
    for leg, (payload, endpoint) in raw_rows.items():
        raw = ca_root / f"{leg}.json"
        _write_json(raw, payload)
        artifacts.append({"leg": leg, "endpoint": endpoint, "http_status": 200, "content_type": "application/json", "path": raw.name, "sha256": _sha(raw)})
    calendar_fp = ca._structural_fingerprint(raw_rows["calendar"][0])
    phase = ca_root / f"{phase_name.lower()}_phase.json"
    capture_timestamp_utc = capture_timestamp_utc or f"{session}T12:00:00+00:00"
    _write_json(phase, {
        "schema_version": ca.PHASE_SCHEMA, "status": "COMPLETE",
        "provider_repository": ca.PROVIDER_REPOSITORY, "provider_commit": ca.PROVIDER_COMMIT,
        "upstream_base_url": ca.UPSTREAM_BASE_URL, "calendar_capture_scope": ca.CALENDAR_CAPTURE_SCOPE,
        "phase": phase_name, "from_session_date": session, "through_session_date": next_session,
        "capture_timestamp_utc": capture_timestamp_utc,
        "required_tickers": list(required),
        "legs": {leg: {"status": "COMPLETE"} for leg in raw_rows},
        "raw_artifacts": artifacts, "calendar_schema_fingerprints": [calendar_fp],
    })
    attestation = ca_root / "attestation.json"
    review_path = None
    verified = None
    if include_event:
        review_path, verified = _write_v12_review(
            root,
            announcement=announcement,
            batch_label=f"{session}_{phase_name}",
            event_schedule=event_schedule,
        )
    evidence_rows = []
    for ticker in required:
        if include_event and ticker == "T00":
            evidence_rows.append({"ticker": ticker, "status": ca.RELEVANT, "reasons": [f"{phase_name}:ANNOUNCEMENT:T00"]})
        else:
            evidence_rows.append({"ticker": ticker, "status": ca.NO_EVENT, "reasons": []})
    _write_json(attestation, {
        "schema_version": ca.ATTESTATION_SCHEMA_V1_2, "capture_phase": phase_name,
        "capture_timestamp_utc": capture_timestamp_utc,
        "provider_repository": ca.PROVIDER_REPOSITORY, "provider_commit": ca.PROVIDER_COMMIT,
        "upstream_base_url": ca.UPSTREAM_BASE_URL,
        "calendar_schema_fingerprint": ca.EXPECTED_CALENDAR_SCHEMA_FINGERPRINT,
        "from_session_date": session, "through_session_date": next_session,
        "status": "RELEVANT_EVENT_DETECTED" if include_event else "NO_RELEVANT_EVENTS",
        "evidence_rows": evidence_rows, "phase_manifest_path": phase.name,
        "phase_manifest_sha256": _sha(phase),
    })
    journal_path = ca_root / "journal.json"
    certified = ()
    if include_event and verified is not None:
        certified = (orchestration.CertifiedDividendJournalEntry(
            announcement_identity=verified.announcement_id or verified.announcement_number,
            ticker=verified.event.ticker, event_id=verified.event.event_id,
            event_sha256=verified.event.source_evidence_sha256,
            evidence_dir=str(review_path.parent.resolve()), review_sha256=verified.review_sha256,
            review_filename=review_path.name,
        ),)
    orchestration.write_journal_document(
        journal_path,
        orchestration.DividendAcquisitionJournal(
            as_of_date=session, required_tickers=required,
            coverage=tuple(orchestration.DividendCoverage(ticker, session) for ticker in required),
            certified_events=certified,
            capture_phase=phase_name,
        ),
    )
    return attestation, journal_path, verified


def _resume_probe(root: Path) -> None:
    snapshot = runtime.load_latest_runtime_snapshot(root)
    if not snapshot.state.base_state.as_of_session_date:
        raise RuntimeError("REPLAY_RESUME_STATE_INVALID")
    executions = list((root / "executions").glob("*.json"))
    if not executions:
        raise RuntimeError("REPLAY_RESUME_EXECUTION_MISSING")


def _progress_path(root: Path) -> Path:
    return root / "replay_progress.json"


def _write_progress(
    root: Path,
    *,
    rows: list[dict[str, object]],
    last_score_manifest: Path,
) -> Path:
    snapshot = runtime.load_latest_runtime_snapshot(root)
    payload: dict[str, object] = {
        "schema_version": PROGRESS_SCHEMA,
        "completed_session_count": len(rows),
        "sessions": rows,
        "last_score_manifest_path": str(last_score_manifest.resolve()),
        "runtime_snapshot_path": str(snapshot.path.resolve()),
        "runtime_snapshot_sha256": snapshot.file_sha256,
        "runtime_state_sha256": snapshot.runtime_state_sha256,
    }
    payload["payload_sha256"] = _canonical_hash(payload)
    _write_json(_progress_path(root), payload)
    return _progress_path(root)


def _load_progress(root: Path) -> tuple[list[dict[str, object]], Path]:
    path = _progress_path(root)
    if not path.is_file():
        raise SystemExit(f"REPLAY_PROGRESS_MISSING:{path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != PROGRESS_SCHEMA:
        raise SystemExit("REPLAY_PROGRESS_SCHEMA_INVALID")
    body = dict(payload)
    declared = str(body.pop("payload_sha256") or "")
    if _canonical_hash(body) != declared:
        raise SystemExit("REPLAY_PROGRESS_HASH_MISMATCH")
    rows = payload.get("sessions")
    if not isinstance(rows, list) or payload.get("completed_session_count") != len(rows):
        raise SystemExit("REPLAY_PROGRESS_COMPLETENESS_INVALID")
    last_score_manifest = Path(str(payload.get("last_score_manifest_path") or "")).resolve()
    if not last_score_manifest.is_file():
        raise SystemExit("REPLAY_PROGRESS_LAST_SCORE_MISSING")
    snapshot = runtime.load_latest_runtime_snapshot(root)
    if str(payload.get("runtime_snapshot_path") or "") != str(snapshot.path.resolve()):
        raise SystemExit("REPLAY_PROGRESS_RUNTIME_PARENT_MISMATCH")
    if str(payload.get("runtime_snapshot_sha256") or "") != snapshot.file_sha256:
        raise SystemExit("REPLAY_PROGRESS_RUNTIME_SHA_MISMATCH")
    if str(payload.get("runtime_state_sha256") or "") != snapshot.runtime_state_sha256:
        raise SystemExit("REPLAY_PROGRESS_RUNTIME_STATE_SHA_MISMATCH")
    return [dict(row) for row in rows], last_score_manifest


def _production_session_oracle(index: int) -> dict[str, object]:
    """Independent expectations for the deterministic fixture schedule."""
    from idx_trade.v4_x1_execution_v1_contract import (
        BUY_FEE_BPS,
        LOT_SIZE_SHARES,
        MAX_ENTRY_WEIGHT,
        MAX_ORDER_NOTIONAL_SHARE_REFERENCE_VALUE,
        SLIPPAGE_BPS,
        STAMP_DUTY_IDR,
        STAMP_DUTY_THRESHOLD_IDR,
    )

    fills: list[dict[str, object]] = []
    if index == 0:
        cash = 50_000_000.0
        eod_nav = 50_000_000.0
        entry_count = len(TICKERS[:10])
        desired = min(0.10 * eod_nav, cash / entry_count)
        candidates: list[dict[str, object]] = []
        for ticker_index, ticker in enumerate(TICKERS[:10]):
            raw_open = 1_000.0 + ticker_index
            effective_price = raw_open * (1.0 + SLIPPAGE_BPS / 10_000.0)
            planned_shares = 5_000 if ticker_index < 7 else 4_900
            gross_per_lot = effective_price * LOT_SIZE_SHARES
            debit_per_lot = gross_per_lot * (1.0 + BUY_FEE_BPS / 10_000.0)
            capacity_notional = MAX_ORDER_NOTIONAL_SHARE_REFERENCE_VALUE * 1_000_000_000.0
            upper_lots = min(
                planned_shares // LOT_SIZE_SHARES,
                int((MAX_ENTRY_WEIGHT * eod_nav) // gross_per_lot),
                int(capacity_notional // gross_per_lot),
            )
            candidates.append({
                "ticker": ticker,
                "raw_open": raw_open,
                "effective_price": effective_price,
                "planned_shares": planned_shares,
                "capacity_notional": capacity_notional,
                "upper_lots": max(0, upper_lots),
                "debit_per_lot": debit_per_lot,
            })

        lots = {
            row["ticker"]: min(
                int(row["upper_lots"]),
                int(desired // float(row["debit_per_lot"])),
            )
            for row in candidates
        }

        def stamp_for(turnover: float) -> float:
            return STAMP_DUTY_IDR if turnover > STAMP_DUTY_THRESHOLD_IDR else 0.0

        def gross_total() -> float:
            return sum(
                lots[row["ticker"]] * float(row["effective_price"]) * LOT_SIZE_SHARES
                for row in candidates
            )

        def debit_total() -> float:
            gross = gross_total()
            return gross + gross * BUY_FEE_BPS / 10_000.0 + stamp_for(gross)

        while debit_total() > cash + 1e-6:
            removable = []
            for row in candidates:
                ticker = row["ticker"]
                count = lots[ticker]
                if count <= 0:
                    continue
                lot_gross = float(row["effective_price"]) * LOT_SIZE_SHARES
                current = count * lot_gross
                after = (count - 1) * lot_gross
                penalty = abs(after - desired) - abs(current - desired)
                removable.append((round(penalty, 15), -int(row["planned_shares"]), ticker))
            if not removable:
                raise RuntimeError("REPLAY_ORACLE_CAPACITY_ALLOCATION_FAILED")
            _, _, ticker = min(removable)
            lots[ticker] -= 1

        while True:
            current_gross = gross_total()
            additions = []
            for row in candidates:
                ticker = row["ticker"]
                count = lots[ticker]
                if count >= int(row["upper_lots"]):
                    continue
                lot_gross = float(row["effective_price"]) * LOT_SIZE_SHARES
                current_error = abs(count * lot_gross - desired) / max(desired, 1.0)
                next_error = abs((count + 1) * lot_gross - desired) / max(desired, 1.0)
                improvement = current_error - next_error
                if improvement < -1e-15:
                    continue
                next_gross = current_gross + lot_gross
                next_debit = next_gross + next_gross * BUY_FEE_BPS / 10_000.0 + stamp_for(next_gross)
                if next_debit <= cash + 1e-6:
                    additions.append((-round(improvement, 15), int(row["planned_shares"]), ticker))
            if not additions:
                break
            _, _, ticker = min(additions)
            lots[ticker] += 1

        for row in candidates:
            ticker = str(row["ticker"])
            filled_shares = lots[ticker] * LOT_SIZE_SHARES
            row["expected_filled_shares"] = filled_shares
            gross = filled_shares * float(row["effective_price"])
            fee = gross * BUY_FEE_BPS / 10_000.0
            fills.append({
                "side": "BUY",
                "ticker": ticker,
                "planned_shares": int(row["planned_shares"]),
                "filled_shares": filled_shares,
                "raw_open": float(row["raw_open"]),
                "effective_price": float(row["effective_price"]),
                "gross_notional": gross,
                "fee_idr": fee,
                "cash_effect_idr": -(gross + fee),
                "status": "SIMULATED_FILLED_JOINT_LOT_CAPACITY_GUARDED",
                "replacement_peer": None,
            })
    fees_total = sum(float(row["fee_idr"]) for row in fills)
    gross_total_value = sum(float(row["gross_notional"]) for row in fills)
    if index == 0:
        first_session_gross = gross_total_value
        first_session_fees = fees_total
        first_session_stamp = 10_000.0 if gross_total_value > 10_000_000.0 else 0.0
        expected_positions = [
            [str(row["ticker"]), int(row["filled_shares"])] for row in fills
        ]
    else:
        first = _production_session_oracle(0)
        first_session_gross = float(first["gross_turnover_idr"])
        first_session_fees = float(first["fee_total_idr"])
        first_session_stamp = float(first["stamp_duty_idr"])
        expected_positions = [list(row) for row in first["positions_after"]]
    cash_after_first_session = (
        50_000_000.0 - first_session_gross - first_session_fees - first_session_stamp
    )
    return {
        "status": "EXECUTION_COMPLETE",
        "fills": fills,
        "fill_count": len(fills),
        "fill_shares_total": sum(int(row["filled_shares"]) for row in fills),
        "fee_total_idr": fees_total,
        "pending_transition_count": 0,
        "gross_turnover_idr": gross_total_value,
        "stamp_duty_idr": 10_000.0 if gross_total_value > STAMP_DUTY_THRESHOLD_IDR else 0.0,
        "cash_idr_after_execution": cash_after_first_session,
        "positions_after": expected_positions,
        "receivables": [],
        "settlements": [],
        "independent_capacity_components": [
            {
                "ticker": row["ticker"],
                "planned_shares": row["planned_shares"],
                "raw_open": row["raw_open"],
                "effective_price": row["effective_price"],
                "capacity_notional": row["capacity_notional"],
                "upper_lots": row["upper_lots"],
                "expected_filled_shares": row["expected_filled_shares"],
            }
            for row in (candidates if index == 0 else [])
        ],
        "preopen_semantic_delta": index == 3,
        "registry_events": 1 if index >= 3 else 0,
        "receivable_nav_delta_idr": 0.0,
    }


def run(root: Path, *, stop_after: int | None = None, resume: bool = False) -> Path | None:
    resume_anchor: dict[str, object] | None = None
    if resume:
        if not root.is_dir() or (root / "acceptance_summary.json").exists():
            raise SystemExit(f"REPLAY_RESUME_ROOT_INVALID:{root}")
        progress_payload = json.loads(_progress_path(root).read_text(encoding="utf-8"))
        rows, previous = _load_progress(root)
        resume_anchor = {
            "completed_session_count": progress_payload["completed_session_count"],
            "runtime_snapshot_path": progress_payload["runtime_snapshot_path"],
            "runtime_snapshot_sha256": progress_payload["runtime_snapshot_sha256"],
            "runtime_state_sha256": progress_payload["runtime_state_sha256"],
        }
        start_index = len(rows)
        if start_index <= 0 or start_index >= len(SESSIONS):
            raise SystemExit("REPLAY_RESUME_PROGRESS_NOT_PARTIAL")
        if start_index != len(list((root / "executions").glob("*.json"))):
            raise SystemExit("REPLAY_RESUME_EXECUTION_COUNT_MISMATCH")
    else:
        if root.exists() and any(root.iterdir()):
            raise SystemExit(f"REPLAY_OUTPUT_NOT_EMPTY:{root}")
        root.mkdir(parents=True, exist_ok=True)
        bootstrap_t0(root, session_date=SESSIONS[0][0])
        previous = None
        rows = []
        start_index = 0
    for index in range(start_index, len(SESSIONS)):
        decision_date, execution_date = SESSIONS[index]
        score_manifest = _score_fixture(root, decision_date, index)
        previous_manifest = None if previous is None else previous
        current = load_score_manifest(score_manifest)
        previous_score = None if previous_manifest is None else load_score_manifest(previous_manifest)
        ohlcv, model_input, calendar = _eod_fixture(root, decision_date, execution_date)
        from idx_trade.v4_x1_execution_v1_verify import verify_eod_execution_inputs, verify_open_execution_inputs
        eod = verify_eod_execution_inputs(
            session_ohlcv_path=ohlcv, model_input_path=model_input, official_calendar_path=calendar,
            decision_session_date=decision_date, required_tickers=TICKERS,
        )
        required = derive_required_execution_tickers(root, current_score=current, previous_score=previous_score, eod_inputs=eod)
        post_attestation, post_journal, _ = _ca_fixture(
            root,
            decision_date,
            execution_date,
            required,
            include_event=False,
            capture_phase="POST_EOD",
            capture_timestamp_utc=f"{decision_date}T10:00:00+00:00",
        )
        post_reconciliation = reconcile_corporate_action_attestation_v1_2_journal(
            attestation_path=post_attestation, journal_path=post_journal,
            expected_from_session_date=decision_date, expected_through_session_date=execution_date,
            required_tickers=required,
        )
        prepared = prepare_post_eod(
            root,
            current_score=current,
            previous_score=previous_score,
            eod_inputs=eod,
            ca_reconciliation=post_reconciliation,
        )
        raw_state = runtime.load_latest_runtime_snapshot(root).state
        post_sizing_state = _state_for_dividend_sizing(
            E2EPaperPaths.from_root(root),
            raw_state,
            post_reconciliation.certified_events,
            session_date=decision_date,
        )
        raw_nav = dividend.paper_total_return_nav_idr(raw_state, eod.raw_close_prices)
        post_projected_nav = dividend.paper_total_return_nav_idr(post_sizing_state, eod.raw_close_prices)
        prepared_payload = json.loads(prepared.path.read_text(encoding="utf-8"))
        declared_nav = float(prepared_payload["execution_plan"]["total_return_nav_idr"])
        if abs(declared_nav - post_projected_nav) > 1e-6:
            raise RuntimeError("REPLAY_RECEIVABLE_NAV_DECLARATION_MISMATCH")
        open_manifest = _open_fixture(root, execution_date)
        open_inputs = verify_open_execution_inputs(execution_session_date=execution_date, manifest_path=open_manifest)
        preopen_attestation, preopen_journal, _ = _ca_fixture(
            root,
            decision_date,
            execution_date,
            required,
            include_event=index == 3,
            capture_phase="PREOPEN",
            capture_timestamp_utc=f"{execution_date}T01:00:00+00:00",
            announcement="2026-08-27T18:00:00",
            event_schedule=("2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"),
        )
        preopen_reconciliation = reconcile_corporate_action_attestation_v1_2_journal(
            attestation_path=preopen_attestation,
            journal_path=preopen_journal,
            expected_from_session_date=decision_date,
            expected_through_session_date=execution_date,
            required_tickers=required,
        )
        preopen_sizing_state = _state_for_dividend_sizing(
            E2EPaperPaths.from_root(root),
            raw_state,
            preopen_reconciliation.certified_events,
            session_date=decision_date,
        )
        preopen_projected_nav = dividend.paper_total_return_nav_idr(
            preopen_sizing_state, eod.raw_close_prices
        )
        receivable_delta = preopen_projected_nav - raw_nav
        if index == 3 and abs(receivable_delta) > 1e-6:
            raise RuntimeError("REPLAY_PREOPEN_FUTURE_EVENT_CHANGED_NAV_ORACLE")
        result = execute_preopen(
            root, prepared_path=prepared.path, current_score=current, previous_score=previous_score,
            eod_inputs=eod, open_inputs=open_inputs, ca_reconciliation=preopen_reconciliation,
        )
        if index == 1:
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--resume-probe", "--output-dir", str(root)], check=True)
        state = runtime.load_latest_runtime_snapshot(root).state
        execution_payload = json.loads(result.path.read_text(encoding="utf-8"))
        oracle = _production_session_oracle(index)
        if result.status != oracle["status"]:
            raise RuntimeError("REPLAY_SESSION_STATUS_ORACLE_MISMATCH")
        if len(execution_payload["fills"]) != oracle["fill_count"]:
            raise RuntimeError("REPLAY_SESSION_FILL_COUNT_ORACLE_MISMATCH")
        actual_fills = execution_payload["fills"]
        expected_fills = oracle["fills"]
        for actual_fill, expected_fill in zip(actual_fills, expected_fills):
            for key in ("side", "ticker", "planned_shares", "filled_shares", "status", "replacement_peer"):
                if actual_fill.get(key) != expected_fill.get(key):
                    raise RuntimeError(f"REPLAY_SESSION_FILL_FIELD_ORACLE_MISMATCH:{key}")
            for key in ("raw_open", "effective_price", "gross_notional", "fee_idr", "cash_effect_idr"):
                if abs(float(actual_fill.get(key)) - float(expected_fill.get(key))) > 1e-6:
                    raise RuntimeError(f"REPLAY_SESSION_FILL_NUMERIC_ORACLE_MISMATCH:{key}")
        if execution_payload["pending_transition_count"] != oracle["pending_transition_count"]:
            raise RuntimeError("REPLAY_SESSION_PENDING_ORACLE_MISMATCH")
        if abs(float(execution_payload["gross_turnover_idr"]) - float(oracle["gross_turnover_idr"])) > 1e-6:
            raise RuntimeError("REPLAY_SESSION_TURNOVER_ORACLE_MISMATCH")
        if abs(float(execution_payload["stamp_duty_idr"]) - float(oracle["stamp_duty_idr"])) > 1e-6:
            raise RuntimeError("REPLAY_SESSION_STAMP_ORACLE_MISMATCH")
        actual_fee_total = sum(float(row.get("fee_idr") or 0.0) for row in actual_fills)
        if abs(actual_fee_total - float(oracle["fee_total_idr"])) > 1e-6:
            raise RuntimeError("REPLAY_SESSION_FEE_TOTAL_ORACLE_MISMATCH")
        if abs(float(state.base_state.cash_idr) - float(oracle["cash_idr_after_execution"])) > 1e-6:
            raise RuntimeError("REPLAY_SESSION_CASH_ORACLE_MISMATCH")
        actual_positions = [
            [row.ticker, row.shares]
            for row in state.base_state.positions
        ]
        if actual_positions != oracle["positions_after"]:
            raise RuntimeError("REPLAY_SESSION_POSITIONS_ORACLE_MISMATCH")
        if [row.event_id for row in state.dividend_ledger.receivables] != oracle["receivables"]:
            raise RuntimeError("REPLAY_SESSION_RECEIVABLES_ORACLE_MISMATCH")
        if [row.event_id for row in state.dividend_ledger.settlements] != oracle["settlements"]:
            raise RuntimeError("REPLAY_SESSION_SETTLEMENTS_ORACLE_MISMATCH")
        if bool(preopen_reconciliation.certified_events) != oracle["preopen_semantic_delta"]:
            raise RuntimeError("REPLAY_SESSION_CA_DELTA_ORACLE_MISMATCH")
        if len(runtime.load_latest_runtime_snapshot(root).certified_dividend_registry) != oracle["registry_events"]:
            raise RuntimeError("REPLAY_SESSION_REGISTRY_ORACLE_MISMATCH")
        if abs(float(receivable_delta) - float(oracle["receivable_nav_delta_idr"])) > 1e-6:
            raise RuntimeError("REPLAY_SESSION_RECEIVABLE_ORACLE_MISMATCH")
        rows.append({
            "decision_session_date": decision_date, "execution_session_date": execution_date,
            "status": result.status, "execution_sha256": result.file_sha256,
            "required_tickers": list(required),
            "post_eod_event_ids": [event.event_id for event in post_reconciliation.certified_events],
            "preopen_event_ids": [event.event_id for event in preopen_reconciliation.certified_events],
            "preopen_semantic_delta": bool(preopen_reconciliation.certified_events),
            "post_eod_attestation_sha256": post_reconciliation.attestation_sha256,
            "preopen_attestation_sha256": preopen_reconciliation.attestation_sha256,
            "registry_events": len(runtime.load_latest_runtime_snapshot(root).certified_dividend_registry),
            "receivables": [row.event_id for row in state.dividend_ledger.receivables],
            "settlements": [row.event_id for row in state.dividend_ledger.settlements],
            "sizing_nav_raw_idr": raw_nav,
            "prepared_nav_total_return_idr": post_projected_nav,
            "preopen_nav_total_return_idr": preopen_projected_nav,
            "receivable_nav_delta_idr": receivable_delta,
            "cash_idr_after_execution": state.base_state.cash_idr,
            "positions_after": [[row.ticker, row.shares] for row in state.base_state.positions],
            "fills": execution_payload["fills"],
            "gross_turnover_idr": execution_payload["gross_turnover_idr"],
            "fee_total_idr": sum(float(row.get("fee_idr") or 0.0) for row in execution_payload["fills"]),
            "stamp_duty_idr": execution_payload["stamp_duty_idr"],
            "pending_transition_count": execution_payload["pending_transition_count"],
            "outcome_access": False,
            "oracle": oracle,
        })
        previous = score_manifest
        _write_progress(root, rows=rows, last_score_manifest=score_manifest)
        if stop_after is not None and len(rows) >= stop_after:
            return None
    body = {
        "schema_version": "idx_trade_e2e_paper_production_replay_v1",
        "synthetic_only": True,
        "guards": replay_boundary_static_audit_v1(
            (
                Path(__file__),
                e2e_orchestration_module.__file__,
                dividend_execution_module.__file__,
                execution_verify_module.__file__,
            ),
            source_kind="synthetic_artifacts_through_production_verifiers",
        ),
        "replay_boundary": {
            "source_kind": "synthetic_artifacts_through_production_verifiers",
            "provider_path_invoked": False,
            "protected_outcome_path_invoked": False,
            "evidence_method": "AST_IMPORT_CALL_AND_MARKER_AUDIT",
            "by_construction": True,
        },
        "sessions": rows, "session_count": len(rows),
        "late_correction_in_production_path": False,
        "late_known_correction_oracle": "deterministic_economic_oracle_v1",
        "post_eod_only_ca_exercised": True,
        "preopen_no_semantic_delta_exercised": True,
        "preopen_new_event_exercised": True,
        "cold_restart": bool(resume),
        "resume_process": bool(resume),
        "resume_anchor": resume_anchor,
    }
    body["summary_sha256"] = _canonical_hash(body)
    summary = root / "acceptance_summary.json"
    _write_json(summary, body)
    return summary


def rerun_completed_session(root: Path, *, index: int = 0) -> dict[str, object]:
    """Re-enter one completed production session and prove idempotent replay."""
    if index < 0 or index >= len(SESSIONS):
        raise SystemExit("REPLAY_DUPLICATE_INDEX_INVALID")
    summary_path = root / "acceptance_summary.json"
    if not summary_path.is_file():
        raise SystemExit("REPLAY_DUPLICATE_SUMMARY_MISSING")
    decision_date, execution_date = SESSIONS[index]
    score_manifest = root / "scores" / decision_date / "manifest.json"
    previous_manifest = (
        None
        if index == 0
        else root / "scores" / SESSIONS[index - 1][0] / "manifest.json"
    )
    current = load_score_manifest(score_manifest)
    previous_score = None if previous_manifest is None else load_score_manifest(previous_manifest)
    eod_dir = root / "eod" / decision_date
    from idx_trade.v4_x1_execution_v1_verify import verify_eod_execution_inputs, verify_open_execution_inputs
    eod = verify_eod_execution_inputs(
        session_ohlcv_path=eod_dir / "session_ohlcv.parquet",
        model_input_path=eod_dir / "model_input.parquet",
        official_calendar_path=eod_dir / "calendar.csv",
        decision_session_date=decision_date,
        required_tickers=TICKERS,
    )
    prepared = root / "prepared" / f"{decision_date}.json"
    prepared_payload = json.loads(prepared.read_text(encoding="utf-8"))
    required = tuple(str(ticker) for ticker in prepared_payload.get("required_tickers", ()))
    if not required:
        raise SystemExit("REPLAY_DUPLICATE_REQUIRED_TICKERS_MISSING")
    preopen_dir = root / "ca" / decision_date / "PREOPEN"
    preopen_reconciliation = reconcile_corporate_action_attestation_v1_2_journal(
        attestation_path=preopen_dir / "attestation.json",
        journal_path=preopen_dir / "journal.json",
        expected_from_session_date=decision_date,
        expected_through_session_date=execution_date,
        required_tickers=required,
    )
    open_inputs = verify_open_execution_inputs(
        execution_session_date=execution_date,
        manifest_path=root / "open" / execution_date / "certified" / "manifest.json",
    )
    target = root / "executions" / f"{execution_date}.json"
    before_target_sha = _sha(target)
    before_snapshot = runtime.load_latest_runtime_snapshot(root)
    before_state_sha = dividend.dividend_aware_state_hash(before_snapshot.state)
    result = execute_preopen(
        root,
        prepared_path=prepared,
        current_score=current,
        previous_score=previous_score,
        eod_inputs=eod,
        open_inputs=open_inputs,
        ca_reconciliation=preopen_reconciliation,
    )
    after_snapshot = runtime.load_latest_runtime_snapshot(root)
    after_target_sha = _sha(target)
    after_state_sha = dividend.dividend_aware_state_hash(after_snapshot.state)
    details = {
        "status": result.status,
        "execution_session_date": execution_date,
        "before_execution_sha256": before_target_sha,
        "after_execution_sha256": after_target_sha,
        "before_runtime_snapshot_sha256": before_snapshot.file_sha256,
        "after_runtime_snapshot_sha256": after_snapshot.file_sha256,
        "before_runtime_state_sha256": before_state_sha,
        "after_runtime_state_sha256": after_state_sha,
        "execution_unchanged": before_target_sha == after_target_sha,
        "runtime_snapshot_unchanged": before_snapshot.file_sha256 == after_snapshot.file_sha256,
        "runtime_state_unchanged": before_state_sha == after_state_sha,
    }
    if result.status != "ALREADY_COMPLETE" or not all(
        details[key] for key in (
            "execution_unchanged", "runtime_snapshot_unchanged", "runtime_state_unchanged"
        )
    ):
        raise SystemExit("REPLAY_DUPLICATE_IDEMPOTENCY_ORACLE_FAILED")
    _write_json(root / "duplicate_rerun.json", details)
    return details


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--resume-probe", action="store_true")
    parser.add_argument("--stop-after", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--rerun-complete", action="store_true")
    parser.add_argument("--session-index", type=int, default=0)
    args = parser.parse_args()
    root = Path(args.output_dir).expanduser().resolve()
    if args.rerun_complete:
        details = rerun_completed_session(root, index=args.session_index)
        print({"status": "DUPLICATE_RERUN_PASS", **details})
        return 0
    if args.resume_probe:
        _resume_probe(root)
        print({"status": "RESUME_PROBE_PASS", "outcome_access": False})
        return 0
    summary = run(root, stop_after=args.stop_after, resume=args.resume)
    if summary is None:
        print({"status": "PARTIAL_REPLAY_STOPPED", "completed_sessions": args.stop_after, "outcome_access": False})
        return 0
    print({"status": "PRODUCTION_PATH_REPLAY_PASS", "summary_path": str(summary), "summary_sha256": _sha(summary), "outcome_access": False})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
