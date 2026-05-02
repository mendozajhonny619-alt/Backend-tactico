from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List

from app.services.live_event_tracker import LiveEventTracker
from app.services.signal_lifecycle_service import SignalLifecycleService
from app.services.signal_risk_reducer import SignalRiskReducer


class LiveSignalManager:
    """
    Gestiona señales activas.
    """

    FINISHED_STATUS = {
        "FT", "AET", "PEN", "PST", "CANC", "ABD", "AWD", "WO"
    }

    def __init__(self) -> None:
        self._active_signals: List[Dict[str, Any]] = []
        self._recently_closed: List[Dict[str, Any]] = []
        self._closed_keys: set[str] = set()

        self._event_tracker = LiveEventTracker()
        self._lifecycle = SignalLifecycleService()
        self._risk_reducer = SignalRiskReducer()

        # Tracking interno de rendimiento
        self._tracking_history: List[Dict[str, Any]] = []
        self._tracked_closed_keys: set[str] = set()

    def sync(self, published_signals: List[Dict[str, Any]]) -> Dict[str, int]:
        published_signals = published_signals or []

        created = 0
        updated = 0
        ignored_closed = 0

        current_by_key: Dict[str, Dict[str, Any]] = {}

        for signal in self._active_signals:
            key = self._signal_key(signal)
            if key:
                current_by_key[key] = deepcopy(signal)

        for incoming in published_signals:
            if not isinstance(incoming, dict):
                continue

            key = self._signal_key(incoming)
            if not key:
                continue

            if key in self._closed_keys:
                ignored_closed += 1
                continue

            if key in current_by_key:
                merged = self._merge_signal(current_by_key[key], incoming)
                merged.update(self._risk_reducer.evaluate(merged))
                current_by_key[key] = self._lifecycle.update_signal(merged)
                updated += 1
            else:
                new_signal = deepcopy(incoming)
                new_signal["signal_key"] = key
                new_signal["live_status"] = "ACTIVE"
                new_signal["entry_score"] = self._score_text(new_signal)
                new_signal["entry_total_goals"] = self._total_goals(new_signal)
                new_signal["entry_minute"] = self._minute(new_signal)
                new_signal["current_score"] = new_signal["entry_score"]
                new_signal["current_minute"] = new_signal["entry_minute"]
                new_signal["activated_at"] = datetime.now().isoformat(timespec="seconds")
                new_signal.update(self._risk_reducer.evaluate(new_signal))

                current_by_key[key] = self._lifecycle.register_signal(new_signal)
                created += 1

        self._active_signals = list(current_by_key.values())

        return {
            "created": created,
            "updated": updated,
            "invalidated": 0,
            "ignored_closed": ignored_closed,
        }

    def resolve_finished_matches(self, live_matches: List[Dict[str, Any]]) -> int:
        live_matches = live_matches or []

        live_by_id = {
            str(match.get("match_id")): match
            for match in live_matches
            if isinstance(match, dict) and match.get("match_id") is not None
        }

        kept: List[Dict[str, Any]] = []
        removed = 0

        for signal in self._active_signals:
            match_id = signal.get("match_id")

            if match_id is None:
                closed = self._close_without_live_match(
                    signal,
                    reason="MATCH_ID_MISSING",
                )
                self._recently_closed.append(closed)
                self._track_closed_signal(closed)
                removed += 1
                continue

            live_match = live_by_id.get(str(match_id))

            if not live_match:
                closed = self._close_without_live_match(
                    signal,
                    reason="MATCH_NOT_LIVE_ANYMORE",
                )
                self._recently_closed.append(closed)
                self._track_closed_signal(closed)
                removed += 1
                continue

            events = live_match.get("events") or []
            self._event_tracker.ingest(match_id, events)

            lifecycle_closed = self._lifecycle.resolve_signal(
                signal=signal,
                live_match=live_match,
                events=events,
            )

            if lifecycle_closed:
                key = self._signal_key(signal)
                if key:
                    self._closed_keys.add(key)

                self._recently_closed.append(lifecycle_closed)
                self._track_closed_signal(lifecycle_closed)
                self._lifecycle.forget_signal(signal)
                removed += 1
                continue

            result = self._evaluate_signal_result(signal, live_match)

            if result:
                closed = self._close_signal(
                    signal=signal,
                    result=result["result"],
                    reason=result["reason"],
                    live_match=live_match,
                )
                self._recently_closed.append(closed)
                self._track_closed_signal(closed)
                self._lifecycle.forget_signal(signal)
                removed += 1
                continue

            updated_signal = deepcopy(signal)
            updated_signal["current_score"] = self._score_text(live_match)
            updated_signal["current_minute"] = self._minute(live_match)

            updated_signal["score"] = self._score_text(live_match)
            updated_signal["minute"] = self._minute(live_match)
            updated_signal["home_score"] = self._safe_int(
                live_match.get("home_score")
                or live_match.get("local_score")
                or live_match.get("marcador_local")
            )
            updated_signal["away_score"] = self._safe_int(
                live_match.get("away_score")
                or live_match.get("visitante_score")
                or live_match.get("marcador_visitante")
            )

            self._refresh_live_fields(updated_signal, live_match)

            updated_signal["last_seen_at"] = datetime.now().isoformat(timespec="seconds")
            updated_signal.update(self._risk_reducer.evaluate(updated_signal))

            updated_signal = self._lifecycle.update_signal(updated_signal)
            kept.append(updated_signal)

        self._active_signals = kept
        return removed

    def pop_recently_closed(self) -> List[Dict[str, Any]]:
        closed = deepcopy(self._recently_closed)
        self._recently_closed = []
        return closed

    def get_active_signals(self) -> List[Dict[str, Any]]:
        return deepcopy(self._active_signals)

    def get_tracking_history(self) -> List[Dict[str, Any]]:
        return deepcopy(self._tracking_history)

    def get_tracking_summary(self) -> Dict[str, Any]:
        return self._build_tracking_summary(self._tracking_history)

    def _refresh_live_fields(
        self,
        signal: Dict[str, Any],
        live_match: Dict[str, Any],
    ) -> None:
        fields = [
            "shots",
            "shots_on_target",
            "corners",
            "dangerous_attacks",
            "xg",
            "xG",
            "red_cards",
            "possession_home",
            "possession_away",
            "status_short",
            "status_long",
            "data_quality",
            "has_live_stats",
            "is_scannable",
            "stats_source",
            "events",
            "event_count",
            "home_logo",
            "away_logo",
            "league_logo",
            "country_flag",
            "home_team_logo",
            "away_team_logo",
            "local_logo",
            "visitor_logo",
            "competition_logo",
            "league_flag",
            "flag",
            "league",
            "country",
            "liga",
            "país",
        ]

        for field in fields:
            if field in live_match:
                signal[field] = deepcopy(live_match.get(field))

        if isinstance(live_match.get("home_stats"), dict):
            signal["home_stats"] = deepcopy(live_match.get("home_stats"))

        if isinstance(live_match.get("away_stats"), dict):
            signal["away_stats"] = deepcopy(live_match.get("away_stats"))

    def _track_closed_signal(self, closed_signal: Dict[str, Any]) -> None:
        key = self._signal_key(closed_signal)
        if not key:
            key = str(closed_signal.get("signal_id") or closed_signal.get("match_id") or "")

        if not key or key in self._tracked_closed_keys:
            return

        self._tracked_closed_keys.add(key)

        result = str(
            closed_signal.get("status")
            or closed_signal.get("resultado")
            or "VOID"
        ).upper()

        tracked = {
            "signal_key": key,
            "signal_id": closed_signal.get("signal_id") or key,
            "match_id": closed_signal.get("match_id"),
            "match_name": closed_signal.get("match_name"),
            "league": closed_signal.get("league"),
            "country": closed_signal.get("country"),
            "market": closed_signal.get("market"),
            "rank": closed_signal.get("rank"),
            "signal_mode": closed_signal.get("signal_mode"),
            "minute": closed_signal.get("minute"),
            "entry_minute": closed_signal.get("entry_minute"),
            "final_minute": closed_signal.get("final_minute"),
            "entry_score": closed_signal.get("entry_score"),
            "final_score": closed_signal.get("final_score"),
            "status": result,
            "resultado": result,
            "close_reason": closed_signal.get("close_reason"),
            "ai_score": closed_signal.get("ai_score"),
            "goal_probability": closed_signal.get("goal_probability"),
            "over_probability": closed_signal.get("over_probability"),
            "under_probability": closed_signal.get("under_probability"),
            "risk_score": closed_signal.get("risk_score"),
            "risk_level": closed_signal.get("risk_level"),
            "signal_score": closed_signal.get("signal_score"),
            "context_state": closed_signal.get("context_state"),
            "data_quality": closed_signal.get("data_quality"),
            "game_quality": closed_signal.get("game_quality"),
            "risk_reducer_status": closed_signal.get("risk_reducer_status"),
            "risk_reducer_reason": closed_signal.get("risk_reducer_reason"),
            "live_advice": closed_signal.get("live_advice"),
            "active_minutes": closed_signal.get("active_minutes"),
            "closed_at": closed_signal.get("closed_at") or datetime.now().isoformat(timespec="seconds"),
        }

        self._tracking_history.append(tracked)

    def _build_tracking_summary(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(history)
        wins = sum(1 for item in history if str(item.get("status")).upper() == "WIN")
        losses = sum(1 for item in history if str(item.get("status")).upper() == "LOSS")
        voids = sum(1 for item in history if str(item.get("status")).upper() == "VOID")

        decided = wins + losses
        winrate = round((wins / decided) * 100, 2) if decided else 0.0

        return {
            "total_signals": total,
            "wins": wins,
            "losses": losses,
            "voids": voids,
            "decided": decided,
            "winrate": winrate,
            "by_rank": self._group_tracking(history, "rank"),
            "by_league": self._group_tracking(history, "league"),
            "by_market": self._group_tracking(history, "market"),
        }

    def _group_tracking(self, history: List[Dict[str, Any]], field: str) -> Dict[str, Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}

        for item in history:
            key = str(item.get(field) or "UNKNOWN").upper()
            status = str(item.get("status") or "VOID").upper()

            if key not in grouped:
                grouped[key] = {
                    "total": 0,
                    "wins": 0,
                    "losses": 0,
                    "voids": 0,
                    "decided": 0,
                    "winrate": 0.0,
                }

            grouped[key]["total"] += 1

            if status == "WIN":
                grouped[key]["wins"] += 1
                grouped[key]["decided"] += 1
            elif status == "LOSS":
                grouped[key]["losses"] += 1
                grouped[key]["decided"] += 1
            else:
                grouped[key]["voids"] += 1

        for key, stats in grouped.items():
            decided = stats["decided"]
            stats["winrate"] = round((stats["wins"] / decided) * 100, 2) if decided else 0.0

        return grouped

    def _evaluate_signal_result(
        self,
        signal: Dict[str, Any],
        live_match: Dict[str, Any],
    ) -> Dict[str, str] | None:
        market = str(signal.get("market") or "").upper()

        entry_total = self._safe_float(signal.get("entry_total_goals"))
        entry_minute = self._safe_int(signal.get("entry_minute"))

        current_total = self._total_goals(live_match)
        current_minute = self._minute(live_match)
        status_short = str(live_match.get("status_short") or "").upper()

        goal_after_entry = (
            current_total > entry_total
            or self._event_tracker.has_goal_after(
                signal.get("match_id"),
                entry_minute
            )
        )

        finished = (
            current_minute >= 90
            or status_short in self.FINISHED_STATUS
        )

        if "OVER" in market:
            if goal_after_entry:
                return {
                    "result": "WIN",
                    "reason": "OVER_GOAL_CONFIRMED",
                }

            if finished:
                return {
                    "result": "LOSS",
                    "reason": "OVER_FULLTIME_WITHOUT_GOAL",
                }

            return None

        if "UNDER" in market:
            if goal_after_entry:
                return {
                    "result": "LOSS",
                    "reason": "UNDER_GOAL_AGAINST",
                }

            if finished:
                return {
                    "result": "WIN",
                    "reason": "UNDER_FULLTIME_WITHOUT_GOAL",
                }

            return None

        return None

    def _close_without_live_match(
        self,
        signal: Dict[str, Any],
        reason: str,
    ) -> Dict[str, Any]:
        key = self._signal_key(signal)
        if key:
            self._closed_keys.add(key)

        self._lifecycle.forget_signal(signal)

        closed = deepcopy(signal)
        closed["signal_key"] = key or closed.get("signal_key")
        closed["final_score"] = (
            closed.get("current_score")
            or closed.get("entry_score")
            or self._score_text(closed)
        )
        closed["final_minute"] = closed.get("current_minute") or closed.get("minute")
        closed["live_status"] = "CLOSED"
        closed["status"] = "VOID"
        closed["resultado"] = "VOID"
        closed["close_reason"] = reason
        closed["closed_at"] = datetime.now().isoformat(timespec="seconds")
        return closed

    def _close_signal(
        self,
        signal: Dict[str, Any],
        result: str,
        reason: str,
        live_match: Dict[str, Any],
    ) -> Dict[str, Any]:
        key = self._signal_key(signal)
        if key:
            self._closed_keys.add(key)

        closed = deepcopy(signal)
        closed["signal_key"] = key or closed.get("signal_key")

        closed["final_score"] = self._score_text(live_match)
        closed["final_minute"] = self._minute(live_match)
        closed["home_score"] = self._safe_int(
            live_match.get("home_score")
            or live_match.get("local_score")
            or live_match.get("marcador_local")
        )
        closed["away_score"] = self._safe_int(
            live_match.get("away_score")
            or live_match.get("visitante_score")
            or live_match.get("marcador_visitante")
        )

        self._refresh_live_fields(closed, live_match)
        closed.update(self._risk_reducer.evaluate(closed))

        closed["live_status"] = "CLOSED"
        closed["status"] = result
        closed["resultado"] = result
        closed["close_reason"] = reason
        closed["closed_at"] = datetime.now().isoformat(timespec="seconds")

        return closed

    def _merge_signal(self, existing, incoming):
        merged = deepcopy(existing)

        entry_score = merged.get("entry_score")
        entry_total = merged.get("entry_total_goals")
        entry_minute = merged.get("entry_minute")
        activated_at = merged.get("activated_at")

        merged.update(deepcopy(incoming))

        merged["live_status"] = "ACTIVE"
        merged["entry_score"] = (
            entry_score if entry_score is not None else self._score_text(incoming)
        )
        merged["entry_total_goals"] = (
            entry_total if entry_total is not None else self._total_goals(incoming)
        )
        merged["entry_minute"] = (
            entry_minute if entry_minute is not None else self._minute(incoming)
        )
        merged["activated_at"] = activated_at or datetime.now().isoformat(timespec="seconds")
        merged["current_score"] = self._score_text(incoming)
        merged["current_minute"] = self._minute(incoming)
        merged["score"] = self._score_text(incoming)
        merged["minute"] = self._minute(incoming)
        merged["last_seen_at"] = datetime.now().isoformat(timespec="seconds")

        return merged

    def _signal_key(self, signal):
        key = signal.get("signal_key") or signal.get("signal_id")
        if key:
            text = str(key).strip().upper()
            parts = text.split(":")
            return f"{parts[0]}:{parts[1]}" if len(parts) >= 2 else text

        match_id = signal.get("match_id")
        market = signal.get("market")

        if match_id is None or market is None:
            return None

        return f"{str(match_id).strip()}:{str(market).strip().upper()}"

    def _score_text(self, item):
        score = item.get("score") or item.get("marcador")
        if score:
            return str(score)

        home = self._safe_int(
            item.get("home_score")
            or item.get("local_score")
            or item.get("marcador_local")
        )
        away = self._safe_int(
            item.get("away_score")
            or item.get("visitante_score")
            or item.get("marcador_visitante")
        )

        return f"{home}-{away}"

    def _total_goals(self, item):
        try:
            h, a = self._score_text(item).split("-")
            return float(h) + float(a)
        except Exception:
            return 0.0

    def _minute(self, item):
        return self._safe_int(
            item.get("minute")
            or item.get("minuto")
            or item.get("current_minute")
            or item.get("match_minute")
            or item.get("final_minute")
        )

    def _safe_int(self, v):
        try:
            return int(float(v or 0))
        except Exception:
            return 0

    def _safe_float(self, v):
        try:
            return float(v or 0)
        except Exception:
            return 0.0
