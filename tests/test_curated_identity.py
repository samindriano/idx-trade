import pandas as pd
import pytest

from idx_trade.curated_identity import (
    canonicalize_curated_security_identities,
    supplement_historical_security_identities,
)
from idx_trade.security_master import build_security_master, existence_state
from idx_trade.states import ExistenceState


def _curated():
    return pd.DataFrame(
        {
            "ticker": ["FREN"],
            "company_name": ["PT Smartfren Telecom Tbk"],
            "security_type": ["Saham Biasa"],
            "listed_from": ["2006-11-29"],
            "listed_to": ["2025-04-16"],
            "source": ["ISSUER_OFFICIAL_IDENTITY_AND_MERGER_EVIDENCE"],
            "source_ref": ["issuer://annual-report|issuer://merger-plan"],
            "evidence_note": ["Official listing and deletion evidence."],
        }
    )


def test_curated_historical_identity_adds_missing_delisted_common_share():
    active = pd.DataFrame(
        {
            "ticker": ["BBCA"],
            "company_name": ["Bank Central Asia Tbk"],
            "listed_from": ["2000-05-31"],
            "listed_to": [pd.NaT],
            "source": ["IDX"],
        }
    )
    delisted = pd.DataFrame(columns=active.columns)
    active2, delisted2, diagnostics = supplement_historical_security_identities(
        active,
        delisted,
        _curated(),
        required_tickers=["FREN"],
    )
    assert set(active2["ticker"]) == {"BBCA"}
    assert delisted2["ticker"].tolist() == ["FREN"]
    assert pd.Timestamp(delisted2.loc[0, "listed_from"]) == pd.Timestamp("2006-11-29")
    assert pd.Timestamp(delisted2.loc[0, "listed_to"]) == pd.Timestamp("2025-04-16")
    assert diagnostics.loc[0, "status"] == "CURATED_IDENTITY_SUPPLEMENTED"

    master = build_security_master(active2, delisted2)
    assert existence_state(master, "FREN", pd.Timestamp("2025-04-16")) is ExistenceState.LISTED
    assert existence_state(master, "FREN", pd.Timestamp("2025-04-17")) is ExistenceState.DELISTED


def test_curated_identity_never_overrides_primary_identity():
    active = pd.DataFrame(
        {
            "ticker": ["FREN"],
            "company_name": ["Primary FREN"],
            "listed_from": ["2006-11-29"],
            "listed_to": [pd.NaT],
            "source": ["IDX_PRIMARY"],
        }
    )
    active2, delisted2, diagnostics = supplement_historical_security_identities(
        active,
        pd.DataFrame(columns=active.columns),
        _curated(),
        required_tickers=["FREN"],
    )
    assert len(active2) == 1
    assert delisted2.empty
    assert diagnostics.loc[0, "status"] == "PRIMARY_IDENTITY_ALREADY_PRESENT"


def test_curated_identity_rejects_non_common_security():
    bad = _curated()
    bad.loc[0, "security_type"] = "Saham Preference"
    with pytest.raises(ValueError, match="common shares only"):
        canonicalize_curated_security_identities(bad)
