from __future__ import annotations

from idx_trade.lbre_lineage_remediation import (
    classify_revision_kind,
    parse_lbre_current_fields,
)


def _report(*, pct: str = "30,29", shares: str = "2.310.408.900") -> str:
    return "\n".join(
        [
            f"Jumlah saham Free Float                         2.310.345.900       {shares}",
            "Jumlah saham tercatat di Bursa per akhir bulan  7.626.663.000       7.626.663.000",
            f"% Saham Free Float                              30,29                {pct}",
            "Saham Free Float menjadi 999.999.999",
        ]
    )


def test_explicit_two_column_summary_is_exact_and_ignores_narrative() -> None:
    result = parse_lbre_current_fields(_report())
    assert result.status == "EXACT"
    assert result.fields is not None
    assert result.fields.free_float_shares == 2_310_408_900
    assert result.fields.free_float_pct == 30.29
    assert result.fields.total_listed_shares == 7_626_663_000


def test_single_percentage_value_is_previous_or_ambiguous_not_current() -> None:
    result = parse_lbre_current_fields(
        _report().replace("30,29                30,29", "30,29")
    )
    assert result.status == "UNRESOLVED"
    assert "free_float_pct_current_value_missing" in result.diagnostics


def test_conflicting_authoritative_summary_columns_fail_closed() -> None:
    text = _report() + "\nThe amount of Free Float Share       2.310.345.900       2.310.400.000"
    result = parse_lbre_current_fields(text)
    assert result.status == "UNRESOLVED"
    assert "free_float_shares_current_value_conflict" in result.diagnostics


def test_explicit_announcement_correction_marker_overrides_bad_default() -> None:
    assert (
        classify_revision_kind(
            "053/CORSEC/BAPA/VII/2026(KOREKSI)",
            "Laporan Bulanan Registrasi Pemegang Efek",
            "ORIGINAL",
        )
        == "CORRECTION"
    )


def test_no_correction_marker_does_not_guess_from_suffix_or_chronology() -> None:
    assert (
        classify_revision_kind(
            "12.114/SL.e/Corsec/BOSS/VII/2026",
            "Laporan Bulanan Registrasi Pemegang Efek",
            "ORIGINAL",
        )
        == "ORIGINAL"
    )
