from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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


class V17DashboardAdapter:
    """
    Adaptador principal V17.

    Responsabilidades:
    - Recibir datos live desde V16 o desde cualquier fuente.
    - Pasarlos al motor V17.
    - Registrar señales publicadas.
    - Actualizar tracking.
    - Entregar un dashboard limpio y rápido al frontend.
    """

    def __init__(self) -> None:
        self.engine = LiveSignalEngineV17()
        self.tracker = SignalTracker()

        self._last_dashboard: Dict[str, Any] = {
            "ok": True,
            "version": "V17",
            "updated_at": utc_now_iso(),
            "top_signals": [],
            "observe": [],
            "no_bet": [],
            "blocked": [],
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
        """
        Construye el dashboard V17 desde una lista de partidos.
        """

        engine_result = self.engine.process_live_matches(raw_matches or [])

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
        """
        Construye dashboard V17 desde una respuesta antigua V16.

        Soporta varias formas:
        - payload["live"]
        - payload["live_matches"]
        - payload["matches"]
        - payload["signals"]
        - payload["opportunities"]
        """

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
        all_analyzed = engine_result.get("all_analyzed", [])

        pending_signals = tracking_result.get("pending", [])
        closed_history = tracking_result.get("closed", [])
        history = pending_signals + closed_history

        tracking_summary = tracking_result.get("summary", {})
        learning = tracking_result.get("learning", {})
        performance_analysis = tracking_result.get("performance_analysis", {})

        stats = {
            "live_matches": engine_result.get("live_count", 0),
            "analyzed_matches": engine_result.get("analyzed_count", 0),
            "published_signals": len(top_signals),
            "observe": len(observe),
            "no_bet": len(no_bet),
            "blocked": len(blocked),
            "pending": tracking_summary.get("pending", 0),
            "closed": tracking_summary.get("closed", 0),
            "wins": tracking_summary.get("wins", 0),
            "losses": tracking_summary.get("losses", 0),
            "voids": tracking_summary.get("voids", 0),
            "precision": tracking_summary.get("precision", 0),
            "total_tracked": tracking_summary.get("total_tracked", 0),
        }

        return {
            "ok": True,
            "version": "V17",
            "updated_at": utc_now_iso(),
            "source_status": source_status,
            "frontend_safe": True,

            "live_matches": all_analyzed,
            "top_signals": self._compact_signals(top_signals),
            "observe": self._compact_signals(observe[:20]),
            "no_bet": self._compact_signals(no_bet[:20]),
            "blocked": self._compact_signals(blocked[:20]),

            "pending_signals": self._compact_history(pending_signals),
            "closed_history": self._compact_history(closed_history),
            "history": self._compact_history(history),

            "registered_signals": self._compact_history(registered),

            "stats": stats,
            "summary": {
                **engine_result.get("summary", {}),
                **tracking_summary,
            },
            "learning": learning,
            "performance_analysis": performance_analysis,

            "message": self._build_dashboard_message(stats),
        }

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
            "opportunities",
            "active_signals",
        ]

        for key in candidate_keys:
            value = payload.get(key)
            collected.extend(self._extract_list(value))

        if "data" in payload:
            collected.extend(self._extract_live_items(payload.get("data") or {}))

        if "payload" in payload:
            collected.extend(self._extract_live_items(payload.get("payload") or {}))

        return self._dedupe_items(collected)

    def _extract_list(self, value: Any) -> List[Dict[str, Any]]:
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]

        if isinstance(value, dict):
            for key in ["items", "data", "matches", "live", "signals", "opportunities"]:
                nested = value.get(key)
                if isinstance(nested, list):
                    return [x for x in nested if isinstance(x, dict)]

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

            old_minute = safe_int(
                old.get("api_minute")
                or old.get("minute")
                or old.get("display_minute"),
                0,
            )
            new_minute = safe_int(
                item.get("api_minute")
                or item.get("minute")
                or item.get("display_minute"),
                0,
            )

            old_score = safe_int(old.get("home_score"), 0) + safe_int(old.get("away_score"), 0)
            new_score = safe_int(item.get("home_score"), 0) + safe_int(item.get("away_score"), 0)

            if new_minute >= old_minute or new_score >= old_score:
                merged = {**old, **item}
                result[match_id] = merged

        return list(result.values())

    def _compact_signals(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compact: List[Dict[str, Any]] = []

        for item in items or []:
            compact.append({
                "version": "V17",
                "signal_key": item.get("signal_key"),
                "signal_id": item.get("signal_id"),
                "match_id": item.get("match_id"),
                "fixture_id": item.get("fixture_id"),

                "home_team": item.get("home_team"),
                "away_team": item.get("away_team"),
                "league": item.get("league"),
                "country": item.get("country"),

                "api_minute": item.get("api_minute"),
                "display_minute": item.get("display_minute"),
                "estimated_minute": item.get("estimated_minute"),
                "clock_status": item.get("clock_status"),
                "clock_action": item.get("clock_action"),
                "data_age_seconds": item.get("data_age_seconds"),

                "home_score": item.get("home_score"),
                "away_score": item.get("away_score"),
                "scoreline": item.get("scoreline"),
                "current_score": item.get("current_score"),

                "market": item.get("market"),
                "suggested_market": item.get("suggested_market"),
                "market_category": item.get("market_category"),
                "context_category": item.get("context_category"),

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

                "over_score": item.get("over_score"),
                "under_score": item.get("under_score"),
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

                "main_reading": item.get("main_reading"),
                "what_is_missing": item.get("what_is_missing"),

                "updated_at": item.get("updated_at"),
            })

        return compact

    def _compact_history(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compact: List[Dict[str, Any]] = []

        for item in items or []:
            compact.append({
                "version": "V17",
                "signal_key": item.get("signal_key"),
                "signal_id": item.get("signal_id"),
                "match_id": item.get("match_id"),

                "home_team": item.get("home_team"),
                "away_team": item.get("away_team"),
                "league": item.get("league"),
                "country": item.get("country"),

                "market": item.get("market"),
                "master_status": item.get("master_status"),
                "master_rank": item.get("master_rank"),
                "elite_score": item.get("elite_score"),
                "elite_rank": item.get("elite_rank"),

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
                "risk_status": item.get("risk_status"),
                "risk_score": item.get("risk_score"),
                "failed_secondary_filters": item.get("failed_secondary_filters", []),
                "soft_warnings": item.get("soft_warnings", []),
            })

        return compact

    def _build_dashboard_message(self, stats: Dict[str, Any]) -> str:
        live = stats.get("live_matches", 0)
        published = stats.get("published_signals", 0)
        pending = stats.get("pending", 0)
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)

        if live <= 0:
            return "V17 activo, pero todavía no recibió partidos vivos."

        if published <= 0:
            return "V17 activo. Hay partidos vivos, pero ninguna señal cumple mayoría suficiente."

        return (
            f"V17 activo con {live} partidos vivos, {published} señales publicadas, "
            f"{pending} pendientes, {wins} aciertos y {losses} fallos."
      )
