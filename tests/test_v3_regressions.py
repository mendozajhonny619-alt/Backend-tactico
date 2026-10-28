"""Pruebas de regresion V3 sin claves ni consumo de API."""
from __future__ import annotations

import base64
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.config.config import Config
from app.fetchers.live_match_fetcher import LiveMatchFetcher
from app.jhonny_elite.engine import JhonnyEliteEngine
from app.v17.ai.advanced_probability_engine import AdvancedProbabilityEngine
from app.v17.core.comparison23 import build_comparison23
from app.v17.signals.result_resolver import ResultResolver
from app.v17.signals.signal_tracker import SignalTracker


def test_empty_live_fetch_normalizes_without_undefined_name():
    fetcher = LiveMatchFetcher()
    assert fetcher._normalize_api_football([]) == []


def test_shadow_candidate_visible_but_never_official(monkeypatch):
    monkeypatch.setattr(Config, 'SHADOW_MODE', True)
    engine = JhonnyEliteEngine()
    monkeypatch.setattr(engine, 'analyze_match', lambda raw: {
        'match_id': raw['match_id'], 'can_publish': True, 'decision_status': 'CONFIRMED_SIGNAL',
        'official_status': 'CONFIRMED_SIGNAL', 'market': 'OVER', 'line': 1.5,
        'official_confidence': 81, 'value_edge': 0.1,
    })
    result = engine.process_live_matches([{'match_id': 23}])
    assert result['top_signals'] == []
    assert len(result['shadow_candidates']) == 1
    assert result['shadow_candidates'][0]['shadow_only'] is True
    assert result['shadow_candidates'][0]['can_publish'] is False
    assert result['shadow_candidates'][0] in result['observe']


def test_market_status_other_than_confirmed_is_never_published(monkeypatch):
    monkeypatch.setattr(Config, 'SHADOW_MODE', False)
    engine = JhonnyEliteEngine()
    monkeypatch.setattr(engine, 'analyze_match', lambda raw: {
        'match_id': raw['match_id'], 'can_publish': False,
        'decision_status': 'OPPORTUNITY', 'market': 'NO_BET'
    })
    result = engine.process_live_matches([{'match_id': 50}])
    assert result['top_signals'] == []
    assert len(result['opportunities']) == 1


def test_legitimate_zero_score_in_resolver():
    resolver = ResultResolver()
    signal = {'market': 'UNDER', 'line': 3.5, 'entry_home_score': 1, 'entry_away_score': 1,
              'entry_minute': 75}
    current = {'home_score': 0, 'away_score': 1, 'local_score': 3,
               'visitante_score': 2, 'status_short': 'FT', 'api_minute': 90}
    settled = resolver.resolve(signal, current)
    assert settled['current_score'] == '0-1'
    assert settled['result_status'] == 'WON'


@pytest.mark.parametrize('home_lam,away_lam', [(0.0, 0.0), (0.3, 0.9), (2.1, 1.5), (7.0, 8.0)])
def test_score_distribution_is_complete(home_lam, away_lam):
    cases = AdvancedProbabilityEngine()._score_scenarios(1, 0, home_lam, away_lam)
    assert cases
    assert abs(sum(x['probability'] for x in cases) - 100.0) < 0.0001
    assert all(x['probability'] >= 0 for x in cases)


def test_comparison_has_23_na_rows_without_invented_stats():
    comparison = build_comparison23({'fixture_id': 100, 'home_score': 0, 'away_score': 0, 'minute': 20})
    assert comparison['count'] == 23
    assert [x['number'] for x in comparison['criteria']] == list(range(1, 24))
    assert comparison['criteria'][8]['status'] == 'N/A'
    assert all(x['score_home'] is None and x['score_away'] is None for x in comparison['criteria'])


def test_comparison_retains_real_zero_xg():
    comparison = build_comparison23({
        'has_live_stats': True, 'home_stats': {'xG': 0.0, 'stats_available_fields': ['expected_goals']},
        'away_stats': {'xG': 0.15, 'stats_available_fields': ['expected_goals']}
    })
    row = comparison['criteria'][8]
    assert row['status'] == 'AVAILABLE'
    assert row['home_value'] == 0.0
    assert row['away_value'] == 0.15


def test_bolivian_day_changes_at_midnight(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, 'DATA_DIR', str(tmp_path))
    monkeypatch.setattr(Config, 'RESULTS_CUTOFF_HOUR', 0)
    monkeypatch.setattr(Config, 'RESULTS_CUTOFF_MINUTE', 0)
    tracker = SignalTracker()
    assert tracker._logical_day_for_datetime(datetime(2026, 10, 29, 3, 59, tzinfo=timezone.utc)) == '2026-10-28'
    assert tracker._logical_day_for_datetime(datetime(2026, 10, 29, 4, 0, tzinfo=timezone.utc)) == '2026-10-29'


