from __future__ import annotations

from fastapi.testclient import TestClient

from app.config.config import Config
from app.jhonny_elite.engine import JhonnyEliteEngine
from app.v17.signals.result_resolver import ResultResolver
from app.v17.signals.signal_tracker import SignalTracker


def match_template(**changes):
    item = {
        "match_id": 9001,
        "fixture_id": 9001,
        "home_team": "Equipo A",
        "away_team": "Equipo B",
        "league": "Serie A",
        "country": "Italy",
        "api_minute": 67,
        "effective_minute": 67,
        "display_minute": "67",
        "home_score": 1,
        "away_score": 0,
        "shots": 8,
        "shots_on_target": 2,
        "dangerous_attacks": 20,
        "corners": 3,
        "xg": 0.75,
        "xG": 0.75,
        "possession_home": 52,
        "possession_away": 48,
        "home_stats": {"shots": 4, "shots_on_target": 1, "dangerous_attacks": 10, "corners": 2, "xG": 0.4, "possession": 52},
        "away_stats": {"shots": 4, "shots_on_target": 1, "dangerous_attacks": 10, "corners": 1, "xG": 0.35, "possession": 48},
        "data_quality": "HIGH",
        "has_live_stats": True,
    }
    item.update(changes)
    return item


def test_prematch_is_not_requested_before_candidate(monkeypatch):
    engine = JhonnyEliteEngine()
    called = {"count": 0}

    def fake_prematch(match):
        called["count"] += 1
        return {"pre_match_available": True, "over_pre_match_score": 80, "under_pre_match_score": 20}

    monkeypatch.setattr(engine, "_load_prematch", fake_prematch)
    result = engine.analyze_match(match_template(shots=2, shots_on_target=0, dangerous_attacks=2, corners=0, xg=0.1, xG=0.1))
    assert called["count"] == 0
    assert result["pre_match_triggered"] is False


def test_strong_over_candidate_triggers_prematch(monkeypatch):
    engine = JhonnyEliteEngine()
    called = {"count": 0}

    def fake_prematch(match):
        called["count"] += 1
        return {
            "pre_match_available": True,
            "pre_match_ok": True,
            "pre_match_source": "TEST",
            "pre_match_avg_total_goals": 3.0,
            "over_pre_match_score": 82,
            "under_pre_match_score": 22,
            "pre_match_support_points": ["Recent high goal profile"],
            "pre_match_caution_points": [],
        }

    monkeypatch.setattr(engine, "_load_prematch", fake_prematch)
    monkeypatch.setattr(engine.odds_service, "enrich", lambda *args, **kwargs: {
        "odds_available": True,
        "odds_status": "TEST",
        "market_direction": "OVER",
        "line": 1.5,
        "odds": 1.80,
        "implied_probability": 55.56,
        "value_edge": 12.0,
        "has_positive_value": True,
    })

    result = engine.analyze_match(match_template(
        shots=22, shots_on_target=8, dangerous_attacks=58, corners=8, xg=2.25, xG=2.25,
        home_stats={"shots": 13, "shots_on_target": 5, "dangerous_attacks": 33, "corners": 5, "xG": 1.4, "possession": 58},
        away_stats={"shots": 9, "shots_on_target": 3, "dangerous_attacks": 25, "corners": 3, "xG": 0.85, "possession": 42},
    ))
    assert called["count"] == 1
    assert result["pre_match_triggered"] is True
    assert result["suggested_market"] == "OVER"
    assert result["probability_next_goal"] > result["probability_no_more_goals"]


def test_under_is_not_published_before_minute_75(monkeypatch):
    engine = JhonnyEliteEngine()
    result = engine.analyze_match(match_template(
        api_minute=70, effective_minute=70, display_minute="70",
        home_score=2, away_score=0, shots=4, shots_on_target=1,
        dangerous_attacks=8, corners=1, xg=0.45, xG=0.45,
    ))
    assert not (result["market"] == "UNDER" and result["can_publish"])


