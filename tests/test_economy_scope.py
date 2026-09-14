from __future__ import annotations

from fastapi.testclient import TestClient

from app.config.config import Config
from app.services.api_quota_monitor import ApiQuotaMonitor
from app.v17.core.league_filter import LeagueFilter


def raw_fixture(league: str, country: str = "Spain"):
    return {"league": {"name": league, "country": country}}


def test_strict_scope_allows_top_two_and_priority_cups():
    league_filter = LeagueFilter()
    assert league_filter.evaluate(raw_fixture("La Liga"))["league_allowed"] is True
    assert league_filter.evaluate(raw_fixture("Segunda Division"))["league_allowed"] is True
    assert league_filter.evaluate(raw_fixture("Copa del Rey"))["league_allowed"] is True
    assert league_filter.evaluate(raw_fixture("CONMEBOL Libertadores", "World"))["league_allowed"] is True


def test_strict_scope_blocks_lower_youth_and_friendlies():
    league_filter = LeagueFilter()
    assert league_filter.evaluate(raw_fixture("Serie C", "Italy"))["league_allowed"] is False
    assert league_filter.evaluate(raw_fixture("Premier League U21", "England"))["league_allowed"] is False
    assert league_filter.evaluate(raw_fixture("Club Friendlies", "World"))["league_allowed"] is False


def test_quota_monitor_guard_uses_headers_without_extra_calls():
    class Response:
        status_code = 200
        headers = {
            "x-ratelimit-requests-limit": "7500",
            "x-ratelimit-requests-remaining": "350",
            "X-RateLimit-Limit": "300",
            "X-RateLimit-Remaining": "299",
        }

    monitor = ApiQuotaMonitor()
    monitor.record_response(Response(), "fixtures_live")
    state = monitor.snapshot()
    assert state["daily_limit"] == 7500
    assert state["daily_remaining"] == 350
    assert monitor.can_spend(required=25, reserve=300) is True
    assert monitor.can_spend(required=60, reserve=300) is False


def test_match_detail_uses_memory_and_merges_tracking_fields():
    Config.WORKER_ENABLED = False
    import main
    from app.services.app_container import app_container

    adapter = app_container.v17_dashboard_adapter
    adapter._detail_by_fixture = {
        "123": {
            "fixture_id": "123",
            "home_team": "A",
            "away_team": "B",
            "home_stats": {"shots": 9},
            "main_reading": "Lectura live completa",
        }
    }
    adapter._detail_by_signal = {
        "sig-123": {
            "fixture_id": "123",
            "signal_key": "sig-123",
            "entry_score": "1-0",
            "current_score": "2-0",
            "result_status": "WON",
        }
    }
    with TestClient(main.app) as client:
        response = client.get("/v17/match/123", params={"signal_key": "sig-123"})
        assert response.status_code == 200
        body = response.json()
        assert body["item"]["home_stats"]["shots"] == 9
        assert body["item"]["entry_score"] == "1-0"
        assert body["item"]["current_score"] == "2-0"


def test_economy_defaults_are_selective():
    assert Config.API_ECONOMY_MODE is True
    assert Config.STRICT_COMPETITION_SCOPE is True
    assert Config.GLOBAL_SENIOR_SCOPE is False
    assert Config.MAX_PREMATCH_ENRICHMENTS_PER_CYCLE <= 1
    assert Config.PUBLISH_MIN_CONFIDENCE >= 82


def test_prematch_hourly_budget_limits_new_packages(monkeypatch, tmp_path):
    from app.v17.services.pre_match_data_service import PreMatchDataService

    monkeypatch.setattr(Config, "PREMATCH_MAX_NEW_PACKAGES_PER_HOUR", 2)
    service = PreMatchDataService(cache_path=str(tmp_path / "prematch.json"))
    assert service._reserve_new_package_slot() is True
    assert service._reserve_new_package_slot() is True
    assert service._reserve_new_package_slot() is False
