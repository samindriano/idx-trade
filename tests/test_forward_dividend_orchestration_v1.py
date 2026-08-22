from __future__ import annotations

import pytest

from idx_trade.forward_dividend_orchestration_v1 import (
    BlockingDividendJournalEntry,
    CertifiedDividendJournalEntry,
    DividendAcquisitionJournal,
    DividendCoverage,
    ForwardDividendOrchestrationError,
    advance_coverage,
    journal_hash,
    load_journal_document,
    merge_journal_state,
    plan_discovery,
    required_execution_tickers,
    unresolved_blockers_for_tickers,
    write_journal_document,
)


def test_required_execution_universe_is_union() -> None:
    result = required_execution_tickers(
        actual_positions=["BBCA", "BBRI"],
        pending_buys=["TLKM"],
        pending_sells=["BBRI"],
        decision_targets=["ASII", "BBCA"],
    )

    assert result == ("ASII", "BBCA", "BBRI", "TLKM")


def test_new_ticker_gets_bootstrap_lookback() -> None:
    result = plan_discovery(
        as_of_date="2026-08-22",
        required_tickers=["BBCA"],
    )

    assert result.date_from == "2025-08-21"
    assert result.date_to == "2026-08-22"


def test_existing_ticker_gets_overlap() -> None:
    result = plan_discovery(
        as_of_date="2026-08-22",
        required_tickers=["BBCA"],
        prior_coverage=[
            DividendCoverage(
                ticker="BBCA",
                covered_through="2026-08-21",
            )
        ],
    )

    assert result.date_from == "2026-08-14"


def test_global_window_uses_earliest_required_start() -> None:
    result = plan_discovery(
        as_of_date="2026-08-22",
        required_tickers=["BBCA", "TLKM"],
        prior_coverage=[
            DividendCoverage(
                ticker="BBCA",
                covered_through="2026-08-21",
            )
        ],
    )

    assert result.date_from == "2025-08-21"


def test_certified_identity_conflict_fails_closed() -> None:
    rows = (
        CertifiedDividendJournalEntry(
            announcement_identity="A1",
            ticker="BBCA",
            event_id="E1",
            event_sha256="a" * 64,
            evidence_dir="C:/idx-trade-test-evidence",
            review_sha256="c" * 64,
        ),
        CertifiedDividendJournalEntry(
            announcement_identity="A1",
            ticker="BBCA",
            event_id="E2",
            event_sha256="b" * 64,
            evidence_dir="C:/idx-trade-test-evidence",
            review_sha256="c" * 64,
        ),
    )

    journal = DividendAcquisitionJournal(
        as_of_date="2026-08-22",
        required_tickers=("BBCA",),
        coverage=(),
        certified_events=rows,
    )

    with pytest.raises(
        ForwardDividendOrchestrationError,
        match="ANNOUNCEMENT_CONFLICT",
    ):
        journal_hash(journal)


def test_certified_and_blocker_overlap_fails_closed() -> None:
    journal = DividendAcquisitionJournal(
        as_of_date="2026-08-22",
        required_tickers=("BBCA",),
        coverage=(),
        certified_events=(
            CertifiedDividendJournalEntry(
                announcement_identity="A1",
                ticker="BBCA",
                event_id="E1",
                event_sha256="a" * 64,
                evidence_dir="C:/idx-trade-test-evidence",
                review_sha256="c" * 64,
            ),
        ),
        blockers=(
            BlockingDividendJournalEntry(
                announcement_identity="A1",
                ticker="BBCA",
                classification="AMBIGUOUS_DIVIDEND_CANDIDATE",
            ),
        ),
    )

    with pytest.raises(
        ForwardDividendOrchestrationError,
        match="CERTIFIED_BLOCKER_OVERLAP",
    ):
        journal_hash(journal)


