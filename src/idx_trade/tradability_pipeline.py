from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Mapping
from uuid import uuid4

import pandas as pd

from .providers.idx_tradability import (
    compile_suspension_intervals,
    fetch_pdf_text,
    ingest_announcement_manifest,
)
from .security_master import canonicalize_coverage_windows, normalise_market
from .tradability_anchor_reconstruction import (
    ANCHOR_DIAGNOSTIC_COLUMNS,
    reconcile_boundary_suspension_anchors,
)


def _window_date(value: object) -> pd.Timestamp | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed).normalize()


def _public_window_from_evidence(
    evidence: Mapping[str, object] | None,
) -> tuple[dict[str, object] | None, str]:
    """Return one exact event-discovery window only when evidence is explicit."""

    if evidence is None:
        return None, "PUBLIC_WINDOW_NOT_PROVEN_DISCOVERY_OR_BOUNDARY"
    if evidence.get("discovery_complete") is not True:
        return None, "PUBLIC_DISCOVERY_COMPLETENESS_UNCONFIRMED"

    required_text = ("source", "discovery_basis", "left_boundary_basis")
    if any(not str(evidence.get(key, "")).strip() for key in required_text):
        return None, "PUBLIC_WINDOW_MISSING_DISCOVERY_OR_BOUNDARY_BASIS"

    effective_from = _window_date(evidence.get("effective_from"))
    effective_to = _window_date(evidence.get("effective_to"))
    if effective_from is None or effective_to is None:
        return None, "PUBLIC_WINDOW_REQUIRES_EXPLICIT_BOTH_BOUNDARIES"
    if effective_to < effective_from:
        return None, "PUBLIC_WINDOW_BOUNDARIES_INVALID"

    try:
        market = normalise_market(evidence.get("market", "REGULAR"))
    except ValueError:
        return None, "PUBLIC_WINDOW_MARKET_INVALID"

    return {
        "market": market,
        "effective_from": effective_from.date().isoformat(),
        "effective_to": effective_to.date().isoformat(),
        "source": str(evidence["source"]).strip(),
        "is_complete": True,
        "discovery_basis": str(evidence["discovery_basis"]).strip(),
        "left_boundary_basis": str(evidence["left_boundary_basis"]).strip(),
    }, "OK"


def ingestion_integrity_report(
    parse_diagnostics: pd.DataFrame,
    compile_diagnostics: pd.DataFrame,
    *,
    coverage_evidence: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Audit parser/compiler integrity without inventing per-ticker state."""

    if parse_diagnostics.empty:
        unresolved_parse = pd.DataFrame()
        status_counts: dict[str, int] = {}
    else:
        statuses = parse_diagnostics["status"].astype(str)
        unresolved_parse = parse_diagnostics[~statuses.eq("PARSED")]
        status_counts = {str(key): int(value) for key, value in statuses.value_counts().items()}

    compile_issue_count = int(len(compile_diagnostics))
    passed = bool(len(parse_diagnostics)) and unresolved_parse.empty and compile_issue_count == 0
    if compile_diagnostics.empty or "status" not in compile_diagnostics.columns:
        compile_status_counts: dict[str, int] = {}
    else:
        compile_statuses = compile_diagnostics["status"].astype(str)
        compile_status_counts = {
            str(key): int(value) for key, value in compile_statuses.value_counts().items()
        }

    candidate_window, window_diagnostic = _public_window_from_evidence(coverage_evidence)
    coverage_complete = bool(passed and candidate_window is not None)
    if not passed:
        window_diagnostic = "INGESTION_INTEGRITY_FAILED"

    return {
        "passed": passed,
        "manifest_rows": int(len(parse_diagnostics)),
        "parse_status_counts": status_counts,
        "unresolved_parse_rows": int(len(unresolved_parse)),
        "compile_issue_rows": compile_issue_count,
        "compile_status_counts": compile_status_counts,
        "coverage_complete": coverage_complete,
        "coverage_window": candidate_window if coverage_complete else None,
        "coverage_diagnostic": window_diagnostic,
        "coverage_note": (
            "Ingestion integrity and event-source completeness are separate from "
            "per-security tradability state. A complete discovery window still "
            "requires authoritative ticker anchors before ACTIVE complements can "
            "be inferred."
        ),
    }


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def _atomic_json(value: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temporary.replace(path)


def run_tradability_ingestion(
    manifest_path: str | Path,
    output_dir: str | Path,
    *,
    fetcher: Callable[[str], tuple[str, str]] = fetch_pdf_text,
    coverage_evidence: Mapping[str, object] | None = None,
    tradability_anchors: pd.DataFrame | None = None,
) -> dict[str, object]:
    """Ingest announcements and optionally reconcile boundary state anchors."""

    manifest_path = Path(manifest_path)
    output_dir = Path(output_dir)
    manifest = pd.read_csv(manifest_path)
    events, parse_diagnostics = ingest_announcement_manifest(manifest, fetcher=fetcher)
    intervals, compile_diagnostics = compile_suspension_intervals(events)

    anchor_diagnostics = pd.DataFrame(columns=ANCHOR_DIAGNOSTIC_COLUMNS)
    candidate_window, _ = _public_window_from_evidence(coverage_evidence)
    if tradability_anchors is not None and candidate_window is not None:
        discovery_windows = canonicalize_coverage_windows(
            pd.DataFrame([candidate_window])
        )
        intervals, compile_diagnostics, anchor_diagnostics = (
            reconcile_boundary_suspension_anchors(
                events,
                intervals,
                compile_diagnostics,
                tradability_anchors,
                discovery_windows,
            )
        )

    report = ingestion_integrity_report(
        parse_diagnostics,
        compile_diagnostics,
        coverage_evidence=coverage_evidence,
    )
    if anchor_diagnostics.empty:
        anchor_status_counts: dict[str, int] = {}
    else:
        anchor_status_counts = {
            str(key): int(value)
            for key, value in anchor_diagnostics["status"].value_counts().items()
        }
    report.update(
        {
            "manifest_path": str(manifest_path),
            "event_rows": int(len(events)),
            "interval_rows": int(len(intervals)),
            "anchor_diagnostic_rows": int(len(anchor_diagnostics)),
            "anchor_status_counts": anchor_status_counts,
        }
    )

    _atomic_csv(events, output_dir / "tradability_events.csv")
    _atomic_csv(parse_diagnostics, output_dir / "tradability_parse_diagnostics.csv")
    _atomic_csv(intervals, output_dir / "tradability_intervals.csv")
    _atomic_csv(compile_diagnostics, output_dir / "tradability_compile_diagnostics.csv")
    _atomic_csv(anchor_diagnostics, output_dir / "tradability_anchor_diagnostics.csv")
    _atomic_json(report, output_dir / "tradability_ingestion_report.json")
    return report
