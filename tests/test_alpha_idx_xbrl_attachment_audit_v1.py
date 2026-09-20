import zipfile
from pathlib import Path

import pytest

from research.alpha_idx_xbrl_attachment_audit_v1 import audit_zip, summarize


def _write_zip(root: Path, name: str = "TEST.instance.zip") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    xml = """<xbrli:xbrl xmlns:xbrli='http://www.xbrl.org/2003/instance' xmlns:ex='urn:example'>
      <xbrli:context id='c1'><xbrli:entity><xbrli:identifier scheme='x'>TEST</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period></xbrli:context>
      <xbrli:unit id='u1'><xbrli:measure>iso4217:IDR</xbrli:measure></xbrli:unit>
      <ex:Assets contextRef='c1' unitRef='u1'>100</ex:Assets>
    </xbrli:xbrl>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("instance.xbrl", xml)
    return path


def test_audit_counts_xbrl_structure_without_emitting_values(tmp_path: Path):
    result = audit_zip(_write_zip(tmp_path))
    assert result["status"] == "PARSED"
    assert result["context_count"] == 1
    assert result["unit_count"] == 1
    assert result["period_min"] == "2024-12-31"
    assert "100" not in str(result)


def test_summarize_requires_zip(tmp_path: Path):
    with pytest.raises(ValueError):
        summarize(tmp_path)