def test_execution_relevant_blocker_is_visible() -> None:
    journal = DividendAcquisitionJournal(
        as_of_date="2026-08-22",
        required_tickers=("BBCA", "TLKM"),
        coverage=(),
        blockers=(
            BlockingDividendJournalEntry(
                announcement_identity="A1",
                ticker="BBCA",
                classification="UNSUPPORTED_NON_CASH_DIVIDEND",
            ),
            BlockingDividendJournalEntry(
                announcement_identity="A2",
                ticker="ASII",
                classification="AMBIGUOUS_DIVIDEND_CANDIDATE",
            ),
        ),
    )

    blockers = unresolved_blockers_for_tickers(
        journal,
        ["BBCA", "TLKM"],
    )

    assert tuple(row.announcement_identity for row in blockers) == (
        "A1",
    )


def test_coverage_only_advances_for_successful_tickers() -> None:
    journal = DividendAcquisitionJournal(
        as_of_date="2026-08-22",
        required_tickers=("BBCA", "TLKM"),
        coverage=(
            DividendCoverage(
                ticker="BBCA",
                covered_through="2026-08-20",
            ),
        ),
    )

    result = advance_coverage(
        journal=journal,
        successful_tickers=["BBCA", "TLKM"],
        covered_through="2026-08-22",
    )

    assert result == (
        DividendCoverage(
            ticker="BBCA",
            covered_through="2026-08-22",
        ),
        DividendCoverage(
            ticker="TLKM",
            covered_through="2026-08-22",
        ),
    )


def test_coverage_regression_fails_closed() -> None:
    journal = DividendAcquisitionJournal(
        as_of_date="2026-08-22",
        required_tickers=("BBCA",),
        coverage=(
            DividendCoverage(
                ticker="BBCA",
                covered_through="2026-08-22",
            ),
        ),
    )

    with pytest.raises(
        ForwardDividendOrchestrationError,
        match="COVERAGE_REGRESSION",
    ):
        advance_coverage(
            journal=journal,
            successful_tickers=["BBCA"],
            covered_through="2026-08-21",
        )


def test_journal_document_roundtrip(tmp_path) -> None:
    journal = DividendAcquisitionJournal(
        as_of_date="2026-08-21",
        required_tickers=("BBCA",),
        coverage=(
            DividendCoverage(
                ticker="BBCA",
                covered_through="2026-08-21",
            ),
        ),
    )

    target = tmp_path / "journal.json"

    written = write_journal_document(
        target,
        journal,
    )

    loaded = load_journal_document(target)

    assert written.file_sha256 == loaded.file_sha256
    assert loaded.journal == journal
    assert loaded.journal_sha256 == journal_hash(journal)
    assert loaded.previous_path is None


def test_exact_journal_rerun_is_idempotent(tmp_path) -> None:
    journal = DividendAcquisitionJournal(
        as_of_date="2026-08-21",
        required_tickers=("BBCA",),
        coverage=(),
    )

    target = tmp_path / "journal.json"

    first = write_journal_document(
        target,
        journal,
    )

    second = write_journal_document(
        target,
        journal,
    )

    assert first.file_sha256 == second.file_sha256
    assert target.read_bytes() == first.path.read_bytes()


def test_same_path_divergent_journal_fails_closed(
    tmp_path,
) -> None:
    target = tmp_path / "journal.json"

    write_journal_document(
        target,
        DividendAcquisitionJournal(
            as_of_date="2026-08-21",
            required_tickers=("BBCA",),
            coverage=(),
        ),
    )

    with pytest.raises(
        ForwardDividendOrchestrationError,
        match="IMMUTABLE_CONFLICT",
    ):
        write_journal_document(
            target,
            DividendAcquisitionJournal(
                as_of_date="2026-08-21",
                required_tickers=("TLKM",),
                coverage=(),
            ),
        )