def test_tracker_key_allows_reentry_after_goal(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    tracker = SignalTracker()
    before = {"match_id": "44", "market": "OVER", "home_score": 1, "away_score": 0, "line": 1.5}
    after = {"match_id": "44", "market": "OVER", "home_score": 2, "away_score": 0, "line": 2.5}
    assert tracker._stable_signal_key(before, "OVER") != tracker._stable_signal_key(after, "OVER")


def test_result_resolver_over_and_under():
    resolver = ResultResolver()
    over = {
        "market": "OVER", "entry_home_score": 1, "entry_away_score": 0,
        "entry_minute": 60, "line": 1.5, "max_follow_minutes": 20,
    }
    live = {"home_score": 2, "away_score": 0, "api_minute": 66, "status_short": "2H"}
    assert resolver.resolve(over, live)["result_status"] == "WON"

    under = {
        "market": "UNDER", "entry_home_score": 2, "entry_away_score": 0,
        "entry_minute": 78, "line": 2.5, "max_follow_minutes": 18,
    }
    live_goal = {"home_score": 2, "away_score": 1, "api_minute": 82, "status_short": "2H"}
    assert resolver.resolve(under, live_goal)["result_status"] == "LOST"


def test_v17_routes_are_mounted():
    Config.WORKER_ENABLED = False
    import main
    with TestClient(main.app) as client:
        response = client.get("/v17/dashboard")
        assert response.status_code == 200
        body = response.json()
        assert body["version"] == "JHONNY_ELITE_19.0"
        assert "top_signals" in body
        assert "live_matches" in body


def test_live_dynamics_detects_recent_opening():
    from app.jhonny_elite.live_dynamics import LiveDynamicsMemory

    memory = LiveDynamicsMemory()
    first = match_template(
        fetched_at=1000,
        shots=8, shots_on_target=2, dangerous_attacks=20, corners=3, xg=0.75, xG=0.75,
        home_stats={"shots": 4, "shots_on_target": 1, "dangerous_attacks": 10, "corners": 2, "xG": 0.4},
        away_stats={"shots": 4, "shots_on_target": 1, "dangerous_attacks": 10, "corners": 1, "xG": 0.35},
    )
    second = match_template(
        fetched_at=1090,
        shots=13, shots_on_target=4, dangerous_attacks=30, corners=5, xg=1.20, xG=1.20,
        home_stats={"shots": 8, "shots_on_target": 3, "dangerous_attacks": 19, "corners": 4, "xG": 0.85},
        away_stats={"shots": 5, "shots_on_target": 1, "dangerous_attacks": 11, "corners": 1, "xG": 0.35},
    )

    warmup = memory.enrich(first)
    live = memory.enrich(second)
    assert warmup["dynamics_available"] is False
    assert live["dynamics_available"] is True
    assert live["recent_threat_score"] >= 58
    assert live["dynamic_match_state"] in {"OPENING", "OPEN"}
    assert live["recent_dominant_team"] == "HOME"


def test_tracker_closes_under_when_fixture_finishes(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    tracker = SignalTracker()
    signal = {
        "match_id": "800", "fixture_id": "800", "market": "UNDER", "can_publish": True,
        "home_team": "A", "away_team": "B", "home_score": 2, "away_score": 0,
        "api_minute": 78, "line": 2.5, "official_confidence": 86,
    }
    tracker.register_published_signals([signal])
    result = tracker.update_with_live_matches([
        {"match_id": "800", "fixture_id": "800", "home_score": 2, "away_score": 0,
         "api_minute": 90, "effective_minute": 94, "status_short": "FT", "status_long": "Match Finished"}
    ])
    assert result["summary"]["pending"] == 0
    assert result["summary"]["wins"] == 1
    assert result["newly_closed"][0]["result_status"] == "WON"


def test_asian_integer_total_push_is_void():
    resolver = ResultResolver()
    over = {"market": "OVER", "entry_home_score": 1, "entry_away_score": 1, "entry_minute": 75, "line": 3.0}
    under = {"market": "UNDER", "entry_home_score": 1, "entry_away_score": 1, "entry_minute": 75, "line": 3.0}
    final = {"home_score": 2, "away_score": 1, "api_minute": 90, "status_short": "FT"}
    assert resolver.resolve(over, final)["result_status"] == "VOID"
    assert resolver.resolve(under, final)["result_status"] == "VOID"
