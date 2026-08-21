from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Sequence

from . import forward_dividend_execution_v1_1 as gate
from . import forward_dividend_v1 as dividend
from .v4_x1_decision_v1_contract import (
    DecisionV1Error,
    ShadowPortfolioState,
    TARGET_POSITIONS,
)
from .v4_x1_execution_v1_contract import (
    PAPER_STATE_SOURCE,
    PaperPortfolioState,
    PaperPosition,
    PendingPaperIntent,
    normalize_state,
    paper_state_hash,
)

RUNTIME_SCHEMA = "idx_trade_forward_dividend_runtime_state_v1_1"
RUNTIME_DIRNAME = "forward_execution_v1_1"
SNAPSHOT_DIRNAME = "state_snapshots"
_VERIFIED_RUNTIME_SNAPSHOT_TOKEN = object()


@dataclass(frozen=True)
class RegisteredDividendEvidence:
    review_path: Path
    attachment_dir: Path
    review_sha256: str
    event: dividend.CertifiedCashDividend
    announcement_id: str
    announcement_number: str


@dataclass(frozen=True)
class VerifiedDividendRuntimeSnapshot:
    path: Path
    file_sha256: str
    snapshot_payload_sha256: str
    runtime_state_sha256: str
    state: dividend.DividendAwarePaperState
    certified_dividend_registry: tuple[RegisteredDividendEvidence, ...]
    previous_snapshot_path: Path | None
    previous_snapshot_sha256: str | None
    _verification_token: object


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _canonical_hash(value: object) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _iso_date(value: object, code: str) -> str:
    text = str(value or "").strip()
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise DecisionV1Error(code) from exc
    if parsed.isoformat() != text:
        raise DecisionV1Error(code)
    return text