def test_parent_journal_hash_chain_roundtrip(
    tmp_path,
) -> None:
    parent_path = tmp_path / "2026-08-21.json"
    child_path = tmp_path / "2026-08-22.json"

    write_journal_document(
        parent_path,
        DividendAcquisitionJournal(
            as_of_date="2026-08-21",
            required_tickers=("BBCA",),
            coverage=(),
        ),
    )

    child = write_journal_document(
        child_path,
        DividendAcquisitionJournal(
            as_of_date="2026-08-22",
            required_tickers=("BBCA",),
            coverage=(),
        ),
        previous_journal_path=parent_path,
    )

    assert child.previous_path == parent_path.resolve()

    loaded = load_journal_document(child_path)

    assert loaded.previous_path == parent_path.resolve()


def test_parent_tamper_breaks_child_chain(
    tmp_path,
) -> None:
    parent_path = tmp_path / "2026-08-21.json"
    child_path = tmp_path / "2026-08-22.json"

    write_journal_document(
        parent_path,
        DividendAcquisitionJournal(
            as_of_date="2026-08-21",
            required_tickers=("BBCA",),
            coverage=(),
        ),
    )

    write_journal_document(
        child_path,
        DividendAcquisitionJournal(
            as_of_date="2026-08-22",
            required_tickers=("BBCA",),
            coverage=(),
        ),
        previous_journal_path=parent_path,
    )

    parent_path.write_text(
        parent_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        ForwardDividendOrchestrationError,
        match="PARENT_FILE_HASH_MISMATCH",
    ):
        load_journal_document(child_path)


def test_blocker_can_resolve_to_certified() -> None:
    prior = DividendAcquisitionJournal(
        as_of_date="2026-08-21",
        required_tickers=("BBCA",),
        coverage=(),
        blockers=(
            BlockingDividendJournalEntry(
                announcement_identity="A1",
                ticker="BBCA",
                classification="AMBIGUOUS_DIVIDEND_CANDIDATE",
            ),
        ),
    )

    certified = CertifiedDividendJournalEntry(
        announcement_identity="A1",
        ticker="BBCA",
        event_id="E1",
        event_sha256="a" * 64,
        evidence_dir="C:/idx-trade-test-evidence",
        review_sha256="c" * 64,
    )

    result = merge_journal_state(
        prior_journal=prior,
        as_of_date="2026-08-22",
        capture_phase="POST_EOD",
        required_tickers=("BBCA",),
        coverage=(),
        current_certified=(certified,),
    )

    assert result.certified_events == (certified,)
    assert result.blockers == ()


def test_certified_event_cannot_mutate() -> None:
    prior = DividendAcquisitionJournal(
        as_of_date="2026-08-21",
        required_tickers=("BBCA",),
        coverage=(),
        certified_events=(
            CertifiedDividendJournalEntry(
                announcement_identity="A1",
                ticker="BBCA",
                event_id="E1",
                event_sha256="a" * 64,
                evidence_dir="C:/idx-trade-test-evidence",
                review_sha256="c" * 64,
            ),
        ),
    )

    with pytest.raises(
        ForwardDividendOrchestrationError,
        match="CERTIFIED_HISTORY_CHANGED",
    ):
        merge_journal_state(
            prior_journal=prior,
            as_of_date="2026-08-22",
        capture_phase="POST_EOD",
            required_tickers=("BBCA",),
            coverage=(),
            current_certified=(
                CertifiedDividendJournalEntry(
                    announcement_identity="A1",
                    ticker="BBCA",
                    event_id="E2",
                    event_sha256="b" * 64,
                    evidence_dir="C:/idx-trade-test-evidence",
                    review_sha256="c" * 64,
                ),
            ),
        )


def test_certified_event_cannot_downgrade_to_blocker() -> None:
    prior = DividendAcquisitionJournal(
        as_of_date="2026-08-21",
        required_tickers=("BBCA",),
        coverage=(),
        certified_events=(
            CertifiedDividendJournalEntry(
                announcement_identity="A1",
                ticker="BBCA",
                event_id="E1",
                event_sha256="a" * 64,
                evidence_dir="C:/idx-trade-test-evidence",
                review_sha256="c" * 64,
            ),
        ),
    )

    with pytest.raises(
        ForwardDividendOrchestrationError,
        match="CERTIFIED_DOWNGRADE_BLOCKED",
    ):
        merge_journal_state(
            prior_journal=prior,
            as_of_date="2026-08-22",
        capture_phase="POST_EOD",
            required_tickers=("BBCA",),
            coverage=(),
            current_blockers=(
                BlockingDividendJournalEntry(
                    announcement_identity="A1",
                    ticker="BBCA",
                    classification="AMBIGUOUS_DIVIDEND_CANDIDATE",
                ),
            ),
        )


