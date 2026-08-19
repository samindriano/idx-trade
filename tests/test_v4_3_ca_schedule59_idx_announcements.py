from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from idx_trade.v4_3_ca_schedule59_idx_announcements import (
    announcement_is_candidate,
    date_window,
    official_idx_attachment_url,
    parse_pipe_dates,
)


def _config() -> dict:
    return json.loads(
        Path("config/v4_3_ca_training_domain_schedule_59_idx_announcements_v1.json").read_text(
            encoding="utf-8"
        )
    )


def test_date_window_is_derived_only_from_source_dates() -> None:
    dates = parse_pipe_dates("2024-04-20|2024-04-25")
    start, end = date_window(dates, before_days=180, after_days=180)
    assert start == (pd.Timestamp("2024-04-20") - pd.Timedelta(days=180)).strftime("%Y%m%d")
    assert end == (pd.Timestamp("2024-04-25") + pd.Timedelta(days=180)).strftime("%Y%m%d")


def test_stock_split_candidate_terms_are_deterministic() -> None:
    config = _config()
    assert announcement_is_candidate(
        "Keterbukaan Informasi Pemecahan Saham",
        "Jadwal pelaksanaan stock split",
        source_type="Stock Split",
        config=config,
    )
    assert not announcement_is_candidate(
        "Laporan Keuangan Tahunan",
        "Publikasi laporan keuangan",
        source_type="Stock Split",
        config=config,
    )


def test_idx_attachment_url_must_remain_on_official_idx_host() -> None:
    config = _config()
    assert official_idx_attachment_url(
        "/StaticData/NewsAndAnnouncement/example.pdf",
        base_url=config["provider"]["base_url"],
        allowed_hosts=config["allowed_attachment_hosts"],
    ) == "https://www.idx.co.id/StaticData/NewsAndAnnouncement/example.pdf"
    assert official_idx_attachment_url(
        "https://evil.example/example.pdf",
        base_url=config["provider"]["base_url"],
        allowed_hosts=config["allowed_attachment_hosts"],
    ) is None


def test_config_preserves_full_residual_scope_and_scientific_firewall() -> None:
    config = _config()
    assert config["diagnosis_parent"]["residual_events"] == 59
    assert config["prior_news_adjudication"]["resolved_events"] == 0
    assert config["provider"]["endpoint"] == "/primary/ListedCompany/GetAnnouncement"
    assert config["provider"]["date_window_days_before"] == 180
    assert config["provider"]["date_window_days_after"] == 180
    for value in config["hard_boundaries"].values():
        assert value is False
