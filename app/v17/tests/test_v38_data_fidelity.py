"""V3.8 phase one: offline tests for provider coverage and per-team momentum.

All fixtures are synthetic. No API key, HTTP call, odds or official signals.
"""
from __future__ import annotations

from app.fetchers.live_match_fetcher import LiveMatchFetcher
from app.jhonny_elite.master_protocol import TemporalMatchMemory


def team_stats(shots=None, sot=None, xg=None, dangerous=None):
    fields = []
    item = {"shots": 0.0, "shots_on_target": 0.0,
            "xG": 0.0, "dangerous_attacks": 0.0}
    if shots is not None:
        item["shots"] = shots
        fields.append("Total Shots")
    if sot is not None:
        item["shots_on_target"] = sot
        fields.append("Shots on Goal")
    if xg is not None:
        item["xG"] = xg
        fields.append("expected_goals")
        item["xg_available"] = True
    if dangerous is not None:
        item["dangerous_attacks"] = dangerous
        fields.append("Dangerous Attacks")
    item["stats_available_fields"] = fields
    return item


def timed_snapshot(minute, **changes):
    record = {
        "fixture_id": "v38-fixture", "api_minute": minute,
        "fetched_at": 1000 + (minute - 50) * 60,
        "home_score": 0, "away_score": 0,
        "has_live_stats": True,
        "home_stats": team_stats(shots=0, sot=0, xg=0),
        "away_stats": team_stats(shots=0, sot=0, xg=0),
        "shots": 0, "shots_on_target": 0, "xg": 0, "xg_available": True,
    }
    record.update(changes)
    return record


def test_timed_team_windows_read_nested_api_football_stats():
    memory = TemporalMatchMemory()
    memory.enrich(timed_snapshot(50))
    end = timed_snapshot(55, home_stats=team_stats(shots=2, sot=1, xg=0.4),
                         away_stats=team_stats(shots=4, sot=2, xg=0.5),
                         shots=6, shots_on_target=3, xg=0.9)
    out = memory.enrich(end)
    w = out["window_5"]
    assert w["available"] is True
    assert w["home_delta_shots"] == 2 and w["away_delta_shots"] == 4
    assert w["home_delta_sot"] == 1 and w["away_delta_sot"] == 2
    assert w["home_delta_xg"] == 0.4 and w["away_delta_xg"] == 0.5
    assert w["team_attribution_available"] is True
    assert out["temporal_team_windows_ready"] is True


def test_no_statistics_never_become_measured_momentum_by_default_zeroes():
    memory = TemporalMatchMemory()
    empty = timed_snapshot(50, has_live_stats=False, home_stats=team_stats(),
                           away_stats=team_stats(), xg_available=False)
    memory.enrich(empty)
    empty_next = timed_snapshot(55, has_live_stats=False, home_stats=team_stats(),
                                away_stats=team_stats(), xg_available=False)
    out = memory.enrich(empty_next)
    assert out["window_5"]["available"] is False
    assert out["temporal_memory_ready"] is False


def test_a_single_teams_shots_cannot_be_reported_as_complete_total():
    memory = TemporalMatchMemory()
    memory.enrich(timed_snapshot(50, home_stats=team_stats(shots=0),
                                 away_stats=team_stats(), xg_available=False))
    out = memory.enrich(timed_snapshot(55, home_stats=team_stats(shots=5),
                                       away_stats=team_stats(), shots=5,
                                       xg_available=False))
    assert out["window_5"]["available"] is False
    assert out["temporal_team_windows_ready"] is False


def test_genuine_published_zero_is_a_valid_window_measurement():
    memory = TemporalMatchMemory()
    memory.enrich(timed_snapshot(50))
    out = memory.enrich(timed_snapshot(55))
    w = out["window_5"]
    assert w["available"] is True
    assert w["delta_shots"] == 0 and w["delta_xg"] == 0
    assert w["home_delta_shots"] == 0


def test_stale_statistics_cannot_create_new_momentum():
    memory = TemporalMatchMemory()
    memory.enrich(timed_snapshot(50, stats_age_seconds=400))
    out = memory.enrich(timed_snapshot(55, stats_age_seconds=400))
    assert not out["window_5"]["available"]
    assert out["window_5"]["reason"] == "SOURCE_UNTRUSTED"


def test_provider_aliases_are_marked_as_published_not_missing():
    source = [{"team": {"id": 17}, "statistics": [
        {"type": "Shots on Target", "value": 3},
        {"type": "Expected Goals", "value": "0.0"},
        {"type": "Possession", "value": "51%"},
        {"type": "Total Shots", "value": 10},
        {"type": "Big Chances", "value": 2},
    ]}]
    row = LiveMatchFetcher._extract_team_stats_api_football(None, source, 0)
    assert row["shots_on_target"] == 3
    assert row["xG"] == 0 and row["xg_available"] is True
    assert "Shots on Goal" in row["stats_available_fields"]
    assert "expected_goals" in row["stats_available_fields"]
    assert "Ball Possession" in row["stats_available_fields"]
    assert "Big Chances" in row["stats_unmapped_fields"]
    assert "Shots on Goal" not in row["stats_missing_fields"]


