from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List


class RuntimeState:
    """
    Estado en memoria del sistema en tiempo real.

    Guarda:
    - partidos live
    - señales activas
    - historial de señales
    - oportunidades
    - bloqueados
    - estadísticas
    - salud del sistema
    """

    MAX_HISTORY = 300

    def __init__(self) -> None:
        self._live_matches: List[Dict[str, Any]] = []
        self._active_signals: List[Dict[str, Any]] = []
        self._signals_history: List[Dict[str, Any]] = []
        self._opportunities: List[Dict[str, Any]] = []
        self._blocked: List[Dict[str, Any]] = []
        self._stats: Dict[str, Any] = {}

        self._meta: Dict[str, Any] = {
            "updated_at": None,
        }

        self._health: Dict[str, Any] = {
            "status": "STARTING",
            "error": None,
        }

    # ----------------------------
    # LIVE MATCHES
    # ----------------------------

    def update_live_matches(self, matches: List[Dict[str, Any]]) -> None:
        self._live_matches = list(matches or [])
        self._touch()

    def get_live_matches(self) -> List[Dict[str, Any]]:
        return deepcopy(self._live_matches)

    # ----------------------------
    # SIGNALS
    # ----------------------------

    def update_active_signals(self, signals: List[Dict[str, Any]]) -> None:
        self._active_signals = list(signals or [])

        for signal in self._active_signals:
            self.add_signal_to_history(signal)

        self._touch()

    def get_active_signals(self) -> List[Dict[str, Any]]:
        return deepcopy(self._active_signals)

    def add_signal_to_history(self, signal: Dict[str, Any]) -> None:
        if not signal:
            return

        signal_key = (
            signal.get("signal_id")
            or signal.get("signal_key")
            or self._build_history_key(signal)
        )

        existing_keys = {
            item.get("signal_id")
            or item.get("signal_key")
            or self._build_history_key(item)
            for item in self._signals_history
        }

        if signal_key in existing_keys:
            return

        item = dict(signal)
        item.setdefault("signal_id", signal_key)
        item.setdefault("signal_key", signal_key)
        item.setdefault("status", "PENDIENTE")
        item.setdefault("resultado", "PENDIENTE")
        item.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))

        self._signals_history.append(item)

        if len(self._signals_history) > self.MAX_HISTORY:
            self._signals_history = self._signals_history[-self.MAX_HISTORY :]

        self._touch()

    def get_signals_history(self) -> List[Dict[str, Any]]:
        return deepcopy(self._signals_history)

    def update_signal_result(
        self,
        signal_id: str,
        status: str,
        extra: Dict[str, Any] | None = None,
    ) -> None:
        for item in self._signals_history:
            if item.get("signal_id") == signal_id or item.get("signal_key") == signal_id:
                item["status"] = status
                item["resultado"] = status
                item["closed_at"] = datetime.now().isoformat(timespec="seconds")

                if extra:
                    item.update(extra)

                self._touch()
                return

    # ----------------------------
    # OPPORTUNITIES
    # ----------------------------

    def update_opportunities(self, opportunities: List[Dict[str, Any]]) -> None:
        self._opportunities = list(opportunities or [])
        self._touch()

    def get_opportunities(self) -> List[Dict[str, Any]]:
        return deepcopy(self._opportunities)

    # ----------------------------
    # BLOCKED
    # ----------------------------

    def update_blocked(self, blocked: List[Dict[str, Any]]) -> None:
        self._blocked = list(blocked or [])
        self._touch()

    def get_blocked(self) -> List[Dict[str, Any]]:
        return deepcopy(self._blocked)

    # ----------------------------
    # STATS
    # ----------------------------

    def update_stats(self, stats: Dict[str, Any]) -> None:
        self._stats = dict(stats or {})
        self._touch()

    def get_stats(self) -> Dict[str, Any]:
        return deepcopy(self._stats)

    # ----------------------------
    # HEALTH
    # ----------------------------

    def set_health_ok(self) -> None:
        self._health = {
            "status": "OK",
            "error": None,
        }
        self._touch()

    def set_health_error(self, error: str) -> None:
        self._health = {
            "status": "ERROR",
            "error": error,
        }
        self._touch()

    def get_health_status(self) -> Dict[str, Any]:
        return deepcopy(self._health)

    # ----------------------------
    # SNAPSHOT GENERAL
    # ----------------------------

    def snapshot(self) -> Dict[str, Any]:
        return {
            "live_matches": deepcopy(self._live_matches),
            "active_signals": deepcopy(self._active_signals),
            "signals_history": deepcopy(self._signals_history),
            "opportunities": deepcopy(self._opportunities),
            "blocked": deepcopy(self._blocked),
            "stats": deepcopy(self._stats),
            "health": deepcopy(self._health),
            "meta": deepcopy(self._meta),
        }

    # ----------------------------
    # HELPERS
    # ----------------------------

    def _touch(self) -> None:
        self._meta["updated_at"] = datetime.now().isoformat(timespec="seconds")

    def _build_history_key(self, signal: Dict[str, Any]) -> str:
        match_id = signal.get("match_id") or signal.get("id") or signal.get("match_name")
        market = signal.get("market") or signal.get("type") or "SIGNAL"
        minute = signal.get("minute") or signal.get("minuto") or "0"

        return f"{match_id}:{market}:{minute}".upper()
