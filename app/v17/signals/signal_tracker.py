from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.v17.signals.learning_memory import LearningMemory
from app.v17.signals.result_resolver import ResultResolver


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


class SignalTracker:
    """
    Tracking de señales V17.

    Funciones:
    - registra señales publicadas
    - evita duplicados
    - mantiene pendientes
    - resuelve resultados
    - guarda aprendizaje
    """

    def __init__(self, max_pending: int = 100) -> None:
        self.max_pending = max_pending
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._closed: List[Dict[str, Any]] = []

        self.resolver = ResultResolver()
        self.learning_memory = LearningMemory()

    def register_published_signals(self, top_signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        registered: List[Dict[str, Any]] = []

        for signal in top_signals or []:
            if not isinstance(signal, dict):
                continue

            if not signal.get("can_publish"):
                continue

            signal_key = signal.get("signal_key") or signal.get("signal_id")

            if not signal_key:
                continue

            if signal_key in self._pending:
                existing = self._pending[signal_key]
                existing.update(self._refresh_tracking_view(existing, signal))
                registered.append(deepcopy(existing))
                continue

            tracked = self._create_tracking_record(signal)
            self._pending[signal_key] = tracked
            registered.append(deepcopy(tracked))

        self._trim_pending()
        return registered

    def update_with_live_matches(self, live_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        match_index = self._build_match_index(live_matches)

        still_pending: Dict[str, Dict[str, Any]] = {}
        newly_closed: List[Dict[str, Any]] = []

        for signal_key, tracked in list(self._pending.items()):
            match_id = str(tracked.get("match_id") or tracked.get("fixture_id") or "")

            current_match = match_index.get(match_id)

            if not current_match:
                tracked["tracking_status"] = "PENDING"
                tracked["pending_reason"] = "MATCH_NOT_FOUND_IN_LIVE_SNAPSHOT"
                still_pending[signal_key] = tracked
                continue

            resolved = self.resolver.resolve(tracked, current_match)

            if resolved.get("resolved"):
                resolved["tracking_status"] = "CLOSED"
                newly_closed.append(resolved)
                self._closed.insert(0, deepcopy(resolved))
                self.learning_memory.add_result(resolved)
            else:
                resolved["tracking_status"] = "PENDING"
                still_pending[signal_key] = resolved

        self._pending = still_pending
        self._closed = self._closed[:500]

        return {
            "pending": self.pending(),
            "closed": self.closed(),
            "newly_closed": newly_closed,
            "summary": self.summary(),
            "learning": self.learning_memory.summary(),
            "performance_analysis": self.learning_memory.performance_analysis(),
        }

    def pending(self) -> List[Dict[str, Any]]:
        return sorted(
            [deepcopy(x) for x in self._pending.values()],
            key=lambda x: safe_int(x.get("entry_minute"), 0),
            reverse=True,
        )

    def closed(self, limit: int = 100) -> List[Dict[str, Any]]:
        return deepcopy(self._closed[:limit])

    def history(self, limit: int = 100) -> List[Dict[str, Any]]:
        items = self.closed(limit=limit) + self.pending()
        return items[:limit]

    def summary(self) -> Dict[str, Any]:
        pending = len(self._pending)
        closed = len(self._closed)

        wins = sum(1 for x in self._closed if x.get("result_status") == "WON")
        losses = sum(1 for x in self._closed if x.get("result_status") == "LOST")
        voids = sum(1 for x in self._closed if x.get("result_status") == "VOID")

        precision = round((wins / max(1, wins + losses)) * 100, 2)

        return {
            "pending": pending,
            "closed": closed,
            "wins": wins,
            "losses": losses,
            "voids": voids,
            "precision": precision,
            "total_tracked": pending + closed,
        }

    def get_tracking_summary(self) -> Dict[str, Any]:
        return self.summary()

    def get_tracking_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.history(limit=limit)

    def get_performance_analysis(self) -> Dict[str, Any]:
        return self.learning_memory.performance_analysis()

    def _create_tracking_record(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        entry_minute = safe_int(
            signal.get("api_minute")
            or signal.get("display_minute")
            or signal.get("minute"),
            0,
        )

        entry_home_score = safe_int(signal.get("home_score"), 0)
        entry_away_score = safe_int(signal.get("away_score"), 0)

        market = str(
            signal.get("market")
            or signal.get("master_market")
            or signal.get("suggested_market")
            or "NO_BET"
        ).upper()

        max_follow_minutes = 20

        if market == "UNDER":
            max_follow_minutes = 18

        if entry_minute >= 80:
            max_follow_minutes = 12

        if entry_minute >= 88:
            max_follow_minutes = 8

        return {
            **deepcopy(signal),
            "tracking_status": "PENDING",
            "result_status": "PENDING",
            "result_label": "PENDIENTE",
            "registered_at": utc_now_iso(),
            "entry_minute": entry_minute,
            "entry_home_score": entry_home_score,
            "entry_away_score": entry_away_score,
            "entry_score": f"{entry_home_score}-{entry_away_score}",
            "entry_total_goals": entry_home_score + entry_away_score,
            "market": market,
            "max_follow_minutes": max_follow_minutes,
            "resolved": False,
            "resolved_at": None,
            "result_reason": "TRACKING_STARTED",
            "result_explanation": "La señal fue publicada y se encuentra en seguimiento.",
        }

    def _refresh_tracking_view(
        self,
        existing: Dict[str, Any],
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Actualiza lectura visual de una señal pendiente sin borrar su entrada original.
        """

        keep_fields = {
            "registered_at",
            "entry_minute",
            "entry_home_score",
            "entry_away_score",
            "entry_score",
            "entry_total_goals",
            "max_follow_minutes",
            "result_status",
            "result_label",
            "tracking_status",
            "resolved",
            "resolved_at",
        }

        refreshed = deepcopy(existing)

        for key, value in signal.items():
            if key not in keep_fields:
                refreshed[key] = value

        refreshed["last_seen_at"] = utc_now_iso()
        refreshed["tracking_status"] = "PENDING"

        return refreshed

    def _build_match_index(self, live_matches: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        index: Dict[str, Dict[str, Any]] = {}

        for match in live_matches or []:
            if not isinstance(match, dict):
                continue

            match_id = str(match.get("match_id") or match.get("fixture_id") or "")
            if match_id:
                index[match_id] = match

        return index

    def _trim_pending(self) -> None:
        if len(self._pending) <= self.max_pending:
            return

        items = sorted(
            self._pending.items(),
            key=lambda kv: safe_int(kv[1].get("entry_minute"), 0),
            reverse=True,
        )

        self._pending = dict(items[: self.max_pending])