def test_provider_nulls_and_invalid_numbers_are_not_published_evidence():
    source = [{"statistics": [
        {"type": "Shots on Goal", "value": None},
        {"type": "Total Shots", "value": "NaN"},
        {"type": "expected_goals", "value": ""},
    ]}]
    row = LiveMatchFetcher._extract_team_stats_api_football(None, source, 0)
    assert "Shots on Goal" not in row["stats_available_fields"]
    assert "Total Shots" not in row["stats_available_fields"]
    assert not row["xg_available"]


def test_team_id_mapping_survives_reversed_provider_rows():
    statistics = [
        {"team": {"id": 32}, "statistics": [{"type": "Total Shots", "value": 4}]},
        {"team": {"id": 17}, "statistics": [{"type": "Total Shots", "value": 12}]},
    ]
    rows, state = LiveMatchFetcher._align_team_statistics(statistics, 17, 32)
    assert state == "VERIFIED_TEAM_IDS"
    assert rows[0]["team"]["id"] == 17
    assert rows[1]["team"]["id"] == 32


def test_unrelated_team_ids_fail_closed_instead_of_attributing_wrong_shots():
    statistics = [
        {"team": {"id": 91}, "statistics": [{"type": "Total Shots", "value": 4}]},
        {"team": {"id": 92}, "statistics": [{"type": "Total Shots", "value": 12}]},
    ]
    rows, state = LiveMatchFetcher._align_team_statistics(statistics, 17, 32)
    assert rows == []
    assert state == "TEAM_ID_MISMATCH"


def test_partial_provider_mapping_preserves_only_known_team():
    statistics = [
        {"team": {"id": 32}, "statistics": [{"type": "Total Shots", "value": 4}]},
    ]
    rows, state = LiveMatchFetcher._align_team_statistics(statistics, 17, 32)
    assert state == "PARTIAL_TEAM_IDS"
    assert rows[0] == {} and rows[1]["team"]["id"] == 32


def test_normalized_fixture_carries_auditable_fields_without_external_calls(monkeypatch):
    fetcher = LiveMatchFetcher()
    monkeypatch.setattr(fetcher, "_is_priority_league", lambda item: True)
    monkeypatch.setattr(fetcher, "_select_deep_scan_fixture_ids", lambda raw: set())
    monkeypatch.setattr(fetcher, "_fetch_fixture_statistics", lambda **kwargs: (_ for _ in ()).throw(AssertionError("unexpected API call")))
    monkeypatch.setattr(fetcher, "_fetch_fixture_events", lambda **kwargs: [])
    monkeypatch.setattr(fetcher, "_fetch_fixture_players", lambda **kwargs: [])
    fixture = {
        "fixture": {"id": 112233, "status": {"short": "2H", "long": "Second Half", "elapsed": 55}},
        "league": {"id": 99, "name": "Liga de prueba", "country": "X", "season": 2026},
        "teams": {"home": {"id": 17, "name": "Local"},
                  "away": {"id": 32, "name": "Visita"}},
        "goals": {"home": 1, "away": 0},
        "statistics": [
            {"team": {"id": 32}, "statistics": [
                {"type": "Total Shots", "value": 4},
                {"type": "Shots on Target", "value": 1},
                {"type": "Big Chances", "value": 1},
            ]},
            {"team": {"id": 17}, "statistics": [
                {"type": "Total Shots", "value": 9},
                {"type": "Shots on Target", "value": 3},
                {"type": "Expected Goals", "value": "0.81"},
            ]},
        ],
    }
    normalized = fetcher._normalize_api_football([fixture])
    assert len(normalized) == 1
    m = normalized[0]
    assert m["home_stats"]["shots"] == 9
    assert m["away_stats"]["shots"] == 4
    assert m["home_stats"]["xG"] == 0.81
    assert m["away_stats"]["xg_available"] is False
    audit = m["statistics_audit"]
    assert audit["team_mapping"] == "VERIFIED_TEAM_IDS"
    assert audit["statistics_source"] == "EMBEDDED"
    assert "Shots on Goal" in audit["home_published_fields"]
    assert "expected_goals" in audit["away_missing_fields"]
    assert "Big Chances" in audit["away_unmapped_provider_fields"]
    assert audit["away_field_origin"]["Shots on Goal"] == "Shots on Target"
    assert "x-apisports-key" not in str(audit)


def test_guard_reads_actual_api_football_names_not_legacy_missing_aliases():
    from app.v17.core.data_quality_guard import DataQualityGuard
    m = {"match_id": "fixture01", "home_team": "Local", "away_team": "Visita",
         "api_minute": 55, "home_score": 1, "away_score": 0,
         "shots": 13, "shots_on_target": 5, "dangerous_attacks": 0,
         "home_stats": team_stats(shots=8, sot=3),
         "away_stats": team_stats(shots=5, sot=2)}
    result = DataQualityGuard().evaluate(m)
    assert result["data_quality_status"] == "DATA_OK"
    assert "NO_SHOTS_DATA" not in result["data_warnings"]
    assert "NO_DANGEROUS_ATTACKS_DATA" not in result["data_warnings"]


