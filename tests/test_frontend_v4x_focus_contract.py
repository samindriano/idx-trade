from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "apps" / "web" / "app" / "page.tsx"
MONITOR = ROOT / "apps" / "web" / "app" / "monitoring" / "page.tsx"
DETAIL = ROOT / "apps" / "web" / "app" / "monitoring" / "models" / "[modelId]" / "page.tsx"
CATALOG = ROOT / "apps" / "web" / "lib" / "v4x-catalog.ts"
COMPARE = ROOT / "apps" / "web" / "app" / "compare" / "page.tsx"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_primary_navigation_hides_compare_without_deleting_page() -> None:
    assert COMPARE.exists()
    for path in (HOME, MONITOR, DETAIL):
        source = text(path)
        assert 'href="/compare"' not in source
        assert ">Compare<" not in source


def test_primary_dashboard_focuses_v4x_and_v2_without_erasing_history() -> None:
    home = text(HOME)
    monitor = text(MONITOR)
    assert "V4-X Geometry3" in home
    assert "V4X_ALPHA" in home
    assert "V2_CHAMPION" in home
    assert "RESEARCH_EXPERIMENTS" in home
    assert "PAST MODEL EVIDENCE" in home
    assert "RESEARCH ARCHIVE" in home
    assert "V4X_ALPHA" in monitor
    assert "V2_CHAMPION" in monitor
    assert "O2_CHALLENGER" not in monitor
    assert "FINAL_RANKER" not in monitor


def test_interactive_model_evidence_features_remain_available() -> None:
    home = text(HOME)
    assert "ModelEvidencePicker" in home
    assert "EvidenceChart" in home
    assert "onMouseEnter" in home
    assert "styles.tooltip" in home
    assert "evidenceHelpButton" in home
    assert "archiveSort" in home
    assert "archiveStatusFilter" in home
    assert "expandedArchiveKey" in home


def test_v4_control_has_user_facing_label_not_internal_context25_name() -> None:
    home = text(HOME)
    assert "V4 control · 25 features" in home
    assert "CONTEXT25 CONTROL" not in home


def test_v4x_catalog_preserves_frozen_folds_and_pins_audited_evidence() -> None:
    catalog = text(CATALOG)
    assert 'id: "V4_X1_GEOMETRY3_PROSPECTIVE"' in catalog
    assert "historicalConsensusIc: 0.09545975125676774" in catalog
    assert "historicalControlConsensusIc: 0.08979323509925058" in catalog
    assert "historicalConsensusRelativeLift: 0.06310627021349466" in catalog
    assert "frozenMedianFoldConsensusIc: 0.09775243938276076" in catalog
    assert "frozenControlMedianFoldConsensusIc: 0.08415844149089491" in catalog
    assert "auditedCommonSupportConsensusIc: 0.09545975125676774" in catalog
    assert "auditedCommonSupportControlConsensusIc: 0.08979323509925058" in catalog
    assert "auditedStrictSupportConsensusIc: 0.08327323251280924" in catalog
    assert "auditedCommonSupportIncrementalIc: 0.00566651615751716" in catalog
    assert "auditedPositivePairedConsensusDeltaFolds: 5" in catalog
    assert 'auditStatus: "PASS_NO_CRITICAL_ERROR_FOUND"' in catalog
    assert "historicalValidationSessions: 600" in catalog
    assert "modelBundleManifestSha256: \"3d5420dd69f348b7e712b6cca3b11f4673f02581c493e04be6ce9da693125094\"" in catalog
    for value in (
        "0.09227078711981862",
        "0.06625356936830826",
        "0.1032340916457029",
        "0.029696513400161204",
        "0.12931364086270405",
        "0.16348225628388718",
    ):
        assert value in catalog


def test_v4x_detail_uses_defensible_audited_rankic_without_claiming_forward_result() -> None:
    detail = text(DETAIL)
    assert "AUDITED HISTORICAL RANKIC" in detail
    assert "auditedCommonSupportConsensusIc" in detail
    assert "auditedStrictSupportConsensusIc" in detail
    assert "auditedCommonSupportIncrementalIc" in detail
    assert "Red-team audit passed" in detail
    assert "historical-development results, not X1 prospective performance" in detail
    assert "realized forward performance stays hidden" in detail


def test_monitoring_routes_only_active_primary_models_and_names_v2() -> None:
    monitor = text(MONITOR)
    detail = text(DETAIL)
    assert 'route: "v4x"' in monitor
    assert 'route: "v2"' in monitor
    assert 'route: "o2"' not in monitor
    assert 'route: "v3"' not in monitor
    assert "V2 ${V2_CHAMPION.shortName}" in monitor
    assert "V2 ${V2_CHAMPION.shortName}" in detail
    assert "median PR-AUC delta +2.39%" in detail
    assert "median ROC-AUC 0.5244" in detail
    assert "median Q5−Q1 +5.12%" in detail
