from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from .provenance import sha256_file
from .stockbit_intraday_capture import DEFAULT_CAPTURE_AFTER, JAKARTA, _now_jakarta, _parse_hhmm, capture_state
from .stockbit_intraday_farm import (
    DEFAULT_MAX_NEW_TICKERS,
    DEFAULT_MONTHLY_QUOTA_RESERVE,
    _atomic_csv,
    _atomic_json,
    _read_status,
    _recursive_manifest,
    _status_path,
    prepare_or_load_day,
    run_farm,
)
from .stockbit_intraday_traded_gate_audit import (
    _activity_columns,
    _request_summary,
    parse_stock_summary_payload,
)


POLICY_VERSION = 1
DEFAULT_SHADOW_SESSIONS = 3
DEFAULT_RECHECK_EVERY = 10
TERMINAL_GATE_SKIP = "SKIPPED_IDX_NO_ACTIVITY"


@dataclass(frozen=True)
class GateResult:
    decisions: pd.DataFrame
    summary_call_made: bool
    safe_headers: dict[str, Any]


@dataclass(frozen=True)
class ShadowMetrics:
    false_negative: int
    false_positive: int
    actual_success: int
    actual_non_success: int
    unexpected_statuses: tuple[str, ...]
    non_404_request_errors: tuple[str, ...]
    certification_eligible: bool


def _policy_default() -> dict[str, Any]:
    return {
        "version": POLICY_VERSION,
        "mode": "SHADOW",
        "consecutive_zero_fn_shadow_sessions": 0,
        "enforced_sessions_since_recheck": 0,
        "history": [],
    }


