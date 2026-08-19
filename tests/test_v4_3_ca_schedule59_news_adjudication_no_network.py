from pathlib import Path


def test_schedule59_news_adjudication_is_offline_only() -> None:
    source = Path("scripts/run_v4_3_ca_training_domain_schedule_59_ksei_news_offline_adjudication.py").read_text(encoding="utf-8")
    assert "capture_request(" not in source
    assert "make_session(" not in source
    assert "requests.get" not in source
