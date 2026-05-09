from __future__ import annotations

from typing import Any, Dict


class MatchWindowEngine:
    """
    Controla ventanas operativas del partido.

    Ahora no bloquea automáticamente el tramo final.
    Permite lectura late-game si hay:
    - reactivación
    - caos
    - presión real extrema
    - red alert
    - añadido con peligro

    Devuelve:
    - phase
    - reason
    - allowed
    - allow_over
    - allow_under
    - bias
    - gate_min_score
    """

    PHASE_BLOCKED = "BLOCKED"
    PHASE_RESTRICTED = "RESTRICTED"
    PHASE_OPERABLE = "OPERABLE"
    PHASE_PREMIUM = "PREMIUM"

    def evaluate(self, match: Dict[str, Any]) -> Dict[str, Any]:
        match = match or {}

        minute = self._extract_minute(match)

        context_state = str(match.get("context_state") or "").upper()
        cooling_detected = bool(match.get("cooling_detected", False))
        under_transition_score = self._safe_float(match.get("under_transition_score"))
        pressure = self._safe_float(match.get("pressure_index"))
        rhythm = self._safe_float(match.get("rhythm_index"))

        late_reactivation = bool(match.get("late_reactivation", False))
        chaos_mode = bool(match.get("chaos_mode", False))
        red_alert = bool(match.get("red_alert", False))
        field_vision_status = str(match.get("field_vision_status") or "").upper()
        is_added_time = bool(
            match.get("is_added_time")
            or match.get("field_vision_is_added_time")
            or minute >= 90
        )

        if minute <= 0:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_BLOCKED,
                allowed=False,
                allow_over=False,
                allow_under=False,
                bias="NONE",
                gate_min_score=999,
                reason="WINDOW_INVALID_MINUTE",
            )

        late_over_allowed = self._has_late_over_permission(
            minute=minute,
            context_state=context_state,
            pressure=pressure,
            rhythm=rhythm,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            red_alert=red_alert,
            field_vision_status=field_vision_status,
            is_added_time=is_added_time,
        )

        if self._is_dead_live_context(
            context_state=context_state,
            cooling_detected=cooling_detected,
            under_transition_score=under_transition_score,
            pressure=pressure,
            rhythm=rhythm,
            late_over_allowed=late_over_allowed,
        ):
            return self._build_response(
                minute=minute,
                phase=self.PHASE_RESTRICTED,
                allowed=True,
                allow_over=False,
                allow_under=True,
                bias="UNDER",
                gate_min_score=76,
                reason="WINDOW_LIVE_CONTEXT_UNDER_ONLY",
            )

        if 1 <= minute <= 14:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_BLOCKED,
                allowed=False,
                allow_over=False,
                allow_under=False,
                bias="NONE",
                gate_min_score=999,
                reason="WINDOW_TOO_EARLY",
            )

        if 15 <= minute <= 24:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_OPERABLE,
                allowed=True,
                allow_over=True,
                allow_under=False,
                bias="OVER",
                gate_min_score=72,
                reason="WINDOW_OPERABLE_FIRST_HALF",
            )

        if 25 <= minute <= 45:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_PREMIUM,
                allowed=True,
                allow_over=True,
                allow_under=False,
                bias="OVER",
                gate_min_score=68,
                reason="WINDOW_PREMIUM_FIRST_HALF",
            )

        if 46 <= minute <= 59:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_OPERABLE,
                allowed=True,
                allow_over=True,
                allow_under=False,
                bias="OVER",
                gate_min_score=70,
                reason="WINDOW_SECOND_HALF_BUILDUP",
            )

        if 60 <= minute <= 75:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_PREMIUM,
                allowed=True,
                allow_over=True,
                allow_under=True,
                bias="BALANCED",
                gate_min_score=68,
                reason="WINDOW_PREMIUM_SECOND_HALF",
            )

        if 76 <= minute <= 85:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_OPERABLE,
                allowed=True,
                allow_over=late_over_allowed,
                allow_under=True,
                bias="OVER" if late_over_allowed else "UNDER",
                gate_min_score=76 if late_over_allowed else 74,
                reason="WINDOW_LATE_REACTIVATION_ALLOWED" if late_over_allowed else "WINDOW_OPERABLE_LATE_GAME",
            )

        if 86 <= minute <= 97:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_RESTRICTED,
                allowed=True,
                allow_over=late_over_allowed,
                allow_under=True,
                bias="OVER" if late_over_allowed else "UNDER",
                gate_min_score=82 if late_over_allowed else 80,
                reason="WINDOW_RESTRICTED_LATE_OVER_ALLOWED" if late_over_allowed else "WINDOW_RESTRICTED_LATE_UNDER_ONLY",
            )

        if 98 <= minute <= 130:
            if late_over_allowed:
                return self._build_response(
                    minute=minute,
                    phase=self.PHASE_RESTRICTED,
                    allowed=True,
                    allow_over=True,
                    allow_under=True,
                    bias="OVER",
                    gate_min_score=86,
                    reason="WINDOW_ADDED_TIME_EXTREME_PRESSURE",
                )

            return self._build_response(
                minute=minute,
                phase=self.PHASE_RESTRICTED,
                allowed=True,
                allow_over=False,
                allow_under=True,
                bias="UNDER",
                gate_min_score=84,
                reason="WINDOW_ADDED_TIME_HOLD_ONLY",
            )

        return self._build_response(
            minute=minute,
            phase=self.PHASE_BLOCKED,
            allowed=False,
            allow_over=False,
            allow_under=False,
            bias="NONE",
            gate_min_score=999,
            reason="WINDOW_TOO_LATE",
        )

    def _has_late_over_permission(
        self,
        minute: int,
        context_state: str,
        pressure: float,
        rhythm: float,
        late_reactivation: bool,
        chaos_mode: bool,
        red_alert: bool,
        field_vision_status: str,
        is_added_time: bool,
    ) -> bool:
        if minute < 76:
            return True

        if late_reactivation or chaos_mode or red_alert:
            return True

        if field_vision_status in {"REACTIVATION", "CHAOS", "OVER_PRESSURE"}:
            return True

        if (
            pressure >= 26
            and rhythm >= 15
            and context_state in {"CALIENTE", "MUY_CALIENTE"}
        ):
            return True

        if is_added_time and pressure >= 30 and rhythm >= 16:
            return True

        return False

    def _is_dead_live_context(
        self,
        context_state: str,
        cooling_detected: bool,
        under_transition_score: float,
        pressure: float,
        rhythm: float,
        late_over_allowed: bool,
    ) -> bool:
        if late_over_allowed:
            return False

        if context_state in {"MUERTO", "FRIO"}:
            return True

        if cooling_detected and context_state in {"CONTROLADO", "FRIO", "MUERTO"}:
            return True

        if under_transition_score >= 70:
            return True

        if context_state == "CONTROLADO" and pressure > 0 and rhythm > 0 and pressure < 26 and rhythm < 20:
            return True

        return False

    def _extract_minute(self, match: Dict[str, Any]) -> int:
        raw = (
            match.get("minute")
            or match.get("current_minute")
            or match.get("match_minute")
            or 0
        )
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return 0

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _build_response(
        self,
        minute: int,
        phase: str,
        allowed: bool,
        allow_over: bool,
        allow_under: bool,
        bias: str,
        gate_min_score: int,
        reason: str,
    ) -> Dict[str, Any]:
        return {
            "minute": minute,
            "phase": phase,
            "allowed": allowed,
            "allow_over": allow_over,
            "allow_under": allow_under,
            "bias": bias,
            "gate_min_score": gate_min_score,
            "reason": reason,
        }
