from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime


class LiveEventTracker:
    """
    Rastrea eventos en vivo por partido.

    Funciona como memoria de eventos:
    - Guarda historial por fixture
    - Detecta nuevos eventos
    - Evita duplicados
    - Permite saber si hubo gol después de la señal
    """

    def __init__(self) -> None:
        # fixture_id -> [eventos]
        self._events_by_fixture: Dict[str, List[Dict[str, Any]]] = {}

    # ---------------------------------------------------
    # INGESTA DE EVENTOS DESDE API
    # ---------------------------------------------------

    def ingest(
        self,
        fixture_id: Any,
        events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Recibe eventos actuales del API y devuelve solo los nuevos.
        """
        if not fixture_id or not isinstance(events, list):
            return []

        key = str(fixture_id)

        stored = self._events_by_fixture.get(key, [])

        stored_ids = {
            self._event_id(e)
            for e in stored
            if self._event_id(e)
        }

        new_events: List[Dict[str, Any]] = []

        for event in events:
            eid = self._event_id(event)

            if not eid:
                continue

            if eid not in stored_ids:
                normalized = self._normalize_event(event)
                new_events.append(normalized)
                stored.append(normalized)

        # guardamos historial actualizado
        self._events_by_fixture[key] = stored[-200:]  # límite de memoria

        return new_events

    # ---------------------------------------------------
    # CONSULTAS
    # ---------------------------------------------------

    def has_goal_after(
        self,
        fixture_id: Any,
        minute: int,
    ) -> bool:
        """
        Detecta si hubo gol después del minuto dado.
        """
        events = self._events_by_fixture.get(str(fixture_id), [])

        for event in events:
            if event["type"] == "GOAL" and event["minute"] > minute:
                return True

        return False

    def last_goal_minute(
        self,
        fixture_id: Any,
    ) -> int:
        events = self._events_by_fixture.get(str(fixture_id), [])

        goals = [
            event["minute"]
            for event in events
            if event["type"] == "GOAL"
        ]

        return max(goals) if goals else 0

    def has_red_card_after(
        self,
        fixture_id: Any,
        minute: int,
    ) -> bool:
        events = self._events_by_fixture.get(str(fixture_id), [])

        for event in events:
            if event["type"] == "RED_CARD" and event["minute"] >= minute:
                return True

        return False

    def get_recent_events(
        self,
        fixture_id: Any,
        last_minutes: int = 5,
        current_minute: int = 0,
    ) -> List[Dict[str, Any]]:
        events = self._events_by_fixture.get(str(fixture_id), [])

        return [
            e for e in events
            if current_minute - e["minute"] <= last_minutes
        ]

    # ---------------------------------------------------
    # NORMALIZACIÓN
    # ---------------------------------------------------

    def _normalize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event_type = str(event.get("type") or "").upper()
        detail = str(event.get("detail") or "").upper()

        minute = self._safe_int(
            event.get("time", {}).get("elapsed")
            or event.get("minute")
        )

        normalized_type = "OTHER"

        if event_type == "GOAL":
            normalized_type = "GOAL"

        elif event_type == "CARD":
            if "RED" in detail:
                normalized_type = "RED_CARD"
            elif "YELLOW" in detail:
                normalized_type = "YELLOW_CARD"

        elif event_type == "VAR":
            normalized_type = "VAR"

        elif event_type == "SUBSTITUTION":
            normalized_type = "SUB"

        return {
            "id": self._event_id(event),
            "type": normalized_type,
            "raw_type": event_type,
            "detail": detail,
            "minute": minute,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

    def _event_id(self, event: Dict[str, Any]) -> str | None:
        return str(
            event.get("id")
            or event.get("event_id")
            or f"{event.get('type')}-{event.get('time', {}).get('elapsed')}-{event.get('team', {}).get('id')}"
        )

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0
