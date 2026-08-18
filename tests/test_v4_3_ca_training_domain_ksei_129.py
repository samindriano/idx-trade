from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "v4_3_ca_training_domain_ksei_129_v1.json"
RUNNER = ROOT / "scripts" / "run_v4_3_ca_training_domain_ksei_129_census.py"


def test_config_freezes_blocked_gate_and_exact_129_identity() -> None:
    value = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert value["schema_version"] == "v4_3_ca_training_domain_ksei_129_v1"
    assert value["outcome_blind"] is True
    blocked = value["blocked_training_gate"]
    assert blocked["manifest_sha256"] == "b7c87f709d27b8d2860f7cde073d048042810c4de21ce6fd4441e8556d96b46d"
    assert blocked["expected_missing_tickers"] == 129
    assert blocked["missing_ticker_identity_sha256"] == "28d39c8b1a08585724e6b78d3b76520073043aa7c0f0a53bf6ae1f2fb5bbf58f"


def test_provider_is_same_strict_ksei_registered_security_path() -> None:
    value = json.loads(CONFIG.read_text(encoding="utf-8"))
    provider = value["provider"]
    assert provider["name"] == "KSEI_PUBLIC_REGISTERED_SECURITY_HISTORY"
    assert provider["transport_library"] == "curl_cffi"
    assert provider["impersonate"] == "chrome110"
    assert provider["fresh_session_per_ticker"] is True
    assert provider["home_warmup_per_ticker"] is True
    assert provider["source_substitution"] is False
    assert provider["parser_relaxation"] is False
    assert "web.ksei.co.id/services/registered-securities/shares/lc/{ticker}" in provider["security_url_template"]


def test_runner_remains_outcome_blind_and_delta_only() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    forbidden = (
        "materialize_v4_target_ledger",
        "fit_v4_head",
        "score_v4_head",
        "ranking_v4_3_model_eval",
        "target_rank_h5",
        "target_rank_h10",
        "performance_computed\": True",
    )
    for token in forbidden:
        assert token not in source
    assert "delta only" in source
    assert '"target_or_rank_materialized": False' in source
    assert '"model_fit": False' in source
    assert '"performance_computed": False' in source


def test_expected_129_identity_hash_matches_diagnostic_list() -> None:
    # This is the exact sorted list emitted by the blocked pre-target gate.
    tickers = """ABBA ADMG ALDO AMAR AMFG AMOR ARII ARKA ATIC AXIO BAJA BALI BAUT BBSS BEBS BEER BESS BIMA BINA BINO BISI BKDP BKSW BMBL BMSR BNII BOBA BOLA BOSS BPTR BSIM BUAH BUDI CAKK CASH CBMF CBPE CBUT CMPP CRSN DEPO DIGI DUCK DYAN EAST ENAK EPMT GDST GOOD HBAT HITS HKMU IDPR INAF INCF INDR IPCM IPPE JAWA JSKY KBAG KING KINO KKES KOBX KREN LINK LMAS LPIN LTLS MASB MBAP MCAS MCOL MCOR META MKTR MSIE MTPS MTWI NFCX OBMD PALM PBID POLI POLL POLY PRAY PSGO PSSI PTDU PTIS PTSN PURA RAFI RANC RIGS RSGK RUIS RUNS SAGE SAMF SCNP SDPC SHID SHIP SICO SMDM SMKL SPMA SULI SURE SWAT TECH TFAS TGRA TIRT TOYS TRGU TRIS TYRE UFOE VICO WGSH WSKT ZBRA ZINC ZONE ZYRX""".split()
    assert len(tickers) == 129
    payload = ("\n".join(sorted(tickers)) + "\n").encode("utf-8")
    assert hashlib.sha256(payload).hexdigest() == "28d39c8b1a08585724e6b78d3b76520073043aa7c0f0a53bf6ae1f2fb5bbf58f"
