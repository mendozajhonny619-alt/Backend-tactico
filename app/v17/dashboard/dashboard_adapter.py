from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.v17.core.league_filter import LeagueFilter
from app.v17.engine.live_signal_engine import LiveSignalEngineV17
from app.v17.signals.signal_tracker import SignalTracker


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def normalize_market(value: Any) -> str:
    text = str(value or "").upper()

    if "OVER" in text:
        return "OVER"

    if "UNDER" in text:
        return "UNDER"

    if "SOBRE" in text:
        return "OVER"

    if "BAJO" in text:
        return "UNDER"

    return "OTHER"


def first_value(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return default

def clamp_probability(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    try:
        number = round(float(value), 2)
        if number < 0:
            return 0
        if number > 100:
            return 100
        if number.is_integer():
            return int(number)
        return number
    except Exception:
        return default


def _sum_probabilities(*values: Any) -> Any:
    total = 0.0
    found = False
    for value in values:
        if value is None:
            continue
        try:
            total += float(value)
            found = True
        except Exception:
            continue
    if not found:
        return None
    return clamp_probability(total)


class V17DashboardAdapter:
    """
    Adaptador principal V17.

    Mantiene el dashboard limpio y expone señales, observaciones,
    historial, métricas y campos predictivos.
    """

    def __init__(self) -> None:
        self.engine = LiveSignalEngineV17()
        self.tracker = SignalTracker()
        self.league_filter = LeagueFilter()

        self._last_dashboard: Dict[str, Any] = {
            "ok": True,
            "version": "V17",
            "updated_at": utc_now_iso(),
            "top_signals": [],
            "observe": [],
            "no_bet": [],
            "blocked": [],
            "blocked_by_league": [],
            "live_matches": [],
            "history": [],
            "stats": {},
            "summary": {},
            "source_status": "EMPTY_INITIAL_STATE",
        }

    def build_from_raw_matches(
        self,
        raw_matches: List[Dict[str, Any]],
        source_status: str = "RAW_MATCHES",
    ) -> Dict[str, Any]:
        prepared_matches = [self._attach_visual_identity(x) for x in raw_matches or []]

        league_filter_result = self.league_filter.filter_matches(prepared_matches)

        allowed_matches = league_filter_result.get("allowed", [])
        blocked_by_league = league_filter_result.get("blocked_by_league", [])

        engine_result = self.engine.process_live_matches(allowed_matches)

        engine_result["blocked_by_league"] = blocked_by_league
        engine_result["league_filter_summary"] = league_filter_result.get("summary", {})

        engine_result = self._attach_identity_to_engine_result(
            engine_result=engine_result,
            raw_matches=allowed_matches,
        )

        top_signals = engine_result.get("top_signals", [])
        all_analyzed = engine_result.get("all_analyzed", [])

        registered = self.tracker.register_published_signals(top_signals)
        tracking_result = self.tracker.update_with_live_matches(all_analyzed)

        dashboard = self._build_dashboard_payload(
            engine_result=engine_result,
            tracking_result=tracking_result,
            registered=registered,
            source_status=source_status,
        )

        self._last_dashboard = dashboard
        return dashboard

    def build_from_v16_payload(
        self,
        payload: Dict[str, Any],
        source_status: str = "V16_PAYLOAD",
    ) -> Dict[str, Any]:
        raw_matches = self._extract_live_items(payload)
        return self.build_from_raw_matches(raw_matches, source_status=source_status)

    def last_dashboard(self) -> Dict[str, Any]:
        return dict(self._last_dashboard)

    def get_signals(self) -> Dict[str, Any]:
        data = self.last_dashboard()
        return {
            "ok": True,
            "version": "V17",
            "updated_at": utc_now_iso(),
            "top_signals": data.get("top_signals", []),
            "observe": data.get("observe", []),
            "summary": data.get("summary", {}),
        }

    def get_history(self) -> Dict[str, Any]:
        data = self.last_dashboard()
        return {
            "ok": True,
            "version": "V17",
            "updated_at": utc_now_iso(),
            "history": data.get("history", []),
            "pending_signals": data.get("pending_signals", []),
            "closed_history": data.get("closed_history", []),
            "stats": data.get("stats", {}),
            "learning": data.get("learning", {}),
            "performance_analysis": data.get("performance_analysis", {}),
        }

    def get_debug(self) -> Dict[str, Any]:
        data = self.last_dashboard()
        return {
            "ok": True,
            "version": "V17",
            "updated_at": utc_now_iso(),
            "source_status": data.get("source_status"),
            "counts": {
                "live_matches": len(data.get("live_matches", [])),
                "top_signals": len(data.get("top_signals", [])),
                "observe": len(data.get("observe", [])),
                "no_bet": len(data.get("no_bet", [])),
                "blocked": len(data.get("blocked", [])),
                "blocked_by_league": len(data.get("blocked_by_league", [])),
                "history": len(data.get("history", [])),
                "pending": len(data.get("pending_signals", [])),
                "closed": len(data.get("closed_history", [])),
            },
            "summary": data.get("summary", {}),
            "stats": data.get("stats", {}),
        }

    def _build_dashboard_payload(
        self,
        engine_result: Dict[str, Any],
        tracking_result: Dict[str, Any],
        registered: List[Dict[str, Any]],
        source_status: str,
    ) -> Dict[str, Any]:
        top_signals = engine_result.get("top_signals", [])
        observe = engine_result.get("observe", [])
        no_bet = engine_result.get("no_bet", [])
        blocked = engine_result.get("blocked", [])
        blocked_by_league = engine_result.get("blocked_by_league", [])
        all_analyzed = engine_result.get("all_analyzed", [])

        pending_signals = tracking_result.get("pending", [])
        closed_history = tracking_result.get("closed", [])
        history = pending_signals + closed_history

        tracking_summary = tracking_result.get("summary", {})
        learning = tracking_result.get("learning", {})
        performance_analysis = tracking_result.get("performance_analysis", {})
        by_market = tracking_summary.get("by_market", {})

        compact_history_source = history + registered
        competition_dashboard = self._build_competition_dashboard(
            signals=all_analyzed,
            history=compact_history_source,
            tracking_summary=tracking_summary,
            performance_analysis=performance_analysis,
        )
        temporal_dashboard = self._build_temporal_dashboard(compact_history_source)

        stats = {
            "live_matches": engine_result.get("live_count", 0),
            "analyzed_matches": engine_result.get("analyzed_count", 0),
            "published_signals": len(top_signals),
            "observe": len(observe),
            "no_bet": len(no_bet),
            "blocked": len(blocked),
            "blocked_by_league": len(blocked_by_league),
            "league_filter": engine_result.get("league_filter_summary", {}),
            "pending": tracking_summary.get("pending", 0),
            "closed": tracking_summary.get("closed", 0),
            "wins": tracking_summary.get("wins", 0),
            "losses": tracking_summary.get("losses", 0),
            "voids": tracking_summary.get("voids", 0),
            "precision": tracking_summary.get("precision", 0),
            "accuracy_rate": tracking_summary.get("precision", 0),
            "total_tracked": tracking_summary.get("total_tracked", 0),
            "by_market": by_market,
            "over": tracking_summary.get("over", by_market.get("OVER", {})),
            "under": tracking_summary.get("under", by_market.get("UNDER", {})),
            "performance_by_market": by_market,
            "performance_over": tracking_summary.get("over", by_market.get("OVER", {})),
            "performance_under": tracking_summary.get("under", by_market.get("UNDER", {})),
            "performance_by_competition": competition_dashboard.get("by_competition", {}),
            "performance_by_tier": competition_dashboard.get("by_tier", {}),
            "performance_world_cup": competition_dashboard.get("world_cup", {}),
            "performance_major_tournaments": competition_dashboard.get("major_tournaments", {}),
            "daily_performance": temporal_dashboard.get("daily", {}),
            "weekly_performance": temporal_dashboard.get("weekly", {}),
            "monthly_performance": temporal_dashboard.get("monthly", {}),
        }

        return {
            "ok": True,
            "version": "V17",
            "updated_at": utc_now_iso(),
            "source_status": source_status,
            "frontend_safe": True,
            "live_matches": self._compact_signals(all_analyzed),
            "top_signals": self._compact_signals(top_signals),
            "observe": self._compact_signals(observe[:20]),
            "no_bet": self._compact_signals(no_bet[:20]),
            "blocked": self._compact_signals(blocked[:20]),
            "blocked_by_league": self._compact_signals(blocked_by_league[:50]),
            "pending_signals": self._compact_history(pending_signals),
            "closed_history": self._compact_history(closed_history),
            "history": self._compact_history(history),
            "registered_signals": self._compact_history(registered),
            "stats": stats,
            "competition_dashboard": competition_dashboard,
            "temporal_dashboard": temporal_dashboard,
            "world_cup_panel": competition_dashboard.get("world_cup", {}),
            "summary": {
                **engine_result.get("summary", {}),
                **tracking_summary,
                "league_filter": engine_result.get("league_filter_summary", {}),
            },
            "learning": learning,
            "performance_analysis": performance_analysis,
            "message": self._build_dashboard_message(stats),
        }

    def _build_competition_dashboard(
        self,
        signals: List[Dict[str, Any]],
        history: List[Dict[str, Any]],
        tracking_summary: Dict[str, Any],
        performance_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Construye métricas compactas por competición sin exigir cambios en el frontend.
        Si SignalTracker o PerformanceAnalyzer ya traen datos, los conserva.
        Si no los traen, calcula un resumen seguro desde el historial disponible.
        """
        by_competition = self._aggregate_performance(history, key="league")
        by_tier = self._aggregate_performance(history, key="competition_tier")

        world_cup_history = [x for x in history if self._truthy(x.get("world_cup_flag"))]
        major_history = [x for x in history if self._truthy(x.get("major_tournament_flag"))]
        national_history = [x for x in history if self._truthy(x.get("national_team_flag"))]

        live_by_tier = self._count_by_key(signals, "competition_tier")

        return {
            "by_competition": performance_analysis.get("performance_by_competition") or by_competition,
            "by_tier": performance_analysis.get("performance_by_tier") or by_tier,
            "world_cup": performance_analysis.get("performance_world_cup") or self._performance_summary(world_cup_history),
            "major_tournaments": performance_analysis.get("performance_major_tournaments") or self._performance_summary(major_history),
            "national_teams": performance_analysis.get("performance_national_teams") or self._performance_summary(national_history),
            "live_by_tier": live_by_tier,
            "best_competitions": self._rank_performance(by_competition, reverse=True),
            "worst_competitions": self._rank_performance(by_competition, reverse=False),
            "tracker_by_competition": tracking_summary.get("by_competition", {}),
            "tracker_by_tier": tracking_summary.get("by_tier", {}),
        }

    def _build_temporal_dashboard(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "daily": self._aggregate_temporal(history, mode="day"),
            "weekly": self._aggregate_temporal(history, mode="week"),
            "monthly": self._aggregate_temporal(history, mode="month"),
        }

    def _aggregate_performance(self, items: List[Dict[str, Any]], key: str) -> Dict[str, Dict[str, Any]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for item in items or []:
            name = str(item.get(key) or "UNKNOWN").strip() or "UNKNOWN"
            grouped.setdefault(name, []).append(item)
        return {name: self._performance_summary(values) for name, values in grouped.items()}

    def _aggregate_temporal(self, items: List[Dict[str, Any]], mode: str) -> Dict[str, Dict[str, Any]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for item in items or []:
            parsed = self._parse_time(item.get("resolved_at") or item.get("registered_at") or item.get("updated_at"))
            if not parsed:
                continue
            if mode == "day":
                key = parsed.strftime("%Y-%m-%d")
            elif mode == "week":
                iso = parsed.isocalendar()
                key = f"{iso.year}-W{iso.week:02d}"
            else:
                key = parsed.strftime("%Y-%m")
            grouped.setdefault(key, []).append(item)
        return {key: self._performance_summary(values) for key, values in sorted(grouped.items())}

    def _performance_summary(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        wins = 0
        losses = 0
        voids = 0
        pending = 0

        for item in items or []:
            status = str(item.get("result_status") or item.get("tracking_status") or item.get("result_label") or "").upper()
            if "WON" in status or "WIN" in status or "ACIERTO" in status:
                wins += 1
            elif "LOST" in status or "LOSS" in status or "FALLO" in status:
                losses += 1
            elif "VOID" in status or "CANCEL" in status or "EXPIRED" in status:
                voids += 1
            else:
                pending += 1

        closed = wins + losses
        total = closed + voids + pending
        accuracy = round((wins / closed) * 100, 2) if closed else 0
        return {
            "total": total,
            "closed": closed,
            "wins": wins,
            "losses": losses,
            "voids": voids,
            "pending": pending,
            "accuracy": accuracy,
            "precision": accuracy,
        }

    def _rank_performance(self, performance: Dict[str, Dict[str, Any]], reverse: bool) -> List[Dict[str, Any]]:
        rows = []
        for name, stats in performance.items():
            closed = safe_int(stats.get("closed"), 0)
            if closed <= 0:
                continue
            rows.append({"name": name, **stats})
        return sorted(rows, key=lambda x: (safe_float(x.get("accuracy"), 0.0), safe_int(x.get("closed"), 0)), reverse=reverse)[:10]

    def _count_by_key(self, items: List[Dict[str, Any]], key: str) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for item in items or []:
            name = str(item.get(key) or "UNKNOWN").strip() or "UNKNOWN"
            result[name] = result.get(name, 0) + 1
        return result

    def _truthy(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "yes", "si", "sí"}

    def _parse_time(self, value: Any) -> Any:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            text = str(value).replace("Z", "+00:00")
            return datetime.fromisoformat(text)
        except Exception:
            return None

    def _extract_live_items(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return []

        collected: List[Dict[str, Any]] = []

        candidate_keys = [
            "live",
            "live_matches",
            "matches",
            "signals",
            "top_signals",
            "published_signals",
            "active_signals",
            "opportunities",
            "observe",
            "no_bet",
            "blocked",
        ]

        for key in candidate_keys:
            collected.extend(self._extract_list(payload.get(key)))

        if "data" in payload:
            collected.extend(self._extract_live_items(payload.get("data") or {}))

        if "payload" in payload:
            collected.extend(self._extract_live_items(payload.get("payload") or {}))

        collected = [self._attach_visual_identity(x) for x in collected]
        return self._dedupe_items(collected)

    def _extract_list(self, value: Any) -> List[Dict[str, Any]]:
        if isinstance(value, list):
            return [self._attach_visual_identity(x) for x in value if isinstance(x, dict)]

        if isinstance(value, dict):
            for key in [
                "items",
                "data",
                "matches",
                "live",
                "live_matches",
                "signals",
                "top_signals",
                "published_signals",
                "active_signals",
                "opportunities",
                "observe",
                "no_bet",
                "blocked",
            ]:
                nested = value.get(key)
                if isinstance(nested, list):
                    return [self._attach_visual_identity(x) for x in nested if isinstance(x, dict)]

        return []

    def _dedupe_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}

        for item in items or []:
            match_id = str(
                item.get("match_id")
                or item.get("fixture_id")
                or item.get("fixture")
                or item.get("id")
                or ""
            )

            if not match_id:
                continue

            old = result.get(match_id)

            if not old:
                result[match_id] = item
                continue

            old_minute = safe_int(old.get("api_minute") or old.get("minute") or old.get("display_minute"), 0)
            new_minute = safe_int(item.get("api_minute") or item.get("minute") or item.get("display_minute"), 0)

            old_score = safe_int(old.get("home_score"), 0) + safe_int(old.get("away_score"), 0)
            new_score = safe_int(item.get("home_score"), 0) + safe_int(item.get("away_score"), 0)

            if new_minute >= old_minute or new_score >= old_score:
                result[match_id] = self._attach_visual_identity({**old, **item})

        return list(result.values())

    def _attach_identity_to_engine_result(
        self,
        engine_result: Dict[str, Any],
        raw_matches: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        result = dict(engine_result or {})
        identity_index = self._build_identity_index(raw_matches)

        for key in ["top_signals", "observe", "no_bet", "blocked", "all_analyzed"]:
            result[key] = [
                self._merge_visual_identity(item, identity_index)
                for item in result.get(key, [])
                if isinstance(item, dict)
            ]

        return result

    def _build_identity_index(self, items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        index: Dict[str, Dict[str, Any]] = {}

        for item in items or []:
            if not isinstance(item, dict):
                continue

            prepared = self._attach_visual_identity(item)
            match_id = str(prepared.get("match_id") or prepared.get("fixture_id") or prepared.get("id") or "").strip()

            if match_id:
                index[match_id] = prepared

        return index

    def _merge_visual_identity(
        self,
        item: Dict[str, Any],
        identity_index: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        current = self._attach_visual_identity(item)
        match_id = str(current.get("match_id") or current.get("fixture_id") or current.get("id") or "").strip()
        source = identity_index.get(match_id, {})

        for key in [
            "home_logo",
            "away_logo",
            "home_team_logo",
            "away_team_logo",
            "league_logo",
            "country_flag",
            "flag",
            "country",
            "league",
            "league_id",
            "country_code",
            "competition_tier",
            "competition_weight",
            "world_cup_flag",
            "national_team_flag",
            "major_tournament_flag",
            "league_filter_status",
            "league_filter_reason",
        ]:
            if not current.get(key) and source.get(key):
                current[key] = source.get(key)

        return current

    def _attach_visual_identity(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(item, dict):
            return item

        data = dict(item)

        fixture = data.get("fixture") if isinstance(data.get("fixture"), dict) else {}
        teams = data.get("teams") if isinstance(data.get("teams"), dict) else {}
        league_obj = data.get("league") if isinstance(data.get("league"), dict) else {}

        home_obj = teams.get("home") if isinstance(teams.get("home"), dict) else {}
        away_obj = teams.get("away") if isinstance(teams.get("away"), dict) else {}

        team_home_obj = data.get("team_home") if isinstance(data.get("team_home"), dict) else {}
        team_away_obj = data.get("team_away") if isinstance(data.get("team_away"), dict) else {}

        data["fixture_id"] = first_value(data.get("fixture_id"), data.get("match_id"), fixture.get("id"), data.get("id"))
        data["match_id"] = first_value(data.get("match_id"), data.get("fixture_id"), fixture.get("id"), data.get("id"))

        data["home_team"] = first_value(
            data.get("home_team"),
            data.get("home"),
            data.get("local"),
            home_obj.get("name"),
            team_home_obj.get("name"),
        )

        data["away_team"] = first_value(
            data.get("away_team"),
            data.get("away"),
            data.get("visitor"),
            data.get("visitante"),
            away_obj.get("name"),
            team_away_obj.get("name"),
        )

        data["home_logo"] = first_value(
            data.get("home_logo"),
            data.get("home_team_logo"),
            data.get("local_logo"),
            home_obj.get("logo"),
            team_home_obj.get("logo"),
        )

        data["away_logo"] = first_value(
            data.get("away_logo"),
            data.get("away_team_logo"),
            data.get("visitor_logo"),
            data.get("visitante_logo"),
            away_obj.get("logo"),
            team_away_obj.get("logo"),
        )

        data["home_team_logo"] = data.get("home_logo")
        data["away_team_logo"] = data.get("away_logo")

        data["league_id"] = first_value(data.get("league_id"), league_obj.get("id"))
        data["league"] = first_value(data.get("league"), data.get("league_name"), data.get("competition"), league_obj.get("name"))
        data["country"] = first_value(data.get("country"), data.get("pais"), league_obj.get("country"))
        data["league_logo"] = first_value(data.get("league_logo"), data.get("competition_logo"), data.get("tournament_logo"), league_obj.get("logo"))
        data["country_flag"] = first_value(data.get("country_flag"), data.get("flag"), data.get("league_flag"), league_obj.get("flag"))
        data["flag"] = data.get("country_flag")
        data["country_code"] = first_value(data.get("country_code"), self._country_code_from_flag(data.get("country_flag")))

        # V17 competition intelligence fields. They are optional and safe for old payloads.
        data["competition_tier"] = first_value(data.get("competition_tier"), data.get("league_tier"), default="")
        data["competition_weight"] = first_value(data.get("competition_weight"), default=0)
        data["world_cup_flag"] = bool(data.get("world_cup_flag", False))
        data["national_team_flag"] = bool(data.get("national_team_flag", False))
        data["major_tournament_flag"] = bool(data.get("major_tournament_flag", False))
        data["league_filter_status"] = first_value(data.get("league_filter_status"), default="")
        data["league_filter_reason"] = first_value(data.get("league_filter_reason"), default="")

        return data

    def _country_code_from_flag(self, flag_url: Any) -> str:
        text = str(flag_url or "").strip().lower()

        if not text:
            return ""

        filename = text.split("/")[-1]
        code = filename.split(".")[0]

        return code if len(code) in {2, 3} else ""


    def _prediction_probability_pack(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Devuelve probabilidades visuales coherentes para el panel.

        Importante:
        - over_score / under_score pueden ser scores internos de oportunidad.
        - prediction_live_over_probability / prediction_live_under_probability
          representan la lectura live real para el panel.
        - Si no existen, se reconstruyen desde:
          no_goal + one_goal + two_plus_goals.
        """
        raw_over_score = item.get("over_score")
        raw_under_score = item.get("under_score")

        no_goal_probability = first_value(
            item.get("prediction_no_goal_probability"),
            item.get("no_goal_probability"),
            item.get("probability_no_goal"),
            item.get("no_more_goals_probability"),
        )
        one_goal_probability = first_value(
            item.get("prediction_one_goal_probability"),
            item.get("one_goal_probability"),
            item.get("probability_one_goal"),
            item.get("one_more_goal_probability"),
        )
        two_plus_goals_probability = first_value(
            item.get("prediction_two_plus_goals_probability"),
            item.get("two_plus_goals_probability"),
            item.get("probability_two_plus_goals"),
            item.get("two_or_more_goals_probability"),
        )

        live_over_probability = first_value(
            item.get("visual_over_probability"),
            item.get("prediction_live_over_probability"),
            item.get("live_over_probability"),
            item.get("prediction_over_live_probability"),
            item.get("live_goal_probability"),
        )

        live_under_probability = first_value(
            item.get("visual_under_probability"),
            item.get("prediction_live_under_probability"),
            item.get("live_under_probability"),
            item.get("prediction_under_live_probability"),
        )

        if live_over_probability is None:
            live_over_probability = _sum_probabilities(one_goal_probability, two_plus_goals_probability)

        if live_under_probability is None:
            live_under_probability = no_goal_probability

        if live_under_probability is None and live_over_probability is not None:
            live_under_probability = 100 - safe_float(live_over_probability, 0)

        if live_over_probability is None and live_under_probability is not None:
            live_over_probability = 100 - safe_float(live_under_probability, 0)

        visual_over_probability = clamp_probability(live_over_probability, default=raw_over_score)
        visual_under_probability = clamp_probability(live_under_probability, default=raw_under_score)

        return {
            "raw_over_score": raw_over_score,
            "raw_under_score": raw_under_score,
            "visual_over_probability": visual_over_probability,
            "visual_under_probability": visual_under_probability,
            "prediction_live_over_probability": visual_over_probability,
            "prediction_live_under_probability": visual_under_probability,
            "prediction_no_goal_probability": clamp_probability(no_goal_probability),
            "prediction_one_goal_probability": clamp_probability(one_goal_probability),
            "prediction_two_plus_goals_probability": clamp_probability(two_plus_goals_probability),
        }


    def _compact_signals(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compact: List[Dict[str, Any]] = []

        for item in items or []:
            item = self._attach_visual_identity(item)

            # La decisión oficial de MasterDecisionAI tiene prioridad.
            # Las demás lecturas quedan como fallback visual/legacy.
            official_market_raw = str(item.get("official_market") or "").upper()
            official_market = normalize_market(official_market_raw)

            if official_market in {"OVER", "UNDER"}:
                market_direction = official_market
            elif official_market_raw in {"OBSERVE", "WAIT_CONFIRMATION", "NO_BET", "BLOCKED", "NO_REENTRY"}:
                # MasterDecisionAI decidió no tomar mercado operativo. No caer a
                # promotion/activation/prediction porque son solo evidencia.
                market_direction = "OTHER"
            else:
                market_direction = normalize_market(
                    item.get("market_direction")
                    or item.get("market")
                    or item.get("master_market")
                    or item.get("suggested_market")
                )

            probability_pack = self._prediction_probability_pack(item)

            compact.append({
                "version": "V17",
                "signal_key": item.get("signal_key"),
                "signal_id": item.get("signal_id"),
                "match_id": item.get("match_id"),
                "fixture_id": item.get("fixture_id"),

                "home_team": item.get("home_team"),
                "away_team": item.get("away_team"),
                "home_logo": item.get("home_logo"),
                "away_logo": item.get("away_logo"),
                "home_team_logo": item.get("home_team_logo"),
                "away_team_logo": item.get("away_team_logo"),

                "league": item.get("league"),
                "league_id": item.get("league_id"),
                "league_logo": item.get("league_logo"),
                "country": item.get("country"),
                "country_flag": item.get("country_flag"),
                "flag": item.get("flag"),
                "country_code": item.get("country_code"),
                "competition_tier": item.get("competition_tier"),
                "competition_weight": item.get("competition_weight"),
                "world_cup_flag": item.get("world_cup_flag"),
                "national_team_flag": item.get("national_team_flag"),
                "major_tournament_flag": item.get("major_tournament_flag"),
                "league_filter_status": item.get("league_filter_status"),
                "league_filter_reason": item.get("league_filter_reason"),

                "api_minute": item.get("api_minute"),
                "display_minute": item.get("display_minute"),
                "estimated_minute": item.get("estimated_minute"),
                "clock_status": item.get("clock_status"),
                "clock_action": item.get("clock_action"),
                "data_age_seconds": item.get("data_age_seconds"),
                "clock_frozen": item.get("clock_frozen"),
                "minute_lag_detected": item.get("minute_lag_detected"),
                "timestamp_missing": item.get("timestamp_missing"),

                "home_score": item.get("home_score"),
                "away_score": item.get("away_score"),
                "scoreline": item.get("scoreline"),
                "current_score": item.get("current_score"),

                "market": market_direction,
                "market_direction": market_direction,
                "suggested_market": item.get("suggested_market"),
                "market_category": item.get("market_category"),
                "context_category": item.get("context_category"),

                # Contrato oficial V17: debe viajar completo hasta el dashboard.
                "official_market": item.get("official_market"),
                "official_status": item.get("official_status"),
                "official_confidence": item.get("official_confidence"),
                "official_main_scenario": item.get("official_main_scenario"),
                "official_probable_score": item.get("official_probable_score"),
                "official_next_goal_team": item.get("official_next_goal_team"),
                "official_can_publish": item.get("official_can_publish"),
                "official_reason": item.get("official_reason"),
                "official_risks": item.get("official_risks", []),
                "decision_id": item.get("decision_id"),
                "decision_timestamp": item.get("decision_timestamp"),

                "master_status": item.get("master_status"),
                "master_rank": item.get("master_rank"),
                "master_confidence": item.get("master_confidence"),
                "master_action": item.get("master_action"),
                "master_reason": item.get("master_reason"),

                "elite_score": item.get("elite_score"),
                "elite_rank": item.get("elite_rank"),
                "elite_position": item.get("elite_position"),
                "published": item.get("published", False),
                "panel_section": item.get("panel_section"),

                "risk_status": item.get("risk_status"),
                "risk_score": item.get("risk_score"),
                "risk_reasons": item.get("risk_reasons", []),
                "risk_warnings": item.get("risk_warnings", []),

                "tactical_status": item.get("tactical_status"),
                "tactical_score": item.get("tactical_score"),
                "pressure_score": item.get("pressure_score"),
                "rhythm_score": item.get("rhythm_score"),
                "goal_need_score": item.get("goal_need_score"),
                "offensive_depth_score": item.get("offensive_depth_score"),
                "offensive_volume_score": item.get("offensive_volume_score"),
                "recent_attack_proxy": item.get("recent_attack_proxy"),

                # Scores visuales: el frontend suele usarlos como porcentajes.
                # Por eso se prioriza la probabilidad live real del MatchPredictionAI.
                "over_score": probability_pack.get("visual_over_probability"),
                "under_score": probability_pack.get("visual_under_probability"),
                "visual_over_probability": probability_pack.get("visual_over_probability"),
                "visual_under_probability": probability_pack.get("visual_under_probability"),
                "raw_over_score": probability_pack.get("raw_over_score"),
                "raw_under_score": probability_pack.get("raw_under_score"),
                "market_gap": item.get("market_gap"),
                "score_hold_probability": item.get("score_hold_probability"),
                "under_transition_score": item.get("under_transition_score"),
                "false_pressure_risk": item.get("false_pressure_risk"),

                "probable_score": item.get("probable_score"),
                "result_probability_reading": item.get("result_probability_reading"),

                "passed_filters": item.get("passed_filters", []),
                "failed_secondary_filters": item.get("failed_secondary_filters", []),
                "hard_blockers": item.get("hard_blockers", []),
                "soft_warnings": item.get("soft_warnings", []),

                "signal_life_status": item.get("signal_life_status"),
                "signal_life_label": item.get("signal_life_label"),
                "signal_age_minutes": item.get("signal_age_minutes"),
                "reactivation_detected": item.get("reactivation_detected"),
                "reactivation_requires_confirmation": item.get("reactivation_requires_confirmation"),
                "lifecycle_can_publish": item.get("lifecycle_can_publish"),
                "lifecycle_requires_wait": item.get("lifecycle_requires_wait"),

                "main_reading": item.get("main_reading"),
                "what_is_missing": item.get("what_is_missing"),

                "decision_valid": item.get("decision_valid"),
                "logic_status": item.get("logic_status"),
                "candidate_level": item.get("candidate_level"),
                "recommended_demotion": item.get("recommended_demotion"),
                "logic_warnings": item.get("logic_warnings", []),

                "promotion_level": item.get("promotion_level"),
                "promotion_score": item.get("promotion_score"),
                "promotion_market": item.get("promotion_market"),
                "promotion_action": item.get("promotion_action"),
                "promotion_reason": item.get("promotion_reason"),
                "promotion_panel_label": item.get("promotion_panel_label"),

                "activation_level": item.get("activation_level"),
                "activation_score": item.get("activation_score"),
                "activation_final_score": item.get("activation_final_score"),
                "activation_market": item.get("activation_market"),
                "activation_action": item.get("activation_action"),
                "activation_reason": item.get("activation_reason"),
                "activation_label": item.get("activation_label"),
                "activation_error": item.get("activation_error"),

                "prediction_mode": item.get("prediction_mode"),
                "prediction_phase": item.get("prediction_phase"),
                "prediction_scenario": item.get("prediction_scenario"),
                "prediction_market": item.get("prediction_market"),
                "prediction_score": item.get("prediction_score"),
                "prediction_alternative_score": item.get("prediction_alternative_score"),
                "prediction_halftime_score": item.get("prediction_halftime_score"),
                "prediction_final_score": item.get("prediction_final_score"),
                "prediction_score_scenarios": item.get("prediction_score_scenarios", []),
                "prediction_market_alignment": item.get("prediction_market_alignment"),
                "prediction_next_goal_probability": item.get("prediction_next_goal_probability"),
                "prediction_live_over_probability": probability_pack.get("prediction_live_over_probability"),
                "prediction_live_under_probability": probability_pack.get("prediction_live_under_probability"),
                "prediction_no_goal_probability": probability_pack.get("prediction_no_goal_probability"),
                "prediction_one_goal_probability": probability_pack.get("prediction_one_goal_probability"),
                "prediction_two_plus_goals_probability": probability_pack.get("prediction_two_plus_goals_probability"),
                "prediction_main_score": item.get("prediction_main_score"),
                "prediction_offensive_score": item.get("prediction_offensive_score"),
                "prediction_break_score": item.get("prediction_break_score"),
                "prediction_conservative_score": item.get("prediction_conservative_score"),
                "break_risk": item.get("break_risk"),
                "break_team": item.get("break_team"),
                "break_scenario": item.get("break_scenario"),
                "prediction_attacking_team": item.get("prediction_attacking_team"),
                "prediction_attacking_side": item.get("prediction_attacking_side"),
                "prediction_confidence": item.get("prediction_confidence"),
                "prediction_panel_message": item.get("prediction_panel_message"),
                "prediction_reason": item.get("prediction_reason"),
                "prediction_error": item.get("prediction_error"),

                "over_candidate_level": item.get("over_candidate_level"),
                "over_candidate_active": item.get("over_candidate_active"),
                "over_support_score": item.get("over_support_score"),
                "over_support_ratio": item.get("over_support_ratio"),
                "over_blockers": item.get("over_blockers", []),
                "why_over_candidate": item.get("why_over_candidate"),
                "why_over_not_ready": item.get("why_over_not_ready"),

                "data_quality": item.get("data_quality"),
                "scan_phase": item.get("scan_phase"),
                "scan_reason": item.get("scan_reason"),
                "stats_source": item.get("stats_source"),
                "can_publish_signal": item.get("can_publish_signal"),
                "can_observe_signal": item.get("can_observe_signal"),
                "is_scannable": item.get("is_scannable"),

                "shots": item.get("shots"),
                "shots_on_target": item.get("shots_on_target"),
                "corners": item.get("corners"),
                "xg": item.get("xg") or item.get("xG"),
                "xG": item.get("xg") or item.get("xG"),
                "dangerous_attacks": item.get("dangerous_attacks"),
                "red_cards": item.get("red_cards"),

                "updated_at": item.get("updated_at"),
            })

        return compact

    def _compact_history(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compact: List[Dict[str, Any]] = []

        for item in items or []:
            item = self._attach_visual_identity(item)

            # La decisión oficial de MasterDecisionAI tiene prioridad.
            # Las demás lecturas quedan como fallback visual/legacy.
            official_market_raw = str(item.get("official_market") or "").upper()
            official_market = normalize_market(official_market_raw)

            if official_market in {"OVER", "UNDER"}:
                market_direction = official_market
            elif official_market_raw in {"OBSERVE", "WAIT_CONFIRMATION", "NO_BET", "BLOCKED", "NO_REENTRY"}:
                # MasterDecisionAI decidió no tomar mercado operativo. No caer a
                # promotion/activation/prediction porque son solo evidencia.
                market_direction = "OTHER"
            else:
                market_direction = normalize_market(
                    item.get("market_direction")
                    or item.get("market")
                    or item.get("master_market")
                    or item.get("suggested_market")
                )

            probability_pack = self._prediction_probability_pack(item)

            compact.append({
                "version": "V17",
                "signal_key": item.get("signal_key"),
                "signal_id": item.get("signal_id"),
                "match_id": item.get("match_id"),
                "fixture_id": item.get("fixture_id"),

                "home_team": item.get("home_team"),
                "away_team": item.get("away_team"),
                "home_logo": item.get("home_logo"),
                "away_logo": item.get("away_logo"),
                "home_team_logo": item.get("home_team_logo"),
                "away_team_logo": item.get("away_team_logo"),

                "league": item.get("league"),
                "league_logo": item.get("league_logo"),
                "country": item.get("country"),
                "country_flag": item.get("country_flag"),
                "flag": item.get("flag"),
                "competition_tier": item.get("competition_tier"),
                "competition_weight": item.get("competition_weight"),
                "world_cup_flag": item.get("world_cup_flag"),
                "national_team_flag": item.get("national_team_flag"),
                "major_tournament_flag": item.get("major_tournament_flag"),
                "league_filter_status": item.get("league_filter_status"),
                "league_filter_reason": item.get("league_filter_reason"),

                "market": market_direction,
                "market_direction": market_direction,
                "master_status": item.get("master_status"),
                "master_rank": item.get("master_rank"),
                "master_confidence": item.get("master_confidence"),
                "elite_score": item.get("elite_score"),
                "elite_rank": item.get("elite_rank"),

                "promotion_level": item.get("promotion_level"),
                "activation_level": item.get("activation_level"),

                "prediction_market": item.get("prediction_market"),
                "prediction_score": item.get("prediction_score"),
                "prediction_alternative_score": item.get("prediction_alternative_score"),
                "prediction_halftime_score": item.get("prediction_halftime_score"),
                "prediction_final_score": item.get("prediction_final_score"),
                "prediction_score_scenarios": item.get("prediction_score_scenarios", []),
                "prediction_market_alignment": item.get("prediction_market_alignment"),
                "prediction_scenario": item.get("prediction_scenario"),
                "prediction_confidence": item.get("prediction_confidence"),
                "prediction_panel_message": item.get("prediction_panel_message"),
                "visual_over_probability": probability_pack.get("visual_over_probability"),
                "visual_under_probability": probability_pack.get("visual_under_probability"),
                "prediction_live_over_probability": probability_pack.get("prediction_live_over_probability"),
                "prediction_live_under_probability": probability_pack.get("prediction_live_under_probability"),
                "prediction_no_goal_probability": probability_pack.get("prediction_no_goal_probability"),
                "prediction_one_goal_probability": probability_pack.get("prediction_one_goal_probability"),
                "prediction_two_plus_goals_probability": probability_pack.get("prediction_two_plus_goals_probability"),
                "prediction_main_score": item.get("prediction_main_score"),
                "prediction_offensive_score": item.get("prediction_offensive_score"),
                "prediction_break_score": item.get("prediction_break_score"),
                "prediction_conservative_score": item.get("prediction_conservative_score"),
                "break_risk": item.get("break_risk"),
                "break_team": item.get("break_team"),

                "entry_minute": item.get("entry_minute"),
                "entry_score": item.get("entry_score"),
                "entry_home_score": item.get("entry_home_score"),
                "entry_away_score": item.get("entry_away_score"),
                "entry_total_goals": item.get("entry_total_goals"),

                "current_minute": item.get("current_minute"),
                "current_score": item.get("current_score"),
                "current_home_score": item.get("current_home_score"),
                "current_away_score": item.get("current_away_score"),
                "current_total_goals": item.get("current_total_goals"),

                "tracking_status": item.get("tracking_status"),
                "result_status": item.get("result_status"),
                "result_label": item.get("result_label"),
                "result_reason": item.get("result_reason"),
                "result_explanation": item.get("result_explanation"),

                "registered_at": item.get("registered_at"),
                "resolved_at": item.get("resolved_at"),

                "clock_status": item.get("clock_status"),
                "data_age_seconds": item.get("data_age_seconds"),
                "timestamp_missing": item.get("timestamp_missing"),
                "risk_status": item.get("risk_status"),
                "risk_score": item.get("risk_score"),
                "failed_secondary_filters": item.get("failed_secondary_filters", []),
                "soft_warnings": item.get("soft_warnings", []),
            })

        return compact

    def _build_dashboard_message(self, stats: Dict[str, Any]) -> str:
        live = stats.get("live_matches", 0)
        analyzed = stats.get("analyzed_matches", 0)
        blocked_by_league = stats.get("blocked_by_league", 0)
        published = stats.get("published_signals", 0)
        pending = stats.get("pending", 0)
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)

        if live <= 0 and blocked_by_league <= 0:
            return "V17 activo, pero todavía no recibió partidos vivos."

        if analyzed <= 0 and blocked_by_league > 0:
            return (
                f"V17 activo. Se recibieron partidos, pero {blocked_by_league} fueron "
                "descartados por filtro de liga."
            )

        if published <= 0:
            return (
                f"V17 activo con {analyzed} partidos analizados. "
                f"{blocked_by_league} fueron descartados por filtro de liga. "
                "Ninguna señal cumple mayoría suficiente."
            )

        return (
            f"V17 activo con {analyzed} partidos analizados, {published} señales publicadas, "
            f"{pending} pendientes, {wins} aciertos y {losses} fallos. "
            f"{blocked_by_league} partidos fueron descartados por liga."
        )
