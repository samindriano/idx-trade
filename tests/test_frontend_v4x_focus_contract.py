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


def test_primary_dashboard_focuses_v4x_and_v2() -> None:
    home = text(HOME)
    monitor = text(MONITOR)
    assert "V4-X Geometry3" in home
    assert "V4X_ALPHA" in home
    assert "V2_CHAMPION" in home
    assert "V4X_ALPHA" in monitor
    assert "V2_CHAMPION" in monitor
    assert "O2_CHALLENGER" not in home
    assert "FINAL_RANKER" not in home
    assert "O2_CHALLENGER" not in monitor
    assert "FINAL_RANKER" not in monitor


def test_v4x_catalog_pins_current_historical_evidence() -> None:
    catalog = text(CATALOG)
    assert 'id: "V4_X1_GEOMETRY3_PROSPECTIVE"' in catalog
    assert "historicalConsensusIc: 0.09775243938276076" in catalog
    assert "historicalControlConsensusIc: 0.08415844149089491" in catalog
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


def test_monitoring_routes_only_active_primary_models() -> None:
    monitor = text(MONITOR)
    assert 'route: "v4x"' in monitor
    assert 'route: "v2"' in monitor
    assert 'route: "o2"' not in monitor
    assert 'route: "v3"' not in monitor