def load_policy(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _policy_default()
    value = json.loads(path.read_text(encoding="utf-8"))
    if int(value.get("version") or -1) != POLICY_VERSION:
        raise ValueError("unsupported Stockbit intraday policy version")
    if value.get("mode") not in {"SHADOW", "ENFORCE"}:
        raise ValueError("invalid Stockbit intraday policy mode")
    value.setdefault("consecutive_zero_fn_shadow_sessions", 0)
    value.setdefault("enforced_sessions_since_recheck", 0)
    value.setdefault("history", [])
    return value


def _run_mode(policy: dict[str, Any], *, recheck_every: int) -> str:
    if policy["mode"] == "SHADOW":
        return "SHADOW"
    if int(policy.get("enforced_sessions_since_recheck") or 0) >= recheck_every:
        return "SHADOW_RECHECK"
    return "ENFORCE"


def _gate_paths(day_root: Path) -> dict[str, Path]:
    gate = day_root / "gate"
    return {
        "dir": gate,
        "raw": gate / "idx_stock_summary_raw.json",
        "headers": gate / "idx_stock_summary_safe_headers.json",
        "normalized": gate / "idx_stock_summary_normalized.csv",
        "decisions": gate / "traded_today_decisions.csv",
        "metadata": gate / "gate_metadata.json",
    }


def _build_gate_decisions(universe: pd.DataFrame, idx_summary: pd.DataFrame) -> pd.DataFrame:
    base = universe[["ticker"]].copy()
    summary = _activity_columns(idx_summary)
    merged = base.merge(summary, on="ticker", how="left", validate="one_to_one")
    merged["idx_summary_present"] = merged["session_date"].notna()
    for column in ("volume_gt0", "value_gt0", "frequency_gt0", "activity_or"):
        merged[column] = merged[column].fillna(False).astype(bool)
    merged["would_fetch_stockbit"] = (~merged["idx_summary_present"]) | merged["activity_or"]
    merged["gate_decision"] = "FETCH_TRADED"
    merged.loc[~merged["idx_summary_present"], "gate_decision"] = "FETCH_MISSING_SUMMARY"
    merged.loc[merged["idx_summary_present"] & ~merged["activity_or"], "gate_decision"] = "SKIP_NO_ACTIVITY"
    return merged.sort_values("ticker").reset_index(drop=True)


def _verify_saved_gate(paths: dict[str, Path], *, expected_date: date, universe_sha: str) -> GateResult | None:
    if not paths["metadata"].exists():
        return None
    metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    if metadata.get("expected_date") != expected_date.isoformat():
        raise ValueError("saved traded gate belongs to a different session")
    if metadata.get("universe_snapshot_sha256") != universe_sha:
        raise ValueError("saved traded gate universe hash mismatch")
    source_kind = str(metadata.get("summary_source") or "ZAPI_IDX_STOCK_SUMMARY")
    if source_kind == "IDX_OFFICIAL_EOD_REUSE":
        source_summary = Path(str(metadata.get("source_summary_path") or ""))
        source_raw = Path(str(metadata.get("source_raw_path") or ""))
        if not source_summary.is_file() or not source_raw.is_file():
            raise FileNotFoundError("saved EOD-reused gate source artifact is missing")
        if metadata.get("source_summary_sha256") != sha256_file(source_summary):
            raise ValueError("saved traded gate source summary hash mismatch")
        if metadata.get("source_raw_sha256") != sha256_file(source_raw):
            raise ValueError("saved traded gate source raw hash mismatch")
        for key in ("normalized", "decisions"):
            path = paths[key]
            if not path.exists():
                raise FileNotFoundError(f"saved traded gate incomplete: {path}")
            expected_hash = metadata.get(f"{key}_sha256")
            if expected_hash != sha256_file(path):
                raise ValueError(f"saved traded gate hash mismatch: {key}")
    else:
        for key in ("raw", "headers", "normalized", "decisions"):
            path = paths[key]
            if not path.exists():
                raise FileNotFoundError(f"saved traded gate incomplete: {path}")
            expected_hash = metadata.get(f"{key}_sha256")
            if expected_hash != sha256_file(path):
                raise ValueError(f"saved traded gate hash mismatch: {key}")
    decisions = pd.read_csv(paths["decisions"])
    safe_headers = json.loads(paths["headers"].read_text(encoding="utf-8"))
    return GateResult(decisions=decisions, summary_call_made=False, safe_headers=safe_headers)


def _load_eod_stock_summary(day_root: Path, *, expected_date: date) -> tuple[pd.DataFrame, dict[str, Any]] | None:
    """Reuse a verified canonical EOD Stock Summary for the same session.

    The intraday gate must not make a second post-close Zapi request when the
    canonical EOD transaction already contains the official snapshot.  This
    is deliberately strict: any missing, stale, partial, or hash-mismatched
    EOD artifact returns ``None`` so the existing Zapi path remains the only
    fallback and can fail closed normally.
    """

    base_root = day_root.parent.parent
    session_root = base_root.parent / "forward_monitoring" / "sessions" / expected_date.isoformat()
    manifest_path = session_root / "manifest.json"
    summary_path = session_root / "idx_stock_summary.csv"
    raw_path = session_root / "idx_stock_summary.raw.json"
    if not manifest_path.is_file() or not summary_path.is_file() or not raw_path.is_file():
        return None

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = manifest.get("stock_summary_source") or {}
    metadata = manifest.get("stock_summary_meta") or {}
    if (
        manifest.get("status") != "DATA_READY"
        or manifest.get("session_date") != expected_date.isoformat()
        or source.get("source") != "IDX_OFFICIAL"
        or source.get("session_date") != expected_date.isoformat()
        or metadata.get("completeness_status") != "COMPLETE_RECORDS_TOTAL_SINGLE_RESPONSE"
    ):
        return None
    if manifest.get("stock_summary_sha256") != sha256_file(summary_path):
        raise ValueError("canonical EOD Stock Summary hash mismatch")
    declared_raw_sha = manifest.get("stock_summary_raw_sha256")
    if not declared_raw_sha or declared_raw_sha != sha256_file(raw_path):
        raise ValueError("canonical EOD Stock Summary raw hash mismatch")

    frame = pd.read_csv(summary_path)
    required = {"ticker", "as_of_date", "volume", "frequency", "regular_value"}
    if required - set(frame.columns):
        raise ValueError("canonical EOD Stock Summary columns are incomplete")
    if len(frame) != int(metadata.get("rows", -1)):
        raise ValueError("canonical EOD Stock Summary row count mismatch")
    if int(metadata.get("rows", -1)) != int(metadata.get("records_total", -2)):
        raise ValueError("canonical EOD Stock Summary recordsTotal mismatch")
    if int(metadata.get("rows", -1)) != int(metadata.get("records_filtered", -3)):
        raise ValueError("canonical EOD Stock Summary recordsFiltered mismatch")
    if frame["ticker"].astype(str).duplicated().any():
        raise ValueError("canonical EOD Stock Summary has duplicate tickers")
    if frame["as_of_date"].astype(str).ne(expected_date.isoformat()).any():
        raise ValueError("canonical EOD Stock Summary date mismatch")

    numeric = frame[["volume", "frequency", "regular_value"]].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or (numeric < 0).any().any():
        raise ValueError("canonical EOD Stock Summary activity fields are invalid")
    summary = pd.DataFrame(
        {
            "ticker": frame["ticker"].astype(str).str.upper().str.strip(),
            "session_date": expected_date.isoformat(),
            "volume": numeric["volume"],
            "value": numeric["regular_value"],
            "frequency": numeric["frequency"],
            "raw_close": float("nan"),
            "raw_high": float("nan"),
            "raw_low": float("nan"),
        }
    ).sort_values("ticker").reset_index(drop=True)
    provenance = {
        "summary_source": "IDX_OFFICIAL_EOD_REUSE",
        "source_ref": source.get("source_ref"),
        "source_summary_path": str(summary_path),
        "source_summary_sha256": sha256_file(summary_path),
        "source_raw_path": str(raw_path),
        "source_raw_sha256": declared_raw_sha,
        "source_observed_available_at_utc": source.get("observed_available_at_utc"),
        "source_records_total": int(metadata["records_total"]),
        "source_records_filtered": int(metadata["records_filtered"]),
    }
    return summary, provenance


def prepare_traded_gate(
    day_root: Path,
    universe: pd.DataFrame,
    *,
    expected_date: date,
    universe_sha: str,
    api_key: str,
    session: requests.Session,
) -> GateResult:
    paths = _gate_paths(day_root)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    saved = _verify_saved_gate(paths, expected_date=expected_date, universe_sha=universe_sha)
    if saved is not None:
        return saved

    summary_call_made = False
    safe_headers: dict[str, Any] = {}
    eod_reuse = _load_eod_stock_summary(day_root, expected_date=expected_date)
    source_provenance: dict[str, Any] = {}
    if eod_reuse is not None:
        idx_summary, source_provenance = eod_reuse
        safe_headers = {
            "source": "IDX_OFFICIAL_EOD_REUSE",
            "source_ref": source_provenance["source_ref"],
            "observed_available_at_utc": source_provenance["source_observed_available_at_utc"],
            "records_total": source_provenance["source_records_total"],
            "records_filtered": source_provenance["source_records_filtered"],
        }
        _atomic_json(paths["headers"], safe_headers)
    elif paths["raw"].exists():
        payload = json.loads(paths["raw"].read_text(encoding="utf-8"))
        if paths["headers"].exists():
            safe_headers = json.loads(paths["headers"].read_text(encoding="utf-8"))
        idx_summary = parse_stock_summary_payload(payload, expected_date=expected_date)
    else:
        payload, safe_headers = _request_summary(session, api_key, expected_date=expected_date)
        summary_call_made = True
        # Persist the network evidence before parsing so a schema failure can be
        # repaired offline without spending another request.
        _atomic_json(paths["raw"], payload)
        _atomic_json(paths["headers"], safe_headers)
        idx_summary = parse_stock_summary_payload(payload, expected_date=expected_date)
    _atomic_csv(paths["normalized"], idx_summary)
    decisions = _build_gate_decisions(universe, idx_summary)
    _atomic_csv(paths["decisions"], decisions)
    metadata = {
        "expected_date": expected_date.isoformat(),
        "universe_snapshot_sha256": universe_sha,
        **source_provenance,
        "summary_source": source_provenance.get("summary_source", "ZAPI_IDX_STOCK_SUMMARY"),
        "canonical_summary_rows": len(idx_summary),
        "universe_rows": len(universe),
        "summary_coverage": int(decisions["idx_summary_present"].sum()),
        "would_fetch_stockbit": int(decisions["would_fetch_stockbit"].sum()),
        "would_skip_no_activity": int((decisions["gate_decision"] == "SKIP_NO_ACTIVITY").sum()),
        "raw_sha256": sha256_file(paths["raw"]) if paths["raw"].exists() else None,
        "headers_sha256": sha256_file(paths["headers"]),
        "normalized_sha256": sha256_file(paths["normalized"]),
        "decisions_sha256": sha256_file(paths["decisions"]),
    }
    _atomic_json(paths["metadata"], metadata)
    return GateResult(decisions=decisions, summary_call_made=summary_call_made, safe_headers=safe_headers)


def apply_gate_skips(day_root: Path, decisions: pd.DataFrame, *, expected_date: date) -> int:
    skipped = 0
    for row in decisions.itertuples(index=False):
        if str(row.gate_decision) != "SKIP_NO_ACTIVITY":
            continue
        path = _status_path(day_root, str(row.ticker))
        if _read_status(path) is not None:
            continue
        _atomic_json(
            path,
            {
                "ticker": str(row.ticker),
                "status": TERMINAL_GATE_SKIP,
                "points": 0,
                "session_date": expected_date.isoformat(),
                "reason": "IDX_STOCK_SUMMARY_VOLUME_VALUE_FREQUENCY_ALL_ZERO",
                "idx_summary_present": True,
                "volume": row.volume,
                "value": row.value,
                "frequency": row.frequency,
            },
        )
        skipped += 1
    return skipped


def shadow_metrics(decisions: pd.DataFrame, status_frame: pd.DataFrame, *, complete: bool) -> ShadowMetrics:
    merged = decisions[["ticker", "would_fetch_stockbit"]].merge(
        status_frame[["ticker", "status", "errors"]] if "errors" in status_frame.columns else status_frame[["ticker", "status"]],
        on="ticker",
        how="left",
        validate="one_to_one",
    )
    actual_success = merged["status"].eq("SUCCESS")
    predicted = merged["would_fetch_stockbit"].fillna(True).astype(bool)
    false_negative = int((~predicted & actual_success).sum())
    false_positive = int((predicted & ~actual_success).sum())

    observed_statuses = sorted(set(merged["status"].dropna().astype(str)))
    allowed = {"SUCCESS", "REQUEST_ERROR", "EMPTY_SESSION"}
    unexpected = tuple(value for value in observed_statuses if value not in allowed)

    non_404: list[str] = []
    if "errors" in merged.columns:
        for row in merged[merged["status"].eq("REQUEST_ERROR")].itertuples(index=False):
            errors = str(getattr(row, "errors", ""))
            if "HTTP_404" not in errors:
                non_404.append(str(row.ticker))

    eligible = bool(
        complete
        and merged["status"].notna().all()
        and not unexpected
        and not non_404
    )
    return ShadowMetrics(
        false_negative=false_negative,
        false_positive=false_positive,
        actual_success=int(actual_success.sum()),
        actual_non_success=int((~actual_success).sum()),
        unexpected_statuses=unexpected,
        non_404_request_errors=tuple(sorted(non_404)),
        certification_eligible=eligible,
    )


def update_policy_after_session(
    policy: dict[str, Any],
    *,
    run_mode: str,
    expected_date: date,
    complete: bool,
    metrics: ShadowMetrics | None,
    shadow_sessions_required: int,
    recheck_every: int,
    manifest_sha256: str | None,
) -> dict[str, Any]:
    updated = json.loads(json.dumps(policy))
    prior_mode = str(updated["mode"])
    reason = "INCOMPLETE_NO_TRANSITION"

    if complete and run_mode in {"SHADOW", "SHADOW_RECHECK"} and metrics is not None and metrics.certification_eligible:
        if metrics.false_negative == 0:
            if run_mode == "SHADOW":
                updated["consecutive_zero_fn_shadow_sessions"] = int(updated.get("consecutive_zero_fn_shadow_sessions") or 0) + 1
                if updated["consecutive_zero_fn_shadow_sessions"] >= shadow_sessions_required:
                    updated["mode"] = "ENFORCE"
                    updated["enforced_sessions_since_recheck"] = 0
                    reason = "SHADOW_PROMOTED_ZERO_FN"
                else:
                    reason = "SHADOW_ZERO_FN_PROGRESS"
            else:
                updated["mode"] = "ENFORCE"
                updated["enforced_sessions_since_recheck"] = 0
                reason = "PERIODIC_RECHECK_ZERO_FN"
        else:
            updated["mode"] = "SHADOW"
            updated["consecutive_zero_fn_shadow_sessions"] = 0
            updated["enforced_sessions_since_recheck"] = 0
            reason = "FALSE_NEGATIVE_REVERT_TO_SHADOW"
    elif complete and run_mode == "ENFORCE":
        updated["enforced_sessions_since_recheck"] = int(updated.get("enforced_sessions_since_recheck") or 0) + 1
        reason = "ENFORCE_SESSION_COMPLETE"
    elif complete and metrics is not None and not metrics.certification_eligible:
        if run_mode in {"SHADOW", "SHADOW_RECHECK"}:
            updated["mode"] = "SHADOW"
            updated["consecutive_zero_fn_shadow_sessions"] = 0
            updated["enforced_sessions_since_recheck"] = 0
        reason = "SHADOW_NOT_CERTIFICATION_ELIGIBLE"

    history = list(updated.get("history") or [])
    history.append(
        {
            "session_date": expected_date.isoformat(),
            "run_mode": run_mode,
            "prior_policy_mode": prior_mode,
            "new_policy_mode": updated["mode"],
            "reason": reason,
            "complete": bool(complete),
            "false_negative": None if metrics is None else metrics.false_negative,
            "false_positive": None if metrics is None else metrics.false_positive,
            "certification_eligible": None if metrics is None else metrics.certification_eligible,
            "manifest_sha256": manifest_sha256,
        }
    )
    updated["history"] = history[-100:]
    updated["shadow_sessions_required"] = shadow_sessions_required
    updated["recheck_every"] = recheck_every
    return updated


def run_daily(
    base_root: Path,
    *,
    expected_date: date,
    api_key: str,
    capture_after: str = DEFAULT_CAPTURE_AFTER,
    monthly_quota_reserve: int = DEFAULT_MONTHLY_QUOTA_RESERVE,
    max_new_tickers: int = DEFAULT_MAX_NEW_TICKERS,
    shadow_sessions_required: int = DEFAULT_SHADOW_SESSIONS,
    recheck_every: int = DEFAULT_RECHECK_EVERY,
    now: datetime | None = None,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    current = now or _now_jakarta()
    local = current.astimezone(JAKARTA)
    if expected_date != local.date():
        raise ValueError("recurring Stockbit today-only capture requires current Asia/Jakarta date")
    if local.weekday() >= 5:
        raise RuntimeError("recurring Stockbit capture is disabled on weekends")
    if capture_state(local, _parse_hhmm(capture_after), False) != "SESSION_COMPLETE_WINDOW":
        raise RuntimeError("recurring Stockbit capture is allowed only after the complete-session gate")
    if shadow_sessions_required <= 0 or recheck_every <= 0:
        raise ValueError("shadow/recheck thresholds must be positive")

    base_root.mkdir(parents=True, exist_ok=True)
    day_root = base_root / "sessions" / expected_date.isoformat()
    policy_path = base_root / "policy_state.json"
    policy = load_policy(policy_path)
    run_mode = _run_mode(policy, recheck_every=recheck_every)

    universe, metadata, universe_created = prepare_or_load_day(
        day_root,
        expected_date=expected_date,
        captured_at=local,
    )
    http = session or requests.Session()
    gate = prepare_traded_gate(
        day_root,
        universe,
        expected_date=expected_date,
        universe_sha=str(metadata["universe_snapshot_sha256"]),
        api_key=api_key,
        session=http,
    )

    gate_skips_written = 0
    if run_mode == "ENFORCE":
        gate_skips_written = apply_gate_skips(day_root, gate.decisions, expected_date=expected_date)

    farm_summary = run_farm(
        day_root,
        expected_date=expected_date,
        capture_after=capture_after,
        max_new_tickers=max_new_tickers,
        monthly_quota_reserve=monthly_quota_reserve,
        retry_errors=False,
        api_key=api_key,
        now=local,
        http=http,
    )

    status_path = day_root / "final" / "stockbit_intraday_ticker_status.csv"
    status_frame = pd.read_csv(status_path)
    complete = bool(farm_summary.get("complete")) and int(farm_summary.get("unfinished_tickers") or 0) == 0
    metrics: ShadowMetrics | None = None
    if run_mode in {"SHADOW", "SHADOW_RECHECK"}:
        metrics = shadow_metrics(gate.decisions, status_frame, complete=complete)

    manifest = _recursive_manifest(day_root)
    policy = update_policy_after_session(
        policy,
        run_mode=run_mode,
        expected_date=expected_date,
        complete=complete,
        metrics=metrics,
        shadow_sessions_required=shadow_sessions_required,
        recheck_every=recheck_every,
        manifest_sha256=manifest["manifest_sha256"],
    )
    _atomic_json(policy_path, policy)

    result = dict(farm_summary)
    result.update(
        {
            "daily_run_mode": run_mode,
            "policy_mode_after": policy["mode"],
            "consecutive_zero_fn_shadow_sessions": policy["consecutive_zero_fn_shadow_sessions"],
            "enforced_sessions_since_recheck": policy["enforced_sessions_since_recheck"],
            "universe_created_this_daily_run": universe_created,
            "idx_summary_call_made_this_run": gate.summary_call_made,
            "gate_summary_coverage": int(gate.decisions["idx_summary_present"].sum()),
            "gate_would_fetch_stockbit": int(gate.decisions["would_fetch_stockbit"].sum()),
            "gate_would_skip_no_activity": int((gate.decisions["gate_decision"] == "SKIP_NO_ACTIVITY").sum()),
            "gate_skips_written": gate_skips_written,
            "shadow_false_negative": None if metrics is None else metrics.false_negative,
            "shadow_false_positive": None if metrics is None else metrics.false_positive,
            "shadow_certification_eligible": None if metrics is None else metrics.certification_eligible,
            "gate_safe_headers": gate.safe_headers,
            "artifact_manifest_sha256": manifest["manifest_sha256"],
        }
    )
    _atomic_json(day_root / "final" / "run_summary.json", result)
    manifest = _recursive_manifest(day_root)
    result["artifact_manifest_sha256"] = manifest["manifest_sha256"]
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recurring policy-aware Stockbit intraday daily capture")
    parser.add_argument("--base-root", type=Path, required=True)
    parser.add_argument("--expected-date", type=date.fromisoformat, default=None)
    parser.add_argument("--capture-after", default=DEFAULT_CAPTURE_AFTER)
    parser.add_argument("--monthly-quota-reserve", type=int, default=DEFAULT_MONTHLY_QUOTA_RESERVE)
    parser.add_argument("--max-new-tickers", type=int, default=DEFAULT_MAX_NEW_TICKERS)
    parser.add_argument("--shadow-sessions-required", type=int, default=DEFAULT_SHADOW_SESSIONS)
    parser.add_argument("--recheck-every", type=int, default=DEFAULT_RECHECK_EVERY)
    parser.add_argument("--execute", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    now = _now_jakarta()
    expected_date = args.expected_date or now.astimezone(JAKARTA).date()
    if not args.execute:
        policy = load_policy(args.base_root / "policy_state.json")
        print(
            json.dumps(
                {
                    "mode": "DRY_RUN",
                    "expected_date": expected_date.isoformat(),
                    "day_root": str(args.base_root / "sessions" / expected_date.isoformat()),
                    "policy_mode": policy["mode"],
                    "next_run_mode": _run_mode(policy, recheck_every=args.recheck_every),
                    "monthly_quota_reserve": args.monthly_quota_reserve,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    api_key = os.environ.get("ZAPI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ZAPI_API_KEY is required for --execute")
    result = run_daily(
        args.base_root,
        expected_date=expected_date,
        api_key=api_key,
        capture_after=args.capture_after,
        monthly_quota_reserve=args.monthly_quota_reserve,
        max_new_tickers=args.max_new_tickers,
        shadow_sessions_required=args.shadow_sessions_required,
        recheck_every=args.recheck_every,
        now=now,
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
