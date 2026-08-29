import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "acquire_inc001_stock_split_discovery_v3.py"
SPEC = importlib.util.spec_from_file_location("inc001_stock_split_discovery_v3", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_source_ids_accepts_raw_v7_hex_identity():
    source_id = "21115a57619788e7d3b5ae95a995e6795057ccc39e604251addd275694b90d8f"
    assert MODULE.source_ids(source_id) == [source_id]
    assert MODULE.source_ids('["A", "B"]') == ["A", "B"]


def test_english_ksei_schedule_parser_requires_explicit_regular_market_basis_semantic(tmp_path):
    text_path = tmp_path / "schedule.txt"
    text_path.write_text(
        """Jakarta, 6 January 2022
Stock Split Ratio with Old Nominal Value of Rp.100,- per Share to New Nominal Value of Rp. 20,- per Share.
Stock Split Ratio 1:5
End of date old securities trade in Regular and Negotiation Market
: 11 January 2022
Start date of new securities trade in Regular and Negotiation Market
: 12 January 2022
Recording Date
: 13 January 2022
Date of securities distribution
: 14 January 2022
""",
        encoding="utf-8",
    )
    parsed = MODULE.parse_document(
        {
            "document_id": "DOC-1",
            "ticker": "AKRA",
            "status_code": "200",
            "source_ref": "https://official.example/DOC-1.pdf",
            "sha256": "a" * 64,
        },
        text_path,
    )
    assert parsed["publication_date"] == "2022-01-06"
    assert parsed["last_old_basis_trading_date"] == "2022-01-11"
    assert parsed["first_new_basis_trading_date"] == "2022-01-12"
    assert parsed["recording_date"] == "2022-01-13"
    assert parsed["distribution_date"] == "2022-01-14"
    assert parsed["ratio"] == "1:5"
    assert parsed["explicit_regular_market_semantic"] == "true"
    assert parsed["parser_status"] == "PARSED_EXACT_STOCK_SPLIT_SCHEDULE"
    assert parsed["status_code"] == "200"