def test_guard_still_warns_when_all_finishing_evidence_is_zero():
    from app.v17.core.data_quality_guard import DataQualityGuard
    m = {"match_id": "fixture02", "home_team": "Local", "away_team": "Visita",
         "api_minute": 55, "home_score": 0, "away_score": 0, "shots": 0,
         "home_stats": team_stats(), "away_stats": team_stats()}
    r = DataQualityGuard().evaluate(m)
    assert r["data_weak"] is True and "NO_SHOTS_DATA" in r["data_warnings"]


def test_league_stat_coverage_is_bilateral_not_union_of_one_team():
    f = LiveMatchFetcher.__new__(LiveMatchFetcher)
    home = {"stats_available_fields": ["Total Shots", "Shots on Goal", "Ball Possession",
                                       "Corner Kicks", "Total passes", "Passes %", "Fouls", "Offsides"]}
    away = {"stats_available_fields": []}
    totals = {"shots": 9, "shots_on_target": 4, "available_stat_fields_count": 8}
    assert f._classify_data_quality(home, away, totals) == "LOW_DATA_AVAILABLE"
    assert f._stats_completeness_score(home, away) < 0.50


def test_zero_shots_with_bilateral_published_coverage_still_has_real_evidence():
    f = LiveMatchFetcher.__new__(LiveMatchFetcher)
    home = team_stats(shots=0, sot=0)
    away = team_stats(shots=0, sot=0)
    totals = f._build_totals(home, away)
    assert totals["both_available_fields_count"] == 2
    assert f._classify_data_quality(home, away, totals) == "MEDIUM"


def test_live_dynamics_never_calls_missing_statistics_a_cold_match():
    from app.jhonny_elite.live_dynamics import LiveDynamicsMemory
    mem = LiveDynamicsMemory()
    first = timed_snapshot(50, has_live_stats=False, home_stats=team_stats(),
                           away_stats=team_stats(), xg_available=False)
    second = timed_snapshot(55, has_live_stats=False, home_stats=team_stats(),
                            away_stats=team_stats(), xg_available=False)
    mem.enrich(first)
    out = mem.enrich(second)
    assert out["dynamics_available"] is False
    assert out["recent_dominant_team"] == "UNKNOWN"


def test_live_dynamics_respects_per_team_field_presence():
    from app.jhonny_elite.live_dynamics import LiveDynamicsMemory
    mem = LiveDynamicsMemory()
    mem.enrich(timed_snapshot(50, home_stats=team_stats(shots=0, sot=0),
                              away_stats=team_stats(shots=0, sot=0),
                              xg_available=False))
    out = mem.enrich(timed_snapshot(55, home_stats=team_stats(shots=1, sot=0),
                                    away_stats=team_stats(shots=6, sot=2),
                                    shots=7, shots_on_target=2, xg_available=False))
    assert out["dynamics_available"] is True
    assert out["recent_dominant_team"] == "AWAY"


def test_live_dynamics_ignores_missing_away_stats_instead_of_fake_zero():
    from app.jhonny_elite.live_dynamics import LiveDynamicsMemory
    mem = LiveDynamicsMemory()
    mem.enrich(timed_snapshot(50, home_stats=team_stats(shots=0),
                              away_stats=team_stats(), xg_available=False))
    out = mem.enrich(timed_snapshot(55, home_stats=team_stats(shots=3),
                                    away_stats=team_stats(), shots=3,
                                    xg_available=False))
    assert out["dynamics_available"] is False
    assert out["recent_dominant_team"] == "UNKNOWN"


def test_live_dynamics_stale_cache_cannot_report_opening_or_closing():
    from app.jhonny_elite.live_dynamics import LiveDynamicsMemory
    mem = LiveDynamicsMemory()
    mem.enrich(timed_snapshot(50, stats_age_seconds=400))
    out = mem.enrich(timed_snapshot(55, stats_age_seconds=400))
    assert out["dynamics_available"] is False
    assert out["dynamic_match_state"] == "UNKNOWN"


def test_dashboard_detail_preserves_compact_statistics_audit():
    from app.v17.dashboard.dashboard_adapter import V17DashboardAdapter
    adapter = V17DashboardAdapter.__new__(V17DashboardAdapter)
    adapter._detail_by_fixture = {
        "123": {"fixture_id": "123", "home_score": 0, "away_score": 0,
                "has_live_stats": False,
                "statistics_audit": {"team_mapping": "PARTIAL_TEAM_IDS",
                                     "home_unmapped_provider_fields": ["Big Chances"]}},
    }
    adapter._detail_by_signal = {}
    result = adapter.get_match_detail("123")
    assert result["ok"] is True
    assert result["item"]["statistics_audit"]["team_mapping"] == "PARTIAL_TEAM_IDS"
    assert result["item"]["statistics_audit"]["home_unmapped_provider_fields"] == ["Big Chances"]