def test_journal_evidence_reference_roundtrip(
    tmp_path,
) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()

    review = evidence / "ATTACHMENT_REVIEW.json"
    review.write_text("{}\n", encoding="utf-8")

    import hashlib

    review_sha = hashlib.sha256(
        review.read_bytes()
    ).hexdigest()

    journal = DividendAcquisitionJournal(
        as_of_date="2026-08-21",
        required_tickers=("BBCA",),
        coverage=(),
        certified_events=(
            CertifiedDividendJournalEntry(
                announcement_identity="A1",
                ticker="BBCA",
                event_id="E1",
                event_sha256="a" * 64,
                evidence_dir=str(evidence.resolve()),
                review_sha256=review_sha,
            ),
        ),
    )

    target = tmp_path / "journal.json"

    written = write_journal_document(
        target,
        journal,
    )

    loaded = load_journal_document(
        written.path
    )

    assert loaded.journal == journal


def test_review_evidence_tamper_breaks_journal(
    tmp_path,
) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()

    review = evidence / "ATTACHMENT_REVIEW.json"
    review.write_text("{}\n", encoding="utf-8")

    import hashlib

    review_sha = hashlib.sha256(
        review.read_bytes()
    ).hexdigest()

    target = tmp_path / "journal.json"

    write_journal_document(
        target,
        DividendAcquisitionJournal(
            as_of_date="2026-08-21",
            required_tickers=("BBCA",),
            coverage=(),
            certified_events=(
                CertifiedDividendJournalEntry(
                    announcement_identity="A1",
                    ticker="BBCA",
                    event_id="E1",
                    event_sha256="a" * 64,
                    evidence_dir=str(evidence.resolve()),
                    review_sha256=review_sha,
                ),
            ),
        ),
    )

    review.write_text(
        '{"tampered": true}\n',
        encoding="utf-8",
    )

    with pytest.raises(
        ForwardDividendOrchestrationError,
        match="REVIEW_FILE_HASH_MISMATCH",
    ):
        load_journal_document(target)


def test_child_cannot_drop_certified_history(
    tmp_path,
) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()

    review = evidence / "ATTACHMENT_REVIEW.json"
    review.write_text("{}\n", encoding="utf-8")

    import hashlib

    review_sha = hashlib.sha256(
        review.read_bytes()
    ).hexdigest()

    parent_path = tmp_path / "2026-08-21.json"

    write_journal_document(
        parent_path,
        DividendAcquisitionJournal(
            as_of_date="2026-08-21",
            required_tickers=("BBCA",),
            coverage=(),
            certified_events=(
                CertifiedDividendJournalEntry(
                    announcement_identity="A1",
                    ticker="BBCA",
                    event_id="E1",
                    event_sha256="a" * 64,
                    evidence_dir=str(evidence.resolve()),
                    review_sha256=review_sha,
                ),
            ),
        ),
    )

    with pytest.raises(
        ForwardDividendOrchestrationError,
        match="CERTIFIED_HISTORY_DROPPED",
    ):
        write_journal_document(
            tmp_path / "2026-08-22.json",
            DividendAcquisitionJournal(
                as_of_date="2026-08-22",
                required_tickers=("BBCA",),
                coverage=(),
            ),
            previous_journal_path=parent_path,
        )


