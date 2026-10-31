"""V3.4 acceptance of the official in-play goals quote contract.

No internet, no actual API key and no modification of the user's database.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.config.config import Config
from app.jhonny_elite.master_protocol import MasterDecisionAI20
from app.v17.services.candidate_odds_service import CandidateOddsService
from app.v17.services.odds_market_validator import extract_match_goals_totals, is_full_time_goals_market
from app.v17.services.odds_observation_store import OddsObservationStore

NOW = datetime.now(timezone.utc)


def live_event(name="Goals Over/Under", values=None, fixture=101, status=None, update=None, bet_id=5):
    return [{
        "fixture": {"id": fixture},
        "status": status or {"stopped": False, "blocked": False, "finished": False},
        "update": update or NOW.isoformat(),
        "bets": [{"id": bet_id, "name": name, "values": values or [
            {"value": "Over", "handicap": "2.5", "odd": "1.87", "main": True, "suspended": False},
            {"value": "Under", "handicap": "2.5", "odd": "2.02", "main": True, "suspended": False},
        ]}]
    }]


@pytest.mark.parametrize("name", [
    "Total Corners Over/Under", "Over/Under Corners", "Yellow Cards Over/Under",
    "Shots on Target Over/Under", "Team Total Goals", "Over/Under First Half",
    "Total", "Asian Total Goals", "Next 15 Minutes Goals Over/Under",
])
def test_unrelated_ou_market_not_accepted(name):
    assert not is_full_time_goals_market(name)
    assert extract_match_goals_totals(live_event(name), "OVER", live=True, fixture_id="101") == []


def test_live_quote_correctly_recognizes_selection_line_market_and_fixture():
    result = extract_match_goals_totals(live_event(), "OVER", live=True, fixture_id="101")
    assert len(result) == 1
    assert result[0]["line"] == 2.5
    assert result[0]["odds"] == 1.87
    assert result[0]["main"] is True
    assert result[0]["market_id"] == 5
    assert result[0]["fixture_verified"] is True
    assert result[0]["market_period"] == "FT"
    assert result[0]["quote_is_live"] is True


@pytest.mark.parametrize("status", [
    {"stopped": True, "blocked": False, "finished": False},
    {"stopped": False, "blocked": True, "finished": False},
    {"stopped": False, "blocked": False, "finished": True},
])
def test_halted_or_blocked_fixture_cannot_yield_quote(status):
    assert not extract_match_goals_totals(live_event(status=status), "OVER", live=True, fixture_id="101")


def test_suspended_option_is_discarded_and_main_used_when_duplicates_exist():
    values = [
        {"value": "Over", "handicap": "2.5", "odd": "1.85", "main": True, "suspended": True},
        {"value": "Over", "handicap": "2.5", "odd": "1.75", "main": False, "suspended": False},
    ]
    parsed = extract_match_goals_totals(live_event(values=values), "OVER", live=True, fixture_id="101")
    assert len(parsed) == 1 and parsed[0]["odds"] == 1.75
    values[0]["suspended"] = False
    parsed = extract_match_goals_totals(live_event(values=values), "OVER", live=True, fixture_id="101")
    chosen = CandidateOddsService()._select_candidate(parsed, 2.5)
    assert chosen["odds"] == 1.85


def test_wrong_fixture_and_wrong_outcome_not_accepted():
    assert extract_match_goals_totals(live_event(fixture=102), "OVER", live=True, fixture_id="101") == []
    assert not extract_match_goals_totals(live_event(values=[{"value":"Over 2.5", "handicap":"3.5", "odd":"1.8"}]), "OVER", live=True, fixture_id="101")
    assert not extract_match_goals_totals(live_event(values=[{"value":"Over", "handicap":"15.5", "odd":"1.8"}]), "OVER", live=True, fixture_id="101")


def test_unknown_market_id_requires_correct_live_catalog_not_invented_goal_type():
    unnamed = live_event(name="")
    unnamed[0]["bets"][0].pop("name")
    assert extract_match_goals_totals(unnamed, "OVER", live=True, fixture_id="101") == []
    assert extract_match_goals_totals(unnamed, "OVER", live=True, fixture_id="101",
                                      market_catalog={"5": "Total Corners"}) == []
    good = extract_match_goals_totals(unnamed, "OVER", live=True, fixture_id="101",
                                    market_catalog={"5": "Goals Over/Under"})
    assert len(good) == 1


def test_unsupported_integer_line_is_not_given_fake_binary_expected_value():
    assert CandidateOddsService._poisson_line_win_probability(0.6, 1, 2.0, "OVER") is None


def test_under_candidate_prefers_one_goal_margin(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(Config, "API_ECONOMY_MODE", False)
    monkeypatch.setattr(Config, "CANDIDATE_ODDS_ENABLED", True)
    monkeypatch.setattr(Config, "THE_ODDS_FALLBACK_ENABLED", False)
    monkeypatch.setattr(Config, "ODDS_PREMATCH_FALLBACK_ENABLED", False, raising=False)
    service = CandidateOddsService()
    service.api_key = "offline-test-key"
    service.observation_store = OddsObservationStore(str(tmp_path / "quotes.jsonl"))
    fake = live_event(values=[
        {"value": "Under", "handicap": "2.5", "odd": "1.80"},
        {"value": "Under", "handicap": "3.5", "odd": "1.79"},
    ])
    def fake_http(url, headers=None, params=None, timeout=None):
        assert url.endswith("/odds/live")
        assert params == {"fixture": "101"}
        return SimpleNamespace(status_code=200, content=b"stub", headers={}, json=lambda: {"response": fake})
    monkeypatch.setattr("app.v17.services.candidate_odds_service.requests.get", fake_http)
    value = service.enrich({"fixture_id": "101", "home_score": 2, "away_score": 0}, "UNDER",
                           math_evidence={"expected_goals_remaining": 0.3, "calibration_status": "NOT_VALIDATED_OUT_OF_SAMPLE"})
    assert value["line"] == 3.5
    assert value["market_type"] == "MATCH_GOALS_TOTAL"
    assert value["quote_is_live"] and value["fixture_verified"]
    assert value["valuation_status"] == "MODEL_NOT_CALIBRATED"
    journal = (tmp_path / "quotes.jsonl").read_text(encoding="utf8")
    assert len(journal.splitlines()) == 1
    assert "offline-test-key" not in journal
    entry = json.loads(journal.splitlines()[0]); assert entry["line"] == 3.5 and entry["selection"] == "UNDER"


def test_genuine_live_quote_requires_timestamp_and_calibration(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    svc = CandidateOddsService()
    match = {"home_score": 1, "away_score": 0}
    row = svc._result_from_api_football(live_event(values=[
        {"value":"Over", "handicap": "1.5", "odd":"1.9"}
    ]), "OVER", 1.5, 60.0, "API_FOOTBALL_LIVE_ODDS", fixture_id="101")
    assert row["market_verified"] and row["fixture_verified"]
    evidence = {"expected_goals_remaining": 0.9, "calibration_status": "VALIDATED_OUT_OF_SAMPLE"}
    priced = svc._value_for_exact_line(row, match, "OVER", evidence)
    assert priced["valuation_status"] == "VERIFIED_FRESH_CALIBRATED"
    assert priced["has_positive_value"] is True
    assert priced["expected_value"] > 0
    row["odds_timestamp"] = None
    assert svc._value_for_exact_line(row, match, "OVER", evidence)["valuation_status"] == "QUOTE_TIMESTAMP_NOT_AVAILABLE"
    row["odds_timestamp"] = (NOW - timedelta(minutes=20)).isoformat()
    assert svc._value_for_exact_line(row, match, "OVER", evidence)["valuation_status"] == "STALE_ODDS"
    row["odds_timestamp"] = NOW.isoformat()
    row["fixture_verified"] = False
    assert svc._value_for_exact_line(row, match, "OVER", evidence)["valuation_status"] == "FIXTURE_UNVERIFIED"


def test_prematch_quote_can_be_seen_but_never_authorized_as_live(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    svc = CandidateOddsService()
    raw = [{"fixture": {"id": 101}, "bookmakers": [{"id": 4, "name": "ExampleBook", "bets": [
        {"name":"Goals Over/Under", "id": 26, "values": [{"value":"Over 1.5", "odd":"1.9"}]}
    ]}]}]
    row = svc._result_from_api_football(raw, "OVER", 1.5, 60, "API_FOOTBALL_PREMATCH_ODDS", fixture_id="101")
    assert row["odds_available"] and not row["quote_is_live"]
    val = svc._value_for_exact_line(row, {"home_score":1,"away_score":0}, "OVER",
                                    {"expected_goals_remaining":.9,"calibration_status":"VALIDATED_OUT_OF_SAMPLE"})
    assert val["valuation_status"] == "QUOTE_NOT_LIVE"
    assert not val["has_positive_value"]


def test_master_blocks_uncertified_odds_even_with_high_synthetic_scores():
    val = MasterDecisionAI20().decide(
        match={"api_minute": 68, "home_score": 1, "away_score": 0, "recent_threat_score": 99},
        direction="OVER", candidate_score=98, candidate=True, blockers=[],
        clock={"clock_status":"CLOCK_OK"},
        data_truth={"data_truth_status":"EXCELLENT", "data_truth_score":98},
        context={"over_context_score":98,"rhythm_score":99},
        tactical={"tactical_score":98},risk={"risk_score":10,"risk_status":"LOW"},
        pre_match={"pre_match_available":True,"over_pre_match_score":98},
        math_evidence={"math_support_over":98},
        odds={"odds_available":True,"verification_required":True,"line":1.5,"odds":1.9,
              "has_positive_value":True,"expected_value":.5,"value_edge":35,
              "valuation_status":"MODEL_NOT_CALIBRATED","quote_is_live":True,
              "fixture_verified":True,"market_verified":True,"market_type":"MATCH_GOALS_TOTAL","market_period":"FT"},
        contradiction={"critical_contradictions": []},
    )
    assert val["official_can_publish"] is False
    assert "LIVE_GOALS_MARKET_NOT_VERIFIED" in val["official_warnings"]


def test_unrelated_market_does_not_fallback_to_prematch_unless_opted_in(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(Config, "API_ECONOMY_MODE", False)
    monkeypatch.setattr(Config, "CANDIDATE_ODDS_ENABLED", True)
    monkeypatch.setattr(Config, "THE_ODDS_FALLBACK_ENABLED", False)
    monkeypatch.setattr(Config, "ODDS_PREMATCH_FALLBACK_ENABLED", False, raising=False)
    svc = CandidateOddsService()
    svc.api_key = "offline-test-key"
    paths=[]
    def fake_http(url, **kwargs):
        paths.append(url)
        return SimpleNamespace(status_code=200, content=b"stub", headers={},
                               json=lambda: {"response": live_event(name="Total Corners Over/Under")})
    monkeypatch.setattr("app.v17.services.candidate_odds_service.requests.get", fake_http)
    result = svc.enrich({"fixture_id":"101","home_score":1,"away_score":0}, "OVER",
                        math_evidence={"expected_goals_remaining":0.8})
    assert not result["odds_available"]
    assert len(paths) == 1 and paths[0].endswith("/odds/live")


def test_unknown_quote_is_warning_not_a_false_critical_football_contradiction():
    from app.jhonny_elite.master_protocol import ContradictionJudgeMaster
    result = ContradictionJudgeMaster().evaluate(
        direction="OVER",
        data_truth={"data_truth_status":"EXCELLENT"},
        match={"recent_threat_score":70},
        context={"rhythm_score":66},
        tactical={"false_pressure_risk":10},
        odds={"odds_available":True,"verification_required":True,
              "valuation_status":"MODEL_NOT_CALIBRATED","has_positive_value":False},
    )
    assert result["contradiction_status"] == "WARNING"
    assert result["critical_contradictions"] == []
    assert "MARKET_NOT_VALIDATED" in [x["code"] for x in result["contradictions"]]


def test_fixture_attached_price_without_market_provenance_is_not_displayed(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(Config, "API_ECONOMY_MODE", False)
    monkeypatch.setattr(Config, "CANDIDATE_ODDS_ENABLED", True)
    monkeypatch.setattr(Config, "THE_ODDS_FALLBACK_ENABLED", False)
    monkeypatch.setattr(Config, "ODDS_ALLOW_ATTACHED_QUOTE", False, raising=False)
    monkeypatch.setattr(Config, "ODDS_PREMATCH_FALLBACK_ENABLED", False, raising=False)
    svc = CandidateOddsService(); svc.api_key = "test"
    def fake_http(url, **kwargs):
        return SimpleNamespace(status_code=200, content=b"stub", headers={}, json=lambda: {"response": []})
    monkeypatch.setattr("app.v17.services.candidate_odds_service.requests.get", fake_http)
    result = svc.enrich({"fixture_id":"101", "home_score":1,"away_score":0,"odds":1.88,"line":2.5},
                        "OVER", math_evidence={"expected_goals_remaining":.5})
    assert result["odds_available"] is False
    assert result["valuation_status"] == "NO_REAL_ODDS"
