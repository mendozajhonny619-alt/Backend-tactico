"""V3.3 acceptance tests - offline, no football provider traffic."""
from datetime import datetime, timezone
from pathlib import Path

from app.config.config import Config
from app.jhonny_elite.engine import JhonnyEliteEngine
from app.jhonny_elite.master_protocol import DataTruthAI
from app.v17.ai.advanced_probability_engine import AdvancedProbabilityEngine
from app.v17.ai.scenario_policy_v3 import choose_scenarios
from app.v17.core.clock_guard import ClockGuard, parse_datetime
from app.v17.core.tactical_scanner23 import build_tactical_scanner23
from app.v17.dashboard.dashboard_adapter import V17DashboardAdapter

BASE = Path(__file__).resolve().parents[3]


def test_primary_without_secondary_for_stable_match():
    scores = [{'score': '2-0','probability': 45}, {'score': '3-0','probability': 35}]
    result = choose_scenarios({'api_minute': 70}, scores)
    assert result['scenario_primary']['score'] == '2-0'
    assert result['scenario_secondary'] is None


def test_secondary_only_after_material_change():
    scores = [{'score': '2-0','probability': 45}, {'score': '2-1','probability': 35}]
    result = choose_scenarios({'api_minute': 70, 'post_goal_reanalysis': True}, scores)
    assert result['scenario_secondary']['score'] == '2-1'
    assert result['scenario_secondary_reason'] == 'EVENTO_MATERIAL_REQUIERE_REANALISIS'


def test_late_game_stoppage_time_uncertainty_is_not_published_as_live_prediction():
    r=AdvancedProbabilityEngine().evaluate({'api_minute':97,'home_score':2,'away_score':0,'status_short':'2H'}, {}, {})
    assert r['expected_goals_remaining'] == 0 and r['primary_final_score'] == '2-0'
    assert r['scenario_secondary'] is None
    import inspect
    assert 'MATCH_END_TIME_UNVERIFIED' in inspect.getsource(JhonnyEliteEngine.analyze_match)


def test_full_distribution_internal_vs_at_most_two_public_scenarios():
    r=AdvancedProbabilityEngine().evaluate({'api_minute':55,'home_score':1,'away_score':1}, {}, {})
    assert abs(sum(x['probability'] for x in r['score_distribution_full'])-100)<0.0001
    assert len(r['alternative_scores']) <= 1


def test_tactical_23_and_mini_6_nd_without_data():
    r=build_tactical_scanner23({'minute':65,'home_score':2,'away_score':0})
    assert len(r['criteria'])==23 and len(r['mini_factors'])==6
    assert r['evaluated_both']==0 and r['mini_evaluated']==0
    assert all(x['quality']=='ND' and x['score_home'] is None for x in r['criteria'])


def test_tactical_scores_require_source_fields_and_do_not_invent_pressures():
    m={'minute':72,'home_score':2,'away_score':0,'has_live_stats':True,
       'home_stats':{'shots':14,'shots_on_target':6,'stats_available_fields':[]},
       'away_stats':{'shots':3,'shots_on_target':1,'stats_available_fields':[]}}
    assert build_tactical_scanner23(m)['evaluated_both']==0
    for key in ('home_stats','away_stats'):
        m[key]['stats_available_fields']=['Total Shots','Shots on Goal']
    r=build_tactical_scanner23(m)
    assert r['criteria'][7]['score_home'] is not None
    assert r['criteria'][8]['score_home'] is not None
    assert r['criteria'][13]['score_home'] is None


def test_real_zero_xg_retained_not_treated_as_unknown():
    r=build_tactical_scanner23({'minute':55,'has_live_stats':True,
       'home_stats':{'xG':0,'stats_available_fields':['expected_goals']},
       'away_stats':{'xG':0.8,'stats_available_fields':['expected_goals']}})
    assert r['criteria'][20]['home_value']==0
    assert r['criteria'][20]['score_home']==1


def test_unix_timestamp_int_float_and_string_support():
    ts=datetime.now(timezone.utc).timestamp()
    assert abs((parse_datetime(ts)-datetime.now(timezone.utc)).total_seconds())<5
    assert abs((parse_datetime(str(ts))-datetime.now(timezone.utc)).total_seconds())<5
    r=ClockGuard().evaluate({'api_minute':50,'fetched_at':ts,'has_live_stats':True})
    assert r['data_age_known'] and r['data_age_seconds']<5


def test_datatruth_unknown_freshness_not_excellent_and_stale_rejected():
    m={'api_minute':70,'has_live_stats':True,'shots':16,'shots_on_target':7,'dangerous_attacks':20,'xG':1.5}
    base={'data_valid':True,'data_issues':[]}
    r=DataTruthAI().evaluate(m,base,ClockGuard().evaluate(m))
    assert r['data_truth_status']!='EXCELLENT'
    stale={**m,'source_timestamp':'2020-01-01T00:00:00Z'}
    old=DataTruthAI().evaluate(stale,base,ClockGuard().evaluate(stale))
    assert old['data_truth_status']=='STALE'


def test_fixture_team_logos_league_logo_and_flag_preserved():
    raw={'fixture':{'id':123},'teams':{
      'home':{'name':'A','logo':'https://media.api-sports.io/football/teams/1.png'},
      'away':{'name':'B','logo':'https://media.api-sports.io/football/teams/2.png'}},
      'league':{'id':99,'name':'Série A','country':'Brazil','logo':'https://media.api-sports.io/football/leagues/99.png',
                'flag':'https://media.api-sports.io/flags/br.svg'}}
    out=V17DashboardAdapter()._attach_visual_identity(raw)
    assert out['league']=='Série A' and out['country']=='Brazil'
    assert out['home_logo'].endswith('1.png') and out['away_logo'].endswith('2.png')
    assert out['league_logo'].endswith('99.png') and out['country_flag'].endswith('br.svg')


def test_top_six_by_value_and_shadow_never_publishes(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    engine=JhonnyEliteEngine()
    monkeypatch.setattr(engine,'analyze_match',lambda m:{
       'match_id':m['match_id'],'can_publish':True,'official_can_publish':True,
       'official_status':'CONFIRMED_SIGNAL','decision_status':'CONFIRMED_SIGNAL',
       'official_expected_value':m['ev'],'odds_age_seconds':2,'data_truth_score':92,'official_confidence':81})
    fixtures=[{'match_id':str(i),'ev':i*0.02} for i in range(9)]
    monkeypatch.setattr(Config,'SHADOW_MODE',False)
    actual=engine.process_live_matches(fixtures)
    assert [m['match_id'] for m in actual['top_signals']]==['8','7','6','5','4','3']
    monkeypatch.setattr(Config,'SHADOW_MODE',True)
    shadow=engine.process_live_matches(fixtures)
    assert len(shadow['top_signals'])==0 and len(shadow['shadow_candidates'])==6
    assert all(not m['official_can_publish'] for m in shadow['shadow_candidates'])


def test_frontend_labels_and_local_snapshot_only():
    html=(BASE/'src/panel_v3/index.html').read_text(encoding='utf8')
    js=(BASE/'src/panel_v3/panel.js').read_text(encoding='utf8')
    assert 'Observación' in html and 'Partidos LIVE' in html
    assert 'scenario_secondary' in js and 'scoreScenario' in js
    assert "get('/v17/dashboard')" in js and "setInterval(refresh,15000)" in js