def test_child_cannot_regress_coverage_history(
    tmp_path,
) -> None:
    parent_path = tmp_path / "2026-08-21.json"

    write_journal_document(
        parent_path,
        DividendAcquisitionJournal(
            as_of_date="2026-08-21",
            required_tickers=("BBCA",),
            coverage=(
                DividendCoverage(
                    ticker="BBCA",
                    covered_through="2026-08-21",
                ),
            ),
        ),
    )

    with pytest.raises(
        ForwardDividendOrchestrationError,
        match="COVERAGE_HISTORY_REGRESSED",
    ):
        write_journal_document(
            tmp_path / "2026-08-22.json",
            DividendAcquisitionJournal(
                as_of_date="2026-08-22",
                required_tickers=("BBCA",),
                coverage=(
                    DividendCoverage(
                        ticker="BBCA",
                        covered_through="2026-08-20",
                    ),
                ),
            ),
            previous_journal_path=parent_path,
        )


def test_same_day_preopen_to_post_eod_is_valid(
    tmp_path,
) -> None:
    parent_path = tmp_path / "2026-08-22_PREOPEN.json"
    child_path = tmp_path / "2026-08-22_POST_EOD.json"

    write_journal_document(
        parent_path,
        DividendAcquisitionJournal(
            as_of_date="2026-08-22",
            required_tickers=("BBCA",),
            coverage=(),
            capture_phase="PREOPEN",
        ),
    )

    child = write_journal_document(
        child_path,
        DividendAcquisitionJournal(
            as_of_date="2026-08-22",
            required_tickers=("BBCA",),
            coverage=(),
            capture_phase="POST_EOD",
        ),
        previous_journal_path=parent_path,
    )

    assert child.journal.capture_phase == "POST_EOD"


def test_same_day_same_phase_parent_is_rejected(
    tmp_path,
) -> None:
    parent_path = tmp_path / "a.json"

    write_journal_document(
        parent_path,
        DividendAcquisitionJournal(
            as_of_date="2026-08-22",
            required_tickers=("BBCA",),
            coverage=(),
            capture_phase="PREOPEN",
        ),
    )

    with pytest.raises(
        ForwardDividendOrchestrationError,
        match="PARENT_ORDER_NOT_PRIOR",
    ):
        write_journal_document(
            tmp_path / "b.json",
            DividendAcquisitionJournal(
                as_of_date="2026-08-22",
                required_tickers=("BBCA",),
                coverage=(),
                capture_phase="PREOPEN",
            ),
            previous_journal_path=parent_path,
        )


def test_post_eod_to_same_day_preopen_is_rejected(
    tmp_path,
) -> None:
    parent_path = tmp_path / "a.json"

    write_journal_document(
        parent_path,
        DividendAcquisitionJournal(
            as_of_date="2026-08-22",
            required_tickers=("BBCA",),
            coverage=(),
            capture_phase="POST_EOD",
        ),
    )

    with pytest.raises(
        ForwardDividendOrchestrationError,
        match="PARENT_ORDER_NOT_PRIOR",
    ):
        write_journal_document(
            tmp_path / "b.json",
            DividendAcquisitionJournal(
                as_of_date="2026-08-22",
                required_tickers=("BBCA",),
                coverage=(),
                capture_phase="PREOPEN",
            ),
            previous_journal_path=parent_path,
        )


def test_next_day_preopen_follows_prior_post_eod(
    tmp_path,
) -> None:
    parent_path = tmp_path / "2026-08-22_POST_EOD.json"

    write_journal_document(
        parent_path,
        DividendAcquisitionJournal(
            as_of_date="2026-08-22",
            required_tickers=("BBCA",),
            coverage=(),
            capture_phase="POST_EOD",
        ),
    )

    child = write_journal_document(
        tmp_path / "2026-08-23_PREOPEN.json",
        DividendAcquisitionJournal(
            as_of_date="2026-08-23",
            required_tickers=("BBCA",),
            coverage=(),
            capture_phase="PREOPEN",
        ),
        previous_journal_path=parent_path,
    )

    assert child.journal.capture_phase == "PREOPEN"
