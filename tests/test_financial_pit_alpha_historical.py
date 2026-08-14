from types import SimpleNamespace

from idx_trade.financial_pit_alpha_historical import eligible_financial_folds


def _block(rows, tickers):
    return {"rows": rows, "tickers": tickers}


def test_financial_era_eligibility_is_frozen_to_f4_f6_thresholds():
    details = {
        "V2F1": {"train": _block(0, 0), "purge": _block(0, 0), "validation": _block(0, 0)},
        "V2F2": {"train": _block(0, 0), "purge": _block(0, 0), "validation": _block(388, 33)},
        "V2F3": {"train": _block(388, 33), "purge": _block(698, 48), "validation": _block(9628, 168)},
        "V2F4": {"train": _block(10714, 168), "purge": _block(2590, 157), "validation": _block(12174, 180)},
        "V2F5": {"train": _block(25478, 203), "purge": _block(2400, 154), "validation": _block(15353, 252)},
        "V2F6": {"train": _block(43231, 274), "purge": _block(3712, 239), "validation": _block(19812, 287)},
    }
    assert eligible_financial_folds(details) == ["V2F4", "V2F5", "V2F6"]


def test_financial_era_eligibility_requires_both_train_and_validation_support():
    details = {
        name: {"train": _block(5000, 100), "purge": _block(0, 0), "validation": _block(5000, 100)}
        for name in ["V2F1", "V2F2", "V2F3", "V2F4", "V2F5", "V2F6"]
    }
    details["V2F3"]["validation"] = _block(4999, 100)
    details["V2F5"]["train"] = _block(5000, 99)
    assert eligible_financial_folds(details) == ["V2F1", "V2F2", "V2F4", "V2F6"]