def _finite_nonnegative(value: object, code: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise DecisionV1Error(code) from exc
    if not math.isfinite(number) or number < 0:
        raise DecisionV1Error(code)
    return number


def _paper_state_payload(state: PaperPortfolioState) -> dict[str, Any]:
    cash, positions, pending_buys, pending_sells = normalize_state(state)
    session = _iso_date(
        state.as_of_session_date,
        "DIVIDEND_V1_1_RUNTIME_STATE_DATE_INVALID",
    )

    def pending_payload(rows: dict[str, PendingPaperIntent]) -> list[dict[str, Any]]:
        return [
            {
                "side": row.side,
                "ticker": row.ticker,
                "rank_consensus": row.rank_consensus,
                "reason": row.reason,
                "replacement_peer": row.replacement_peer,
            }
            for row in sorted(rows.values(), key=lambda x: x.ticker)
        ]

    return {
        "as_of_session_date": session,
        "cash_idr": float(cash),
        "positions": [
            {"ticker": ticker, "shares": int(shares)}
            for ticker, shares in sorted(positions.items())
        ],
        "pending_buys": pending_payload(pending_buys),
        "pending_sells": pending_payload(pending_sells),
        "reconciliation_required": bool(state.reconciliation_required),
        "source": state.source,
    }


def _paper_state_from_payload(value: object) -> PaperPortfolioState:
    if not isinstance(value, dict):
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_BASE_STATE_INVALID")
    if value.get("source") != PAPER_STATE_SOURCE:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_BASE_STATE_SOURCE_CHANGED")
    session = _iso_date(
        value.get("as_of_session_date"),
        "DIVIDEND_V1_1_RUNTIME_STATE_DATE_INVALID",
    )
    cash = _finite_nonnegative(
        value.get("cash_idr"),
        "DIVIDEND_V1_1_RUNTIME_CASH_INVALID",
    )

    raw_positions = value.get("positions")
    raw_buys = value.get("pending_buys")
    raw_sells = value.get("pending_sells")
    if not isinstance(raw_positions, list):
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_POSITIONS_INVALID")
    if not isinstance(raw_buys, list) or not isinstance(raw_sells, list):
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_PENDING_INVALID")

    try:
        positions = tuple(
            PaperPosition(str(row["ticker"]), int(row["shares"]))
            for row in raw_positions
            if isinstance(row, dict)
        )
        pending_buys = tuple(
            PendingPaperIntent(
                side=str(row["side"]),
                ticker=str(row["ticker"]),
                rank_consensus=(
                    None
                    if row.get("rank_consensus") is None
                    else int(row["rank_consensus"])
                ),
                reason=str(row["reason"]),
                replacement_peer=(
                    None
                    if row.get("replacement_peer") is None
                    else str(row["replacement_peer"])
                ),
            )
            for row in raw_buys
            if isinstance(row, dict)
        )
        pending_sells = tuple(
            PendingPaperIntent(
                side=str(row["side"]),
                ticker=str(row["ticker"]),
                rank_consensus=(
                    None
                    if row.get("rank_consensus") is None
                    else int(row["rank_consensus"])
                ),
                reason=str(row["reason"]),
                replacement_peer=(
                    None
                    if row.get("replacement_peer") is None
                    else str(row["replacement_peer"])
                ),
            )
            for row in raw_sells
            if isinstance(row, dict)
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_STATE_ROW_INVALID") from exc
    if len(positions) != len(raw_positions):
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_POSITION_ROW_INVALID")
    if len(pending_buys) != len(raw_buys) or len(pending_sells) != len(raw_sells):
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_PENDING_ROW_INVALID")

    state = PaperPortfolioState(
        as_of_session_date=session,
        cash_idr=cash,
        positions=positions,
        pending_buys=pending_buys,
        pending_sells=pending_sells,
        reconciliation_required=bool(value.get("reconciliation_required")),
        source=PAPER_STATE_SOURCE,
    )
    normalize_state(state)
    return state


def _ledger_payload(ledger: dividend.DividendLedger) -> dict[str, Any]:
    normalized = dividend.normalize_dividend_ledger(ledger)
    return {
        "entitlements": [asdict(row) for row in normalized.entitlements],
        "receivables": [asdict(row) for row in normalized.receivables],
        "settlements": [asdict(row) for row in normalized.settlements],
    }


def _ledger_from_payload(value: object) -> dividend.DividendLedger:
    if not isinstance(value, dict):
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_LEDGER_INVALID")

    def rows(name: str) -> list[dict[str, Any]]:
        raw = value.get(name)
        if not isinstance(raw, list) or any(not isinstance(row, dict) for row in raw):
            raise DecisionV1Error(
                f"DIVIDEND_V1_1_RUNTIME_LEDGER_{name.upper()}_INVALID"
            )
        return raw

    try:
        ledger = dividend.DividendLedger(
            entitlements=tuple(
                dividend.PaperDividendEntitlement(**row)
                for row in rows("entitlements")
            ),
            receivables=tuple(
                dividend.PaperDividendReceivable(**row)
                for row in rows("receivables")
            ),
            settlements=tuple(
                dividend.PaperDividendSettlement(**row)
                for row in rows("settlements")
            ),
        )
    except TypeError as exc:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_LEDGER_ROW_INVALID") from exc
    return dividend.normalize_dividend_ledger(ledger)


def _event_payload(event: dividend.CertifiedCashDividend) -> dict[str, Any]:
    return asdict(dividend._validated_event(event))


def _registered_payload(row: RegisteredDividendEvidence) -> dict[str, Any]:
    verified = _verify_registered_evidence(row)
    return {
        "review_path": str(verified.review_path),
        "attachment_dir": str(verified.attachment_dir),
        "review_sha256": verified.review_sha256,
        "announcement_id": verified.announcement_id,
        "announcement_number": verified.announcement_number,
        "event": _event_payload(verified.event),
    }


def _registered_from_payload(value: object) -> RegisteredDividendEvidence:
    if not isinstance(value, dict) or not isinstance(value.get("event"), dict):
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_REGISTRY_ROW_INVALID")
    try:
        event = dividend.CertifiedCashDividend(**value["event"])
    except TypeError as exc:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_REGISTRY_EVENT_INVALID") from exc
    row = RegisteredDividendEvidence(
        review_path=Path(str(value.get("review_path") or "")).expanduser().resolve(),
        attachment_dir=Path(
            str(value.get("attachment_dir") or "")
        ).expanduser().resolve(),
        review_sha256=str(value.get("review_sha256") or ""),
        event=event,
        announcement_id=str(value.get("announcement_id") or ""),
        announcement_number=str(value.get("announcement_number") or ""),
    )
    return _verify_registered_evidence(row)


def _verify_registered_evidence(
    row: RegisteredDividendEvidence,
) -> RegisteredDividendEvidence:
    if not isinstance(row, RegisteredDividendEvidence):
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_REGISTERED_EVIDENCE_REQUIRED")
    review_path = row.review_path.expanduser().resolve()
    attachment_dir = row.attachment_dir.expanduser().resolve()
    if not review_path.is_file():
        raise DecisionV1Error(
            f"DIVIDEND_V1_1_RUNTIME_REVIEW_MISSING:{review_path}"
        )
    actual_review_sha = _sha256_file(review_path)
    if actual_review_sha != row.review_sha256:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_REVIEW_SHA_MISMATCH")
    verified = gate.verify_cash_dividend_evidence_for_execution(
        review_path=review_path,
        attachment_dir=attachment_dir,
    )
    event = dividend._validated_event(row.event)
    if verified.event != event:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_EVENT_REVERIFY_MISMATCH")
    if verified.review_sha256 != actual_review_sha:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_VERIFIER_REVIEW_SHA_MISMATCH")
    if (
        verified.announcement_id != row.announcement_id
        or verified.announcement_number != row.announcement_number
    ):
        raise DecisionV1Error(
            "DIVIDEND_V1_1_RUNTIME_ANNOUNCEMENT_IDENTITY_MISMATCH"
        )
    return RegisteredDividendEvidence(
        review_path=review_path,
        attachment_dir=attachment_dir,
        review_sha256=actual_review_sha,
        event=event,
        announcement_id=verified.announcement_id,
        announcement_number=verified.announcement_number,
    )


def normalize_certified_dividend_registry(
    rows: Sequence[RegisteredDividendEvidence],
) -> tuple[RegisteredDividendEvidence, ...]:
    by_event: dict[str, RegisteredDividendEvidence] = {}
    ticker_cum: dict[tuple[str, str], str] = {}
    for raw in rows:
        row = _verify_registered_evidence(raw)
        event = row.event
        existing = by_event.get(event.event_id)
        if existing is not None and existing != row:
            raise DecisionV1Error(
                "DIVIDEND_V1_1_RUNTIME_DUPLICATE_EVENT_CONFLICT"
            )
        key = (event.ticker, event.cum_date)
        existing_event = ticker_cum.get(key)
        if existing_event is not None and existing_event != event.event_id:
            raise DecisionV1Error(
                "DIVIDEND_V1_1_RUNTIME_CONFLICTING_EVENT_SAME_TICKER_CUM"
            )
        by_event[event.event_id] = row
        ticker_cum[key] = event.event_id
    return tuple(by_event[key] for key in sorted(by_event))


def register_verified_cash_dividend_evidence(
    rows: Sequence[RegisteredDividendEvidence],
    verified: gate.VerifiedCashDividendEvidence,
    *,
    attachment_dir: str | Path,
) -> tuple[RegisteredDividendEvidence, ...]:
    if (
        not isinstance(verified, gate.VerifiedCashDividendEvidence)
        or verified._verification_token is not gate._VERIFIED_DIVIDEND_EVIDENCE_TOKEN
    ):
        raise DecisionV1Error(
            "DIVIDEND_V1_1_RUNTIME_VERIFIED_DIVIDEND_EVIDENCE_REQUIRED"
        )
    attachment_root = Path(attachment_dir).expanduser().resolve()
    reverified = gate.verify_cash_dividend_evidence_for_execution(
        review_path=verified.review_path,
        attachment_dir=attachment_root,
    )
    if (
        reverified.event != verified.event
        or reverified.review_sha256 != verified.review_sha256
        or reverified.announcement_id != verified.announcement_id
        or reverified.announcement_number != verified.announcement_number
    ):
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_EVIDENCE_REVERIFY_MISMATCH")
    candidate = RegisteredDividendEvidence(
        review_path=verified.review_path.expanduser().resolve(),
        attachment_dir=attachment_root,
        review_sha256=verified.review_sha256,
        event=dividend._validated_event(verified.event),
        announcement_id=verified.announcement_id,
        announcement_number=verified.announcement_number,
    )
    return normalize_certified_dividend_registry((*rows, candidate))


def certified_registry_hash(
    rows: Sequence[RegisteredDividendEvidence],
) -> str:
    normalized = normalize_certified_dividend_registry(rows)
    return _canonical_hash([_registered_payload(row) for row in normalized])


def registered_certified_events(
    rows: Sequence[RegisteredDividendEvidence],
) -> tuple[dividend.CertifiedCashDividend, ...]:
    normalized = normalize_certified_dividend_registry(rows)
    return tuple(row.event for row in normalized)


def runtime_state_hash(
    state: dividend.DividendAwarePaperState,
    registry: Sequence[RegisteredDividendEvidence],
) -> str:
    return _canonical_hash(
        {
            "dividend_aware_state_sha256": dividend.dividend_aware_state_hash(state),
            "certified_dividend_registry_sha256": certified_registry_hash(registry),
        }
    )


def reconstruct_decision_shadow_state(
    state: dividend.DividendAwarePaperState,
) -> ShadowPortfolioState:
    if not isinstance(state, dividend.DividendAwarePaperState):
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_AWARE_STATE_REQUIRED")
    _, positions, pending_buys, pending_sells = normalize_state(state.base_state)
    shadow = set(positions)
    shadow.difference_update(pending_sells)
    shadow.update(pending_buys)
    if len(shadow) > TARGET_POSITIONS:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_SHADOW_OVER_TARGET")
    session = _iso_date(
        state.base_state.as_of_session_date,
        "DIVIDEND_V1_1_RUNTIME_STATE_DATE_INVALID",
    )
    return ShadowPortfolioState(
        as_of_session_date=session,
        positions=tuple(sorted(shadow)),
    )


def _snapshot_payload(
    state: dividend.DividendAwarePaperState,
    registry: Sequence[RegisteredDividendEvidence],
    previous_snapshot: VerifiedDividendRuntimeSnapshot | None,
) -> dict[str, Any]:
    if not isinstance(state, dividend.DividendAwarePaperState):
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_AWARE_STATE_REQUIRED")
    session = _iso_date(
        state.base_state.as_of_session_date,
        "DIVIDEND_V1_1_RUNTIME_STATE_DATE_INVALID",
    )
    base_payload = _paper_state_payload(state.base_state)
    ledger_payload = _ledger_payload(state.dividend_ledger)
    normalized_registry = normalize_certified_dividend_registry(registry)

    previous: dict[str, Any] | None = None
    if previous_snapshot is not None:
        if (
            not isinstance(previous_snapshot, VerifiedDividendRuntimeSnapshot)
            or previous_snapshot._verification_token
            is not _VERIFIED_RUNTIME_SNAPSHOT_TOKEN
        ):
            raise DecisionV1Error(
                "DIVIDEND_V1_1_RUNTIME_VERIFIED_PARENT_SNAPSHOT_REQUIRED"
            )
        parent_session = previous_snapshot.state.base_state.as_of_session_date
        if date.fromisoformat(parent_session) >= date.fromisoformat(session):
            raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_PARENT_DATE_NOT_PRIOR")
        if not previous_snapshot.path.is_file():
            raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_PARENT_MISSING")
        if _sha256_file(previous_snapshot.path) != previous_snapshot.file_sha256:
            raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_PARENT_SHA_CHANGED")
        previous = {
            "path": str(previous_snapshot.path),
            "sha256": previous_snapshot.file_sha256,
            "runtime_state_sha256": previous_snapshot.runtime_state_sha256,
            "session_date": parent_session,
        }

    hashes = {
        "base_paper_state_sha256": paper_state_hash(state.base_state),
        "dividend_ledger_sha256": dividend.dividend_ledger_hash(
            state.dividend_ledger
        ),
        "dividend_aware_state_sha256": dividend.dividend_aware_state_hash(state),
        "certified_dividend_registry_sha256": certified_registry_hash(
            normalized_registry
        ),
        "runtime_state_sha256": runtime_state_hash(state, normalized_registry),
    }
    payload: dict[str, Any] = {
        "schema_version": RUNTIME_SCHEMA,
        "session_date": session,
        "state": {
            "base_paper_state": base_payload,
            "dividend_ledger": ledger_payload,
        },
        "certified_dividend_registry": [
            _registered_payload(row) for row in normalized_registry
        ],
        "hashes": hashes,
        "previous_snapshot": previous,
    }
    payload["snapshot_payload_sha256"] = _canonical_hash(payload)
    return payload


def _snapshot_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def write_runtime_snapshot(
    runtime_root: str | Path,
    state: dividend.DividendAwarePaperState,
    registry: Sequence[RegisteredDividendEvidence] = (),
    *,
    previous_snapshot: VerifiedDividendRuntimeSnapshot | None = None,
) -> VerifiedDividendRuntimeSnapshot:
    payload = _snapshot_payload(state, registry, previous_snapshot)
    session = str(payload["session_date"])
    root = Path(runtime_root).expanduser().resolve()
    snapshot_dir = root / RUNTIME_DIRNAME / SNAPSHOT_DIRNAME
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    target = snapshot_dir / f"{session}.json"
    data = _snapshot_bytes(payload)

    if target.exists():
        if target.read_bytes() != data:
            raise DecisionV1Error(
                f"DIVIDEND_V1_1_RUNTIME_SNAPSHOT_SESSION_CONFLICT:{session}"
            )
        return load_runtime_snapshot(target)

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{session}.",
        suffix=".tmp",
        dir=snapshot_dir,
    )
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists():
            if target.read_bytes() != data:
                raise DecisionV1Error(
                    f"DIVIDEND_V1_1_RUNTIME_SNAPSHOT_SESSION_CONFLICT:{session}"
                )
            temp.unlink(missing_ok=True)
        else:
            os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)

    if target.read_bytes() != data:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_SNAPSHOT_WRITE_MISMATCH")
    return load_runtime_snapshot(target)


