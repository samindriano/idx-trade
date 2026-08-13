from decimal import Decimal

import pytest

from idx_trade.personal_portfolio import CashBalance, derive_subaccount_ref


def test_shape_only_subaccount_reference_is_not_accepted_as_factory_origin():
    shaped_but_untrusted = "ksa_" + ("f" * 64)
    with pytest.raises(ValueError, match="derive_subaccount_ref"):
        CashBalance("IDR", Decimal("1"), subaccount_ref=shaped_but_untrusted)


def test_server_factory_returns_accepted_opaque_reference():
    ref = derive_subaccount_ref(
        "SYNTHETIC-ACCOUNT-REFERENCE",
        b"synthetic-subaccount-key-material-32-bytes!!",
    )
    balance = CashBalance("IDR", Decimal("1"), subaccount_ref=ref)
    assert str(balance.subaccount_ref).startswith("ksa_")
