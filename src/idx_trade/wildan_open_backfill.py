from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .provenance import sha256_file
from .secondary_open_witness import cross_validate_secondary_open_witness
from .storage import write_parquet_atomic


WILDAN_SOURCE_ID = "WILDAN_IDX_ARCHIVE"
WILDAN_REPOSITORY = "https://github.com/wildangunawan/Dataset-Saham-IDX"
WILDAN_DATA_SUBDIR = Path("Saham") / "Semua"


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    frame.to_csv(temp, index=False)
    temp.replace(path)


def _atomic_json(value: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.stem}.{uuid4().hex}.tmp{path.suffix}")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temp.replace(path)


def _normalise_ticker(value: object) -> str:
    return str(value).upper().replace(".JK", "").strip()


def _normalise_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.tz_localize(None).dt.normalize()


def read_wildan_archive_info(root: str | Path) -> dict[str, object]:
    """Read repository metadata, but never use it as a hard coverage boundary.

    The public repository currently contains rows later than the date recorded in
    ``info.json``. Coverage is therefore measured from the actual pinned CSV
    snapshot, while ``info.json`` is retained as provenance metadata only.
    """

    info_path = Path(root) / "info.json"
    if not info_path.is_file():
        return {}
    value = json.loads(info_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Wildan archive info.json must contain an object")
    return value


def parse_wildan_stock_csv(
    path: str | Path,
    *,
    ticker: str,
    source_commit: str,
) -> pd.DataFrame:
    """Parse one existing Wildan/IDX-derived CSV into secondary OHLC evidence."""

    data = pd.read_csv(Path(path))
    data.columns = [str(column).strip().casefold() for column in data.columns]
    aliases = {
        "date": "date",
        "openprice": "secondary_open",
        "open_price": "secondary_open",
        "high": "secondary_high",
        "low": "secondary_low",
        "close": "secondary_close",
    }
    data = data.rename(columns={column: aliases.get(column, column) for column in data.columns})
    required = {"date", "secondary_open", "secondary_high", "secondary_low", "secondary_close"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Wildan CSV columns missing for {ticker}: {sorted(missing)}")

    result = data[["date", "secondary_open", "secondary_high", "secondary_low", "secondary_close"]].copy()
    result["ticker"] = _normalise_ticker(ticker)
    result["date"] = _normalise_date(result["date"])
    for column in ("secondary_open", "secondary_high", "secondary_low", "secondary_close"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    commit = str(source_commit).strip()
    result["secondary_source_ref"] = (
        f"{WILDAN_REPOSITORY}@{commit}:{WILDAN_DATA_SUBDIR.as_posix()}/{_normalise_ticker(ticker)}.csv"
    )
    return (
        result.dropna(subset=["date"])
        .sort_values("date")
        .drop_duplicates(["ticker", "date"], keep="last")
        .reset_index(drop=True)
    )


def load_wildan_archive(
    root: str | Path,
    tickers: list[str] | tuple[str, ...] | set[str],
    *,
    source_commit: str,
    start: object | None = None,
    end: object | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load requested ticker files from a pinned local clone of the public archive."""

    data_root = Path(root) / WILDAN_DATA_SUBDIR
    if not data_root.is_dir():
        raise FileNotFoundError(f"Wildan archive data directory missing: {data_root}")
    commit = str(source_commit).strip()
    if not commit:
        raise ValueError("source_commit is required to pin external provenance")

    lower = pd.Timestamp(start).normalize() if start is not None else None
    upper = pd.Timestamp(end).normalize() if end is not None else None
    frames: list[pd.DataFrame] = []
    coverage: list[dict[str, object]] = []
    for raw_ticker in sorted({_normalise_ticker(value) for value in tickers}):
        path = data_root / f"{raw_ticker}.csv"
        if not path.is_file():
            coverage.append(
                {
                    "ticker": raw_ticker,
                    "status": "FILE_MISSING",
                    "rows": 0,
                    "first_date": None,
                    "last_date": None,
                }
            )
            continue
        parsed = parse_wildan_stock_csv(path, ticker=raw_ticker, source_commit=commit)
        if lower is not None:
            parsed = parsed[parsed["date"].ge(lower)]
        if upper is not None:
            parsed = parsed[parsed["date"].le(upper)]
        parsed = parsed.reset_index(drop=True)
        if not parsed.empty:
            frames.append(parsed)
        coverage.append(
            {
                "ticker": raw_ticker,
                "status": "OK" if not parsed.empty else "NO_ROWS_IN_WINDOW",
                "rows": int(len(parsed)),
                "first_date": parsed["date"].min() if not parsed.empty else None,
                "last_date": parsed["date"].max() if not parsed.empty else None,
            }
        )
    secondary = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(
            columns=[
                "ticker",
                "date",
                "secondary_open",
                "secondary_high",
                "secondary_low",
                "secondary_close",
                "secondary_source_ref",
            ]
        )
    )
    return secondary, pd.DataFrame(coverage)


def _prepare_panel(panel: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "date", "open", "high", "low", "close", "volume"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"Signal panel columns missing: {sorted(missing)}")
    data = panel.copy()
    data["ticker"] = data["ticker"].map(_normalise_ticker)
    data["date"] = _normalise_date(data["date"])
    if data["date"].isna().any() or data.duplicated(["ticker", "date"]).any():
        raise ValueError("Signal panel has invalid or duplicate ticker/date rows")
    for column in ("open", "high", "low", "close", "volume"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    return data


def official_missing_open_evidence(panel: pd.DataFrame) -> pd.DataFrame:
    data = _prepare_panel(panel)
    missing_open = data["open"].isna() | data["open"].le(0)
    targets = data.loc[missing_open, ["ticker", "date", "high", "low", "close", "volume"]].copy()
    targets = targets.rename(
        columns={
            "high": "official_high",
            "low": "official_low",
            "close": "official_close",
            "volume": "official_volume",
        }
    )
    if "price_provenance" in data.columns:
        source_map = data.loc[missing_open, ["ticker", "date", "price_provenance"]].copy()
        source_map = source_map.rename(columns={"price_provenance": "official_source_ref"})
        targets = targets.merge(source_map, on=["ticker", "date"], how="left", validate="one_to_one")
    else:
        targets["official_source_ref"] = "IMMUTABLE_SIGNAL_RESEARCH_PANEL"
    targets["official_source_ref"] = (
        targets["official_source_ref"].fillna("IMMUTABLE_SIGNAL_RESEARCH_PANEL").astype(str)
    )
    return targets


def audit_existing_open_overlap(panel: pd.DataFrame, secondary: pd.DataFrame) -> pd.DataFrame:
    """Known-answer audit against rows whose Open already exists in the panel."""

    data = _prepare_panel(panel)
    existing = data[data["open"].gt(0)][["ticker", "date", "open", "high", "low", "close"]].copy()
    if existing.empty or secondary.empty:
        return pd.DataFrame(
            columns=[
                "ticker",
                "date",
                "hlc_exact",
                "open_exact",
                "panel_open",
                "secondary_open",
                "secondary_source_ref",
            ]
        )
    merged = existing.merge(secondary, on=["ticker", "date"], how="inner", validate="one_to_one")
    if merged.empty:
        return pd.DataFrame(
            columns=[
                "ticker",
                "date",
                "hlc_exact",
                "open_exact",
                "panel_open",
                "secondary_open",
                "secondary_source_ref",
            ]
        )
    merged["hlc_exact"] = (
        merged["high"].eq(merged["secondary_high"])
        & merged["low"].eq(merged["secondary_low"])
        & merged["close"].eq(merged["secondary_close"])
    )
    merged["open_exact"] = merged["open"].eq(merged["secondary_open"])
    return merged[
        ["ticker", "date", "hlc_exact", "open_exact", "open", "secondary_open", "secondary_source_ref"]
    ].rename(columns={"open": "panel_open"})


def apply_accepted_open_backfill(
    panel: pd.DataFrame,
    accepted: pd.DataFrame,
    *,
    source_commit: str,
) -> pd.DataFrame:
    """Fill null Open only. Existing Open/H/L/C/V rows are never overwritten."""

    data = _prepare_panel(panel)
    existing = data["open"].notna() & data["open"].gt(0)
    data["open_source"] = existing.map({True: "EXISTING_PANEL", False: "UNRESOLVED"})
    if "open_evidence_status" in data.columns:
        data["open_source_ref"] = data["open_evidence_status"].where(existing, pd.NA)
    else:
        data["open_source_ref"] = existing.map({True: "EXISTING_PANEL", False: pd.NA})
    data["open_source_commit"] = pd.NA
    data["open_validation_status"] = existing.map(
        {True: "EXISTING_OPEN_PRESERVED", False: "UNRESOLVED"}
    )
    if accepted.empty:
        return data

    fill = accepted[["ticker", "date", "raw_open", "secondary_open_source_ref"]].copy()
    fill = fill.rename(columns={"raw_open": "candidate_open"})
    merged = data.merge(fill, on=["ticker", "date"], how="left", validate="one_to_one")
    eligible = merged["open"].isna() & merged["candidate_open"].gt(0)
    merged.loc[eligible, "open"] = merged.loc[eligible, "candidate_open"]
    if "open_available" in merged.columns:
        merged.loc[eligible, "open_available"] = True
    if "open_evidence_status" in merged.columns:
        merged.loc[eligible, "open_evidence_status"] = "WILDAN_IDX_ARCHIVE_OPEN_OPTIONAL"
    merged.loc[eligible, "open_source"] = WILDAN_SOURCE_ID
    merged.loc[eligible, "open_source_ref"] = merged.loc[eligible, "secondary_open_source_ref"]
    merged.loc[eligible, "open_source_commit"] = str(source_commit).strip()
    merged.loc[eligible, "open_validation_status"] = "HLC_EXACT_AND_OPEN_IN_RANGE"
    return merged.drop(columns=["candidate_open", "secondary_open_source_ref"])


def run_wildan_open_backfill(
    *,
    panel_path: str | Path,
    wildan_root: str | Path,
    source_commit: str,
    output_dir: str | Path,
    expected_panel_sha256: str | None = None,
) -> dict[str, object]:
    """Build a derivative panel from exact-HLC cross-validated archive Open rows."""

    panel_file = Path(panel_path)
    if not panel_file.is_file():
        raise FileNotFoundError(panel_file)
    panel_sha = sha256_file(panel_file)
    if expected_panel_sha256 and panel_sha != str(expected_panel_sha256).strip():
        raise RuntimeError(f"Panel SHA mismatch: {panel_sha}")

    panel = _prepare_panel(pd.read_parquet(panel_file))
    archive_info = read_wildan_archive_info(wildan_root)
    secondary, coverage = load_wildan_archive(
        wildan_root,
        set(panel["ticker"]),
        source_commit=source_commit,
        start=panel["date"].min(),
        end=panel["date"].max(),
    )
    overlap = audit_existing_open_overlap(panel, secondary)
    official_targets = official_missing_open_evidence(panel)
    candidate_for_targets = secondary.merge(
        official_targets[["ticker", "date"]],
        on=["ticker", "date"],
        how="inner",
        validate="one_to_one",
    )
    accepted, diagnostics = cross_validate_secondary_open_witness(
        official_targets,
        candidate_for_targets,
    )
    derivative = apply_accepted_open_backfill(panel, accepted, source_commit=source_commit)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    panel_output = output / "execution_open_backfill_wildan_v1.parquet"
    coverage_output = output / "wildan_source_coverage.csv"
    overlap_output = output / "wildan_existing_open_overlap_audit.csv"
    diagnostics_output = output / "wildan_open_backfill_diagnostics.csv"
    summary_output = output / "wildan_open_backfill_summary.json"

    write_parquet_atomic(derivative, panel_output)
    _atomic_csv(coverage, coverage_output)
    _atomic_csv(overlap, overlap_output)
    _atomic_csv(diagnostics, diagnostics_output)

    initial_null = int(panel["open"].isna().sum())
    final_null = int(derivative["open"].isna().sum())
    overlap_rows = int(len(overlap))
    hlc_exact_rows = int(overlap["hlc_exact"].sum()) if overlap_rows else 0
    open_exact_rows = int(overlap["open_exact"].sum()) if overlap_rows else 0
    observed_last_date = secondary["date"].max() if not secondary.empty else pd.NaT
    info_last_update = str(archive_info.get("last_update", "")).strip() or None
    summary: dict[str, object] = {
        "status": "WILDAN_BACKFILL_COMPLETE",
        "input_panel": str(panel_file),
        "input_panel_sha256": panel_sha,
        "source_id": WILDAN_SOURCE_ID,
        "source_repository": WILDAN_REPOSITORY,
        "source_commit": str(source_commit).strip(),
        "source_info_last_update": info_last_update,
        "source_observed_last_date": (
            pd.Timestamp(observed_last_date).date().isoformat() if pd.notna(observed_last_date) else None
        ),
        "input_rows": int(len(panel)),
        "input_tickers": int(panel["ticker"].nunique()),
        "initial_null_open_rows": initial_null,
        "source_rows_in_window": int(len(secondary)),
        "source_tickers_with_rows": int(secondary["ticker"].nunique()) if not secondary.empty else 0,
        "source_files_missing": int(coverage["status"].eq("FILE_MISSING").sum()) if not coverage.empty else 0,
        "known_open_overlap_rows": overlap_rows,
        "known_open_overlap_hlc_exact_rows": hlc_exact_rows,
        "known_open_overlap_hlc_exact_rate": float(hlc_exact_rows / overlap_rows) if overlap_rows else None,
        "known_open_overlap_open_exact_rows": open_exact_rows,
        "known_open_overlap_open_exact_rate": float(open_exact_rows / overlap_rows) if overlap_rows else None,
        "missing_open_target_rows": int(len(official_targets)),
        "source_candidate_target_rows": int(len(candidate_for_targets)),
        "accepted_backfill_rows": int(len(accepted)),
        "rejected_or_unresolved_target_rows": (
            int(len(diagnostics) - diagnostics["status"].eq("ACCEPTED").sum())
            if not diagnostics.empty
            else int(len(official_targets))
        ),
        "final_null_open_rows": final_null,
        "filled_open_rows": initial_null - final_null,
        "remaining_null_open_percentage": (
            float(final_null / len(derivative) * 100.0) if len(derivative) else None
        ),
        "execution_grade_promoted": False,
        "note": (
            "Derivative only. Strict execution-grade certification requires separate review of "
            "coverage/provenance and any remaining Open gaps."
        ),
    }
    summary["output_sha256"] = {
        panel_output.name: sha256_file(panel_output),
        coverage_output.name: sha256_file(coverage_output),
        overlap_output.name: sha256_file(overlap_output),
        diagnostics_output.name: sha256_file(diagnostics_output),
    }
    _atomic_json(summary, summary_output)
    returned = dict(summary)
    returned["summary_sha256"] = sha256_file(summary_output)
    return returned


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-validated Wildan/IDX archive Open backfill")
    parser.add_argument("--panel", required=True)
    parser.add_argument("--wildan-root", required=True)
    parser.add_argument("--wildan-commit", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-panel-sha256")
    return parser


def main() -> None:
    args = _parser().parse_args()
    summary = run_wildan_open_backfill(
        panel_path=args.panel,
        wildan_root=args.wildan_root,
        source_commit=args.wildan_commit,
        output_dir=args.output_dir,
        expected_panel_sha256=args.expected_panel_sha256,
    )
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
