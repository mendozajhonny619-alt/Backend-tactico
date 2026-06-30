from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return "{}"


class FootballIntelligenceMemoryService:
    """
    Football Intelligence Memory V17.

    Rol:
    - EVIDENCE_ONLY.
    - No decide.
    - No publica.
    - No modifica official_*.
    - No reemplaza MasterDecisionAI.
    - Solo registra hechos y devuelve memoria contextual.
    """

    VERSION = "V17_FOOTBALL_INTELLIGENCE_MEMORY_1_PASSIVE"
    ROLE = "EVIDENCE_ONLY"

    def __init__(
        self,
        db_path: str = "app/v17/storage/football_intelligence_memory.db",
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_tables()

    def record_match_snapshot(self, match: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(match, dict):
            return self._result(False, "INVALID_MATCH_PAYLOAD")

        now = utc_now_iso()
        fixture_id = self._fixture_id(match)

        home_id = self._team_id(match, "home")
        away_id = self._team_id(match, "away")
        home_name = self._team_name(match, "home")
        away_name = self._team_name(match, "away")

        league_id = self._league_id(match)
        league_name = safe_str(match.get("league") or match.get("liga"))
        country = safe_str(match.get("country") or match.get("país"))

        minute = safe_int(
            match.get("api_minute")
            or match.get("minute")
            or match.get("minuto")
            or match.get("display_minute"),
            0,
        )

        home_score = safe_int(match.get("home_score") or match.get("local_score"), 0)
        away_score = safe_int(match.get("away_score") or match.get("visitante_score"), 0)
        total_goals = home_score + away_score

        total_shots = safe_float(match.get("total_shots") or match.get("shots"), 0.0)
        total_shots_on = safe_float(
            match.get("total_shots_on") or match.get("shots_on_target"),
            0.0,
        )
        total_dangerous_attacks = safe_float(
            match.get("total_dangerous_attacks") or match.get("dangerous_attacks"),
            0.0,
        )
        total_corners = safe_float(match.get("total_corners") or match.get("corners"), 0.0)
        total_xg = safe_float(match.get("total_xg") or match.get("xg") or match.get("xG"), 0.0)

        data_source_quality = safe_str(
            match.get("data_source_quality")
            or match.get("data_quality")
            or match.get("calidad_datos")
            or "UNKNOWN"
        )

        stats_completeness_score = safe_float(match.get("stats_completeness_score"), 0.0)
        xg_available = 1 if bool(match.get("xg_available")) or total_xg > 0 else 0

        score_state = self._score_state(home_score, away_score)
        minute_bucket = self._minute_bucket(minute)
        market = safe_str(
            match.get("market")
            or match.get("suggested_market")
            or match.get("prediction_market")
            or "UNKNOWN"
        ).upper()

        match_direction = safe_str(
            match.get("match_direction")
            or match.get("football_game_state")
            or match.get("momentum_label")
            or "UNKNOWN"
        ).upper()

        payload = {
            "fixture_id": fixture_id,
            "minute": minute,
            "home_team": home_name,
            "away_team": away_name,
            "league": league_name,
            "country": country,
            "score": f"{home_score}-{away_score}",
            "total_goals": total_goals,
            "total_shots": total_shots,
            "total_shots_on": total_shots_on,
            "total_dangerous_attacks": total_dangerous_attacks,
            "total_corners": total_corners,
            "total_xg": total_xg,
            "data_source_quality": data_source_quality,
            "stats_completeness_score": stats_completeness_score,
            "xg_available": xg_available,
            "score_state": score_state,
            "minute_bucket": minute_bucket,
            "market": market,
            "match_direction": match_direction,
        }

        with self._connect() as conn:
            self._insert_event(conn=conn, event_type="MATCH_SNAPSHOT", fixture_id=fixture_id, payload=payload, now=now)
            self._upsert_team_snapshot(conn=conn, team_id=home_id, team_name=home_name, country=country, league_id=league_id, league_name=league_name, venue="HOME", goals_for=home_score, goals_against=away_score, total_goals=total_goals, total_shots=total_shots, total_shots_on=total_shots_on, total_dangerous_attacks=total_dangerous_attacks, total_corners=total_corners, total_xg=total_xg, now=now)
            self._upsert_team_snapshot(conn=conn, team_id=away_id, team_name=away_name, country=country, league_id=league_id, league_name=league_name, venue="AWAY", goals_for=away_score, goals_against=home_score, total_goals=total_goals, total_shots=total_shots, total_shots_on=total_shots_on, total_dangerous_attacks=total_dangerous_attacks, total_corners=total_corners, total_xg=total_xg, now=now)
            self._upsert_league_snapshot(conn=conn, league_id=league_id, league_name=league_name, country=country, total_goals=total_goals, total_shots=total_shots, total_shots_on=total_shots_on, total_dangerous_attacks=total_dangerous_attacks, total_corners=total_corners, total_xg=total_xg, data_source_quality=data_source_quality, stats_completeness_score=stats_completeness_score, xg_available=xg_available, now=now)
            self._upsert_matchup_snapshot(conn=conn, home_team_id=home_id, away_team_id=away_id, home_team=home_name, away_team=away_name, league_id=league_id, league_name=league_name, total_goals=total_goals, score_state=score_state, now=now)
            self._upsert_live_pattern_snapshot(conn=conn, league_id=league_id, league_name=league_name, minute_bucket=minute_bucket, score_state=score_state, market=market, match_direction=match_direction, total_goals=total_goals, total_xg=total_xg, total_shots_on=total_shots_on, now=now)

        return self._result(True, "MATCH_SNAPSHOT_RECORDED")

    def record_signal_snapshot(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(signal, dict):
            return self._result(False, "INVALID_SIGNAL_PAYLOAD")
        now = utc_now_iso()
        fixture_id = self._fixture_id(signal)
        payload = {
            "fixture_id": fixture_id,
            "signal_key": safe_str(signal.get("signal_key") or signal.get("signal_id")),
            "home_team": safe_str(signal.get("home_team")),
            "away_team": safe_str(signal.get("away_team")),
            "league": safe_str(signal.get("league")),
            "country": safe_str(signal.get("country")),
            "minute": safe_int(signal.get("api_minute") or signal.get("display_minute"), 0),
            "scoreline": safe_str(signal.get("scoreline") or signal.get("current_score")),
            "market": safe_str(signal.get("market") or signal.get("suggested_market") or signal.get("prediction_market") or "UNKNOWN").upper(),
            "master_status": safe_str(signal.get("master_status")),
            "promotion_level": safe_str(signal.get("promotion_level") or signal.get("current_promotion_level") or signal.get("candidate_level")),
            "activation_level": safe_str(signal.get("activation_level")),
            "prediction_scenario": safe_str(signal.get("prediction_scenario")),
            "prediction_score": safe_str(signal.get("prediction_score")),
            "match_direction": safe_str(signal.get("match_direction") or signal.get("football_game_state") or signal.get("momentum_label") or "UNKNOWN").upper(),
            "score_fairness": safe_str(signal.get("score_fairness") or "UNKNOWN").upper(),
            "data_source_quality": safe_str(signal.get("data_source_quality") or signal.get("data_quality")),
        }
        with self._connect() as conn:
            self._insert_event(conn=conn, event_type="SIGNAL_SNAPSHOT", fixture_id=fixture_id, payload=payload, now=now)
        return self._result(True, "SIGNAL_SNAPSHOT_RECORDED")

    def record_resolution(self, resolved_signal: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(resolved_signal, dict):
            return self._result(False, "INVALID_RESOLUTION_PAYLOAD")
        now = utc_now_iso()
        fixture_id = self._fixture_id(resolved_signal)
        result_status = safe_str(resolved_signal.get("result_status")).upper()
        market = safe_str(resolved_signal.get("market") or resolved_signal.get("suggested_market") or resolved_signal.get("prediction_market") or "UNKNOWN").upper()
        final_scoreline = safe_str(resolved_signal.get("final_scoreline") or resolved_signal.get("current_scoreline") or resolved_signal.get("scoreline"))
        final_home, final_away = self._parse_scoreline(final_scoreline)
        payload = {
            "fixture_id": fixture_id,
            "signal_key": safe_str(resolved_signal.get("signal_key") or resolved_signal.get("signal_id")),
            "result_status": result_status,
            "result_reason": safe_str(resolved_signal.get("result_reason")),
            "market": market,
            "final_scoreline": final_scoreline,
            "final_total_goals": final_home + final_away,
            "league": safe_str(resolved_signal.get("league")),
            "country": safe_str(resolved_signal.get("country")),
            "home_team": safe_str(resolved_signal.get("home_team")),
            "away_team": safe_str(resolved_signal.get("away_team")),
        }
        with self._connect() as conn:
            self._insert_event(conn=conn, event_type="RESOLUTION", fixture_id=fixture_id, payload=payload, now=now)
        return self._result(True, "RESOLUTION_RECORDED")

    def get_team_memory(self, team_id: Any = None, team_name: Optional[str] = None) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM team_memory WHERE team_key = ?", (self._entity_key(team_id, team_name),)).fetchone()
        return self._memory_response("team_memory", row)

    def get_league_memory(self, league_id: Any = None, league_name: Optional[str] = None) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM league_memory WHERE league_key = ?", (self._entity_key(league_id, league_name),)).fetchone()
        return self._memory_response("league_memory", row)

    def get_matchup_memory(self, home_team_id: Any = None, away_team_id: Any = None, home_team: Optional[str] = None, away_team: Optional[str] = None) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM matchup_memory WHERE matchup_key = ?", (self._matchup_key(home_team_id, away_team_id, home_team, away_team),)).fetchone()
        return self._memory_response("matchup_memory", row)

    def get_live_pattern_memory(self, league_id: Any = None, minute: Any = None, score_state: Optional[str] = None, market: Optional[str] = None, match_direction: Optional[str] = None) -> Dict[str, Any]:
        pattern_key = self._pattern_key(league_id=league_id, minute_bucket=self._minute_bucket(safe_int(minute, 0)), score_state=safe_str(score_state or "UNKNOWN").upper(), market=safe_str(market or "UNKNOWN").upper(), match_direction=safe_str(match_direction or "UNKNOWN").upper())
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM live_pattern_memory WHERE pattern_key = ?", (pattern_key,)).fetchone()
        return self._memory_response("live_pattern_memory", row)

    def _ensure_tables(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS memory_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, fixture_id TEXT, event_time TEXT NOT NULL, payload_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS team_memory (team_key TEXT PRIMARY KEY, team_id TEXT, team_name TEXT, country TEXT, latest_league_id TEXT, latest_league_name TEXT, snapshots_seen INTEGER DEFAULT 0, home_snapshots_seen INTEGER DEFAULT 0, away_snapshots_seen INTEGER DEFAULT 0, avg_goals_for_live REAL DEFAULT 0, avg_goals_against_live REAL DEFAULT 0, avg_total_goals_live REAL DEFAULT 0, avg_shots_live REAL DEFAULT 0, avg_shots_on_live REAL DEFAULT 0, avg_dangerous_attacks_live REAL DEFAULT 0, avg_corners_live REAL DEFAULT 0, avg_xg_live REAL DEFAULT 0, over_15_observed_rate REAL DEFAULT 0, over_25_observed_rate REAL DEFAULT 0, btts_observed_rate REAL DEFAULT 0, first_seen_at TEXT, updated_at TEXT);
                CREATE TABLE IF NOT EXISTS league_memory (league_key TEXT PRIMARY KEY, league_id TEXT, league_name TEXT, country TEXT, snapshots_seen INTEGER DEFAULT 0, avg_total_goals_live REAL DEFAULT 0, avg_shots_live REAL DEFAULT 0, avg_shots_on_live REAL DEFAULT 0, avg_dangerous_attacks_live REAL DEFAULT 0, avg_corners_live REAL DEFAULT 0, avg_xg_live REAL DEFAULT 0, over_15_observed_rate REAL DEFAULT 0, over_25_observed_rate REAL DEFAULT 0, xg_available_rate REAL DEFAULT 0, avg_stats_completeness_score REAL DEFAULT 0, high_quality_rate REAL DEFAULT 0, medium_quality_rate REAL DEFAULT 0, low_quality_rate REAL DEFAULT 0, stale_cache_rate REAL DEFAULT 0, first_seen_at TEXT, updated_at TEXT);
                CREATE TABLE IF NOT EXISTS matchup_memory (matchup_key TEXT PRIMARY KEY, home_team_id TEXT, away_team_id TEXT, home_team TEXT, away_team TEXT, league_id TEXT, league_name TEXT, snapshots_seen INTEGER DEFAULT 0, avg_total_goals_live REAL DEFAULT 0, over_15_observed_rate REAL DEFAULT 0, over_25_observed_rate REAL DEFAULT 0, home_leading_rate REAL DEFAULT 0, away_leading_rate REAL DEFAULT 0, draw_state_rate REAL DEFAULT 0, first_seen_at TEXT, updated_at TEXT);
                CREATE TABLE IF NOT EXISTS live_pattern_memory (pattern_key TEXT PRIMARY KEY, league_id TEXT, league_name TEXT, minute_bucket TEXT, score_state TEXT, market TEXT, match_direction TEXT, observations INTEGER DEFAULT 0, avg_total_goals_live REAL DEFAULT 0, avg_xg_live REAL DEFAULT 0, avg_shots_on_live REAL DEFAULT 0, over_15_observed_rate REAL DEFAULT 0, over_25_observed_rate REAL DEFAULT 0, first_seen_at TEXT, updated_at TEXT);
                CREATE INDEX IF NOT EXISTS idx_memory_events_fixture ON memory_events(fixture_id);
                CREATE INDEX IF NOT EXISTS idx_memory_events_type ON memory_events(event_type);
            """)
            conn.commit()

    def _upsert_team_snapshot(self, *, conn: sqlite3.Connection, team_id: Any, team_name: str, country: str, league_id: Any, league_name: str, venue: str, goals_for: int, goals_against: int, total_goals: int, total_shots: float, total_shots_on: float, total_dangerous_attacks: float, total_corners: float, total_xg: float, now: str) -> None:
        team_key = self._entity_key(team_id, team_name)
        row = conn.execute("SELECT * FROM team_memory WHERE team_key = ?", (team_key,)).fetchone()
        if not row:
            conn.execute("""INSERT INTO team_memory (team_key, team_id, team_name, country, latest_league_id, latest_league_name, snapshots_seen, home_snapshots_seen, away_snapshots_seen, avg_goals_for_live, avg_goals_against_live, avg_total_goals_live, avg_shots_live, avg_shots_on_live, avg_dangerous_attacks_live, avg_corners_live, avg_xg_live, over_15_observed_rate, over_25_observed_rate, btts_observed_rate, first_seen_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (team_key, safe_str(team_id), team_name, country, safe_str(league_id), league_name, 1, 1 if venue == "HOME" else 0, 1 if venue == "AWAY" else 0, goals_for, goals_against, total_goals, total_shots, total_shots_on, total_dangerous_attacks, total_corners, total_xg, 1.0 if total_goals >= 2 else 0.0, 1.0 if total_goals >= 3 else 0.0, 1.0 if goals_for > 0 and goals_against > 0 else 0.0, now, now))
            return
        n = safe_int(row["snapshots_seen"], 0)
        conn.execute("""UPDATE team_memory SET country = ?, latest_league_id = ?, latest_league_name = ?, snapshots_seen = ?, home_snapshots_seen = home_snapshots_seen + ?, away_snapshots_seen = away_snapshots_seen + ?, avg_goals_for_live = ?, avg_goals_against_live = ?, avg_total_goals_live = ?, avg_shots_live = ?, avg_shots_on_live = ?, avg_dangerous_attacks_live = ?, avg_corners_live = ?, avg_xg_live = ?, over_15_observed_rate = ?, over_25_observed_rate = ?, btts_observed_rate = ?, updated_at = ? WHERE team_key = ?""", (country, safe_str(league_id), league_name, n + 1, 1 if venue == "HOME" else 0, 1 if venue == "AWAY" else 0, self._avg(row["avg_goals_for_live"], goals_for, n), self._avg(row["avg_goals_against_live"], goals_against, n), self._avg(row["avg_total_goals_live"], total_goals, n), self._avg(row["avg_shots_live"], total_shots, n), self._avg(row["avg_shots_on_live"], total_shots_on, n), self._avg(row["avg_dangerous_attacks_live"], total_dangerous_attacks, n), self._avg(row["avg_corners_live"], total_corners, n), self._avg(row["avg_xg_live"], total_xg, n), self._avg(row["over_15_observed_rate"], 1.0 if total_goals >= 2 else 0.0, n), self._avg(row["over_25_observed_rate"], 1.0 if total_goals >= 3 else 0.0, n), self._avg(row["btts_observed_rate"], 1.0 if goals_for > 0 and goals_against > 0 else 0.0, n), now, team_key))

    def _upsert_league_snapshot(self, *, conn: sqlite3.Connection, league_id: Any, league_name: str, country: str, total_goals: int, total_shots: float, total_shots_on: float, total_dangerous_attacks: float, total_corners: float, total_xg: float, data_source_quality: str, stats_completeness_score: float, xg_available: int, now: str) -> None:
        league_key = self._entity_key(league_id, league_name)
        row = conn.execute("SELECT * FROM league_memory WHERE league_key = ?", (league_key,)).fetchone()
        high = 1.0 if data_source_quality == "HIGH" else 0.0
        medium = 1.0 if data_source_quality in {"MEDIUM", "MEDIUM_HIGH"} else 0.0
        low = 1.0 if "LOW" in data_source_quality else 0.0
        stale = 1.0 if data_source_quality == "STALE_CACHE" else 0.0
        if not row:
            conn.execute("""INSERT INTO league_memory (league_key, league_id, league_name, country, snapshots_seen, avg_total_goals_live, avg_shots_live, avg_shots_on_live, avg_dangerous_attacks_live, avg_corners_live, avg_xg_live, over_15_observed_rate, over_25_observed_rate, xg_available_rate, avg_stats_completeness_score, high_quality_rate, medium_quality_rate, low_quality_rate, stale_cache_rate, first_seen_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (league_key, safe_str(league_id), league_name, country, 1, total_goals, total_shots, total_shots_on, total_dangerous_attacks, total_corners, total_xg, 1.0 if total_goals >= 2 else 0.0, 1.0 if total_goals >= 3 else 0.0, float(xg_available), stats_completeness_score, high, medium, low, stale, now, now))
            return
        n = safe_int(row["snapshots_seen"], 0)
        conn.execute("""UPDATE league_memory SET country = ?, snapshots_seen = ?, avg_total_goals_live = ?, avg_shots_live = ?, avg_shots_on_live = ?, avg_dangerous_attacks_live = ?, avg_corners_live = ?, avg_xg_live = ?, over_15_observed_rate = ?, over_25_observed_rate = ?, xg_available_rate = ?, avg_stats_completeness_score = ?, high_quality_rate = ?, medium_quality_rate = ?, low_quality_rate = ?, stale_cache_rate = ?, updated_at = ? WHERE league_key = ?""", (country, n + 1, self._avg(row["avg_total_goals_live"], total_goals, n), self._avg(row["avg_shots_live"], total_shots, n), self._avg(row["avg_shots_on_live"], total_shots_on, n), self._avg(row["avg_dangerous_attacks_live"], total_dangerous_attacks, n), self._avg(row["avg_corners_live"], total_corners, n), self._avg(row["avg_xg_live"], total_xg, n), self._avg(row["over_15_observed_rate"], 1.0 if total_goals >= 2 else 0.0, n), self._avg(row["over_25_observed_rate"], 1.0 if total_goals >= 3 else 0.0, n), self._avg(row["xg_available_rate"], float(xg_available), n), self._avg(row["avg_stats_completeness_score"], stats_completeness_score, n), self._avg(row["high_quality_rate"], high, n), self._avg(row["medium_quality_rate"], medium, n), self._avg(row["low_quality_rate"], low, n), self._avg(row["stale_cache_rate"], stale, n), now, league_key))

    def _upsert_matchup_snapshot(self, *, conn: sqlite3.Connection, home_team_id: Any, away_team_id: Any, home_team: str, away_team: str, league_id: Any, league_name: str, total_goals: int, score_state: str, now: str) -> None:
        matchup_key = self._matchup_key(home_team_id, away_team_id, home_team, away_team)
        row = conn.execute("SELECT * FROM matchup_memory WHERE matchup_key = ?", (matchup_key,)).fetchone()
        home_leading = 1.0 if score_state == "HOME_LEADING" else 0.0
        away_leading = 1.0 if score_state == "AWAY_LEADING" else 0.0
        draw_state = 1.0 if score_state == "DRAW" else 0.0
        if not row:
            conn.execute("""INSERT INTO matchup_memory (matchup_key, home_team_id, away_team_id, home_team, away_team, league_id, league_name, snapshots_seen, avg_total_goals_live, over_15_observed_rate, over_25_observed_rate, home_leading_rate, away_leading_rate, draw_state_rate, first_seen_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (matchup_key, safe_str(home_team_id), safe_str(away_team_id), home_team, away_team, safe_str(league_id), league_name, 1, total_goals, 1.0 if total_goals >= 2 else 0.0, 1.0 if total_goals >= 3 else 0.0, home_leading, away_leading, draw_state, now, now))
            return
        n = safe_int(row["snapshots_seen"], 0)
        conn.execute("""UPDATE matchup_memory SET snapshots_seen = ?, avg_total_goals_live = ?, over_15_observed_rate = ?, over_25_observed_rate = ?, home_leading_rate = ?, away_leading_rate = ?, draw_state_rate = ?, updated_at = ? WHERE matchup_key = ?""", (n + 1, self._avg(row["avg_total_goals_live"], total_goals, n), self._avg(row["over_15_observed_rate"], 1.0 if total_goals >= 2 else 0.0, n), self._avg(row["over_25_observed_rate"], 1.0 if total_goals >= 3 else 0.0, n), self._avg(row["home_leading_rate"], home_leading, n), self._avg(row["away_leading_rate"], away_leading, n), self._avg(row["draw_state_rate"], draw_state, n), now, matchup_key))

    def _upsert_live_pattern_snapshot(self, *, conn: sqlite3.Connection, league_id: Any, league_name: str, minute_bucket: str, score_state: str, market: str, match_direction: str, total_goals: int, total_xg: float, total_shots_on: float, now: str) -> None:
        pattern_key = self._pattern_key(league_id=league_id, minute_bucket=minute_bucket, score_state=score_state, market=market, match_direction=match_direction)
        row = conn.execute("SELECT * FROM live_pattern_memory WHERE pattern_key = ?", (pattern_key,)).fetchone()
        if not row:
            conn.execute("""INSERT INTO live_pattern_memory (pattern_key, league_id, league_name, minute_bucket, score_state, market, match_direction, observations, avg_total_goals_live, avg_xg_live, avg_shots_on_live, over_15_observed_rate, over_25_observed_rate, first_seen_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (pattern_key, safe_str(league_id), league_name, minute_bucket, score_state, market, match_direction, 1, total_goals, total_xg, total_shots_on, 1.0 if total_goals >= 2 else 0.0, 1.0 if total_goals >= 3 else 0.0, now, now))
            return
        n = safe_int(row["observations"], 0)
        conn.execute("""UPDATE live_pattern_memory SET observations = ?, avg_total_goals_live = ?, avg_xg_live = ?, avg_shots_on_live = ?, over_15_observed_rate = ?, over_25_observed_rate = ?, updated_at = ? WHERE pattern_key = ?""", (n + 1, self._avg(row["avg_total_goals_live"], total_goals, n), self._avg(row["avg_xg_live"], total_xg, n), self._avg(row["avg_shots_on_live"], total_shots_on, n), self._avg(row["over_15_observed_rate"], 1.0 if total_goals >= 2 else 0.0, n), self._avg(row["over_25_observed_rate"], 1.0 if total_goals >= 3 else 0.0, n), now, pattern_key))

    def _insert_event(self, *, conn: sqlite3.Connection, event_type: str, fixture_id: str, payload: Dict[str, Any], now: str) -> None:
        conn.execute("INSERT INTO memory_events (event_type, fixture_id, event_time, payload_json) VALUES (?, ?, ?, ?)", (event_type, fixture_id, now, safe_json(payload)))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _memory_response(self, memory_type: str, row: Optional[sqlite3.Row]) -> Dict[str, Any]:
        if not row:
            return {"memory_role": self.ROLE, "memory_is_official_decision": False, "memory_can_publish": False, "memory_type": memory_type, "memory_available": False, "memory_confidence": "LOW", "memory_data": {}, "memory_support_points": [], "memory_warnings": ["No hay memoria suficiente para esta entidad."]}
        data = dict(row)
        sample_count = safe_int(data.get("snapshots_seen"), 0) or safe_int(data.get("observations"), 0)
        confidence = "HIGH" if sample_count >= 50 else "MEDIUM" if sample_count >= 15 else "LOW"
        warnings = ["Muestra baja: usar solo como contexto, no como decisión."] if confidence == "LOW" else []
        return {"memory_role": self.ROLE, "memory_is_official_decision": False, "memory_can_publish": False, "memory_type": memory_type, "memory_available": True, "memory_confidence": confidence, "memory_sample_count": sample_count, "memory_data": data, "memory_support_points": self._support_points(memory_type, data), "memory_warnings": warnings}

    def _support_points(self, memory_type: str, data: Dict[str, Any]) -> list[str]:
        points = []
        over_25 = safe_float(data.get("over_25_observed_rate"), 0.0)
        avg_goals = safe_float(data.get("avg_total_goals_live") or data.get("avg_total_goals"), 0.0)
        if avg_goals >= 2.7:
            points.append("Memoria con tendencia de goles alta.")
        elif avg_goals > 0 and avg_goals <= 1.7:
            points.append("Memoria con tendencia de marcador controlado.")
        if over_25 >= 0.58:
            points.append("Frecuencia observada de Over 2.5 elevada.")
        elif over_25 > 0 and over_25 <= 0.35:
            points.append("Frecuencia observada de Over 2.5 baja.")
        if memory_type == "league_memory" and safe_float(data.get("xg_available_rate"), 0.0) < 0.35:
            points.append("La liga tiene baja disponibilidad histórica de xG.")
        return points

    def _result(self, ok: bool, reason: str) -> Dict[str, Any]:
        return {"memory_role": self.ROLE, "memory_is_official_decision": False, "memory_can_publish": False, "memory_ok": ok, "memory_reason": reason}

    def _avg(self, old_avg: Any, new_value: Any, old_count: int) -> float:
        old_avg = safe_float(old_avg, 0.0)
        new_value = safe_float(new_value, 0.0)
        old_count = max(0, safe_int(old_count, 0))
        return round(((old_avg * old_count) + new_value) / max(1, old_count + 1), 4)

    def _fixture_id(self, data: Dict[str, Any]) -> str:
        return safe_str(data.get("fixture_id") or data.get("match_id") or data.get("id"))

    def _team_id(self, data: Dict[str, Any], side: str) -> str:
        if side == "home":
            return safe_str(data.get("home_id") or data.get("home_team_id"))
        return safe_str(data.get("away_id") or data.get("away_team_id"))

    def _team_name(self, data: Dict[str, Any], side: str) -> str:
        if side == "home":
            return safe_str(data.get("home_team") or data.get("home_name") or data.get("home"))
        return safe_str(data.get("away_team") or data.get("away_name") or data.get("away"))

    def _league_id(self, data: Dict[str, Any]) -> str:
        return safe_str(data.get("league_id"))

    def _entity_key(self, entity_id: Any, name: Optional[str]) -> str:
        entity_id = safe_str(entity_id)
        name = safe_str(name).upper()
        if entity_id:
            return f"ID:{entity_id}"
        return f"NAME:{name}"

    def _matchup_key(self, home_team_id: Any, away_team_id: Any, home_team: Optional[str], away_team: Optional[str]) -> str:
        return f"{self._entity_key(home_team_id, home_team)}__VS__{self._entity_key(away_team_id, away_team)}"

    def _pattern_key(self, *, league_id: Any, minute_bucket: str, score_state: str, market: str, match_direction: str) -> str:
        return "|".join([safe_str(league_id) or "UNKNOWN_LEAGUE", safe_str(minute_bucket).upper(), safe_str(score_state).upper(), safe_str(market).upper(), safe_str(match_direction).upper()])

    def _minute_bucket(self, minute: int) -> str:
        minute = safe_int(minute, 0)
        if minute <= 15:
            return "M00_15"
        if minute <= 30:
            return "M16_30"
        if minute <= 45:
            return "M31_45"
        if minute <= 60:
            return "M46_60"
        if minute <= 75:
            return "M61_75"
        if minute <= 90:
            return "M76_90"
        return "M90_PLUS"

    def _score_state(self, home_score: int, away_score: int) -> str:
        if home_score > away_score:
            return "HOME_LEADING"
        if away_score > home_score:
            return "AWAY_LEADING"
        return "DRAW"

    def _parse_scoreline(self, scoreline: str) -> Tuple[int, int]:
        scoreline = safe_str(scoreline)
        if "-" not in scoreline:
            return 0, 0
        left, right = scoreline.split("-", 1)
        return safe_int(left, 0), safe_int(right, 0)
