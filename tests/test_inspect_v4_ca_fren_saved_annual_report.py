from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import inspect_v4_ca_fren_saved_annual_report as forensic


def test_contexts_surfaces_exact_ex_right_schedule() -> None:
    text = (
        "PMHMETD V. Cum Right Pasar Reguler dan Pasar Negosiasi 16 April 2024. "
        "Ex Right Pasar Reguler dan Pasar Negosiasi 17 April 2024. "
        "Setiap 178 saham lama memperoleh 75 HMETD."
    )
    rows = forensic.contexts(text, ("17 April 2024", "PMHMETD"), radius=200)
    assert rows
    joined = " ".join(row["context"] for row in rows).casefold()
    assert "ex right" in joined
    assert "pasar reguler" in joined
    assert "pasar negosiasi" in joined


def test_relevant_rejects_unrelated_text() -> None:
    assert forensic.relevant("ordinary company profile") is False


def test_target_sha_is_frozen() -> None:
    assert forensic.TARGET_SHA256 == "980b8bd046a828f48fe4bb645a1b687acc9f183ad6da8c3a75c49d5e80386887"
