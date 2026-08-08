from __future__ import annotations

import json
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pandas as pd

from .providers.idx_tradability import (
    compile_suspension_intervals,
    fetch_pdf_text,
    ingest_announcement_manifest,
)


def ingestion_integrity_report(
    parse_diagnostics: pd.DataFrame,
    compile_diagnostics: pd.DataFrame,
) -> dict[str, object]:
    """Audit parser/compiler integrity without claiming source completeness.

    A clean report means every supplied document was machine-resolved and its
    event sequence was internally coherent. It does NOT prove that every IDX
    suspension announcement in the research period has been discovered.
    """

    if parse_diagnostics.empty:
        unresolved_parse = pd.DataFrame()
        status_counts: dict[str, int] = {}
    else:
        statuses = parse_diagnostics["status"].astype(str)
        unresolved_parse = parse_diagnostics[~statuses.eq("PARSED")]
        status_counts = {str(key): int(value) for key, value in statuses.value_counts().items()}

    compile_issue_count = int(len(compile_diagnostics))
    passed = bool(len(parse_diagnostics)) and unresolved_parse.empty and compile_issue_count == 0
    return {
        "passed": passed,
        "manifest_rows": int(len(parse_diagnostics)),
        "parse_status_counts": status_counts,
        "unresolved_parse_rows": int(len(unresolved_parse)),
        "compile_issue_rows": compile_issue_count,
        "coverage_complete": False,
        "coverage_note": (
            "Ingestion integrity never implies historical discovery completeness. "
            "Create a complete tradability coverage window only after source-discovery audit."
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
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def run_tradability_ingestion(
    manifest_path: str | Path,
    output_dir: str | Path,
    *,
    fetcher: Callable[[str], tuple[str, str]] = fetch_pdf_text,
) -> dict[str, object]:
    """Ingest an auditable IDX announcement manifest and persist raw outcomes.

    The function intentionally writes diagnostics even when the integrity gate
    fails, so ambiguous documents can be reviewed without mutating historical
    coverage assumptions.
    """

    manifest_path = Path(manifest_path)
    output_dir = Path(output_dir)
    manifest = pd.read_csv(manifest_path)
    events, parse_diagnostics = ingest_announcement_manifest(manifest, fetcher=fetcher)
    intervals, compile_diagnostics = compile_suspension_intervals(events)
    report = ingestion_integrity_report(parse_diagnostics, compile_diagnostics)
    report.update(
        {
            "manifest_path": str(manifest_path),
            "event_rows": int(len(events)),
            "interval_rows": int(len(intervals)),
        }
    )

    _atomic_csv(events, output_dir / "tradability_events.csv")
    _atomic_csv(parse_diagnostics, output_dir / "tradability_parse_diagnostics.csv")
    _atomic_csv(intervals, output_dir / "tradability_intervals.csv")
    _atomic_csv(compile_diagnostics, output_dir / "tradability_compile_diagnostics.csv")
    _atomic_json(report, output_dir / "tradability_ingestion_report.json")
    return report
