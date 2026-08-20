from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from idx_trade.price_basis_open_remediation import (
    DISAGREEMENT_CLASS,
    FALLBACK_CLASS,
    OFFICIAL_CLASS,
    UNRESOLVED_CLASS,
    fail_closed_view,
    materialize_open_candidate,
    overlay_view,
)


def rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "AAA", "date": "2025-01-01", "adjudication_class": OFFICIAL_CLASS,
                "official_open": 100.0, "factor_up_open": 100.0, "low": 90.0, "high": 110.0,
                "accepted_open": 50.0, "accepted_open_source": "DERIVATIVE_OPEN", "expected_factor": 2.0,
            },
            {
                "ticker": "BBB", "date": "2025-01-01", "adjudication_class": DISAGREEMENT_CLASS,
                "official_open": 200.0, "factor_up_open": 198.0, "low": 190.0, "high": 210.0,
                "accepted_open": 99.0, "accepted_open_source": "DERIVATIVE_OPEN", "expected_factor": 2.0,
            },
            {
                "ticker": "CCC", "date": "2025-01-01", "adjudication_class": FALLBACK_CLASS,
                "official_open": np.nan, "factor_up_open": 300.0, "low": 290.0, "high": 310.0,
                "accepted_open": 100.0, "accepted_open_source": "DERIVATIVE_OPEN", "expected_factor": 3.0,
            },
            {
                "ticker": "DDD", "date": "2025-01-01", "adjudication_class": UNRESOLVED_CLASS,
                "official_open": np.nan, "factor_up_open": 50.0, "low": 90.0, "high": 110.0,
                "accepted_open": 25.0, "accepted_open_source": "DERIVATIVE_OPEN", "expected_factor": 2.0,
            },
        ]
    )


def test_policy_prefers_official_and_uses_factor_only_as_fallback() -> None:
    out, diag = materialize_open_candidate(rows())
    values = dict(zip(out["ticker"], out["remediated_open"]))
    assert values["AAA"] == 100.0
    assert values["BBB"] == 200.0
    assert values["CCC"] == 300.0
    assert np.isnan(values["DDD"])
    assert diag == {
        "rows": 4,
        "official_primary_rows": 2,
        "factor_fallback_rows": 1,
        "unresolved_fail_closed_rows": 1,
        "admitted_rows": 3,
        "admitted_within_corrected_hlc_rows": 3,
        "official_factor_disagreement_rows": 1,
    }


def test_overlay_excludes_fail_closed_rows() -> None:
    out, _ = materialize_open_candidate(rows())
    assert overlay_view(out)["ticker"].tolist() == ["AAA", "BBB", "CCC"]
    assert fail_closed_view(out)["ticker"].tolist() == ["DDD"]


def test_admitted_open_outside_corrected_hlc_fails_closed() -> None:
    frame = rows()
    frame.loc[frame["ticker"].eq("CCC"), "factor_up_open"] = 999.0
    with pytest.raises(ValueError, match="outside corrected H/L"):
        materialize_open_candidate(frame)


def test_unknown_adjudication_class_is_rejected() -> None:
    frame = rows()
    frame.loc[0, "adjudication_class"] = "UNKNOWN"
    with pytest.raises(ValueError, match="unrecognized adjudication"):
        materialize_open_candidate(frame)