def _load_runtime_snapshot(
    path: Path,
    *,
    seen: set[Path],
) -> VerifiedDividendRuntimeSnapshot:
    resolved = path.expanduser().resolve()
    if resolved in seen:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_PARENT_CYCLE")
    seen.add(resolved)
    if not resolved.is_file():
        raise DecisionV1Error(f"DIVIDEND_V1_1_RUNTIME_SNAPSHOT_MISSING:{resolved}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_SNAPSHOT_INVALID") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != RUNTIME_SCHEMA:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_SCHEMA_CHANGED")

    session = _iso_date(
        payload.get("session_date"),
        "DIVIDEND_V1_1_RUNTIME_SNAPSHOT_DATE_INVALID",
    )
    if resolved.name != f"{session}.json":
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_SNAPSHOT_FILENAME_MISMATCH")
    declared_payload_sha = str(payload.get("snapshot_payload_sha256") or "")
    hash_input = dict(payload)
    hash_input.pop("snapshot_payload_sha256", None)
    if _canonical_hash(hash_input) != declared_payload_sha:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_SNAPSHOT_PAYLOAD_SHA_MISMATCH")

    state_raw = payload.get("state")
    if not isinstance(state_raw, dict):
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_STATE_MISSING")
    base_state = _paper_state_from_payload(state_raw.get("base_paper_state"))
    if base_state.as_of_session_date != session:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_STATE_DATE_MISMATCH")
    ledger = _ledger_from_payload(state_raw.get("dividend_ledger"))
    state = dividend.DividendAwarePaperState(
        base_state=base_state,
        dividend_ledger=ledger,
    )

    registry_raw = payload.get("certified_dividend_registry")
    if not isinstance(registry_raw, list):
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_REGISTRY_INVALID")
    registry = normalize_certified_dividend_registry(
        tuple(_registered_from_payload(row) for row in registry_raw)
    )

    hashes = payload.get("hashes")
    if not isinstance(hashes, dict):
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_HASHES_MISSING")
    expected_hashes = {
        "base_paper_state_sha256": paper_state_hash(base_state),
        "dividend_ledger_sha256": dividend.dividend_ledger_hash(ledger),
        "dividend_aware_state_sha256": dividend.dividend_aware_state_hash(state),
        "certified_dividend_registry_sha256": certified_registry_hash(registry),
        "runtime_state_sha256": runtime_state_hash(state, registry),
    }
    if hashes != expected_hashes:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_INTERNAL_HASH_MISMATCH")

    previous_path: Path | None = None
    previous_sha: str | None = None
    previous = payload.get("previous_snapshot")
    if previous is not None:
        if not isinstance(previous, dict):
            raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_PARENT_INVALID")
        previous_path = Path(str(previous.get("path") or "")).expanduser().resolve()
        previous_sha = str(previous.get("sha256") or "")
        if not previous_path.is_file():
            raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_PARENT_MISSING")
        if _sha256_file(previous_path) != previous_sha:
            raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_PARENT_SHA_MISMATCH")
        parent = _load_runtime_snapshot(previous_path, seen=seen)
        if parent.file_sha256 != previous_sha:
            raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_PARENT_SHA_MISMATCH")
        if previous.get("runtime_state_sha256") != parent.runtime_state_sha256:
            raise DecisionV1Error(
                "DIVIDEND_V1_1_RUNTIME_PARENT_STATE_HASH_MISMATCH"
            )
        if previous.get("session_date") != parent.state.base_state.as_of_session_date:
            raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_PARENT_DATE_MISMATCH")
        if date.fromisoformat(parent.state.base_state.as_of_session_date) >= date.fromisoformat(session):
            raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_PARENT_DATE_NOT_PRIOR")

    return VerifiedDividendRuntimeSnapshot(
        path=resolved,
        file_sha256=_sha256_file(resolved),
        snapshot_payload_sha256=declared_payload_sha,
        runtime_state_sha256=expected_hashes["runtime_state_sha256"],
        state=state,
        certified_dividend_registry=registry,
        previous_snapshot_path=previous_path,
        previous_snapshot_sha256=previous_sha,
        _verification_token=_VERIFIED_RUNTIME_SNAPSHOT_TOKEN,
    )


