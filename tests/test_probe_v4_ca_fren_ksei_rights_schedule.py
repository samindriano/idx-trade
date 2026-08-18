from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import probe_v4_ca_fren_ksei_rights_schedule as probe


def test_extracts_only_fren_ksei_announcement_pdf() -> None:
    payload = b'''
    <table>
      <tr><td>WIKA</td><td><a href="/Announcement/Files/wika.pdf">WIKA</a></td></tr>
      <tr><td>FREN - SMARTFREN TELECOM Tbk</td><td><a href="/Announcement/Files/fren.pdf">FREN HMETD</a></td></tr>
      <tr><td>FREN fake</td><td><a href="https://example.com/fren.pdf">bad</a></td></tr>
    </table>
    '''
    assert probe.extract_fren_pdf_links(payload) == (
        "https://web.ksei.co.id/Announcement/Files/fren.pdf",
    )


def test_verifies_explicit_regular_negotiated_ex_right_schedule() -> None:
    text = '''
    PT Kustodian Sentral Efek Indonesia
    Kode dan Nama Saham : FREN - SMARTFREN TELECOM Tbk
    Jadwal HMETD adalah sebagai berikut:
    Tanggal Cum di Pasar Regular dan Pasar Negosiasi 16 April 2024
    Tanggal Ex di Pasar Regular dan Pasar Negosiasi 17 April 2024
    Tanggal Pencatatan (Recording Date) 18 April 2024
    Tanggal Distribusi 19 April 2024
    Tanggal Pencatatan di Bursa 22 April 2024
    Periode Perdagangan HMETD 22 April 2024 - 6 Mei 2024
    Setiap 178 saham lama mendapatkan 75 HMETD.
    No. Ref. : KSEI-12345/JKU/0424
    '''
    result = probe.verify_ksei_fren_schedule_text(text)
    assert result["transition_date"] == "2024-04-17"
    assert result["ratio"] == "178_OLD_TO_75_HMETD"
    assert result["reference_no"] == "KSEI-12345/JKU/0424"


def test_rejects_record_date_only_without_explicit_ex_label() -> None:
    text = '''
    FREN SMARTFREN TELECOM HMETD 178 saham 75 HMETD
    16 April 2024 17 April 2024 18 April 2024 19 April 2024
    Tanggal Pencatatan Recording Date 18 April 2024
    Tanggal Distribusi 19 April 2024
    22 April 2024 - 6 Mei 2024
    '''
    try:
        probe.verify_ksei_fren_schedule_text(text)
    except RuntimeError as exc:
        assert "EX_RIGHT_LABEL_MISSING" in str(exc)
    else:
        raise AssertionError("record-date-only evidence must fail closed")
