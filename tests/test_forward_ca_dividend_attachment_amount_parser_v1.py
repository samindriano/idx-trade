from __future__ import annotations

from decimal import Decimal
import importlib.util
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "review_forward_ca_idx_dividend_attachments_v1.py"
    spec = importlib.util.spec_from_file_location("review_forward_ca_idx_dividend_attachments_v1", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_amount_parser_accepts_official_indonesian_sentence() -> None:
    module = _load_module()
    text = module._norm(
        "Perseroan akan melaksanakan pembagian dividen interim sebesar Rp25,00 per lembar saham."
    )
    assert module._has_dividend_amount(text, Decimal("25"))


def test_amount_parser_accepts_official_english_sentence() -> None:
    module = _load_module()
    text = module._norm(
        "The Company is going to distribute interim dividend of Rp25.00 per share."
    )
    assert module._has_dividend_amount(text, Decimal("25"))


def test_amount_parser_rejects_wrong_amount() -> None:
    module = _load_module()
    text = module._norm("dividen interim sebesar Rp30,00 per lembar saham")
    assert not module._has_dividend_amount(text, Decimal("25"))
