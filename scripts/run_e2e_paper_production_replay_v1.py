"""Replay the E2E paper path with synthetic, hash-pinned production artifacts.

The replay intentionally uses the public score/EOD/Open/CA verifiers and the
real POST_EOD/PREOPEN orchestrator. It never calls a provider or opens an
outcome artifact.
"""

from __future__ import annotations

import argparse
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


def _write_pdf(path: Path) -> None:
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
    content = (
        b"BT /F1 12 Tf 72 720 Td (T00 cash dividend Rp 25 per share. "
        b"Cum dividend 25 August 2026. Ex dividend 26 August 2026. "
        b"Record date 27 August 2026. Payment date 31 August 2026.) Tj ET"
    )
    stream = DecodedStreamObject()
    stream.set_data(content)
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


def _write_v12_review(root: Path, *, announcement: str) -> tuple[Path, object]:
    batch_root = root / "batches" / "2026-08-27_POST_EOD"
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
    candidate = _candidate(
        "T00", cum="2026-08-25", ex="2026-08-26", record="2026-08-27",
        payment="2026-08-31", announcement=announcement,
    )
    _write_json(discovery, {
        "schema_version": "idx_trade_forward_dividend_announcement_capture_v1",
        "status": "COMPLETE",
        "raw_artifacts": [{"ticker": "T00", "path": page.name, "sha256": _sha(page)}],
        "candidates": [candidate],
    })
    pdf = evidence_dir / "official.pdf"
    _write_pdf(pdf)
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
            "cum_regular_negotiated": "2026-08-25", "ex_regular_negotiated": "2026-08-26",
            "record_date": "2026-08-27", "payment_date": "2026-08-31",
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


def _ca_fixture(root: Path, session: str, next_session: str, required: tuple[str, ...], *, include_event: bool) -> Path:
    ca_root = root / "ca" / session
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
    phase = ca_root / "post_phase.json"
    capture_timestamp_utc = (
        f"{session}T12:00:00+00:00"
    )
    _write_json(phase, {
        "schema_version": ca.PHASE_SCHEMA, "status": "COMPLETE",
        "provider_repository": ca.PROVIDER_REPOSITORY, "provider_commit": ca.PROVIDER_COMMIT,
        "upstream_base_url": ca.UPSTREAM_BASE_URL, "calendar_capture_scope": ca.CALENDAR_CAPTURE_SCOPE,
        "phase": "POST_EOD", "from_session_date": session, "through_session_date": next_session,
        "capture_timestamp_utc": capture_timestamp_utc,
        "required_tickers": list(required),
        "legs": {leg: {"status": "COMPLETE"} for leg in raw_rows},
        "raw_artifacts": artifacts, "calendar_schema_fingerprints": [calendar_fp],
    })
    attestation = ca_root / "attestation.json"
    review_path = None
    verified = None
    if include_event:
        review_path, verified = _write_v12_review(root, announcement="2026-08-27T10:00:00")
    evidence_rows = []
    for ticker in required:
        if include_event and ticker == "T00":
            evidence_rows.append({"ticker": ticker, "status": ca.RELEVANT, "reasons": ["POST_EOD:ANNOUNCEMENT:T00"]})
        else:
            evidence_rows.append({"ticker": ticker, "status": ca.NO_EVENT, "reasons": []})
    _write_json(attestation, {
        "schema_version": ca.ATTESTATION_SCHEMA_V1_2, "capture_phase": "POST_EOD",
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
            capture_phase=orchestration.POST_EOD,
        ),
    )
    return attestation, journal_path


def _resume_probe(root: Path) -> None:
    snapshot = runtime.load_latest_runtime_snapshot(root)
    if not snapshot.state.base_state.as_of_session_date:
        raise RuntimeError("REPLAY_RESUME_STATE_INVALID")
    if not snapshot.certified_dividend_registry and list((root / "forward_execution_v1_1" / "executions").glob("*.json")):
        raise RuntimeError("REPLAY_RESUME_REGISTRY_MISSING")