def test_local_panel_served_and_private_lan_requires_password(monkeypatch):
    monkeypatch.setattr(Config, 'WORKER_ENABLED', False)
    monkeypatch.setenv('JHONNY_LAN_PASSWORD', 'clave-prueba-123')
    from main import app
    with TestClient(app) as client:
        assert client.get('/panel').status_code == 401
        creds = base64.b64encode(b'jhonny:clave-prueba-123').decode()
        headers = {'Authorization': 'Basic ' + creds}
        panel = client.get('/panel', headers=headers)
        assert panel.status_code == 200
        assert 'JHONNY ELITE' in panel.text
        assert client.get('/ready', headers=headers).json()['version'] == '3.0-local'
        assert client.get('/elite-live/dashboard', headers=headers, follow_redirects=True).status_code == 200


def test_missing_live_snapshot_does_not_erase_official_signal(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, 'DATA_DIR', str(tmp_path))
    monkeypatch.setattr(Config, 'SCAN_INTERVAL_SECONDS', 30)
    tracker = SignalTracker()
    signal = {'match_id': '880', 'fixture_id': '880', 'market': 'OVER', 'line': 1.5,
              'odds': 1.85, 'can_publish': True, 'home_score': 0, 'away_score': 0, 'api_minute': 55}
    tracker.register_published_signals([signal])
    assert len(tracker.pending()) == 1
    for _ in range(42):
        tracker.update_with_live_matches([])
    pending = tracker.pending()
    assert len(pending) == 1
    assert pending[0]['operational_active'] is False
    assert pending[0]['tracking_status'] == 'SUSPENDED_AWAITING_SETTLEMENT'
    assert tracker.summary()['losses'] == 0


def test_api_budget_adapts_to_small_provider_plan():
    from app.services.api_quota_monitor import ApiQuotaMonitor
    monitor = ApiQuotaMonitor()
    monitor._state.update(daily_limit=100, daily_remaining=80)
    assert monitor.can_spend(required=1, reserve=300)
    assert monitor.pressure_level() == 'NORMAL'
    monitor._state['daily_remaining'] = 20
    assert not monitor.can_spend(required=1, reserve=300)
    monitor._state['daily_remaining'] = 9
    assert monitor.pressure_level() == 'CRITICAL'


def test_launch_config_creates_single_password_line(tmp_path, monkeypatch):
    from scripts import start_local
    example = tmp_path / '.env.example'
    example.write_text('API_FOOTBALL_KEY=\nJHONNY_LAN_PASSWORD=\n',encoding='utf-8')
    monkeypatch.setattr(start_local, 'ROOT', tmp_path)
    monkeypatch.setattr(start_local, 'ENV', tmp_path / '.env')
    settings = start_local.config_lines()
    assert len(settings['JHONNY_LAN_PASSWORD']) >= 20
    actual = (tmp_path / '.env').read_text(encoding='utf-8')
    assert sum(line.startswith('JHONNY_LAN_PASSWORD=') for line in actual.splitlines()) == 1
    assert start_local.config_lines()['JHONNY_LAN_PASSWORD'] == settings['JHONNY_LAN_PASSWORD']


def test_shadow_survives_full_dashboard_adapter_pipeline(tmp_path, monkeypatch):
    from app.v17.dashboard.dashboard_adapter import V17DashboardAdapter
    monkeypatch.setattr(Config, 'DATA_DIR', str(tmp_path))
    monkeypatch.setattr(Config, 'SHADOW_MODE', True)
    adapter = V17DashboardAdapter()
    fixture = {
        'fixture_id': '33010', 'match_id': '33010', 'home_team': 'LOCAL',
        'away_team': 'VISITANTE', 'league': 'Serie A', 'country': 'Italy',
        'api_minute': 77, 'minute': 77, 'home_score': 1, 'away_score': 0,
    }
    monkeypatch.setattr(adapter.league_filter, 'filter_matches', lambda rows: {
        'allowed': rows, 'blocked_by_league': [], 'summary': {'allowed': len(rows)}
    })
    monkeypatch.setattr(adapter.engine, 'analyze_match', lambda raw: {
        **raw, 'can_publish': True, 'decision_status': 'CONFIRMED_SIGNAL',
        'official_confidence': 90, 'market': 'OVER', 'line': 1.5, 'odds': 1.8
    })
    result = adapter.build_from_raw_matches([fixture], source_status='SIMULATED_TEST')
    assert result['top_signals'] == []
    assert len(result['shadow_candidates']) == 1
    assert result['shadow_candidates'][0]['shadow_only'] is True
    assert result['shadow_mode'] is True
    assert adapter.tracker.pending() == []
    assert adapter.get_match_detail('33010')['item']['comparison23']['count'] == 23
