from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from idx_trade.e2e_cloud_security_master_v1 import (
    CloudSecurityMasterError,
    refresh_cloud_runtime_security_master,
)
from idx_trade.forward_monitoring import _load_security_master, runtime_paths
from idx_trade.security_master import SECURITY_COLUMNS


JAKARTA = ZoneInfo("Asia/Jakarta")


def _write_baseline(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False, lineterminator="\n")


def _active(rows: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": ticker,
                "company_name": ticker,
                "listed_from": listed_from,
                "listed_to": pd.NaT,
                "source": "IDX_STOCK_LIST",
            }
            for ticker, listed_from in rows
        ]
    )


def _delisted(rows: list[tuple[str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": ticker,
                "company_name": ticker,
                "listed_from": listed_from,
                "listed_to": listed_to,
                "source": "IDX_DIGITAL_STATISTIC_DELISTING",
            }
            for ticker, listed_from, listed_to in rows
        ],
        columns=["ticker", "company_name", "listed_from", "listed_to", "source"],
    )


def test_fresh_cloud_bootstrap_satisfies_exact_canonical_eod_discovery_boundary(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.csv"
    _write_baseline(
        baseline,
        [{"ticker": "AAAA", "listed_from": "2020-01-01", "listed_to": ""}],
    )
    calls: dict[str, object] = {}

    def delisted_fetcher(start_year: int, *, end) -> pd.DataFrame:
        calls["start_year"] = start_year
        calls["end"] = end
        return _delisted([])

    runtime_root = tmp_path / "runtime"
    result = refresh_cloud_runtime_security_master(
        runtime_root,
        baseline_master=baseline,
        observed_at=datetime(2026, 8, 26, 18, 35, tzinfo=JAKARTA),
        active_fetcher=lambda: _active([("AAAA", "2020-01-01"), ("NEWW", "2026-08-21")]),
        delisted_fetcher=delisted_fetcher,
    )

    output = Path(str(result["security_master_path"]))
    manifest = Path(str(result["manifest_path"]))
    frame = pd.read_csv(output)
    assert list(frame.columns) == list(SECURITY_COLUMNS)
    assert set(frame["ticker"]) == {"AAAA", "NEWW"}

    # This is the exact loader that raised in genuine scheduled run 32966156577.
    loaded = _load_security_master(runtime_paths(runtime_root))
    assert set(loaded["ticker"]) == {"AAAA", "NEWW"}

    assert result["post_freeze_new_tickers"] == ["NEWW"]
    assert result["guards"]["outcome_accessed"] is False
    assert manifest.is_file()
    assert calls == {"start_year": 2026, "end": datetime(2026, 8, 26).date()}


def test_refresh_preserves_baseline_live_identity_missing_from_current_active(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.csv"
    _write_baseline(
        baseline,
        [{"ticker": "AAAA", "listed_from": "2020-01-01", "listed_to": ""}],
    )
    result = refresh_cloud_runtime_security_master(
        tmp_path / "runtime",
        baseline_master=baseline,
        observed_at=datetime(2026, 8, 26, 18, 35, tzinfo=JAKARTA),
        active_fetcher=lambda: _active([("NEWW", "2026-08-21")]),
        delisted_fetcher=lambda *args, **kwargs: _delisted([]),
    )
    frame = pd.read_csv(Path(str(result["security_master_path"])))
    preserved = frame.loc[frame["ticker"].eq("AAAA")].iloc[0]
    assert set(frame["ticker"]) == {"AAAA", "NEWW"}
    assert preserved["source"] == "IDX_FROZEN_BASELINE_IDENTITY_CONTINUITY"
    assert result["baseline_identities_preserved_not_in_current_active"] == ["AAAA"]


def test_refresh_rejects_malformed_unknown_source_identity(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.csv"
    _write_baseline(
        baseline,
        [{"ticker": "AAAA", "listed_from": "2020-01-01", "listed_to": ""}],
    )
    with pytest.raises(CloudSecurityMasterError, match="ACTIVE_INVALID_IDENTITY"):
        refresh_cloud_runtime_security_master(
            tmp_path / "runtime",
            baseline_master=baseline,
            observed_at=datetime(2026, 8, 26, 18, 35, tzinfo=JAKARTA),
            active_fetcher=lambda: _active([("AAAA", "2020-01-01"), ("BOGUS", "2026-08-21")]),
            delisted_fetcher=lambda *args, **kwargs: _delisted([]),
        )


def test_refresh_rejects_source_listing_after_observation(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.csv"
    _write_baseline(
        baseline,
        [{"ticker": "AAAA", "listed_from": "2020-01-01", "listed_to": ""}],
    )
    with pytest.raises(CloudSecurityMasterError, match="LISTING_AFTER_OBSERVED_DATE"):
        refresh_cloud_runtime_security_master(
            tmp_path / "runtime",
            baseline_master=baseline,
            observed_at=datetime(2026, 8, 26, 18, 35, tzinfo=JAKARTA),
            active_fetcher=lambda: _active([("AAAA", "2020-01-01"), ("NEWW", "2026-08-27")]),
            delisted_fetcher=lambda *args, **kwargs: _delisted([]),
        )


def test_refresh_rejects_baseline_and_current_listing_identity_conflict(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.csv"
    _write_baseline(
        baseline,
        [{"ticker": "AAAA", "listed_from": "2020-01-01", "listed_to": ""}],
    )
    with pytest.raises(CloudSecurityMasterError, match="BASELINE_IDENTITY_CONFLICT:AAAA"):
        refresh_cloud_runtime_security_master(
            tmp_path / "runtime",
            baseline_master=baseline,
            observed_at=datetime(2026, 8, 26, 18, 35, tzinfo=JAKARTA),
            active_fetcher=lambda: _active([("AAAA", "2021-01-01")]),
            delisted_fetcher=lambda *args, **kwargs: _delisted([]),
        )


def test_refresh_does_not_require_baseline_identity_ended_before_observation(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.csv"
    _write_baseline(
        baseline,
        [{"ticker": "OLDX", "listed_from": "2020-01-01", "listed_to": "2026-08-25"}],
    )
    result = refresh_cloud_runtime_security_master(
        tmp_path / "runtime",
        baseline_master=baseline,
        observed_at=datetime(2026, 8, 26, 18, 35, tzinfo=JAKARTA),
        active_fetcher=lambda: _active([("NEWW", "2026-08-21")]),
        delisted_fetcher=lambda *args, **kwargs: _delisted([]),
    )
    frame = pd.read_csv(Path(str(result["security_master_path"])))
    assert set(frame["ticker"]) == {"NEWW"}
    assert result["baseline_identities_preserved_not_in_current_active"] == []


def test_refresh_rejects_duplicate_current_identity_before_build_deduplicates(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.csv"
    _write_baseline(
        baseline,
        [{"ticker": "AAAA", "listed_from": "2020-01-01", "listed_to": ""}],
    )
    with pytest.raises(CloudSecurityMasterError, match="ACTIVE_DUPLICATE_TICKER"):
        refresh_cloud_runtime_security_master(
            tmp_path / "runtime",
            baseline_master=baseline,
            observed_at=datetime(2026, 8, 26, 18, 35, tzinfo=JAKARTA),
            active_fetcher=lambda: _active(
                [("AAAA", "2020-01-01"), ("AAAA", "2020-01-01")]
            ),
            delisted_fetcher=lambda *args, **kwargs: _delisted([]),
        )


def test_refresh_rejects_invalid_identity_interval(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.csv"
    _write_baseline(
        baseline,
        [{"ticker": "AAAA", "listed_from": "2020-01-01", "listed_to": ""}],
    )
    with pytest.raises(CloudSecurityMasterError, match="ACTIVE_INVALID_LISTING_INTERVAL"):
        refresh_cloud_runtime_security_master(
            tmp_path / "runtime",
            baseline_master=baseline,
            observed_at=datetime(2026, 8, 26, 18, 35, tzinfo=JAKARTA),
            active_fetcher=lambda: _active([("AAAA", "2021-01-01")]).assign(
                listed_to=pd.to_datetime(["2020-01-01"])
            ),
            delisted_fetcher=lambda *args, **kwargs: _delisted([]),
        )


def test_refresh_is_deterministic_on_restart_with_same_source_inputs(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.csv"
    _write_baseline(
        baseline,
        [{"ticker": "AAAA", "listed_from": "2020-01-01", "listed_to": ""}],
    )
    kwargs = {
        "baseline_master": baseline,
        "observed_at": datetime(2026, 8, 26, 18, 35, tzinfo=JAKARTA),
        "active_fetcher": lambda: _active([("AAAA", "2020-01-01"), ("NEWW", "2026-08-21")]),
        "delisted_fetcher": lambda *args, **kwargs: _delisted([]),
    }
    first = refresh_cloud_runtime_security_master(tmp_path / "runtime", **kwargs)
    first_bytes = Path(str(first["security_master_path"])).read_bytes()
    second = refresh_cloud_runtime_security_master(tmp_path / "runtime", **kwargs)
    second_bytes = Path(str(second["security_master_path"])).read_bytes()
    assert first_bytes == second_bytes
    assert first["security_master_sha256"] == second["security_master_sha256"]
    assert first["baseline_identities_preserved_not_in_current_active"] == []


def test_refresh_rejects_identity_absent_from_baseline_if_not_strictly_post_freeze(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.csv"
    _write_baseline(
        baseline,
        [{"ticker": "AAAA", "listed_from": "2020-01-01", "listed_to": ""}],
    )
    with pytest.raises(CloudSecurityMasterError, match="PRE_FREEZE_EXTRA_IDENTITY"):
        refresh_cloud_runtime_security_master(
            tmp_path / "runtime",
            baseline_master=baseline,
            observed_at=datetime(2026, 8, 26, 18, 35, tzinfo=JAKARTA),
            active_fetcher=lambda: _active([("AAAA", "2020-01-01"), ("OLDD", "2026-08-20")]),
            delisted_fetcher=lambda *args, **kwargs: _delisted([]),
        )


def test_post_freeze_listing_that_later_delists_remains_in_runtime_identity_history(
    tmp_path: Path,
) -> None:
    baseline = tmp_path / "baseline.csv"
    _write_baseline(
        baseline,
        [{"ticker": "AAAA", "listed_from": "2020-01-01", "listed_to": ""}],
    )
    result = refresh_cloud_runtime_security_master(
        tmp_path / "runtime",
        baseline_master=baseline,
        observed_at=datetime(2026, 8, 26, 18, 35, tzinfo=JAKARTA),
        active_fetcher=lambda: _active([("AAAA", "2020-01-01")]),
        delisted_fetcher=lambda *args, **kwargs: _delisted(
            [("NEWW", "2026-08-21", "2026-08-25")]
        ),
    )
    frame = pd.read_csv(Path(str(result["security_master_path"])))
    new_row = frame.loc[frame["ticker"].eq("NEWW")].iloc[0]
    assert str(new_row["listed_to"]) == "2026-08-25"
    assert result["post_freeze_new_tickers"] == ["NEWW"]


def test_refresh_requires_timezone_aware_observation(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.csv"
    _write_baseline(
        baseline,
        [{"ticker": "AAAA", "listed_from": "2020-01-01", "listed_to": ""}],
    )
    with pytest.raises(CloudSecurityMasterError, match="CLOCK_NOT_TIMEZONE_AWARE"):
        refresh_cloud_runtime_security_master(
            tmp_path / "runtime",
            baseline_master=baseline,
            observed_at=datetime(2026, 8, 26, 18, 35),
            active_fetcher=lambda: _active([("AAAA", "2020-01-01")]),
            delisted_fetcher=lambda *args, **kwargs: _delisted([]),
        )
