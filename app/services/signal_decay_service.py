from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict


class SignalDecayService:
    """
    Controla fatiga / vida útil de señales activas.

    No bloquea.
    No cierra señales.
    Solo agrega lectura:
    - signal_trend
    - signal_decay_status
    - signal_decay_advice
    """

    FRESH_MINUTES = 3
    CONFIRM_MINUTES = 7
    WARNING_MINUTES = 12

    def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        data = deepcopy(signal or {})

        active_minutes = self._active_minutes(data)
        current_score = self._score(data)
        entry_score = self._safe_float(
            data.get("entry_signal_score")
            or data.get("entry_decision_score")
            or data.get("signal_score")
            or data.get("decision_score")
        )

        final_decision = str(data.get("final_decision") or "").upper()
        cooling_detected = bool(data.get("cooling_detected", False))
        under_transition_score = self._safe_float(data.get("under_transition_score"))
        retention_risk = self._safe_float(data.get("retention_risk"))
        score_hold_probability = self._safe_float(data.get("score_hold_probability"))
        live_decay_factor = self._safe_float(data.get("live_decay_factor") or 1.0)

        trend = "STABLE"
        if current_score >= entry_score + 8:
            trend = "UP"
        elif current_score <= entry_score - 8:
            trend = "DOWN"

        status = "FRESH"
        advice = "Señal fresca. Todavía está dentro de ventana útil."

        if active_minutes <= self.FRESH_MINUTES:
            status = "FRESH"
            advice = "Señal fresca. Ventana ideal de entrada."

        elif active_minutes <= self.CONFIRM_MINUTES:
            status = "CONFIRM"
            advice = "Confirmar que la presión siga viva antes de entrar."

        elif active_minutes <= self.WARNING_MINUTES:
            status = "AGING"
            advice = "Señal envejeciendo. Precaución si no hubo gol ni presión nueva."

        else:
            status = "NO_REENTRY"
            advice = "Señal envejecida sin gol. No reentrar salvo nueva presión fuerte."

        if trend == "DOWN" and active_minutes >= 5:
            status = "COOLING"
            advice = "La señal está bajando respecto a su entrada. Riesgo de enfriamiento."

        if cooling_detected or live_decay_factor <= 0.70:
            status = "COOLING"
            advice = "La señal muestra enfriamiento live. No reentrar sin nueva confirmación fuerte."

        if under_transition_score >= 70:
            status = "NO_REENTRY"
            advice = "Transición UNDER activa. No reentrar en señales OVER sin reactivación real."

        if retention_risk >= 70 or score_hold_probability >= 70:
            status = "NO_REENTRY"
            advice = "Alta probabilidad de retención del marcador. No reentrar."

        if final_decision == "WAIT":
            status = "WAIT_CONFIRMATION"
            advice = "La decisión maestra exige esperar confirmación."

        if final_decision == "NO_REENTRY":
            status = "NO_REENTRY"
            advice = "La decisión maestra indica no reentrar."

        if final_decision == "AVOID":
            status = "AVOID"
            advice = "La decisión maestra indica evitar la señal."

        return {
            "active_minutes": active_minutes,
            "signal_trend": trend,
            "signal_decay_status": status,
            "signal_decay_advice": advice,
            "signal_decay_score": max(0.0, min(100.0, current_score)),
        }

    def _score(self, item: Dict[str, Any]) -> float:
        return self._safe_float(
            item.get("decision_score")
            or item.get("revalidation_score")
            or item.get("signal_score")
            or item.get("ai_score")
        )

    def _active_minutes(self, item: Dict[str, Any]) -> int:
        activated_at = item.get("activated_at")
        if not activated_at:
            return 0

        try:
            start = datetime.fromisoformat(str(activated_at))
            now = datetime.now()
            return max(0, int((now - start).total_seconds() // 60))
        except Exception:
            return 0

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
