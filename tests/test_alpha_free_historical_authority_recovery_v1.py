from __future__ import annotations

import csv
import json
from pathlib import Path

from research.alpha_free_historical_authority_recovery_v1 import (
    compare_cntx_csvs,
    parse_cntx_anchor,
    parse_ksei_archive,
    parse_ksei_deflist,
    parse_ksei_shares,
)


def test_ksei_deflist_preserves_fail_closed_empty_record(tmp_path: Path) -> None:
    path = tmp_path / "cntx.html"
    path.write_text(
        "<dt>Security name</dt><dd></dd><dt>Type</dt><dd>UNDEFINED ()</dd><dt>Status</dt><dd>UNKNOWN ()</dd>",
        encoding="utf-8",
    )
    fields = parse_ksei_deflist(path)
    assert fields["Security name"] == ""
    assert fields["Type"].startswith("UNDEFINED")
    assert fields["Status"] == "UNKNOWN ()"


def test_ksei_share_list_deduplicates_codes(tmp_path: Path) -> None:
    path = tmp_path / "shares.html"
    path.write_text(
        '<a href="/services/registered-securities/shares/lc/AAA">AAA</a>'
        '<a href="/services/registered-securities/shares/lc/AAA">AAA</a>'
        '<a href="/services/registered-securities/shares/lc/BBB">BBB</a>',
        encoding="utf-8",
    )
    result = parse_ksei_shares(path)
    assert result["unique_codes"] == 2


def test_archive_counts_only_explicit_new_isin_notices(tmp_path: Path) -> None:
    path = tmp_path / "archive.html"
    path.write_text(
        '<select><option value="2003">2003</option><option value="2021">2021</option></select>'
        '<h2 class="h4 no-margin">PENG-1</h2><small><b>January 1, 2021</b></small>'
        '<p>Announcement of New Isin Code: ID1000000001 (AAA)</p>',
        encoding="utf-8",
    )
    result = parse_ksei_archive(path)
    assert result["announcement_headers"] == 1
    assert result["new_isin_notices"] == 1
    assert result["year_option_min"] == 2003
    assert result["year_option_max"] == 2021


def test_cntx_anchor_counts_states_and_dates(tmp_path: Path) -> None:
    path = tmp_path / "anchor.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ticker", "state", "as_of_date"])
        writer.writeheader()
        writer.writerows([
            {"ticker": "CNTX", "state": "ACTIVE", "as_of_date": "2021-01-01"},
            {"ticker": "CNTX", "state": "NO_TRADE", "as_of_date": "2021-01-02"},
            {"ticker": "OTHER", "state": "ACTIVE", "as_of_date": "2021-01-01"},
        ])
    result = parse_cntx_anchor(path)
    assert result["rows"] == 2
    assert result["active_rows"] == 1
    assert result["no_trade_rows"] == 1
    assert result["active_min"] == "2021-01-01"


def test_mirror_comparison_is_numeric_and_date_keyed(tmp_path: Path) -> None:
    mirror = tmp_path / "mirror.csv"
    local = tmp_path / "local.csv"
    mirror.write_text("Date,Previous,Open,High,Low,Close,Volume,Value,Frequency,ListedShares,TradebleShares\n2021-01-01,1,2,3,4,5,6,7,8,9,10\n", encoding="utf-8")
    local.write_text("date,previous,open_price,high,low,close,volume,value,frequency,listed_shares,tradeble_shares\n2021-01-01,1,2,3,4,5,6,7,8,9,10\n", encoding="utf-8")
    result = compare_cntx_csvs(mirror, local)
    assert result["common_date_rows"] == 1
    assert not any(result["field_mismatch_counts"].values())
