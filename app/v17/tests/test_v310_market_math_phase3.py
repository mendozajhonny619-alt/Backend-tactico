"""V3.10 phase 3: actual line math, quote safety, model diagnostics.

No network, no API credentials and no changes to production history.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from types import SimpleNamespace

import pytest

from app.config.config import Config
from app.jhonny_elite.master_protocol import MasterDecisionAI20
from app.v17.ai.advanced_probability_engine import AdvancedProbabilityEngine
from app.v17.ai.poisson_market_math import half_goal_line_probability, preview_full_time_lines
from app.v17.services.candidate_odds_service import CandidateOddsService


def quote(*, price=1.8, line=3.5, selection="UNDER", when=None):
    return {
        "odds_available": True, "odds_source": "API_FOOTBALL_LIVE_ODDS",
        "quote_is_live": True, "market_verified": True, "fixture_verified": True,
        "market_direction": selection, "market_type": "MATCH_GOALS_TOTAL",
        "market_period": "FT", "odds": price, "line": line,
        "odds_timestamp": when or datetime.now(timezone.utc).isoformat(),
        "odds_status": "MATCH_GOALS_TOTAL_RECOGNIZED",
    }


def evidence(lam=0.8, calibrated=False):
    return {
        "expected_goals_remaining": lam,
        "calibration_status": "VALIDATED_OUT_OF_SAMPLE" if calibrated else "NOT_VALIDATED_OUT_OF_SAMPLE",
    }


@pytest.mark.parametrize("lam", [0, .05, .5, .8, 1.2, 2.0, 3.5, 5, 15])
@pytest.mark.parametrize("score", [0, 1, 2, 4])
@pytest.mark.parametrize("line", [.5, 1.5, 2.5, 3.5, 4.5, 5.5])
def test_all_binary_ft_line_probabilities_complement_exactly(lam, score, line):
    over = half_goal_line_probability(lam, score, line, "OVER")
    under = half_goal_line_probability(lam, score, line, "UNDER")
    assert 0 <= over <= 1 and 0 <= under <= 1
    assert over + under == pytest.approx(1, abs=1e-12)


@pytest.mark.parametrize('invalid', [float('nan'), float('inf'), float('-inf'), -1, 21, None, True, 'broken'])
def test_invalid_lambda_produces_no_probability(invalid):
    assert half_goal_line_probability(invalid, 2, 3.5, "UNDER") is None


@pytest.mark.parametrize('line', [0, 1.0, 2.0, 2.25, 3.75, -0.5, float('nan')])
def test_unsupported_lines_never_receive_binary_ev(line):
    assert half_goal_line_probability(1.0, 2, line, "OVER") is None


def test_under_3_5_is_distinct_from_zero_additional_goals_at_2_0():
    lam = 0.8
    no_more = math.exp(-lam)
    under = half_goal_line_probability(lam, 2, 3.5, "UNDER")
    assert under == pytest.approx(math.exp(-lam) * (1 + lam), abs=1e-10)
    assert under > no_more + .3
    assert half_goal_line_probability(lam, 2, 2.5, "UNDER") == pytest.approx(no_more)


def test_market_probability_preview_is_monotone_and_not_a_quote():
    data = preview_full_time_lines(1.2, 2)
    ovs = [row["over_probability"] for row in data.values()]
    assert ovs == sorted(ovs, reverse=True)
    assert all(abs(x["over_probability"] + x["under_probability"] - 100) < 1e-6 for x in data.values())


def test_math_model_keeps_provenance_and_unverified_extreme_warning():
    result = AdvancedProbabilityEngine().evaluate(
        {"api_minute": 30, "home_score": 1, "away_score": 0,
         "shots": 22, "shots_on_target": 14, "xg_available": False,
         "has_live_stats": True, "data_quality": "MEDIUM"}, {}, {})
    assert result["calibration_status"] == "NOT_VALIDATED_OUT_OF_SAMPLE"
    assert result["raw_model_probability_status"] == "RESEARCH_ONLY_NOT_CALIBRATED"
    assert "XG_ESTIMATED_PROXY_NOT_PROVIDER_XG" in result["model_limitations"]
    assert "GENERIC_PREMATCH_AVERAGE_2_45" in result["model_limitations"]
    assert result["model_input_diagnostics"]["quality_of_snapshot"] == "MEDIUM"
    assert result["ft_line_probabilities_research_only"]["1.5"]["over_probability"] == pytest.approx(result["probability_next_goal"], abs=.01)


def test_model_finite_on_corrupt_provider_number():
    result = AdvancedProbabilityEngine().evaluate({
        "api_minute": 75, "home_score": 0, "away_score": 0,
        "xG": float('nan'), "shots": float('inf'), "shots_on_target": "nan",
        "dangerous_attacks": "garbage", "xg_available": False,
    }, {}, {})
    assert math.isfinite(result["expected_goals_remaining"])
    assert math.isfinite(result["probability_next_goal"])
    assert abs(sum(s["probability"] for s in result["score_distribution_full"]) - 100) < .0001


def test_unpriced_quote_cannot_claim_positive_ev_even_if_any_goal_99_percent(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    svc = CandidateOddsService()
    synthetic = {"line": 4.5, "odds": 1.9, "bookmaker": "Test", "market_verified": True,
                 "market_type": "MATCH_GOALS_TOTAL", "market_period": "FT",
                 "fixture_verified": True, "quote_is_live": True,
                 "market_id": 5, "timestamp": datetime.now(timezone.utc).isoformat()}
    raw = svc._make_result(synthetic, "OVER", 4.5, 99.0, "API_FOOTBALL_LIVE_ODDS")
    assert raw["has_positive_value"] is False
    assert raw["expected_value"] == 0
    assert raw["model_probability_for_value"] is None


def test_undervaluation_uses_exact_line_probability_not_p_no_goal(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    svc = CandidateOddsService()
    result = svc._value_for_exact_line(quote(), {"home_score": 2, "away_score": 0}, "UNDER", evidence(.8))
    assert result["quote_validation_status"] == "VERIFIED_FRESH_LIVE_GOALS_FT"
    assert result["model_probability_for_value"] == pytest.approx(80.88, abs=.05)
    assert result["has_positive_value"] is False
    assert result["expected_value"] == 0 and result["value_edge"] == 0
    assert result["valuation_status"] == "MODEL_NOT_CALIBRATED"


def test_independently_calibrated_quote_can_be_valued_for_exact_line(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    svc = CandidateOddsService()
    result = svc._value_for_exact_line(quote(), {"home_score": 2, "away_score": 0}, "UNDER", evidence(.8, True))
    assert result["valuation_status"] == "VERIFIED_FRESH_CALIBRATED"
    assert result["expected_value"] == pytest.approx(math.exp(-.8) * (1+.8) * 1.8 - 1, abs=.0001)
    assert result["market_value_authorized"] and result["has_positive_value"]


@pytest.mark.parametrize('change,reason', [
    ({"quote_is_live": False}, "QUOTE_NOT_LIVE"),
    ({"odds_source": "API_FOOTBALL_PREMATCH_ODDS"}, "QUOTE_NOT_LIVE"),
    ({"market_type": "CORNERS_TOTAL"}, "MARKET_UNVERIFIED"),
    ({"fixture_verified": False}, "FIXTURE_UNVERIFIED"),
    ({"market_direction": "OVER"}, "MARKET_DIRECTION_MISMATCH"),
    ({"odds_timestamp": None}, "QUOTE_TIMESTAMP_NOT_AVAILABLE"),
    ({"odds_timestamp": "2026-10-30T12:30:00"}, "QUOTE_TIMESTAMP_HAS_NO_TIMEZONE"),
    ({"odds_timestamp": "bad"}, "QUOTE_TIMESTAMP_INVALID"),
    ({"odds_timestamp": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}, "STALE_ODDS"),
    ({"odds_timestamp": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()}, "STALE_ODDS"),
    ({"odds": 1.05}, "PRICE_OUT_OF_ALLOWED_RANGE"),
    ({"odds": 12.1}, "PRICE_OUT_OF_ALLOWED_RANGE"),
    ({"line": 1.5}, "LINE_ALREADY_SETTLED_OR_UNSAFE"),
])
def test_unverified_quote_never_creates_ev(change, reason, tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    q = quote(); q.update(change)
    result = CandidateOddsService()._value_for_exact_line(
        q, {"home_score": 2, "away_score": 0}, "UNDER", evidence(.8, True))
    assert result["valuation_status"] == reason
    assert not result["has_positive_value"] and result["expected_value"] == 0
    assert not result["market_value_authorized"]


def test_unsupported_integer_line_refuses_ev_with_real_quote(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    q = quote(line=3.0)
    result = CandidateOddsService()._value_for_exact_line(q, {"home_score":2,"away_score":0}, "UNDER", evidence(.8, True))
    assert result["valuation_status"] == "UNSUPPORTED_SETTLEMENT_LINE"
    assert result["expected_value"] == 0


def test_master_uses_under_exact_line_instead_of_zero_goal_probability():
    match={"api_minute":76,"home_score":2,"away_score":0,"recent_threat_score":10,"has_live_stats":True}
    odds = CandidateOddsService()._value_for_exact_line(quote(price=1.8),match,"UNDER",evidence(.8, True))
    master=MasterDecisionAI20().decide(
        match=match, direction="UNDER", candidate_score=95, candidate=True,
        blockers=[], clock={"clock_status":"CLOCK_OK"},
        data_truth={"data_truth_status":"EXCELLENT","data_truth_score":96},
        context={"over_context_score":10,"under_context_score":96,"rhythm_score":20},
        tactical={"tactical_score":95}, risk={"risk_score":5,"risk_status":"LOW"},
        pre_match={"pre_match_available":True,"under_pre_match_score":95},
        math_evidence={"math_support_under":44.93,"calibration_status":"VALIDATED_OUT_OF_SAMPLE"},
        odds=odds, contradiction={"critical_contradictions":[]},
    )
    assert all(not s.startswith('MATH_SUPPORT_44.9') for s in master['official_warnings'])
    assert master['official_market_probability'] == pytest.approx(80.88, abs=.05)
    assert master['official_market_risk'] == 'ASSESSED'


def test_market_risk_not_evaluable_when_no_verified_quote():
    out=MasterDecisionAI20().decide(
        match={"api_minute":76,"home_score":2,"away_score":0},
        direction="UNDER", candidate_score=90,candidate=True,blockers=[],
        clock={"clock_status":"CLOCK_OK"},
        data_truth={"data_truth_status":"EXCELLENT","data_truth_score":90},
        context={"under_context_score":95,"rhythm_score":20},
        tactical={"tactical_score":90}, risk={"risk_score":5,"risk_status":"LOW"},
        pre_match={"pre_match_available":True,"under_pre_match_score":90},
        math_evidence=evidence(.8), odds={"odds_available":False,"valuation_status":"NO_REAL_ODDS"},
        contradiction={"critical_contradictions":[]},
    )
    assert out['official_market_risk'] == 'NOT_EVALUABLE'
    assert out['official_market_probability'] is None
    assert not out['official_can_publish']


def test_cache_invalidated_when_red_card_or_score_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(Config, "API_ECONOMY_MODE", False)
    monkeypatch.setattr(Config, "THE_ODDS_FALLBACK_ENABLED", False)
    monkeypatch.setattr(Config, "CANDIDATE_ODDS_ENABLED", True)
    svc=CandidateOddsService(ttl_seconds=90)
    svc.api_key="offline-only"
    calls=[]
    now=datetime.now(timezone.utc).isoformat()
    def respond(url, **kwargs):
        calls.append(url)
        return SimpleNamespace(status_code=200, content=b'fixture', headers={},json=lambda: {'response': [{
            'fixture':{'id':101},'status':{'stopped':False,'blocked':False,'finished':False},
            'update':now,'bets':[{'id':5,'name':'Goals Over/Under','values':[
                {'value':'Over','handicap':'2.5','odd':'1.80','main':True,'suspended':False},
            ]}] } ]})
    monkeypatch.setattr('app.v17.services.candidate_odds_service.requests.get',respond)
    m={'fixture_id':'101','home_score':2,'away_score':0,'red_cards':0}
    svc.enrich(m,'OVER',math_evidence=evidence(.8))
    svc.enrich(m,'OVER',math_evidence=evidence(.8))
    assert len(calls)==1
    svc.enrich({**m,'red_cards':1},'OVER',math_evidence=evidence(.8))
    assert len(calls)==2
    svc.enrich({**m,'post_goal_reanalysis':True},'OVER',math_evidence=evidence(.8))
    assert len(calls)==3


def test_provider_naive_time_is_not_silently_promoted_to_utc():
    from app.v17.services.odds_market_validator import extract_match_goals_totals
    event = [{
        "fixture": {"id": 101}, "update": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "status": {"stopped": False, "blocked": False, "finished": False},
        "bets": [{"id": 5, "name": "Goals Over/Under", "values": [
            {"value": "Under", "handicap": "3.5", "odd": "1.8"},
        ]}],
    }]
    selection = extract_match_goals_totals(event, "UNDER", live=True, fixture_id="101")[0]
    assert selection["timestamp"] is None
    row = CandidateOddsService()._make_result(selection, "UNDER", 3.5, 95, "API_FOOTBALL_LIVE_ODDS")
    result = CandidateOddsService()._value_for_exact_line(
        row, {"home_score": 2, "away_score": 0}, "UNDER", evidence(.8, True))
    assert result["valuation_status"] == "QUOTE_TIMESTAMP_NOT_AVAILABLE"
    assert result["expected_value"] == 0
