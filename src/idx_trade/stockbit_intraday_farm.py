from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import requests

from .provenance import sha256_file
from .providers.idx import fetch_active_listings
from .security_master import normalise_ticker
from .stockbit_intraday_capture import (
    DEFAULT_CAPTURE_AFTER,
    JAKARTA,
    _now_jakarta,
    _parse_hhmm,
    _request_chart,
    capture_state,
    parse_chart_payload,
)
from .stockbit_intraday_universe import ticker_list_sha256


DEFAULT_MAX_NEW_TICKERS = 1_200
DEFAULT_MONTHLY_QUOTA_RESERVE = 3_000
TERMINAL_SUCCESS = {"SUCCESS"}


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _atomic_json(path: Path, value: object) -> None:
    _atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n")


def _atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    temporary.replace(path)


def _canonical_current_idx_universe(frame: pd.DataFrame, expected_date: date) -> pd.DataFrame:
    required = {"ticker", "listed_from"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"IDX active listing snapshot missing columns: {sorted(missing)}")

    data = frame.copy()
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["listed_from"] = pd.to_datetime(data["listed_from"], errors="coerce").dt.normalize()
    expected = pd.Timestamp(expected_date).normalize()
    data = data[
        data["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)
        & data["listed_from"].notna()
        & data["listed_from"].le(expected)
    ].copy()
    if data.empty:
        raise ValueError("IDX current active-stock universe is empty")
    if data["ticker"].duplicated(keep=False).any():
        tickers = sorted(data.loc[data["ticker"].duplicated(keep=False), "ticker"].unique())
        raise ValueError(f"duplicate current IDX ticker(s): {tickers[:20]}")

    keep = [column for column in ("ticker", "company_name", "listed_from", "source") if column in data.columns]
    data = data[keep].sort_values("ticker").reset_index(drop=True)
    data.insert(0, "as_of_date", expected_date.isoformat())
    return data


def freeze_current_idx_universe(
    root: Path,
    *,
    expected_date: date,
    captured_at: datetime,
    fetcher: Callable[[], pd.DataFrame] = fetch_active_listings,
) -> dict[str, Any]:
    universe_path = root / "universe_snapshot.csv"
    metadata_path = root / "day_metadata.json"
    if universe_path.exists() or metadata_path.exists():
        raise FileExistsError("universe/day metadata already exists")

    universe = _canonical_current_idx_universe(fetcher(), expected_date)
    _atomic_csv(universe_path, universe)
    tickers = universe["ticker"].astype(str).tolist()
    metadata: dict[str, Any] = {
        "expected_date": expected_date.isoformat(),
        "captured_universe_at": captured_at.astimezone(JAKARTA).isoformat(),
        "universe_source": "IDX_CURRENT_ACTIVE_STOCK_LIST",
        "universe_rows": len(universe),
        "ticker_list_sha256": ticker_list_sha256(tickers),
        "universe_snapshot_sha256": sha256_file(universe_path),
        "resumable_layout_version": 1,
    }
    _atomic_json(metadata_path, metadata)
    return metadata


def _load_frozen_day(root: Path, *, expected_date: date) -> tuple[pd.DataFrame, dict[str, Any]]:
    universe_path = root / "universe_snapshot.csv"
    metadata_path = root / "day_metadata.json"
    if not universe_path.exists() or not metadata_path.exists():
        raise FileNotFoundError("frozen universe/day metadata is incomplete")

    universe = pd.read_csv(universe_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    tickers = [normalise_ticker(value) for value in universe["ticker"].astype(str).tolist()]
    if metadata.get("expected_date") != expected_date.isoformat():
        raise ValueError("existing day root belongs to a different expected_date")
    if metadata.get("universe_snapshot_sha256") != sha256_file(universe_path):
        raise ValueError("frozen universe snapshot hash mismatch")
    if metadata.get("ticker_list_sha256") != ticker_list_sha256(tickers):
        raise ValueError("frozen ticker-list hash mismatch")
    if int(metadata.get("universe_rows") or -1) != len(universe):
        raise ValueError("frozen universe row-count mismatch")
    return universe, metadata


def prepare_or_load_day(
    root: Path,
    *,
    expected_date: date,
    captured_at: datetime,
    fetcher: Callable[[], pd.DataFrame] = fetch_active_listings,
) -> tuple[pd.DataFrame, dict[str, Any], bool]:
    root.mkdir(parents=True, exist_ok=True)
    metadata_path = root / "day_metadata.json"
    universe_path = root / "universe_snapshot.csv"
    if metadata_path.exists() or universe_path.exists():
        universe, metadata = _load_frozen_day(root, expected_date=expected_date)
        return universe, metadata, False
    metadata = freeze_current_idx_universe(
        root,
        expected_date=expected_date,
        captured_at=captured_at,
        fetcher=fetcher,
    )
    universe, metadata = _load_frozen_day(root, expected_date=expected_date)
    return universe, metadata, True


def _status_path(root: Path, ticker: str) -> Path:
    return root / "status" / f"{ticker}.json"


def _raw_path(root: Path, ticker: str) -> Path:
    return root / "raw" / f"{ticker}.json"


def _rows_path(root: Path, ticker: str) -> Path:
    return root / "rows" / f"{ticker}.csv"


def _read_status(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def pending_tickers(
    root: Path,
    tickers: list[str],
    *,
    retry_errors: bool,
) -> tuple[list[str], list[str]]:
    pending: list[str] = []
    skipped: list[str] = []
    for ticker in tickers:
        status = _read_status(_status_path(root, ticker))
        if status is None:
            pending.append(ticker)
            continue
        if status.get("status") in TERMINAL_SUCCESS:
            skipped.append(ticker)
            continue
        if retry_errors:
            pending.append(ticker)
        else:
            skipped.append(ticker)
    return pending, skipped


def _remaining_month(headers: dict[str, Any]) -> int | None:
    try:
        return int(str(headers.get("remaining_month")))
    except (TypeError, ValueError):
        return None


def _write_ticker_evidence(
    root: Path,
    ticker: str,
    *,
    payload: object | None,
    frame: pd.DataFrame,
    status: dict[str, Any],
    captured_at: datetime,
) -> None:
    if payload is not None:
        _atomic_json(
            _raw_path(root, ticker),
            {"ticker": ticker, "captured_at": captured_at.astimezone(JAKARTA).isoformat(), "payload": payload},
        )
    if not frame.empty:
        _atomic_csv(_rows_path(root, ticker), frame)
    _atomic_json(_status_path(root, ticker), status)


def _recursive_manifest(root: Path) -> dict[str, Any]:
    excluded = {"artifact_manifest.json"}
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in excluded or path.suffix == ".tmp":
            continue
        relative = path.relative_to(root).as_posix()
        files[relative] = sha256_file(path)
    manifest = {"files": files}
    manifest_path = root / "artifact_manifest.json"
    _atomic_json(manifest_path, manifest)
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    return manifest


def finalize_day(root: Path, *, expected_date: date) -> dict[str, Any]:
    universe, metadata = _load_frozen_day(root, expected_date=expected_date)
    tickers = universe["ticker"].astype(str).tolist()
    statuses: list[dict[str, Any]] = []
    frames: list[pd.DataFrame] = []
    for ticker in tickers:
        status = _read_status(_status_path(root, ticker))
        if status is not None:
            statuses.append(status)
        rows_path = _rows_path(root, ticker)
        if rows_path.exists():
            frames.append(pd.read_csv(rows_path))

    status_frame = pd.DataFrame(statuses)
    rows = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    final_dir = root / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    _atomic_csv(final_dir / "stockbit_intraday_ticker_status.csv", status_frame)
    _atomic_csv(final_dir / "stockbit_intraday_rows.csv", rows)

    attempted = len(statuses)
    successful = int(status_frame["status"].eq("SUCCESS").sum()) if not status_frame.empty else 0
    summary: dict[str, Any] = {
        "expected_date": expected_date.isoformat(),
        "universe_source": metadata["universe_source"],
        "universe_tickers": len(tickers),
        "ticker_list_sha256": metadata["ticker_list_sha256"],
        "attempted_tickers": attempted,
        "successful_tickers": successful,
        "unfinished_tickers": len(tickers) - attempted,
        "normalized_points": len(rows),
        "complete": attempted == len(tickers),
        "synthetic_fill_used": False,
        "minute_volume_available": False,
    }
    _atomic_json(final_dir / "run_summary.json", summary)
    manifest = _recursive_manifest(root)
    summary["artifact_manifest_sha256"] = manifest["manifest_sha256"]
    return summary


def run_farm(
    root: Path,
    *,
    expected_date: date,
    capture_after: str = DEFAULT_CAPTURE_AFTER,
    max_new_tickers: int = DEFAULT_MAX_NEW_TICKERS,
    monthly_quota_reserve: int = DEFAULT_MONTHLY_QUOTA_RESERVE,
    retry_errors: bool = False,
    api_key: str,
    now: datetime | None = None,
    http: requests.Session | None = None,
    universe_fetcher: Callable[[], pd.DataFrame] = fetch_active_listings,
) -> dict[str, Any]:
    current = now or _now_jakarta()
    if current.astimezone(JAKARTA).date() != expected_date:
        raise ValueError("Stockbit today-only farm requires expected_date == current Asia/Jakarta date")
    state = capture_state(current, _parse_hhmm(capture_after), False)
    if state != "SESSION_COMPLETE_WINDOW":
        raise RuntimeError("daily farm is allowed only in the complete-session window")
    if max_new_tickers <= 0:
        raise ValueError("max_new_tickers must be positive")
    if monthly_quota_reserve < 0:
        raise ValueError("monthly_quota_reserve must be non-negative")

    universe, metadata, universe_created = prepare_or_load_day(
        root,
        expected_date=expected_date,
        captured_at=current,
        fetcher=universe_fetcher,
    )
    tickers = universe["ticker"].astype(str).tolist()
    pending, skipped = pending_tickers(root, tickers, retry_errors=retry_errors)
    if len(pending) > max_new_tickers:
        raise ValueError(f"pending ticker count {len(pending)} exceeds max_new_tickers={max_new_tickers}")

    session = http or requests.Session()
    newly_attempted = retries = rate_limits = request_attempts = 0
    stop_reason = "COMPLETED_PENDING_SET"
    quota_last: dict[str, Any] = {}

    for ticker in pending:
        payload, meta = _request_chart(session, ticker, api_key)
        newly_attempted += 1
        request_attempts += int(meta.get("attempts") or 0)
        retries += int(meta.get("retries") or 0)
        rate_limits += int(meta.get("rate_limit_events") or 0)
        quota_last = dict(meta.get("safe_headers") or {})

        if payload is None:
            frame = pd.DataFrame()
            status: dict[str, Any] = {
                "ticker": ticker,
                "status": "REQUEST_ERROR",
                "points": 0,
                "attempts": meta.get("attempts"),
                "retries": meta.get("retries"),
                "rate_limit_events": meta.get("rate_limit_events"),
                "errors": meta.get("errors") or [],
            }
        else:
            frame, status = parse_chart_payload(
                ticker,
                payload,
                expected_date=expected_date,
                capture_state="SESSION_COMPLETE_WINDOW",
            )
            status.update(
                {
                    "attempts": meta.get("attempts"),
                    "retries": meta.get("retries"),
                    "rate_limit_events": meta.get("rate_limit_events"),
                }
            )

        _write_ticker_evidence(
            root,
            ticker,
            payload=payload,
            frame=frame,
            status=status,
            captured_at=current,
        )

        remaining = _remaining_month(quota_last)
        if remaining is not None and remaining <= monthly_quota_reserve:
            stop_reason = "MONTHLY_QUOTA_RESERVE_REACHED"
            break

    summary = finalize_day(root, expected_date=expected_date)
    summary.update(
        {
            "universe_created_this_run": universe_created,
            "prior_terminal_or_skipped": len(skipped),
            "newly_attempted_tickers": newly_attempted,
            "request_attempts": request_attempts,
            "retries": retries,
            "http_429_events": rate_limits,
            "stop_reason": stop_reason,
            "monthly_quota_reserve": monthly_quota_reserve,
            "quota_last_response": quota_last,
        }
    )
    _atomic_json(root / "final" / "run_summary.json", summary)
    manifest = _recursive_manifest(root)
    summary["artifact_manifest_sha256"] = manifest["manifest_sha256"]
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resumable daily Stockbit intraday farm")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-date", type=date.fromisoformat, default=None)
    parser.add_argument("--capture-after", default=DEFAULT_CAPTURE_AFTER)
    parser.add_argument("--max-new-tickers", type=int, default=DEFAULT_MAX_NEW_TICKERS)
    parser.add_argument("--monthly-quota-reserve", type=int, default=DEFAULT_MONTHLY_QUOTA_RESERVE)
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument("--execute", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    now = _now_jakarta()
    expected_date = args.expected_date or now.astimezone(JAKARTA).date()

    if not args.execute:
        universe, metadata, created = prepare_or_load_day(
            args.output_root,
            expected_date=expected_date,
            captured_at=now,
        )
        pending, skipped = pending_tickers(
            args.output_root,
            universe["ticker"].astype(str).tolist(),
            retry_errors=bool(args.retry_errors),
        )
        report = {
            "mode": "DRY_RUN",
            "expected_date": expected_date.isoformat(),
            "universe_created": created,
            "universe_tickers": len(universe),
            "ticker_list_sha256": metadata["ticker_list_sha256"],
            "pending_tickers": len(pending),
            "skipped_existing": len(skipped),
            "estimated_new_chart_calls": len(pending),
            "monthly_quota_reserve": args.monthly_quota_reserve,
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    api_key = os.environ.get("ZAPI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ZAPI_API_KEY is required for --execute")
    summary = run_farm(
        args.output_root,
        expected_date=expected_date,
        capture_after=args.capture_after,
        max_new_tickers=args.max_new_tickers,
        monthly_quota_reserve=args.monthly_quota_reserve,
        retry_errors=bool(args.retry_errors),
        api_key=api_key,
        now=now,
    )
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