def run(root: Path) -> Path:
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"REPLAY_OUTPUT_NOT_EMPTY:{root}")
    root.mkdir(parents=True, exist_ok=True)
    bootstrap_t0(root, session_date=SESSIONS[0][0])
    previous = None
    rows = []
    for index, (decision_date, execution_date) in enumerate(SESSIONS):
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
        attestation, journal = _ca_fixture(root, decision_date, execution_date, required, include_event=index == 3)
        reconciliation = reconcile_corporate_action_attestation_v1_2_journal(
            attestation_path=attestation, journal_path=journal,
            expected_from_session_date=decision_date, expected_through_session_date=execution_date,
            required_tickers=required,
        )
        prepared = prepare_post_eod(root, current_score=current, previous_score=previous_score, eod_inputs=eod, ca_reconciliation=reconciliation)
        raw_state = runtime.load_latest_runtime_snapshot(root).state
        sizing_state = _state_for_dividend_sizing(
            E2EPaperPaths.from_root(root),
            raw_state,
            reconciliation.certified_events,
            session_date=decision_date,
        )
        raw_nav = dividend.paper_total_return_nav_idr(raw_state, eod.raw_close_prices)
        projected_nav = dividend.paper_total_return_nav_idr(sizing_state, eod.raw_close_prices)
        prepared_payload = json.loads(prepared.path.read_text(encoding="utf-8"))
        declared_nav = float(prepared_payload["execution_plan"]["total_return_nav_idr"])
        if abs(declared_nav - projected_nav) > 1e-6:
            raise RuntimeError("REPLAY_RECEIVABLE_NAV_DECLARATION_MISMATCH")
        receivable_delta = projected_nav - raw_nav
        if index == 3 and abs(receivable_delta - 125_000.0) > 1e-6:
            raise RuntimeError("REPLAY_RECEIVABLE_NAV_ORACLE_MISMATCH")
        open_manifest = _open_fixture(root, execution_date)
        open_inputs = verify_open_execution_inputs(execution_session_date=execution_date, manifest_path=open_manifest)
        result = execute_preopen(
            root, prepared_path=prepared.path, current_score=current, previous_score=previous_score,
            eod_inputs=eod, open_inputs=open_inputs, ca_reconciliation=reconciliation,
        )
        if index == 1:
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--resume-probe", "--output-dir", str(root)], check=True)
        state = runtime.load_latest_runtime_snapshot(root).state
        execution_payload = json.loads(result.path.read_text(encoding="utf-8"))
        rows.append({
            "decision_session_date": decision_date, "execution_session_date": execution_date,
            "status": result.status, "execution_sha256": result.file_sha256,
            "required_tickers": list(required),
            "registry_events": len(runtime.load_latest_runtime_snapshot(root).certified_dividend_registry),
            "receivables": [row.event_id for row in state.dividend_ledger.receivables],
            "settlements": [row.event_id for row in state.dividend_ledger.settlements],
            "sizing_nav_raw_idr": raw_nav,
            "sizing_nav_total_return_idr": projected_nav,
            "receivable_nav_delta_idr": receivable_delta,
            "cash_idr_after_execution": state.base_state.cash_idr,
            "fills": execution_payload["fills"],
            "gross_turnover_idr": execution_payload["gross_turnover_idr"],
            "stamp_duty_idr": execution_payload["stamp_duty_idr"],
            "pending_transition_count": execution_payload["pending_transition_count"],
            "outcome_access": False,
        })
        previous = score_manifest
    body = {
        "schema_version": "idx_trade_e2e_paper_production_replay_v1",
        "synthetic_only": True, "provider_calls": False, "protected_outcomes_accessed": False,
        "sessions": rows, "session_count": len(rows),
        "late_correction_exercised": True, "post_eod_only_ca_exercised": True,
    }
    body["summary_sha256"] = _canonical_hash(body)
    summary = root / "acceptance_summary.json"
    _write_json(summary, body)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--resume-probe", action="store_true")
    args = parser.parse_args()
    root = Path(args.output_dir).expanduser().resolve()
    if args.resume_probe:
        _resume_probe(root)
        print({"status": "RESUME_PROBE_PASS", "outcome_access": False})
        return 0
    summary = run(root)
    print({"status": "PRODUCTION_PATH_REPLAY_PASS", "summary_path": str(summary), "summary_sha256": _sha(summary), "outcome_access": False})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
