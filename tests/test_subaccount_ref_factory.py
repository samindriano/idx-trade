from copy import deepcopy
from decimal import Decimal

import pytest

from idx_trade.personal_portfolio import CashBalance, derive_subaccount_ref
from idx_trade.personal_portfolio.validation import jsonable


def test_shape_only_subaccount_reference_is_not_accepted_as_factory_origin():
    shaped_but_untrusted = "ksa_" + ("f" * 64)
    with pytest.raises(ValueError, match="server-derived keyed-HMAC.*derive_subaccount_ref"):
        CashBalance("IDR", Decimal("1"), subaccount_ref=shaped_but_untrusted)


def test_server_factory_returns_accepted_opaque_reference():
    ref = derive_subaccount_ref(
        "SYNTHETIC-ACCOUNT-REFERENCE",
        b"synthetic-subaccount-key-material-32-bytes!!",
    )
    balance = CashBalance("IDR", Decimal("1"), subaccount_ref=ref)
    assert str(balance.subaccount_ref).startswith("ksa_")


def test_canonical_jsonable_normalizes_opaque_ref_to_plain_string_for_copying():
    ref = derive_subaccount_ref(
        "SYNTHETIC-ACCOUNT-REFERENCE",
        b"synthetic-subaccount-key-material-32-bytes!!",
    )
    canonical = {"subaccount_ref": jsonable(ref)}
    assert type(canonical["subaccount_ref"]) is str
    assert deepcopy(canonical) == canonical