def load_runtime_snapshot(
    path: str | Path,
) -> VerifiedDividendRuntimeSnapshot:
    return _load_runtime_snapshot(Path(path), seen=set())


def load_latest_runtime_snapshot(
    runtime_root: str | Path,
) -> VerifiedDividendRuntimeSnapshot:
    root = (
        Path(runtime_root).expanduser().resolve()
        / RUNTIME_DIRNAME
        / SNAPSHOT_DIRNAME
    )
    if not root.is_dir():
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_SNAPSHOT_DIR_MISSING")
    candidates: list[tuple[date, Path]] = []
    for path in root.glob("*.json"):
        try:
            session = date.fromisoformat(path.stem)
        except ValueError:
            raise DecisionV1Error(
                f"DIVIDEND_V1_1_RUNTIME_NONCANONICAL_SNAPSHOT_FILENAME:{path.name}"
            )
        candidates.append((session, path))
    if not candidates:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_NO_SNAPSHOT")
    candidates.sort(key=lambda item: item[0])
    latest = load_runtime_snapshot(candidates[-1][1])

    # Every earlier snapshot must be an ancestor of the latest. This catches
    # accidental forked state histories instead of silently selecting one.
    ancestor_paths: set[Path] = set()
    cursor = latest
    while cursor.previous_snapshot_path is not None:
        ancestor_paths.add(cursor.previous_snapshot_path.resolve())
        cursor = load_runtime_snapshot(cursor.previous_snapshot_path)
    non_latest = {path.resolve() for _, path in candidates[:-1]}
    if ancestor_paths != non_latest:
        raise DecisionV1Error("DIVIDEND_V1_1_RUNTIME_SNAPSHOT_CHAIN_FORK")
    return latest


__all__ = [
    "RUNTIME_SCHEMA",
    "RUNTIME_DIRNAME",
    "SNAPSHOT_DIRNAME",
    "RegisteredDividendEvidence",
    "VerifiedDividendRuntimeSnapshot",
    "normalize_certified_dividend_registry",
    "register_verified_cash_dividend_evidence",
    "certified_registry_hash",
    "registered_certified_events",
    "runtime_state_hash",
    "reconstruct_decision_shadow_state",
    "write_runtime_snapshot",
    "load_runtime_snapshot",
    "load_latest_runtime_snapshot",
]
