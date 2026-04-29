from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Dict, List


class SignalLifecycleService:
    """
    Controla el ciclo de vida de una señal.

    Objetivo:
    - Evitar cierres falsos por delay de API.
    - Mantener señales activas con buffer.
    - Resolver por evento real o final del partido.
    - No reemplaza LiveSignalManager todavía; queda listo para integración.
    """

    DEFAULT_ACTIVE_SECONDS = 120
    API_DELAY_BUFFER_SECONDS = 60

    FINISHED_STATUS = {
        "FT", "AET", "PEN", "PST", "CANC", "ABD", "AWD", "WO"
    }

    def __init__(self) -> None:
        self._signals: Dict[str, Dict[str, Any]] = {}

    def register_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(signal, dict):
            return {}

        signal_key = self._signal_key(signal)
        now = datetime.now()

        record = deepcopy(signal)
        record["signal_key"] = signal_key
        record["lifecycle_status"] = "ACTIVE"
        record["lifecycle_created_at"] = record.get("lifecycle_created_at") or now.isoformat(timespec="seconds")
        record["lifecycle_expires_at"] = (
            now + timedelta(seconds=self.DEFAULT_ACTIVE_SECONDS + self.API_DELAY_BUFFER_SECONDS)
        ).isoformat(timespec="seconds")
        record["lifecycle_close_reason"] = None

        self._signals[signal_key] = record
        return deepcopy(record)

    def update_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        signal_key = self._signal_key(signal)

        if signal_key not in self._signals:
            return self.register_signal(signal)

        existing = deepcopy(self._signals[signal_key])
        created_at = existing.get("lifecycle_created_at")
        expires_at = existing.get("lifecycle_expires_at")

        existing.update(deepcopy(signal))
        existing["signal_key"] = signal_key
        existing["lifecycle_status"] = "ACTIVE"
        existing["lifecycle_created_at"] = created_at
        existing["lifecycle_expires_at"] = expires_at

        self._signals[signal_key] = existing
        return deepcopy(existing)

    def resolve_signal(
        self,
        signal: Dict[str, Any],
        live_match: Dict[str, Any],
        events: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any] | None:
        """
        Devuelve None si sigue activa.
        Devuelve señal cerrada si ya hay resultado.
        """
        if not isinstance(signal, dict):
            return None

        signal_key = self._signal_key(signal)
        record = deepcopy(self._signals.get(signal_key) or signal)

        market = str(record.get("market") or "").upper()
        entry_minute = self._safe_int(record.get("entry_minute") or record.get("minute"))
        entry_total = self._safe_float(record.get("entry_total_goals"))
        current_total = self._total_goals(live_match)
        current_minute = self._minute(live_match)
        status_short = str(live_match.get("status_short") or "").upper()

        goal_after_entry = (
            current_total > entry_total
            or self._has_goal_after(events or [], entry_minute)
        )

        finished = current_minute >= 90 or status_short in self.FINISHED_STATUS

        if "OVER" in market:
            if goal_after_entry:
                return self._close(record, live_match, "WIN", "OVER_GOAL_CONFIRMED_BY_LIFECYCLE")

            if finished:
                return self._close(record, live_match, "LOSS", "OVER_FULLTIME_WITHOUT_GOAL")

            return None

        if "UNDER" in market:
            if goal_after_entry:
                return self._close(record, live_match, "LOSS", "UNDER_GOAL_AGAINST_BY_LIFECYCLE")

            if finished:
                return self._close(record, live_match, "WIN", "UNDER_FULLTIME_WITHOUT_GOAL")

            return None

        return None

    def get_active_signals(self) -> List[Dict[str, Any]]:
        return [
            deepcopy(signal)
            for signal in self._signals.values()
            if signal.get("lifecycle_status") == "ACTIVE"
        ]

    def forget_signal(self, signal: Dict[str, Any]) -> None:
        key = self._signal_key(signal)
        self._signals.pop(key, None)

    def _close(
        self,
        signal: Dict[str, Any],
        live_match: Dict[str, Any],
        result: str,
        reason: str,
    ) -> Dict[str, Any]:
        key = self._signal_key(signal)

        closed = deepcopy(signal)
        closed["signal_key"] = key
        closed["status"] = result
        closed["resultado"] = result
        closed["live_status"] = "CLOSED"
        closed["lifecycle_status"] = "CLOSED"
        closed["lifecycle_close_reason"] = reason
        closed["close_reason"] = reason
        closed["closed_at"] = datetime.now().isoformat(timespec="seconds")
        closed["final_score"] = self._score_text(live_match)
        closed["final_minute"] = self._minute(live_match)

        self._signals[key] = closed
        return deepcopy(closed)

    def _has_goal_after(self, events: List[Dict[str, Any]], minute: int) -> bool:
        for event in events:
            event_type = str(event.get("type") or event.get("raw_type") or "").upper()
            detail = str(event.get("detail") or "").upper()
            event_minute = self._event_minute(event)

            if event_minute < minute:
                continue

            if event_type == "GOAL" or "GOAL" in detail:
                return True

        return False

    def _event_minute(self, event: Dict[str, Any]) -> int:
        time_data = event.get("time") if isinstance(event.get("time"), dict) else {}

        return self._safe_int(
            event.get("minute")
            or event.get("elapsed")
            or time_data.get("elapsed")
        )

    def _signal_key(self, signal: Dict[str, Any]) -> str:
        key = signal.get("signal_key") or signal.get("signal_id")
        if key:
            return str(key).strip().upper()

        match_id = signal.get("match_id")
        market = signal.get("market") or "SIGNAL"

        return f"{str(match_id).strip()}:{str(market).strip().upper()}"

    def _score_text(self, item: Dict[str, Any]) -> str:
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

    def _total_goals(self, item: Dict[str, Any]) -> float:
        try:
            home, away = self._score_text(item).split("-", 1)
            return float(home.strip()) + float(away.strip())
        except Exception:
            return 0.0

    def _minute(self, item: Dict[str, Any]) -> int:
        return self._safe_int(
            item.get("minute")
            or item.get("minuto")
            or item.get("current_minute")
            or item.get("match_minute")
            or item.get("final_minute")
        )

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
