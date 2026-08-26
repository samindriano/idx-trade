"""Causal security-master bootstrap for ephemeral cloud E2E POST_EOD runners.

The accepted clean scorer deliberately keeps a frozen historical identity
baseline while allowing only genuinely post-freeze listing identities from the
mutable canonical runtime master.  Local/Windows runtimes historically had
that runtime master on disk.  A fresh GitHub runner does not, so cloud POST_EOD
must materialize the mutable identity reference explicitly before the existing
canonical EOD engine starts.

This module uses only official IDX identity/reference endpoints.  It does not
read model targets, outcomes, paper state, or protected forward artifacts.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

import pandas as pd

from .forward_monitoring import runtime_paths
from .provenance import sha256_file, write_manifest_atomic
from .providers.idx import (
    IDX_DELISTING_URL,
    IDX_STOCK_LIST_URL,
    fetch_active_listings,
    fetch_delisted_listings,
)
from .security_master import SECURITY_COLUMNS, build_security_master, normalise_ticker
from .storage import write_csv_atomic


SCHEMA_VERSION = "idx_e2e_cloud_runtime_security_master_v1"
FREEZE_LOCAL_DATE = pd.Timestamp("2026-08-20")
JAKARTA = ZoneInfo("Asia/Jakarta")


class CloudSecurityMasterError(RuntimeError):
    pass


def _normalize_identity(frame: pd.DataFrame, *, label: str) -> pd.DataFrame:
    required = {"ticker", "listed_from", "listed_to"}
    missing = required - set(frame.columns)
    if missing:
        raise CloudSecurityMasterError(f"{label}_MISSING_COLUMNS:{sorted(missing)}")
    data = frame.copy()
    data["ticker"] = data["ticker"].map(normalise_ticker)
    data["listed_from"] = pd.to_datetime(data["listed_from"], errors="coerce").dt.normalize()
    data["listed_to"] = pd.to_datetime(data["listed_to"], errors="coerce").dt.normalize()
    if data["ticker"].eq("").any() or data["listed_from"].isna().any():
        raise CloudSecurityMasterError(f"{label}_INVALID_IDENTITY")
    if data["ticker"].duplicated().any():
        duplicates = sorted(data.loc[data["ticker"].duplicated(keep=False), "ticker"].unique())[:10]
        raise CloudSecurityMasterError(f"{label}_DUPLICATE_TICKER:{duplicates}")
    return data.sort_values("ticker", kind="mergesort").reset_index(drop=True)


def refresh_cloud_runtime_security_master(
    runtime_root: str | Path,
    *,
    baseline_master: str | Path,
    observed_at: datetime,
    active_fetcher: Callable[[], pd.DataFrame] = fetch_active_listings,
    delisted_fetcher: Callable[..., pd.DataFrame] = fetch_delisted_listings,
) -> dict[str, object]:
    """Refresh the mutable runtime listing reference from official IDX data.

    The frozen clean baseline is never rewritten.  It is used only as a
    completeness anchor: every security that was live at the model freeze must
    still be represented by either the current active listing response or the
    post-freeze delisting history.  Any identity absent from the baseline is
    admissible only when its official ``listed_from`` is strictly after the
    freeze date, matching the clean scorer's preregistered future-IPO rule.
    """

    if observed_at.tzinfo is None:
        raise CloudSecurityMasterError("RUNTIME_SECURITY_MASTER_CLOCK_NOT_TIMEZONE_AWARE")
    local_observed = observed_at.astimezone(JAKARTA)
    observed_date = pd.Timestamp(local_observed.date()).normalize()
    if observed_date < FREEZE_LOCAL_DATE:
        raise CloudSecurityMasterError("RUNTIME_SECURITY_MASTER_OBSERVED_BEFORE_FREEZE")

    baseline_path = Path(baseline_master).expanduser().resolve()
    if not baseline_path.is_file():
        raise CloudSecurityMasterError(f"RUNTIME_SECURITY_MASTER_BASELINE_MISSING:{baseline_path}")
    baseline = _normalize_identity(
        pd.read_csv(baseline_path),
        label="RUNTIME_SECURITY_MASTER_BASELINE",
    )

    active = active_fetcher()
    delisted = delisted_fetcher(FREEZE_LOCAL_DATE.year, end=local_observed.date())
    current = build_security_master(active, delisted)
    current = _normalize_identity(current, label="RUNTIME_SECURITY_MASTER_CURRENT")

    baseline_live_at_freeze = baseline[
        baseline["listed_from"].le(FREEZE_LOCAL_DATE)
        & (baseline["listed_to"].isna() | baseline["listed_to"].ge(FREEZE_LOCAL_DATE))
    ]
    current_tickers = set(current["ticker"])
    missing_live = sorted(set(baseline_live_at_freeze["ticker"]) - current_tickers)
    if missing_live:
        raise CloudSecurityMasterError(
            "RUNTIME_SECURITY_MASTER_BASELINE_LIVE_IDENTITY_MISSING:" + ",".join(missing_live[:20])
        )

    baseline_tickers = set(baseline["ticker"])
    additions = current.loc[~current["ticker"].isin(baseline_tickers)].copy()
    invalid_additions = additions[additions["listed_from"].le(FREEZE_LOCAL_DATE)]
    if not invalid_additions.empty:
        sample = invalid_additions.loc[:, ["ticker", "listed_from"]].copy()
        sample["listed_from"] = sample["listed_from"].dt.strftime("%Y-%m-%d")
        raise CloudSecurityMasterError(
            "RUNTIME_SECURITY_MASTER_PRE_FREEZE_EXTRA_IDENTITY:"
            + sample.head(20).to_json(orient="records")
        )

    # Preserve the canonical full schema produced by build_security_master.
    # Reindexing is defensive against accidental column-order drift.
    current_full = build_security_master(active, delisted).loc[:, list(SECURITY_COLUMNS)]
    output = runtime_paths(runtime_root).listings_root / "security_master.csv"
    write_csv_atomic(current_full, output)
    artifact_sha = sha256_file(output)

    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "authority": "IDX",
        "semantics": "CURRENT_LISTING_IDENTITY_REFERENCE_WITH_POST_FREEZE_DELISTING_HISTORY",
        "observed_at_jakarta": local_observed.isoformat(),
        "observed_date": observed_date.date().isoformat(),
        "freeze_local_date": FREEZE_LOCAL_DATE.date().isoformat(),
        "baseline_path": str(baseline_path),
        "baseline_sha256": sha256_file(baseline_path),
        "active_source": IDX_STOCK_LIST_URL,
        "delisting_source": IDX_DELISTING_URL,
        "delisting_start_year": int(FREEZE_LOCAL_DATE.year),
        "active_rows": int(len(active)),
        "delisted_rows": int(len(delisted)),
        "runtime_rows": int(len(current_full)),
        "post_freeze_new_tickers": sorted(additions["ticker"].astype(str).tolist()),
        "security_master_path": str(output.resolve()),
        "security_master_sha256": artifact_sha,
        "guards": {
            "outcome_accessed": False,
            "protected_forward_accessed": False,
            "model_refit": False,
            "paper_state_mutated": False,
            "retroactive_capture_authorized": False,
        },
    }
    manifest_path = output.with_name("security_master_refresh_manifest.json")
    write_manifest_atomic(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path.resolve())
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    return manifest
