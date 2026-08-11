from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

import pandas as pd

from .provenance import sha256_file
from .security_master import normalise_ticker


def ticker_list_sha256(tickers: list[str]) -> str:
    canonical = "\n".join(sorted(dict.fromkeys(normalise_ticker(t) for t in tickers))) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_security_master(path: Path) -> pd.DataFrame:
    suffix = path.suffix.casefold()
    if suffix in {".parquet", ".pq"}:
        frame = pd.read_parquet(path)
    elif suffix in {".csv", ".txt"}:
        frame = pd.read_csv(path)
    else:
        raise ValueError(f"unsupported security-master format: {path.suffix}")
    return frame


def active_common_stock_snapshot(
    security_master: pd.DataFrame,
    *,
    as_of_date: date,
    allowed_tickers: set[str] | None = None,
) -> pd.DataFrame:
    required = {"ticker", "listed_from", "listed_to"}
    missing = required - set(security_master.columns)
    if missing:
        raise ValueError(f"security master missing columns: {sorted(missing)}")

    data = security_master.copy()
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["listed_from"] = pd.to_datetime(data["listed_from"], errors="coerce").dt.normalize()
    data["listed_to"] = pd.to_datetime(data["listed_to"], errors="coerce").dt.normalize()
    as_of = pd.Timestamp(as_of_date).normalize()

    valid_ticker = data["ticker"].str.fullmatch(r"[A-Z0-9]{4}", na=False)
    active = data["listed_from"].notna() & data["listed_from"].le(as_of) & (
        data["listed_to"].isna() | data["listed_to"].ge(as_of)
    )
    data = data[valid_ticker & active].copy()

    if allowed_tickers is not None:
        allowed = {normalise_ticker(value) for value in allowed_tickers}
        data = data[data["ticker"].isin(allowed)].copy()

    if data.empty:
        raise ValueError("active common-stock snapshot is empty")

    # A ticker may have multiple historical listing intervals in the master.
    # At a single as-of date, fail closed if more than one interval is active.
    duplicated = data["ticker"].duplicated(keep=False)
    if duplicated.any():
        conflicts = data.loc[duplicated, ["ticker", "listed_from", "listed_to"]]
        raise ValueError(
            "multiple active listing intervals for ticker(s): "
            + ", ".join(sorted(conflicts["ticker"].unique())[:20])
        )

    keep = [column for column in ("ticker", "company_name", "listed_from", "listed_to", "source") if column in data.columns]
    result = data[keep].sort_values("ticker").reset_index(drop=True)
    result.insert(0, "as_of_date", as_of.date().isoformat())
    return result


def _load_allowed_tickers(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        frame = pd.read_csv(path)
        for column in ("ticker", "symbol", "code"):
            if column in frame.columns:
                return {normalise_ticker(value) for value in frame[column].dropna().tolist()}
        raise ValueError("allowed-tickers CSV needs ticker/symbol/code column")
    text = path.read_text(encoding="utf-8-sig")
    tokens = [token for token in text.replace(",", " ").replace(";", " ").split() if token]
    return {normalise_ticker(token) for token in tokens}


def freeze_universe_snapshot(
    security_master_path: Path,
    output_csv: Path,
    metadata_json: Path,
    *,
    as_of_date: date,
    allowed_tickers_path: Path | None = None,
) -> dict[str, object]:
    if output_csv.exists() or metadata_json.exists():
        raise FileExistsError("refusing to overwrite existing universe snapshot artifacts")

    master = load_security_master(security_master_path)
    allowed = _load_allowed_tickers(allowed_tickers_path)
    snapshot = active_common_stock_snapshot(master, as_of_date=as_of_date, allowed_tickers=allowed)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    snapshot.to_csv(output_csv, index=False, lineterminator="\n")
    tickers = snapshot["ticker"].astype(str).tolist()
    metadata: dict[str, object] = {
        "as_of_date": as_of_date.isoformat(),
        "ticker_count": len(tickers),
        "ticker_list_sha256": ticker_list_sha256(tickers),
        "security_master_path": str(security_master_path),
        "security_master_sha256": sha256_file(security_master_path),
        "allowed_tickers_path": str(allowed_tickers_path) if allowed_tickers_path else None,
        "allowed_tickers_sha256": sha256_file(allowed_tickers_path) if allowed_tickers_path else None,
        "snapshot_csv": str(output_csv),
        "snapshot_csv_sha256": sha256_file(output_csv),
    }
    metadata_json.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Freeze an as-of-date Stockbit intraday capture universe")
    parser.add_argument("--security-master", type=Path, required=True)
    parser.add_argument("--as-of-date", type=date.fromisoformat, required=True)
    parser.add_argument("--allowed-tickers", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--metadata-json", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    metadata = freeze_universe_snapshot(
        args.security_master,
        args.output_csv,
        args.metadata_json,
        as_of_date=args.as_of_date,
        allowed_tickers_path=args.allowed_tickers,
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
